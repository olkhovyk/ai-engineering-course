from __future__ import annotations

from src.langsmith_tracing import is_langsmith_enabled
from src.baseline_agent import AgentResult


def metrics_row(result: AgentResult) -> dict[str, object]:
    return {
        "architecture": result.architecture,
        "intent": result.intent,
        "latency_ms": result.latency_ms,
    }


def tool_call_rows(result: AgentResult) -> list[dict[str, object]]:
    return [
        {
            "tool": tool_call.name,
            "args": str(tool_call.args),
        }
        for tool_call in result.tool_calls
    ]


def trace_rows(result: AgentResult) -> list[dict[str, object]]:
    return [
        {
            "step": step.name,
            "detail": step.detail,
            "latency_ms": step.latency_ms,
        }
        for step in result.trace
    ]


def langsmith_status() -> str:
    return "enabled" if is_langsmith_enabled() else "disabled"
