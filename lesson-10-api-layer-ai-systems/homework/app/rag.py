from functools import lru_cache
from pathlib import Path
from time import time

import numpy as np
import tiktoken
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from .config import Settings, get_settings


CHUNK_TOKENS = 500
CHUNK_OVERLAP = 50
CACHE_TTL_SECONDS = 3600
CACHE_THRESHOLD = 0.92


@lru_cache
def get_embedding_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


@lru_cache
def get_tokenizer() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def chunk_text(text: str, chunk_tokens: int = CHUNK_TOKENS, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    tokenizer = get_tokenizer()
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks = []
    current_parts = []
    current_token_count = 0
    index = 0

    def flush_current() -> None:
        nonlocal current_parts, current_token_count, index
        if not current_parts:
            return

        chunk = "\n\n".join(current_parts).strip()
        chunks.append(
            {
                "chunk_id": f"chunk_{index:04d}",
                "text": chunk,
                "chunk_index": index,
                "token_count": current_token_count,
            }
        )
        index += 1
        current_parts = []
        current_token_count = 0

    for paragraph in paragraphs:
        paragraph_tokens = len(tokenizer.encode(paragraph))

        if paragraph.startswith("## ") and current_parts:
            flush_current()

        if current_parts and current_token_count + paragraph_tokens > chunk_tokens:
            flush_current()

        if paragraph_tokens > chunk_tokens:
            token_ids = tokenizer.encode(paragraph)
            start = 0
            while start < len(token_ids):
                end = min(start + chunk_tokens, len(token_ids))
                chunk_token_ids = token_ids[start:end]
                chunk = tokenizer.decode(chunk_token_ids).strip()
                if chunk:
                    chunks.append(
                        {
                            "chunk_id": f"chunk_{index:04d}",
                            "text": chunk,
                            "chunk_index": index,
                            "token_count": len(chunk_token_ids),
                        }
                    )
                    index += 1
                if end == len(token_ids):
                    break
                start = end - overlap
        else:
            current_parts.append(paragraph)
            current_token_count += paragraph_tokens

    flush_current()

    return chunks


def token_window_chunk_text(
    text: str,
    chunk_tokens: int = CHUNK_TOKENS,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    tokenizer = get_tokenizer()
    token_ids = tokenizer.encode(text)
    chunks = []
    start = 0
    index = 0

    while start < len(token_ids):
        end = min(start + chunk_tokens, len(token_ids))
        chunk_token_ids = token_ids[start:end]
        chunk = tokenizer.decode(chunk_token_ids).strip()

        if chunk:
            chunks.append(
                {
                    "chunk_id": f"chunk_{index:04d}",
                    "text": chunk,
                    "chunk_index": index,
                    "token_count": len(chunk_token_ids),
                }
            )

        if end == len(token_ids):
            break

        start = end - overlap
        index += 1

    return chunks


def embed_texts(
    texts: list[str],
    settings: Settings | None = None,
    show_progress_bar: bool = False,
) -> np.ndarray:
    settings = settings or get_settings()
    model = get_embedding_model(settings.embedding_model)
    embeddings = model.encode(
        texts,
        batch_size=64,
        normalize_embeddings=True,
        show_progress_bar=show_progress_bar,
    )
    return embeddings.astype("float32")


def get_qdrant_client(settings: Settings | None = None) -> QdrantClient:
    settings = settings or get_settings()
    return QdrantClient(url=settings.qdrant_url)


def recreate_collection(client: QdrantClient, collection_name: str, vector_size: int) -> None:
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )


def ensure_collection(client: QdrantClient, collection_name: str, vector_size: int) -> None:
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def upsert_chunks(
    client: QdrantClient,
    collection_name: str,
    chunks: list[dict],
    embeddings: np.ndarray,
) -> None:
    points = []
    for point_id, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        points.append(
            PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload={
                    "chunk_id": chunk["chunk_id"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "token_count": chunk["token_count"],
                },
            )
        )

    client.upsert(collection_name=collection_name, points=points)


def index_source_document(source_path: Path, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    text = read_source(source_path)
    chunks = chunk_text(text)
    embeddings = embed_texts([chunk["text"] for chunk in chunks], settings, show_progress_bar=True)

    client = get_qdrant_client(settings)
    recreate_collection(client, settings.chunks_collection, embeddings.shape[1])
    upsert_chunks(client, settings.chunks_collection, chunks, embeddings)

    return {
        "source_path": str(source_path),
        "collection": settings.chunks_collection,
        "chunks": len(chunks),
        "vector_size": int(embeddings.shape[1]),
    }


def search_chunks(query: str, top_k: int = 3, settings: Settings | None = None) -> list[dict]:
    settings = settings or get_settings()
    query_embedding = embed_texts([query], settings)[0]
    return search_chunks_by_vector(query_embedding, top_k, settings)


def search_chunks_by_vector(
    query_embedding: np.ndarray,
    top_k: int = 3,
    settings: Settings | None = None,
) -> list[dict]:
    settings = settings or get_settings()
    client = get_qdrant_client(settings)

    result = client.query_points(
        collection_name=settings.chunks_collection,
        query=query_embedding.tolist(),
        limit=top_k,
        with_payload=True,
    )

    chunks = []
    for point in result.points:
        payload = point.payload or {}
        chunks.append(
            {
                "chunk_id": payload.get("chunk_id"),
                "text": payload.get("text", ""),
                "score": point.score,
                "token_count": payload.get("token_count"),
            }
        )
    return chunks


def lookup_semantic_cache(
    query_embedding: np.ndarray,
    settings: Settings | None = None,
) -> dict | None:
    settings = settings or get_settings()
    client = get_qdrant_client(settings)
    ensure_collection(client, settings.cache_collection, len(query_embedding))

    result = client.query_points(
        collection_name=settings.cache_collection,
        query=query_embedding.tolist(),
        limit=5,
        with_payload=True,
    )
    if not result.points:
        return {"hit": False, "similarity": None}

    best_similarity = result.points[0].score
    saw_expired = False
    now = time()

    for point in result.points:
        payload = point.payload or {}
        if point.score < CACHE_THRESHOLD:
            continue

        expire_at = payload.get("expire_at")
        if expire_at is not None and expire_at < now:
            saw_expired = True
            continue

        return {
            "hit": True,
            "query": payload.get("query"),
            "response": payload.get("response", ""),
            "model": payload.get("model", "cache"),
            "sources": payload.get("sources", []),
            "similarity": point.score,
        }

    return {
        "hit": False,
        "similarity": best_similarity,
        "expired": saw_expired,
    }


def store_semantic_cache(
    query_embedding: np.ndarray,
    query: str,
    response: str,
    model: str,
    sources: list[str],
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    client = get_qdrant_client(settings)
    ensure_collection(client, settings.cache_collection, len(query_embedding))

    point_id = abs(hash((query, response, int(time())))) % (2**63)
    client.upsert(
        collection_name=settings.cache_collection,
        points=[
            PointStruct(
                id=point_id,
                vector=query_embedding.tolist(),
                payload={
                    "query": query,
                    "response": response,
                    "model": model,
                    "sources": sources,
                    "created_at": time(),
                    "expire_at": time() + CACHE_TTL_SECONDS,
                },
            )
        ],
    )


def clear_semantic_cache(settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    client = get_qdrant_client(settings)

    if client.collection_exists(settings.cache_collection):
        client.delete_collection(settings.cache_collection)

    return {"cleared": True, "collection": settings.cache_collection}


def semantic_cache_status(settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    client = get_qdrant_client(settings)

    if not client.collection_exists(settings.cache_collection):
        return {"collection": settings.cache_collection, "exists": False, "points_count": 0}

    info = client.get_collection(settings.cache_collection)
    return {
        "collection": settings.cache_collection,
        "exists": True,
        "points_count": getattr(info, "points_count", 0) or 0,
    }


def format_context(chunks: list[dict]) -> str:
    parts = []
    for chunk in chunks:
        parts.append(f"<chunk id=\"{chunk['chunk_id']}\">\n{chunk['text']}\n</chunk>")
    return "\n\n".join(parts)
