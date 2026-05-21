from src.baseline_agent import AgentResult, ToolCall, TraceStep
from src.ui_helpers import langsmith_status, metrics_row, trace_rows, tool_call_rows


def test_ui_helpers_convert_agent_result_to_table_rows():
    result = AgentResult(
        architecture="crew",
        answer="answer",
        intent="savings",
        tool_calls=[ToolCall("savings_opportunities", {"limit": 3})],
        trace=[TraceStep("coordinator.route", "intent=savings", 1.2)],
        latency_ms=9.87,
    )

    assert metrics_row(result) == {
        "architecture": "crew",
        "intent": "savings",
        "latency_ms": 9.87,
    }
    assert tool_call_rows(result) == [
        {"tool": "savings_opportunities", "args": "{'limit': 3}"}
    ]
    assert trace_rows(result) == [
        {"step": "coordinator.route", "detail": "intent=savings", "latency_ms": 1.2}
    ]


def test_langsmith_status_shows_disabled_without_key(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)

    assert langsmith_status() == "disabled"
