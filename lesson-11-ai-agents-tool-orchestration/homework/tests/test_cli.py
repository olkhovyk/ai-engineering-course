from src.baseline_agent import AgentResult, ToolCall, TraceStep
from src.cli import build_agent, build_composer, build_router, format_result
from src.finance_data import Transaction
from datetime import datetime
import pytest


def test_format_result_without_trace_returns_only_answer():
    result = AgentResult(
        architecture="baseline",
        answer="Hello",
        intent="savings",
        tool_calls=[ToolCall("savings_opportunities")],
        trace=[TraceStep("route_question", "intent=savings", 0.1)],
        latency_ms=1.23,
    )

    assert format_result(result, show_trace=False) == "Hello"


def test_format_result_with_trace_includes_metrics_tool_calls_and_steps():
    result = AgentResult(
        architecture="baseline",
        answer="Hello",
        intent="savings",
        tool_calls=[ToolCall("savings_opportunities", {"limit": 3})],
        trace=[
            TraceStep("route_question", "intent=savings", 0.1),
            TraceStep("savings_opportunities", "items=3", 0.2),
        ],
        latency_ms=1.23,
    )

    output = format_result(result, show_trace=True)

    assert "ANSWER" in output
    assert "METRICS" in output
    assert "architecture: baseline" in output
    assert "intent: savings" in output
    assert "latency_ms: 1.23" in output
    assert "- savings_opportunities {'limit': 3}" in output
    assert "- route_question: intent=savings, 0.1 ms" in output


def test_build_agent_selects_baseline_or_crew_architecture():
    pytest.importorskip("langgraph")
    transactions = [
        Transaction(
            date=datetime.fromisoformat("2025-06-01T08:00"),
            merchant="Aroma Kava",
            amount=-4.0,
            currency="USD",
            category="coffee",
            account="main_debit",
            recurring=False,
        )
    ]

    baseline = build_agent("baseline", transactions)
    crew = build_agent("crew", transactions)

    assert baseline.run("Скільки витратив на каву?").architecture == "baseline"
    assert crew.run("Скільки витратив на каву?").architecture == "crew"


def test_build_router_selects_rule_router_by_default():
    router = build_router("rule")

    assert router.route("Скільки витратив на каву?").intent == "category_spending"


def test_build_composer_selects_template_composer():
    composer = build_composer("template")

    assert composer.__class__.__name__ == "TemplateComposer"


def test_build_llm_composer_uses_larger_completion_budget(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    composer = build_composer("llm")

    assert composer.client.max_tokens >= 400
