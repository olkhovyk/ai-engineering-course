"""Print a compact comparison table for base vs fine-tuned metrics."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE_PATH = ROOT / "results" / "base_8b_metrics.json"
FT_PATH = ROOT / "results" / "finetuned_8b_metrics.json"


FIELDS = [
    "customer_name",
    "product",
    "issue_category",
    "urgency",
    "summary",
]


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing metrics file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def pct(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value) * 100:.1f}%"


def number(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.2f}"


def print_row(metric: str, base: str, finetuned: str) -> None:
    print(f"| {metric:<24} | {base:<12} | {finetuned:<12} |")


def main() -> None:
    base = load_json(BASE_PATH)
    ft = load_json(FT_PATH)

    print("| Metric                   | Base 8B      | Fine-tuned 8B |")
    print("|--------------------------|--------------|---------------|")
    print_row("json_valid_rate", pct(base.get("json_valid_rate")), pct(ft.get("json_valid_rate")))
    print_row("exact_match_rate", pct(base.get("exact_match_rate")), pct(ft.get("exact_match_rate")))

    base_fields = base.get("field_accuracy", {})
    ft_fields = ft.get("field_accuracy", {})
    for field in FIELDS:
        print_row(f"field.{field}", pct(base_fields.get(field)), pct(ft_fields.get(field)))

    print_row("avg_input_tokens", number(base.get("avg_input_tokens")), number(ft.get("avg_input_tokens")))
    print_row("avg_output_tokens", number(base.get("avg_output_tokens")), number(ft.get("avg_output_tokens")))
    print_row("latency_p50_sec", number(base.get("latency_p50_sec")), number(ft.get("latency_p50_sec")))
    print_row("latency_p95_sec", number(base.get("latency_p95_sec")), number(ft.get("latency_p95_sec")))


if __name__ == "__main__":
    main()
