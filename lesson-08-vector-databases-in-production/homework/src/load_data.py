import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable

from datasets import Dataset, DatasetDict, load_dataset
from tqdm import tqdm


DATASET_NAME = "BeIR/quora"
QRELS_DATASET_NAME = "BeIR/quora-qrels"


def _first_split(dataset: Dataset | DatasetDict) -> Dataset:
    if isinstance(dataset, DatasetDict):
        if "test" in dataset:
            return dataset["test"]
        return dataset[next(iter(dataset.keys()))]
    return dataset


def _load_config(config: str) -> Dataset:
    return _first_split(load_dataset(DATASET_NAME, config))


def _load_qrels() -> Dataset:
    return _first_split(load_dataset(QRELS_DATASET_NAME))


def _pick(row: dict[str, Any], names: Iterable[str], default: str = "") -> str:
    for name in names:
        if name in row and row[name] is not None:
            return str(row[name])
    return default


def write_jsonl(path: Path, rows: Iterable[dict[str, str]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def normalize_corpus(dataset: Dataset, limit: int | None = None) -> Iterable[dict[str, str]]:
    iterable = dataset if limit is None else dataset.select(range(min(limit, len(dataset))))
    for row in tqdm(iterable, desc="corpus"):
        doc_id = _pick(row, ["_id", "id", "doc_id", "corpus-id"])
        title = _pick(row, ["title"])
        text = _pick(row, ["text"])
        full_text = f"{title}\n{text}".strip() if title else text
        yield {"id": doc_id, "text": full_text}


def normalize_queries(dataset: Dataset, limit: int | None = None) -> Iterable[dict[str, str]]:
    iterable = dataset if limit is None else dataset.select(range(min(limit, len(dataset))))
    for row in tqdm(iterable, desc="queries"):
        query_id = _pick(row, ["_id", "id", "query_id", "query-id"])
        text = _pick(row, ["text", "query"])
        yield {"id": query_id, "text": text}


def write_qrels(dataset: Dataset, path: Path, limit_queries: int | None = None) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    seen_queries: set[str] = set()
    count = 0
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["query_id", "doc_id", "score"])
        for row in tqdm(dataset, desc="qrels"):
            query_id = _pick(row, ["query-id", "query_id", "qid"])
            doc_id = _pick(row, ["corpus-id", "corpus_id", "doc_id"])
            score = _pick(row, ["score"], "1")
            if limit_queries is not None and query_id not in seen_queries:
                if len(seen_queries) >= limit_queries:
                    continue
                seen_queries.add(query_id)
            writer.writerow([query_id, doc_id, score])
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and normalize BeIR/quora.")
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    parser.add_argument("--limit-docs", type=int, default=None)
    parser.add_argument("--limit-queries", type=int, default=None)
    args = parser.parse_args()

    output_dir = args.output_dir
    corpus = _load_config("corpus")
    queries = _load_config("queries")
    qrels = _load_qrels()

    corpus_count = write_jsonl(
        output_dir / "corpus.jsonl",
        normalize_corpus(corpus, args.limit_docs),
    )
    query_count = write_jsonl(
        output_dir / "queries.jsonl",
        normalize_queries(queries, args.limit_queries),
    )
    qrels_count = write_qrels(qrels, output_dir / "qrels.tsv", args.limit_queries)

    print(f"Wrote {corpus_count} corpus docs")
    print(f"Wrote {query_count} queries")
    print(f"Wrote {qrels_count} qrels")


if __name__ == "__main__":
    main()
