from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langsmith import Client, evaluate

from src.cli import build_agent, build_composer, build_router
from src.env import load_project_env
from src.eval_runner import DEFAULT_DATA_PATH, DEFAULT_GOLDEN_PATH
from src.finance_data import load_transactions
from src.langsmith_experiments import (
    case_to_example,
    intent_accuracy,
    tool_accuracy,
    tool_names,
)
from src.langsmith_tracing import flush_langsmith


DEFAULT_DATASET_NAME = "lesson-11-finance-golden-set"


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def ensure_dataset(client: Client, dataset_name: str, cases: list[dict[str, Any]]) -> None:
    if not client.has_dataset(dataset_name=dataset_name):
        client.create_dataset(
            dataset_name,
            description="Golden set for Lesson 11 finance agent baseline vs LangGraph crew eval.",
        )

    existing_case_ids = {
        example.outputs.get("case_id")
        for example in client.list_examples(dataset_name=dataset_name)
        if example.outputs
    }
    examples = [
        case_to_example(case)
        for case in cases
        if case["id"] not in existing_case_ids
    ]
    if examples:
        client.create_examples(dataset_name=dataset_name, examples=examples)


def build_target(architecture: str, router_name: str, composer_name: str, data_path: str | Path):
    transactions = load_transactions(data_path)

    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        result = build_agent(
            architecture,
            transactions,
            router=build_router(router_name),
            composer=build_composer(composer_name),
        ).run(inputs["question"])
        return {
            "answer": result.answer,
            "intent": str(result.intent),
            "tool_calls": tool_names(result.tool_calls),
            "latency_ms": result.latency_ms,
            "architecture": result.architecture,
        }

    return target


def run_experiment(
    client: Client,
    dataset_name: str,
    architecture: str,
    router_name: str,
    composer_name: str,
    data_path: str | Path,
) -> None:
    evaluate(
        build_target(architecture, router_name, composer_name, data_path),
        data=dataset_name,
        evaluators=[intent_accuracy, tool_accuracy],
        experiment_prefix=f"{architecture}-{router_name}-{composer_name}",
        metadata={
            "architecture": architecture,
            "router": router_name,
            "composer": composer_name,
        },
        client=client,
        blocking=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--golden", default=str(DEFAULT_GOLDEN_PATH))
    parser.add_argument("--data", default=str(DEFAULT_DATA_PATH))
    parser.add_argument("--router", choices=["rule", "llm"], default="rule")
    parser.add_argument("--composer", choices=["template", "llm"], default="template")
    parser.add_argument("--architectures", nargs="+", choices=["baseline", "crew"], default=["baseline", "crew"])
    args = parser.parse_args()

    load_project_env()
    client = Client()
    cases = load_cases(args.golden)
    ensure_dataset(client, args.dataset, cases)

    for architecture in args.architectures:
        run_experiment(
            client=client,
            dataset_name=args.dataset,
            architecture=architecture,
            router_name=args.router,
            composer_name=args.composer,
            data_path=args.data,
        )
        print(f"Uploaded experiment: {architecture}-{args.router}-{args.composer}")

    flush_langsmith()
    print(f"Dataset: {args.dataset}")


if __name__ == "__main__":
    main()
