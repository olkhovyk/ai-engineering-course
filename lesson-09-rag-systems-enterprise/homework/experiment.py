import argparse
from pathlib import Path
from time import perf_counter

import faiss
import numpy as np
import pandas as pd
from data_loader import build_subset, load_cache
from metrics import evaluate
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


CACHE_PATH = Path(__file__).parent / "cache" / "corpus.json"
RESULTS_PATH = Path(__file__).parent / "results" / "results.csv"
MODEL_NAME = "BAAI/bge-small-en-v1.5"
BATCH_SIZE = 256
DEVICE = "cuda"
TOP_K = 10
RRF_K = 60
HYBRID_CANDIDATES = 100
DENSE_RRF_WEIGHT = 0.8
BM25_RRF_WEIGHT = 0.2


def tokenize(text: str) -> list[str]:
    return text.lower().split()


def reciprocal_rank_fusion(dense_ids: list[str], bm25_ids: list[str], top_k: int) -> list[str]:
    scores: dict[str, float] = {}

    for rank, doc_id in enumerate(dense_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + DENSE_RRF_WEIGHT / (RRF_K + rank)

    for rank, doc_id in enumerate(bm25_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + BM25_RRF_WEIGHT / (RRF_K + rank)

    return [
        doc_id
        for doc_id, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
    ]


def run_dense_retrieval(
    model: SentenceTransformer,
    pool: list[dict],
    eval_set: list[dict],
    size: int,
    retriever: str,
) -> dict:
    subset = build_subset(pool, eval_set, size=size)

    doc_texts = [doc["text"] for doc in subset]
    query_texts = [query["query"] for query in eval_set]

    print(f"\n=== {retriever}: {size} docs ===")
    print("Embedding documents...")
    started_at = perf_counter()
    doc_embeddings = model.encode(
        doc_texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    elapsed_sec = perf_counter() - started_at
    throughput = len(doc_texts) / elapsed_sec

    print("Embedding queries...")
    query_embeddings = model.encode(
        query_texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    doc_ids = [doc["id"] for doc in subset]
    retrieved_per_query = []
    latencies_ms = []

    if retriever == "dense_bruteforce":
        print("Running brute-force retrieval...")
        for query_embedding in query_embeddings:
            started_at = perf_counter()
            scores = query_embedding @ doc_embeddings.T
            top_indices = np.argsort(scores)[-TOP_K:][::-1]
            latencies_ms.append((perf_counter() - started_at) * 1000)
            retrieved_per_query.append([doc_ids[index] for index in top_indices])
    elif retriever == "hybrid_bm25_dense_rrf":
        print("Building BM25 index...")
        tokenized_docs = [tokenize(text) for text in doc_texts]
        bm25 = BM25Okapi(tokenized_docs)

        print("Running hybrid BM25 + dense + RRF retrieval...")
        for query, query_embedding in zip(eval_set, query_embeddings):
            started_at = perf_counter()

            dense_scores = query_embedding @ doc_embeddings.T
            dense_indices = np.argsort(dense_scores)[-HYBRID_CANDIDATES:][::-1]
            dense_ids = [doc_ids[index] for index in dense_indices]

            bm25_scores = bm25.get_scores(tokenize(query["query"]))
            bm25_indices = np.argsort(bm25_scores)[-HYBRID_CANDIDATES:][::-1]
            bm25_ids = [doc_ids[index] for index in bm25_indices]

            retrieved = reciprocal_rank_fusion(dense_ids, bm25_ids, TOP_K)
            latencies_ms.append((perf_counter() - started_at) * 1000)
            retrieved_per_query.append(retrieved)
    elif retriever == "faiss_hnsw":
        print("Building FAISS HNSW index...")
        index = faiss.IndexHNSWFlat(doc_embeddings.shape[1], 32, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = 100
        index.hnsw.efSearch = 64
        index.add(doc_embeddings.astype("float32"))

        print("Running FAISS HNSW retrieval...")
        for query_embedding in query_embeddings.astype("float32"):
            started_at = perf_counter()
            _, top_indices = index.search(query_embedding.reshape(1, -1), TOP_K)
            latencies_ms.append((perf_counter() - started_at) * 1000)
            retrieved_per_query.append([doc_ids[index] for index in top_indices[0]])
    else:
        raise ValueError(f"Unknown retriever: {retriever}")

    metrics = evaluate(eval_set, retrieved_per_query, ks=(1, 10))
    latency_p50 = float(np.percentile(latencies_ms, 50))
    latency_p95 = float(np.percentile(latencies_ms, 95))
    latency_p99 = float(np.percentile(latencies_ms, 99))

    row = {
        "retriever": retriever,
        "num_docs": size,
        "num_queries": len(eval_set),
        "embedding_time_sec": round(elapsed_sec, 3),
        "embedding_throughput_docs_sec": round(throughput, 2),
        "recall_at_1": metrics["recall@1"],
        "recall_at_10": metrics["recall@10"],
        "mrr_at_10": metrics["mrr@10"],
        "latency_p50_ms": round(latency_p50, 3),
        "latency_p95_ms": round(latency_p95, 3),
        "latency_p99_ms": round(latency_p99, 3),
    }

    print(f"  Recall@1: {metrics['recall@1']}")
    print(f"  Recall@10: {metrics['recall@10']}")
    print(f"  MRR@10: {metrics['mrr@10']}")
    print(f"  Latency p50: {latency_p50:.3f} ms")
    print(f"  Latency p95: {latency_p95:.3f} ms")
    print(f"  Latency p99: {latency_p99:.3f} ms")

    return row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run dense retrieval scaling experiment.")
    parser.add_argument(
        "--retriever",
        choices=["dense_bruteforce", "faiss_hnsw", "hybrid_bm25_dense_rrf"],
        default="dense_bruteforce",
        help="Retriever implementation to benchmark.",
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[1_000, 10_000],
        help="Corpus subset sizes to benchmark, for example: --sizes 1000 10000 100000",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=RESULTS_PATH,
        help="Path to CSV results file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pool, eval_set = load_cache(CACHE_PATH)

    print(f"Loaded corpus pool: {len(pool)} docs")
    print(f"Loaded eval set: {len(eval_set)} queries")
    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME, device=DEVICE)

    rows = []
    for size in args.sizes:
        rows.append(run_dense_retrieval(model, pool, eval_set, size, args.retriever))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)
    print(f"\nSaved results to {args.output}")


if __name__ == "__main__":
    main()
