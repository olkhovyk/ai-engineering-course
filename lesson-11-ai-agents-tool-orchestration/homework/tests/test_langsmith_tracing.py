from src.baseline_agent import AgentResult, ToolCall, TraceStep
from src.langsmith_tracing import is_langsmith_enabled, serialize_for_langsmith, traceable


def test_langsmith_disabled_without_api_key(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)

    assert is_langsmith_enabled() is False


def test_traceable_wrapper_returns_function_result_when_disabled(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)

    @traceable(name="test.fn")
    def add(left, right):
        return left + right

    assert add(2, 3) == 5


def test_langsmith_serializer_converts_agent_result_to_plain_dict():
    result = AgentResult(
        architecture="crew",
        answer="ok",
        intent="savings",
        tool_calls=[ToolCall("savings_opportunities", {"limit": 3})],
        trace=[TraceStep("crew.savings_agent", "items=3", 1.2)],
        latency_ms=9.87,
    )

    assert serialize_for_langsmith(result) == {
        "architecture": "crew",
        "answer": "ok",
        "intent": "savings",
        "tool_calls": [{"name": "savings_opportunities", "args": {"limit": 3}}],
        "trace": [{"name": "crew.savings_agent", "detail": "items=3", "latency_ms": 1.2}],
        "latency_ms": 9.87,
    }
