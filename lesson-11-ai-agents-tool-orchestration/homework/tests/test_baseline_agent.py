from datetime import datetime

from src.baseline_agent import BaselineAgent
from src.constants import Category, Intent, Period
from src.finance_data import Transaction
from src.router import Route


def tx(date, merchant, amount, category, account="main_debit", recurring=False):
    return Transaction(
        date=datetime.fromisoformat(date),
        merchant=merchant,
        amount=amount,
        currency="USD",
        category=category,
        account=account,
        recurring=recurring,
    )


class FakeRouter:
    def __init__(self, route):
        self.route_value = route

    def route(self, question):
        return self.route_value


def test_baseline_agent_routes_question_calls_tool_and_returns_trace():
    transactions = [
        tx("2025-06-01T08:00", "Aroma Kava", -4.0, "coffee"),
        tx("2025-06-02T08:00", "Blue Bottle", -6.0, "coffee"),
        tx("2025-06-03T12:00", "ATB", -30.0, "groceries"),
    ]
    agent = BaselineAgent(transactions)

    result = agent.run("Скільки витратив на каву?")

    assert result.architecture == "baseline"
    assert result.intent == "category_spending"
    assert result.answer == "coffee: $10.00 за останні 7 днів (2 транзакцій)."
    assert result.tool_calls[0].name == "spending_for_category"
    assert result.tool_calls[0].args["category"] == "coffee"
    assert [step.name for step in result.trace] == ["route_question", "spending_for_category", "format_answer"]
    assert result.latency_ms >= 0


def test_baseline_agent_can_use_injected_router():
    transactions = [
        tx("2025-06-01T08:00", "Aroma Kava", -4.0, "coffee"),
        tx("2025-06-02T08:00", "Blue Bottle", -6.0, "coffee"),
    ]
    agent = BaselineAgent(
        transactions,
        router=FakeRouter(Route(intent="category_spending", category="coffee")),
    )

    result = agent.run("опечатка: кавву")

    assert result.intent == "category_spending"
    assert result.tool_calls[0].name == "spending_for_category"


def test_baseline_agent_uses_route_period_for_category_spending():
    transactions = [
        tx("2025-06-01T08:00", "Aroma Kava", -4.0, "coffee"),
        tx("2025-06-20T08:00", "Blue Bottle", -6.0, "coffee"),
    ]
    agent = BaselineAgent(
        transactions,
        router=FakeRouter(
            Route(
                intent=Intent.CATEGORY_SPENDING,
                category=Category.COFFEE,
                period=Period.CURRENT_MONTH,
            )
        ),
    )

    result = agent.run("А за місяць?")

    assert result.answer.startswith("coffee: $10.00")
    assert result.tool_calls[0].args == {"category": "coffee", "period": "current_month"}


def test_baseline_agent_unknown_question_returns_no_tool_call():
    agent = BaselineAgent([])

    result = agent.run("Купи мені акції Apple")

    assert result.intent == "unknown"
    assert result.tool_calls == []
    assert "не розумію" in result.answer


def test_baseline_agent_handles_fraud_as_escalation_scenario():
    transactions = [
        tx("2025-12-03T15:00", "Booking.com", -890.0, "travel", account="credit_card"),
    ]
    agent = BaselineAgent(transactions)

    result = agent.run("Я не робила транзакцію Booking.com")

    assert result.intent == "fraud"
    assert result.tool_calls[0].name == "suspicious_transactions"
    assert "fraud/escalation" in result.answer
    assert "Booking.com" in result.answer
