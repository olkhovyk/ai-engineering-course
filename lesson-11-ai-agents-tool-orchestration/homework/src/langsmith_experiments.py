from __future__ import annotations

from typing import Any

from src.baseline_agent import ToolCall


def case_to_example(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "inputs": {"question": case["question"]},
        "outputs": {
            "case_id": case["id"],
            "expected_intent": case["expected_intent"],
            "expected_tools": case.get("expected_tools", []),
        },
        "metadata": {"case_id": case["id"]},
    }


def tool_names(tool_calls: list[ToolCall]) -> list[str]:
    return [str(tool_call.name) for tool_call in tool_calls]


def intent_accuracy(run: Any, example: Any, **kwargs: Any) -> dict[str, Any]:
    outputs = run.outputs or {}
    reference_outputs = example.outputs if example and example.outputs else {}
    return {
        "key": "intent_accuracy",
        "score": outputs.get("intent") == reference_outputs.get("expected_intent"),
    }


def tool_accuracy(run: Any, example: Any, **kwargs: Any) -> dict[str, Any]:
    outputs = run.outputs or {}
    reference_outputs = example.outputs if example and example.outputs else {}
    return {
        "key": "tool_accuracy",
        "score": outputs.get("tool_calls") == reference_outputs.get("expected_tools", []),
    }
