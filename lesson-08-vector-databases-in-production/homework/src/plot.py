import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _ok_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["status"] == "ok"].copy()


def plot_pareto(df: pd.DataFrame, output_dir: Path) -> None:
    ok = _ok_rows(df)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(ok["latency_p95_ms"], ok["recall_at_10"], s=90)
    for _, row in ok.iterrows():
        ax.annotate(row["db"], (row["latency_p95_ms"], row["recall_at_10"]), xytext=(6, 6), textcoords="offset points")
    ax.set_title("Pareto frontier: Recall@10 vs p95 latency")
    ax.set_xlabel("Latency p95, ms (lower is better)")
    ax.set_ylabel("Recall@10 (higher is better)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "pareto_frontier.png", dpi=160)
    plt.close(fig)


def plot_latency(df: pd.DataFrame, output_dir: Path) -> None:
    ok = _ok_rows(df).set_index("db")
    fig, ax = plt.subplots(figsize=(10, 6))
    ok[["latency_p50_ms", "latency_p95_ms", "latency_p99_ms"]].plot(kind="bar", ax=ax)
    ax.set_title("Query latency percentiles")
    ax.set_xlabel("Vector DB")
    ax.set_ylabel("Latency, ms")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "latency_distribution.png", dpi=160)
    plt.close(fig)


def plot_disk_size(df: pd.DataFrame, output_dir: Path) -> None:
    ok = _ok_rows(df).set_index("db")
    fig, ax = plt.subplots(figsize=(9, 6))
    ok["disk_mb"].plot(kind="bar", ax=ax)
    ax.set_title("Index disk size")
    ax.set_xlabel("Vector DB")
    ax.set_ylabel("Disk size, MB")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "disk_size_chart.png", dpi=160)
    plt.close(fig)


def plot_results_table(df: pd.DataFrame, output_dir: Path) -> None:
    columns = [
        "db",
        "status",
        "recall_at_10",
        "mrr_at_10",
        "latency_p50_ms",
        "latency_p95_ms",
        "latency_p99_ms",
        "disk_mb",
        "index_time_sec",
    ]
    display_df = df[columns]
    fig, ax = plt.subplots(figsize=(14, max(3, len(display_df) * 0.55 + 1)))
    ax.axis("off")
    table = ax.table(
        cellText=display_df.fillna("").values,
        colLabels=display_df.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.35)
    fig.tight_layout()
    fig.savefig(output_dir / "results_table.png", dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate benchmark plots.")
    parser.add_argument("--input", type=Path, default=Path("results/results.csv"))
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.input)
    plot_pareto(df, args.output)
    plot_latency(df, args.output)
    plot_disk_size(df, args.output)
    plot_results_table(df, args.output)
    print(f"Wrote plots to {args.output}")


if __name__ == "__main__":
    main()
