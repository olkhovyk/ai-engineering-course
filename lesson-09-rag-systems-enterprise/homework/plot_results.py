import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


DEFAULT_INPUT = Path(__file__).parent / "results" / "baseline_all.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "results"


def save_quality_chart(df: pd.DataFrame, output_dir: Path) -> None:
    plt.figure(figsize=(9, 5))
    plt.plot(df["num_docs"], df["recall_at_1"], marker="o", label="Recall@1")
    plt.plot(df["num_docs"], df["recall_at_10"], marker="o", label="Recall@10")
    plt.plot(df["num_docs"], df["mrr_at_10"], marker="o", label="MRR@10")
    plt.xscale("log")
    plt.xlabel("Corpus size, docs")
    plt.ylabel("Score")
    plt.title("Retrieval quality while corpus grows")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "baseline_quality.png", dpi=160)
    plt.close()


def save_latency_chart(df: pd.DataFrame, output_dir: Path) -> None:
    plt.figure(figsize=(9, 5))
    plt.plot(df["num_docs"], df["latency_p50_ms"], marker="o", label="p50")
    plt.plot(df["num_docs"], df["latency_p95_ms"], marker="o", label="p95")
    plt.plot(df["num_docs"], df["latency_p99_ms"], marker="o", label="p99")
    plt.xscale("log")
    plt.xlabel("Corpus size, docs")
    plt.ylabel("Latency, ms")
    plt.title("Brute-force search latency while corpus grows")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "baseline_latency.png", dpi=160)
    plt.close()


def save_throughput_chart(df: pd.DataFrame, output_dir: Path) -> None:
    plt.figure(figsize=(9, 5))
    plt.plot(df["num_docs"], df["embedding_throughput_docs_sec"], marker="o")
    plt.xscale("log")
    plt.xlabel("Corpus size, docs")
    plt.ylabel("Docs/sec")
    plt.title("Embedding throughput")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "baseline_embedding_throughput.png", dpi=160)
    plt.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot retrieval experiment results.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--inputs", nargs="+", type=Path, help="Multiple CSV files to compare.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input).sort_values("num_docs")

    save_quality_chart(df, args.output_dir)
    save_latency_chart(df, args.output_dir)
    save_throughput_chart(df, args.output_dir)

    print(f"Saved charts to {args.output_dir}")

    if args.inputs:
        compare_df = pd.concat(
            [pd.read_csv(path).assign(source=path.stem) for path in args.inputs],
            ignore_index=True,
        ).sort_values(["retriever", "num_docs"])

        save_comparison_charts(compare_df, args.output_dir)
        print(f"Saved comparison charts to {args.output_dir}")


def save_comparison_charts(df: pd.DataFrame, output_dir: Path) -> None:
    metrics = [
        ("recall_at_1", "Recall@1", "comparison_recall_at_1.png"),
        ("recall_at_10", "Recall@10", "comparison_recall_at_10.png"),
        ("mrr_at_10", "MRR@10", "comparison_mrr_at_10.png"),
        ("latency_p50_ms", "Latency p50, ms", "comparison_latency_p50.png"),
        ("latency_p95_ms", "Latency p95, ms", "comparison_latency_p95.png"),
    ]

    for column, label, filename in metrics:
        plt.figure(figsize=(9, 5))
        for retriever, group in df.groupby("retriever"):
            group = group.sort_values("num_docs")
            plt.plot(group["num_docs"], group[column], marker="o", label=retriever)

        plt.xscale("log")
        plt.xlabel("Corpus size, docs")
        plt.ylabel(label)
        plt.title(f"{label} comparison")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / filename, dpi=160)
        plt.close()


if __name__ == "__main__":
    main()
