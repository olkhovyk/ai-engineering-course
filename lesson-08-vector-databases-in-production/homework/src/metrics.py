from typing import Iterable, List, Sequence, Set

import numpy as np


def recall_at_k(retrieved: Sequence[str], relevant: Set[str], k: int = 10) -> float:
    if not relevant:
        return 0.0
    hits = len(set(retrieved[:k]) & relevant)
    return hits / min(k, len(relevant))


def mrr_at_k(retrieved: Sequence[str], relevant: Set[str], k: int = 10) -> float:
    for rank, doc_id in enumerate(retrieved[:k], start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def latency_percentiles(latencies_ms: Iterable[float]) -> dict[str, float]:
    values = np.array(list(latencies_ms), dtype=np.float64)
    if values.size == 0:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
    return {
        "p50": round(float(np.percentile(values, 50)), 3),
        "p95": round(float(np.percentile(values, 95)), 3),
        "p99": round(float(np.percentile(values, 99)), 3),
    }


def mean(values: List[float]) -> float:
    return float(np.mean(values)) if values else 0.0
