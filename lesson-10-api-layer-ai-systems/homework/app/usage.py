import aiosqlite
from pathlib import Path
from statistics import quantiles

from .config import get_settings


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS usage_log (
    request_id TEXT PRIMARY KEY,
    api_key TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    latency_ms INTEGER NOT NULL,
    ttft_ms INTEGER NOT NULL,
    cache_hit INTEGER NOT NULL,
    fallback_used INTEGER NOT NULL,
    output_filtered INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


async def init_usage_db() -> None:
    settings = get_settings()
    Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.sqlite_path) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()


async def log_usage(record: dict) -> None:
    settings = get_settings()
    async with aiosqlite.connect(settings.sqlite_path) as db:
        await db.execute(
            """
            INSERT INTO usage_log (
                request_id, api_key, model, input_tokens, output_tokens, cost_usd,
                latency_ms, ttft_ms, cache_hit, fallback_used, output_filtered
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["request_id"],
                record["api_key"],
                record["model"],
                record["input_tokens"],
                record["output_tokens"],
                record["cost_usd"],
                record["latency_ms"],
                record["ttft_ms"],
                int(record["cache_hit"]),
                int(record["fallback_used"]),
                int(record["output_filtered"]),
            ),
        )
        await db.commit()


async def usage_today(api_key: str) -> dict:
    settings = get_settings()
    async with aiosqlite.connect(settings.sqlite_path) as db:
        cursor = await db.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(input_tokens + output_tokens), 0), COALESCE(SUM(cost_usd), 0)
            FROM usage_log
            WHERE api_key = ? AND date(created_at) = date('now')
            """,
            (api_key,),
        )
        requests, tokens, cost = await cursor.fetchone()

    return {"requests": requests, "tokens": tokens, "cost_usd": round(cost, 6)}


async def usage_breakdown(api_key: str) -> dict:
    settings = get_settings()
    async with aiosqlite.connect(settings.sqlite_path) as db:
        model_cursor = await db.execute(
            """
            SELECT model, COUNT(*), COALESCE(SUM(input_tokens + output_tokens), 0), COALESCE(SUM(cost_usd), 0)
            FROM usage_log
            WHERE api_key = ?
            GROUP BY model
            """,
            (api_key,),
        )
        rows = await model_cursor.fetchall()

        stats_cursor = await db.execute(
            """
            SELECT cache_hit, fallback_used, latency_ms
            FROM usage_log
            WHERE api_key = ?
            """,
            (api_key,),
        )
        stats = await stats_cursor.fetchall()

    latencies = [row[2] for row in stats]
    p95 = quantiles(latencies, n=20)[18] if len(latencies) >= 20 else (max(latencies) if latencies else 0)

    return {
        "by_model": [
            {
                "model": model,
                "requests": requests,
                "tokens": tokens,
                "cost_usd": round(cost, 6),
            }
            for model, requests, tokens, cost in rows
        ],
        "cache_hit_rate": round(sum(row[0] for row in stats) / len(stats), 4) if stats else 0.0,
        "fallback_rate": round(sum(row[1] for row in stats) / len(stats), 4) if stats else 0.0,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "p95_latency_ms": round(p95, 2),
    }

