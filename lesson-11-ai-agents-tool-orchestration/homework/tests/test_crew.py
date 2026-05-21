from datetime import datetime

from src.crew import CrewCoordinator
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


def test_crew_routes_savings_question_to_savings_agent():
    transactions = [
        tx("2025-06-01T22:30", "Glovo", -40.0, "delivery"),
        tx("2025-06-02T22:30", "Bolt Food", -60.0, "delivery"),
        tx("2025-06-03T08:30", "Aroma Kava", -5.0, "coffee"),
        tx("2025-06-04T10:00", "Sportlife", -15.0, "subscriptions", recurring=True),
    ]
    crew = CrewCoordinator(transactions)

    result = crew.run("Де можна зекономити цього місяця?")

    assert result.architecture == "crew"
    assert result.intent == "savings"
    assert result.tool_calls[0].name == "savings_opportunities"
    assert "delivery" in result.answer
    assert [step.name for step in result.trace] == [
        "coordinator.route",
        "savings_agent.run",
        "savings_opportunities",
        "coordinator.finalize",
    ]


def test_crew_can_use_injected_router():
    transactions = [
        tx("2025-06-01T22:30", "Glovo", -40.0, "delivery"),
    ]
    crew = CrewCoordinator(
        transactions,
        router=FakeRouter(Route(intent="savings")),
    )

    result = crew.run("складно сформульоване питання")

    assert result.intent == "savings"
    assert result.tool_calls[0].name == "savings_opportunities"


def test_crew_routes_fraud_question_to_risk_agent_first():
    transactions = [
        tx("2025-12-03T15:00", "Booking.com", -890.0, "travel", account="credit_card"),
    ]
    crew = CrewCoordinator(transactions)

    result = crew.run("Я не робила транзакцію Booking.com")

    assert result.architecture == "crew"
    assert result.intent == "fraud"
    assert result.tool_calls[0].name == "suspicious_transactions"
    assert "fraud/escalation" in result.answer
    assert [step.name for step in result.trace] == [
        "coordinator.route",
        "risk_agent.run",
        "suspicious_transactions",
        "coordinator.finalize",
    ]


def test_crew_routes_stats_question_to_stats_agent():
    transactions = [
        tx("2025-06-01T08:00", "Aroma Kava", -4.0, "coffee"),
        tx("2025-06-02T08:00", "Blue Bottle", -6.0, "coffee"),
    ]
    crew = CrewCoordinator(transactions)

    result = crew.run("Скільки витратив на каву?")

    assert result.architecture == "crew"
    assert result.intent == "category_spending"
    assert result.tool_calls[0].name == "spending_for_category"
    assert "coffee: $10.00" in result.answer
    assert [step.name for step in result.trace] == [
        "coordinator.route",
        "stats_agent.run",
        "spending_for_category",
        "coordinator.finalize",
    ]
