import argparse
import csv
import os
import time
import traceback
from pathlib import Path
from typing import Dict, List, Set

import numpy as np

from benchmarks.chroma_db import ChromaDB
from benchmarks.faiss_flat import FaissFlatDB
from benchmarks.faiss_hnsw import FaissHnswDB
from benchmarks.pgvector_db import PgVectorDB
from benchmarks.qdrant_db import QdrantDB
from metrics import latency_percentiles, mean, mrr_at_k, recall_at_k


WARMUP_QUERIES = 50
NUM_REPEATS = 3
RESULT_FIELDS = [
    "db",
    "status",
    "error",
    "index_time_sec",
    "disk_mb",
    "latency_p50_ms",
    "latency_p95_ms",
    "latency_p99_ms",
    "recall_at_10",
    "mrr_at_10",
    "num_docs",
    "num_queries",
]


def read_ids(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_qrels(path: Path) -> Dict[str, Set[str]]:
    qrels: Dict[str, Set[str]] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            score = float(row.get("score", 1) or 1)
            if score <= 0:
                continue
            qrels.setdefault(row["query_id"], set()).add(row["doc_id"])
    return qrels


def select_queries_with_qrels(
    query_vectors: np.ndarray,
    query_ids: list[str],
    qrels: Dict[str, Set[str]],
    max_queries: int | None,
) -> tuple[np.ndarray, list[str]]:
    indexes = [i for i, query_id in enumerate(query_ids) if query_id in qrels]
    if max_queries is not None:
        indexes = indexes[:max_queries]
    return query_vectors[indexes], [query_ids[i] for i in indexes]


def benchmark_db(
    db,
    doc_vectors: np.ndarray,
    doc_ids: List[str],
    query_vectors: np.ndarray,
    query_ids: List[str],
    qrels: Dict[str, Set[str]],
    top_k: int = 10,
) -> dict:
    t0 = time.perf_counter()
    db.index(doc_vectors, ids=doc_ids)
    index_time = time.perf_counter() - t0

    for q_vec in query_vectors[: min(WARMUP_QUERIES, len(query_vectors))]:
        db.search(q_vec, top_k=top_k)

    all_latencies: List[List[float]] = []
    recalls: List[float] = []
    mrrs: List[float] = []

    for repeat in range(NUM_REPEATS):
        latencies = []
        for q_vec, q_id in zip(query_vectors, query_ids):
            t0 = time.perf_counter()
            results = db.search(q_vec, top_k=top_k)
            latencies.append((time.perf_counter() - t0) * 1000)

            if repeat == 0:
                retrieved_ids = [doc_id for doc_id, _score in results]
                relevant = qrels.get(q_id, set())
                recalls.append(recall_at_k(retrieved_ids, relevant, top_k))
                mrrs.append(mrr_at_k(retrieved_ids, relevant, top_k))
        all_latencies.append(latencies)

    latencies_arr = np.median(np.array(all_latencies), axis=0)
    latency = latency_percentiles(latencies_arr)

    return {
        "db": db.name,
        "status": "ok",
        "error": "",
        "index_time_sec": round(index_time, 2),
        "disk_mb": round(db.disk_size_mb(), 1),
        "latency_p50_ms": latency["p50"],
        "latency_p95_ms": latency["p95"],
        "latency_p99_ms": latency["p99"],
        "recall_at_10": round(mean(recalls), 4),
        "mrr_at_10": round(mean(mrrs), 4),
        "num_docs": len(doc_vectors),
        "num_queries": len(query_vectors),
    }


def build_databases(names: list[str]):
    all_dbs = {
        "faiss_flat": lambda: FaissFlatDB(),
        "faiss_hnsw": lambda: FaissHnswDB(),
        "qdrant": lambda: QdrantDB(url=os.getenv("QDRANT_URL", "http://localhost:6333")),
        "chroma": lambda: ChromaDB(),
        "pgvector": lambda: PgVectorDB(
            dsn=os.getenv("POSTGRES_DSN", "postgresql://bench:bench@localhost:5432/bench")
        ),
    }
    return [all_dbs[name]() for name in names]


def write_results(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run vector DB benchmarks.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("results/results.csv"))
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--max-docs", type=int, default=None)
    parser.add_argument("--max-queries", type=int, default=None)
    parser.add_argument(
        "--dbs",
        nargs="+",
        default=["faiss_flat", "faiss_hnsw", "qdrant", "chroma", "pgvector"],
        choices=["faiss_flat", "faiss_hnsw", "qdrant", "chroma", "pgvector"],
    )
    args = parser.parse_args()

    doc_vectors = np.load(args.data_dir / "corpus_embeddings.npy").astype("float32")
    query_vectors = np.load(args.data_dir / "query_embeddings.npy").astype("float32")
    doc_ids = read_ids(args.data_dir / "corpus_embeddings.ids.txt")
    query_ids = read_ids(args.data_dir / "query_embeddings.ids.txt")
    qrels = load_qrels(args.data_dir / "qrels.tsv")

    if args.max_docs is not None:
        doc_vectors = doc_vectors[: args.max_docs]
        doc_ids = doc_ids[: args.max_docs]
        allowed_docs = set(doc_ids)
        qrels = {qid: docs & allowed_docs for qid, docs in qrels.items()}

    query_vectors, query_ids = select_queries_with_qrels(
        query_vectors,
        query_ids,
        qrels,
        args.max_queries,
    )

    rows = []
    for db in build_databases(args.dbs):
        print(f"\n=== Benchmarking {db.name} ===")
        try:
            row = benchmark_db(
                db=db,
                doc_vectors=doc_vectors,
                doc_ids=doc_ids,
                query_vectors=query_vectors,
                query_ids=query_ids,
                qrels=qrels,
                top_k=args.top_k,
            )
            print(row)
        except Exception as exc:
            row = {
                "db": db.name,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "index_time_sec": "",
                "disk_mb": "",
                "latency_p50_ms": "",
                "latency_p95_ms": "",
                "latency_p99_ms": "",
                "recall_at_10": "",
                "mrr_at_10": "",
                "num_docs": len(doc_vectors),
                "num_queries": len(query_vectors),
            }
            print(row["error"])
            traceback.print_exc()
        finally:
            db.cleanup()
        rows.append(row)
        write_results(args.output, rows)

    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
