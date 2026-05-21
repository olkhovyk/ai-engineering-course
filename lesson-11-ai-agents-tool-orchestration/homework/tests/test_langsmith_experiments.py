import json

from src.langsmith_experiments import case_to_example, intent_accuracy, tool_accuracy, tool_names
from src.baseline_agent import ToolCall


class FakeRun:
    def __init__(self, outputs):
        self.outputs = outputs


class FakeExample:
    def __init__(self, outputs):
        self.outputs = outputs


def test_case_to_example_converts_golden_case_to_langsmith_example():
    case = {
        "id": "coffee_last_week",
        "question": "Скільки витратив на каву?",
        "expected_intent": "category_spending",
        "expected_tools": ["spending_for_category"],
    }

    assert case_to_example(case) == {
        "inputs": {"question": "Скільки витратив на каву?"},
        "outputs": {
            "case_id": "coffee_last_week",
            "expected_intent": "category_spending",
            "expected_tools": ["spending_for_category"],
        },
        "metadata": {"case_id": "coffee_last_week"},
    }


def test_tool_names_converts_tool_calls_to_strings():
    calls = [ToolCall("spending_for_category"), ToolCall("cashflow_for_period")]

    assert tool_names(calls) == ["spending_for_category", "cashflow_for_period"]


def test_langsmith_evaluators_compare_run_outputs_with_reference_outputs():
    run = FakeRun(
        {
            "intent": "category_spending",
            "tool_calls": ["spending_for_category"],
        }
    )
    example = FakeExample(
        {
            "expected_intent": "category_spending",
            "expected_tools": ["spending_for_category"],
        }
    )

    assert intent_accuracy(run, example) == {"key": "intent_accuracy", "score": True}
    assert tool_accuracy(run, example) == {"key": "tool_accuracy", "score": True}
