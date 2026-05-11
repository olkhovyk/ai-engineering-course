import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import get_api_keys, get_settings
from .llm import stream_with_fallback
from .observability import init_phoenix, maybe_span, set_attribute, set_output, tracing_initialized
from .pricing import estimate_cost
from .rag import (
    clear_semantic_cache,
    embed_texts,
    format_context,
    index_source_document,
    lookup_semantic_cache,
    search_chunks_by_vector,
    semantic_cache_status,
    store_semantic_cache,
)
from .rate_limit import check_rate_limit, get_redis, refund_tokens
from .security import (
    get_api_key_metadata,
    log_suspicious_output,
    output_looks_suspicious,
    validate_user_input,
)
from .usage import init_usage_db, log_usage, usage_breakdown, usage_today


settings = get_settings()
semaphore = asyncio.Semaphore(20)
active_streams = 0
aborted_streams = 0


class ChatRequest(BaseModel):
    message: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_phoenix(settings)
    await init_usage_db()
    yield


app = FastAPI(title="Lesson 10 RAG API", lifespan=lifespan)
ROOT_DIR = Path(__file__).parent.parent

app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")


def sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def count_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def build_prompts(message: str, chunks: list[dict]) -> tuple[str, str]:
    context = format_context(chunks)
    system_prompt = (
        "You are a careful RAG assistant. Answer only from the provided context. "
        "If the context is not enough, say that the document does not contain enough information."
    )
    user_prompt = f"""
<retrieved_context>
{context}
</retrieved_context>

<user_query>
{message}
</user_query>
"""
    return system_prompt, user_prompt


def text_chunks(text: str, size: int = 24):
    for start in range(0, len(text), size):
        yield text[start:start + size]


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(ROOT_DIR / "static" / "index.html")


@app.get("/health")
async def health() -> dict:
    redis_ok = False
    try:
        redis_ok = bool(await get_redis().ping())
    except Exception:
        redis_ok = False

    return {
        "status": "ok",
        "active_streams": active_streams,
        "aborted_streams": aborted_streams,
        "concurrency_limit": 20,
        "redis_ok": redis_ok,
        "qdrant_url": settings.qdrant_url,
    }


@app.get("/usage/today")
async def get_usage_today(auth: dict = Depends(get_api_key_metadata)) -> dict:
    return await usage_today(auth["api_key"])


@app.get("/usage/breakdown")
async def get_usage_breakdown(auth: dict = Depends(get_api_key_metadata)) -> dict:
    return await usage_breakdown(auth["api_key"])


@app.get("/debug/config")
async def debug_config(auth: dict = Depends(get_api_key_metadata)) -> dict:
    api_keys = get_api_keys()
    return {
        "force_bad_primary": settings.force_bad_primary,
        "tier": auth["name"],
        "models": api_keys[auth["api_key"]]["models"],
        "phoenix_enabled": settings.phoenix_enabled,
        "phoenix_initialized": tracing_initialized(),
        "phoenix_collector_endpoint": settings.phoenix_collector_endpoint,
        "phoenix_project_name": settings.phoenix_project_name,
    }


@app.post("/debug/trace-test")
async def debug_trace_test(auth: dict = Depends(get_api_key_metadata)) -> dict:
    with maybe_span(
        settings,
        "manual-trace-test",
        "tool",
        input_value={"message": "manual phoenix trace test"},
        tier=auth["name"],
    ) as span:
        set_output(span, {"ok": True})

    return {"ok": True, "phoenix_initialized": tracing_initialized()}


@app.post("/index/rebuild")
async def rebuild_index(auth: dict = Depends(get_api_key_metadata)) -> dict:
    source_path = Path(__file__).parent.parent / "data" / "source.md"
    return await asyncio.to_thread(index_source_document, source_path, settings)


@app.post("/cache/clear")
async def clear_cache(auth: dict = Depends(get_api_key_metadata)) -> dict:
    return await asyncio.to_thread(clear_semantic_cache, settings)


@app.get("/cache/status")
async def cache_status(auth: dict = Depends(get_api_key_metadata)) -> dict:
    return await asyncio.to_thread(semantic_cache_status, settings)


@app.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    request: Request,
    auth: dict = Depends(get_api_key_metadata),
) -> StreamingResponse:
    validate_user_input(req.message)

    estimated_tokens = count_tokens(req.message) + 600
    await check_rate_limit(auth["api_key"], auth["tokens_per_minute"], estimated_tokens)

    async def event_stream():
        global active_streams, aborted_streams

        request_id = str(uuid4())
        active_streams += 1
        started_at = time.monotonic()
        first_token_at: float | None = None
        full_response = ""
        output_tokens = 0
        model_used = "cache"
        fallback_used = False
        cache_hit = False
        cache_similarity: float | None = None
        cache_expired = False
        sources: list[str] = []

        try:
            with maybe_span(
                settings,
                "chat-stream",
                "chain",
                input_value=req.message,
                api_key=auth["api_key"],
                tier=auth["name"],
            ) as root_span:
                with maybe_span(settings, "auth", "guardrail", input_value={"tier": auth["name"]}) as auth_span:
                    set_output(auth_span, {"ok": True})

                with maybe_span(
                    settings,
                    "rate-limit",
                    "tool",
                    input_value={"estimated_tokens": estimated_tokens},
                ) as rate_span:
                    set_output(rate_span, {"reserved_tokens": estimated_tokens})

                with maybe_span(
                    settings,
                    "embed-query",
                    "embedding",
                    input_value=req.message,
                    model=settings.embedding_model,
                ) as embed_span:
                    query_embedding = await asyncio.to_thread(embed_texts, [req.message], settings)
                    query_embedding = query_embedding[0]
                    set_output(embed_span, {"vector_size": len(query_embedding)})

                with maybe_span(settings, "cache-check", "tool", input_value={"threshold": 0.92}) as cache_span:
                    cached = await asyncio.to_thread(lookup_semantic_cache, query_embedding, settings)
                    cache_similarity = cached.get("similarity") if cached else None
                    cache_expired = bool(cached and cached.get("expired"))
                    cache_hit = bool(cached and cached.get("hit"))
                    set_output(
                        cache_span,
                        {
                            "cache_hit": cache_hit,
                            "similarity": cache_similarity,
                            "expired": cache_expired,
                        },
                    )

                if cache_hit:
                    model_used = cached["model"]
                    sources = cached["sources"]
                    with maybe_span(settings, "stream-cache-response", "chain", input_value={"sources": sources}) as cache_stream_span:
                        for token in text_chunks(cached["response"]):
                            if await request.is_disconnected():
                                aborted_streams += 1
                                await refund_tokens(auth["api_key"], auth["tokens_per_minute"], estimated_tokens)
                                return
                            full_response += token
                            output_tokens += count_tokens(token)
                            if first_token_at is None:
                                first_token_at = time.monotonic()
                            yield sse_event({"type": "token", "content": token})
                            await asyncio.sleep(0.01)
                        set_output(cache_stream_span, full_response)
                else:
                    with maybe_span(settings, "vector-search", "retriever", input_value=req.message) as search_span:
                        chunks = await asyncio.to_thread(search_chunks_by_vector, query_embedding, 3, settings)
                        sources = [chunk["chunk_id"] for chunk in chunks]
                        set_output(
                            search_span,
                            {
                                "sources": sources,
                                "scores": [chunk["score"] for chunk in chunks],
                            },
                        )

                    system_prompt, user_prompt = build_prompts(req.message, chunks)

                    with maybe_span(
                        settings,
                        "llm-call",
                        "generation",
                        input_value={"system": system_prompt, "user": user_prompt},
                    ) as llm_span:
                        async with semaphore:
                            async for model, token, used_fallback in stream_with_fallback(
                                auth["models"],
                                system_prompt,
                                user_prompt,
                            ):
                                if await request.is_disconnected():
                                    aborted_streams += 1
                                    await refund_tokens(auth["api_key"], auth["tokens_per_minute"], estimated_tokens)
                                    return

                                model_used = model
                                fallback_used = fallback_used or used_fallback
                                full_response += token
                                output_tokens += 1
                                if first_token_at is None:
                                    first_token_at = time.monotonic()
                                yield sse_event({"type": "token", "content": token})

                        set_attribute(llm_span, "model", model_used)
                        set_attribute(llm_span, "fallback_used", fallback_used)
                        set_attribute(llm_span, "llm.input_tokens", count_tokens(req.message))
                        set_attribute(llm_span, "llm.output_tokens", output_tokens)
                        set_output(llm_span, full_response)

                    with maybe_span(settings, "cache-store", "tool", input_value={"sources": sources}) as store_span:
                        await asyncio.to_thread(
                            store_semantic_cache,
                            query_embedding,
                            req.message,
                            full_response,
                            model_used,
                            sources,
                            settings,
                        )
                        set_output(store_span, {"stored": True})

                latency_ms = round((time.monotonic() - started_at) * 1000)
                ttft_ms = round(((first_token_at or time.monotonic()) - started_at) * 1000)
                input_tokens = count_tokens(req.message)
                actual_tokens = input_tokens + output_tokens
                await refund_tokens(
                    auth["api_key"],
                    auth["tokens_per_minute"],
                    estimated_tokens - actual_tokens,
                )
                cost_usd = 0.0 if cache_hit else estimate_cost(model_used, input_tokens, output_tokens)
                output_filtered = output_looks_suspicious(full_response)

                if output_filtered:
                    log_suspicious_output(request_id, full_response)

                with maybe_span(settings, "usage-log", "tool") as usage_span:
                    await log_usage(
                        {
                            "request_id": request_id,
                            "api_key": auth["api_key"],
                            "model": model_used,
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "cost_usd": cost_usd,
                            "latency_ms": latency_ms,
                            "ttft_ms": ttft_ms,
                            "cache_hit": cache_hit,
                            "cache_similarity": cache_similarity,
                            "cache_expired": cache_expired,
                            "fallback_used": fallback_used,
                            "output_filtered": output_filtered,
                        }
                    )
                    set_output(usage_span, {"logged": True, "cost_usd": cost_usd})

                done_event = {
                    "type": "done",
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    },
                    "cost_usd": cost_usd,
                    "cache_hit": cache_hit,
                    "cache_similarity": cache_similarity,
                    "cache_expired": cache_expired,
                    "fallback_used": fallback_used,
                    "model": model_used,
                    "sources": sources,
                    "latency_ms": latency_ms,
                    "ttft_ms": ttft_ms,
                }
                set_attribute(root_span, "model", model_used)
                set_attribute(root_span, "cache_hit", cache_hit)
                set_attribute(root_span, "fallback_used", fallback_used)
                set_output(root_span, {"answer": full_response, "done": done_event})

                yield sse_event(done_event)
        except Exception as error:
            await refund_tokens(auth["api_key"], auth["tokens_per_minute"], estimated_tokens)
            yield sse_event(
                {
                    "type": "error",
                    "message": str(error),
                }
            )
        finally:
            active_streams -= 1

    return StreamingResponse(event_stream(), media_type="text/event-stream")
