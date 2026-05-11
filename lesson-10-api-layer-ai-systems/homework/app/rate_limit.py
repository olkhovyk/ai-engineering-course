import time

import redis.asyncio as redis
from fastapi import HTTPException

from .config import get_settings


_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


async def check_rate_limit(api_key: str, tokens_per_minute: int, estimated_tokens: int) -> None:
    client = get_redis()
    bucket_key = f"rate:{api_key}:tokens"
    updated_key = f"rate:{api_key}:updated"
    now = time.time()

    current_raw = await client.get(bucket_key)
    updated_raw = await client.get(updated_key)

    current = float(current_raw) if current_raw is not None else float(tokens_per_minute)
    updated = float(updated_raw) if updated_raw is not None else now

    refill_per_second = tokens_per_minute / 60.0
    current = min(tokens_per_minute, current + (now - updated) * refill_per_second)

    if current < estimated_tokens:
        missing = estimated_tokens - current
        retry_after = max(1, int(missing / refill_per_second))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )

    current -= estimated_tokens
    await client.set(bucket_key, current, ex=120)
    await client.set(updated_key, now, ex=120)


async def refund_tokens(api_key: str, tokens_per_minute: int, tokens: int) -> None:
    if tokens <= 0:
        return

    client = get_redis()
    bucket_key = f"rate:{api_key}:tokens"
    updated_key = f"rate:{api_key}:updated"
    now = time.time()

    current_raw = await client.get(bucket_key)
    current = float(current_raw) if current_raw is not None else float(tokens_per_minute)
    current = min(tokens_per_minute, current + tokens)

    await client.set(bucket_key, current, ex=120)
    await client.set(updated_key, now, ex=120)
