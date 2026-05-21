from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any, Protocol

from src.constants import Intent
from src.finance_data import Transaction
from src.langsmith_tracing import traceable
from src.tools import (
    CashflowSummary,
    DeliverySummary,
    SavingsOpportunity,
    SpendingSummary,
    SubscriptionSummary,
)


class AnswerComposer(Protocol):
    def compose(
        self,
        question: str,
        intent: str,
        tool_name: str | None,
        tool_result: Any,
    ) -> str:
        ...


class TemplateComposer(AnswerComposer):
    @traceable(name="composer.template", run_type="chain")
    def compose(
        self,
        question: str,
        intent: str,
        tool_name: str | None,
        tool_result: Any,
    ) -> str:
        match intent:
            case Intent.CATEGORY_SPENDING if isinstance(tool_result, SpendingSummary):
                return f"{tool_result.category}: ${tool_result.total:.2f} за останні 7 днів ({tool_result.count} транзакцій)."

            case Intent.TOP_CATEGORIES if isinstance(tool_result, list):
                lines = [f"{index}. {category}: ${total:.2f}" for index, (category, total) in enumerate(tool_result, 1)]
                return "Топ категорій витрат:\n" + "\n".join(lines)

            case Intent.DELIVERY if isinstance(tool_result, DeliverySummary):
                return (
                    f"Delivery: ${tool_result.total_amount:.2f}, {tool_result.total_orders} замовлень. "
                    f"Після 21:00: {tool_result.late_night_orders} "
                    f"({tool_result.late_night_share:.0%}), сума ${tool_result.late_night_amount:.2f}."
                )

            case Intent.CASHFLOW if isinstance(tool_result, CashflowSummary):
                return (
                    f"За останні 7 днів: income ${tool_result.income:.2f}, "
                    f"expenses ${tool_result.expenses:.2f}, net ${tool_result.net:.2f}."
                )

            case Intent.SAVINGS if isinstance(tool_result, list):
                opportunities = [item for item in tool_result if isinstance(item, SavingsOpportunity)]
                lines = [
                    (
                        f"- {item.category}: ~${item.estimated_monthly_saving:.2f}/міс. "
                        f"{item.reason} Дія: {item.action}"
                    )
                    for item in opportunities
                ]
                return "Ідеї для економії:\n" + "\n".join(lines)

            case Intent.SUBSCRIPTIONS if isinstance(tool_result, dict):
                summaries = [item for item in tool_result.values() if isinstance(item, SubscriptionSummary)]
                lines = [
                    f"- {summary.merchant}: ~${summary.monthly_amount:.2f}/міс, платежів: {summary.payments}"
                    for summary in summaries
                ]
                return "Підписки:\n" + "\n".join(lines)

            case Intent.FRAUD if isinstance(tool_result, list):
                suspicious = [item for item in tool_result if isinstance(item, Transaction)]
                lines = [
                    f"- {transaction.date.date()} {transaction.merchant}: ${abs(transaction.amount):.2f}"
                    for transaction in suspicious
                ]
                return (
                    "Це схоже на fraud/escalation сценарій. Агент не повинен сам блокувати картку.\n"
                    "Підозрілі транзакції:\n"
                    + "\n".join(lines)
                )

        return "Поки не розумію цей запит. Наступним кроком додамо більше intent-ів."


class ComposerLLMClient(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        ...


class LLMComposer(AnswerComposer):
    def __init__(
        self,
        client: ComposerLLMClient,
        fallback_composer: AnswerComposer | None = None,
    ):
        self.client = client
        self.fallback_composer = fallback_composer or TemplateComposer()

    @traceable(name="composer.llm", run_type="chain")
    def compose(
        self,
        question: str,
        intent: str,
        tool_name: str | None,
        tool_result: Any,
    ) -> str:
        try:
            return self.client.complete(
                _composer_system_prompt(),
                _composer_user_prompt(question, intent, tool_name, tool_result),
            ).strip()
        except Exception:
            return self.fallback_composer.compose(question, intent, tool_name, tool_result)


def _composer_system_prompt() -> str:
    return (
        "You are a friendly personal finance coach. "
        "Answer in Ukrainian, using informal 'ти'. "
        "Use only the grounded facts provided by the tool result. "
        "Do not invent numbers, merchants, dates, transactions, or categories. "
        "If the request is fraud-related, explain that support must handle blocking or chargeback. "
        "Keep the answer concise and actionable."
    )


def _composer_user_prompt(
    question: str,
    intent: str,
    tool_name: str | None,
    tool_result: Any,
) -> str:
    payload = {
        "question": question,
        "intent": intent,
        "tool_name": tool_name,
        "tool_result": _jsonable(tool_result),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
