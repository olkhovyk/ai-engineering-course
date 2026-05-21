from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.baseline_agent import BaselineAgent
from src.baseline_agent import AgentResult
from src.composer import AnswerComposer, LLMComposer, TemplateComposer
from src.crew import CrewCoordinator
from src.env import load_project_env
from src.finance_data import Transaction
from src.finance_data import load_transactions
from src.langsmith_tracing import flush_langsmith
from src.llm_router import LLMRouter, OpenRouterClient
from src.routing import Router, RuleBasedRouter


DATA_PATH = Path(__file__).resolve().parents[1] / "starter" / "data" / "transactions.csv"


def build_router(router_name: str) -> Router:
    if router_name == "rule":
        return RuleBasedRouter()
    if router_name == "llm":
        return LLMRouter(client=OpenRouterClient())
    raise ValueError(f"Unknown router: {router_name}")


def build_composer(composer_name: str) -> AnswerComposer:
    if composer_name == "template":
        return TemplateComposer()
    if composer_name == "llm":
        return LLMComposer(
            client=OpenRouterClient(
                model=os.getenv("OPENROUTER_COMPOSER_MODEL") or os.getenv("OPENROUTER_ROUTER_MODEL"),
                max_tokens=500,
            )
        )
    raise ValueError(f"Unknown composer: {composer_name}")


def build_agent(
    architecture: str,
    transactions: list[Transaction],
    router: Router | None = None,
    composer: AnswerComposer | None = None,
):
    if architecture == "baseline":
        return BaselineAgent(transactions, router=router, composer=composer)
    if architecture == "crew":
        from src.langgraph_crew import LangGraphCrewCoordinator

        return LangGraphCrewCoordinator(transactions, router=router, composer=composer)
    raise ValueError(f"Unknown architecture: {architecture}")


def format_result(result: AgentResult, show_trace: bool = False) -> str:
    if not show_trace:
        return result.answer

    tool_lines = [
        f"- {tool_call.name} {tool_call.args}"
        for tool_call in result.tool_calls
    ]
    trace_lines = [
        f"- {step.name}: {step.detail}, {step.latency_ms} ms"
        for step in result.trace
    ]

    return "\n".join(
        [
            "ANSWER",
            result.answer,
            "",
            "METRICS",
            f"architecture: {result.architecture}",
            f"intent: {result.intent}",
            f"latency_ms: {result.latency_ms}",
            "",
            "TOOL CALLS",
            "\n".join(tool_lines) if tool_lines else "- none",
            "",
            "TRACE",
            "\n".join(trace_lines) if trace_lines else "- none",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--data", default=str(DATA_PATH))
    parser.add_argument("--architecture", choices=["baseline", "crew"], default="baseline")
    parser.add_argument("--router", choices=["rule", "llm"], default="rule")
    parser.add_argument("--composer", choices=["template", "llm"], default="template")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()

    load_project_env()
    transactions = load_transactions(args.data)
    router = build_router(args.router)
    composer = build_composer(args.composer)
    result = build_agent(args.architecture, transactions, router=router, composer=composer).run(args.question)
    print(format_result(result, show_trace=args.trace))
    flush_langsmith()


if __name__ == "__main__":
    main()
