from datetime import datetime

import pytest

pytest.importorskip("langgraph")

from src.baseline_agent import AgentResult
from src.cli import build_agent
from src.finance_data import Transaction
from src.langgraph_crew import LangGraphCrewCoordinator


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


def test_build_agent_uses_langgraph_for_crew_architecture():
    agent = build_agent("crew", [])

    assert isinstance(agent, LangGraphCrewCoordinator)


def test_langgraph_crew_returns_agent_result_for_savings_question():
    transactions = [
        tx("2025-06-01T22:15", "Glovo", -40.0, "delivery"),
        tx("2025-06-02T09:10", "Aroma Kava", -5.0, "coffee"),
    ]
    agent = LangGraphCrewCoordinator(transactions)

    result = agent.run("Де можна зекономити цього місяця?")

    assert isinstance(result, AgentResult)
    assert result.architecture == "crew"
    assert result.intent == "savings"
    assert [call.name for call in result.tool_calls] == ["savings_opportunities"]
    assert any(step.name == "langgraph.route" for step in result.trace)
    assert any(step.name == "langgraph.savings_agent" for step in result.trace)
