import asyncio
import time
from collections import deque
from typing import AsyncIterator

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from .config import get_settings


RETRYABLE_STATUS_CODES = {402, 404, 429, 500, 502, 503, 504}
_client: AsyncOpenAI | None = None
_failures: dict[str, deque[float]] = {}
_circuit_until: dict[str, float] = {}


def get_client() -> AsyncOpenAI:
    global _client
    settings = get_settings()
    if _client is None:
        _client = AsyncOpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
        )
    return _client


def circuit_open(model: str) -> bool:
    return _circuit_until.get(model, 0) > time.time()


def record_failure(model: str) -> None:
    now = time.time()
    failures = _failures.setdefault(model, deque())
    failures.append(now)

    while failures and now - failures[0] > 60:
        failures.popleft()

    if len(failures) >= 5:
        _circuit_until[model] = now + 60


def is_retryable_error(error: Exception) -> bool:
    if isinstance(error, (APITimeoutError, APIConnectionError, asyncio.TimeoutError)):
        return True
    if isinstance(error, APIStatusError):
        if error.status_code == 400 and "not a valid model ID" in str(error):
            return True
        return error.status_code in RETRYABLE_STATUS_CODES
    return False


async def mock_stream() -> AsyncIterator[str]:
    text = (
        "Mock response: according to the retrieved document, configuration should be stored "
        "in environment variables and persistent state should live in backing services."
    )
    for word in text.split(" "):
        await asyncio.sleep(0.04)
        yield word + " "


async def stream_openrouter(
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> AsyncIterator[str]:
    settings = get_settings()
    if not settings.openrouter_api_key:
        async for token in mock_stream():
            yield token
        return

    client = get_client()
    stream = await asyncio.wait_for(
        client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=500,
            temperature=0.2,
            stream=True,
        ),
        timeout=15,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


async def stream_with_fallback(
    models: list[str],
    system_prompt: str,
    user_prompt: str,
) -> AsyncIterator[tuple[str, str, bool]]:
    last_error: Exception | None = None

    for index, model in enumerate(models):
        if circuit_open(model):
            continue

        fallback_used = index > 0
        try:
            async for token in stream_openrouter(model, system_prompt, user_prompt):
                yield model, token, fallback_used
            return
        except Exception as error:
            if is_retryable_error(error):
                record_failure(model)
                last_error = error
                continue
            raise

    raise RuntimeError(f"All fallback models failed: {last_error}")
