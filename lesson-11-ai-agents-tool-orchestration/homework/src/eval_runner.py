from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.cli import build_agent, build_composer, build_router
from src.env import load_project_env
from src.finance_data import Transaction, load_transactions
from src.langsmith_tracing import flush_langsmith, traceable


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = BASE_DIR / "starter" / "data" / "transactions.csv"
DEFAULT_GOLDEN_PATH = BASE_DIR / "eval" / "golden_set.json"
DEFAULT_OUTPUT_PATH = BASE_DIR / "results" / "eval_results.csv"

FIELDNAMES = [
    "architecture",
    "case_id",
    "question",
    "expected_intent",
    "intent",
    "intent_ok",
    "expected_tools",
    "tool_calls",
    "tool_ok",
    "latency_ms",
    "answer_preview",
]


def load_golden_set(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


@traceable(name="eval.case", run_type="chain")
def evaluate_case(
    architecture: str,
    case: dict[str, Any],
    transactions: list[Transaction],
    router_name: str = "rule",
    composer_name: str = "template",
) -> dict[str, str]:
    result = build_agent(
        architecture,
        transactions,
        router=build_router(router_name),
        composer=build_composer(composer_name),
    ).run(case["question"])
    expected_tools = case.get("expected_tools", [])
    actual_tools = [tool_call.name for tool_call in result.tool_calls]

    return {
        "architecture": architecture,
        "case_id": case["id"],
        "question": case["question"],
        "expected_intent": case["expected_intent"],
        "intent": result.intent,
        "intent_ok": _bool_text(result.intent == case["expected_intent"]),
        "expected_tools": "|".join(expected_tools),
        "tool_calls": "|".join(actual_tools),
        "tool_ok": _bool_text(actual_tools == expected_tools),
        "latency_ms": f"{result.latency_ms:.3f}",
        "answer_preview": _preview(result.answer),
    }


@traceable(name="eval.run", run_type="chain")
def run_eval(
    transactions: list[Transaction],
    golden_path: str | Path,
    output_path: str | Path,
    architectures: list[str],
    router_name: str = "rule",
    composer_name: str = "template",
) -> list[dict[str, str]]:
    cases = load_golden_set(golden_path)
    rows: list[dict[str, str]] = []

    for case in cases:
        for architecture in architectures:
            rows.append(
                evaluate_case(
                    architecture,
                    case,
                    transactions,
                    router_name=router_name,
                    composer_name=composer_name,
                )
            )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    return rows


def summarize(rows: list[dict[str, str]]) -> str:
    lines = ["architecture,cases,intent_accuracy,tool_accuracy,avg_latency_ms"]
    architectures = sorted({row["architecture"] for row in rows})
    for architecture in architectures:
        subset = [row for row in rows if row["architecture"] == architecture]
        intent_accuracy = _share(row["intent_ok"] == "true" for row in subset)
        tool_accuracy = _share(row["tool_ok"] == "true" for row in subset)
        avg_latency = sum(float(row["latency_ms"]) for row in subset) / len(subset)
        lines.append(
            f"{architecture},{len(subset)},{intent_accuracy:.2f},{tool_accuracy:.2f},{avg_latency:.3f}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(DEFAULT_DATA_PATH))
    parser.add_argument("--golden", default=str(DEFAULT_GOLDEN_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--architectures", nargs="+", default=["baseline", "crew"])
    parser.add_argument("--router", choices=["rule", "llm"], default="rule")
    parser.add_argument("--composer", choices=["template", "llm"], default="template")
    args = parser.parse_args()

    load_project_env()
    transactions = load_transactions(args.data)
    rows = run_eval(
        transactions=transactions,
        golden_path=args.golden,
        output_path=args.output,
        architectures=args.architectures,
        router_name=args.router,
        composer_name=args.composer,
    )
    print(summarize(rows))
    print(f"\nWrote {args.output}")
    flush_langsmith()


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _preview(answer: str, limit: int = 120) -> str:
    compact = " ".join(answer.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _share(values) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(1 for item in items if item) / len(items)


if __name__ == "__main__":
    main()
