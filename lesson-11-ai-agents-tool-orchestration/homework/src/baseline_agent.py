from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from src.composer import AnswerComposer, TemplateComposer
from src.constants import Intent, Period, ToolName
from src.finance_data import Transaction
from src.langsmith_tracing import traceable
from src.routing import Router, RuleBasedRouter
from src.tools import (
    cashflow_for_period,
    delivery_late_night_summary,
    savings_opportunities,
    spending_for_category,
    subscriptions_summary,
    suspicious_transactions,
    top_spending_categories,
)


@dataclass(frozen=True)
class TraceStep:
    name: str
    detail: str
    latency_ms: float


@dataclass(frozen=True)
class ToolCall:
    name: ToolName
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentResult:
    architecture: str
    answer: str
    intent: str
    tool_calls: list[ToolCall]
    trace: list[TraceStep]
    latency_ms: float


class BaselineAgent:
    def __init__(
        self,
        transactions: list[Transaction],
        router: Router | None = None,
        composer: AnswerComposer | None = None,
    ):
        self.transactions = transactions
        self.router = router or RuleBasedRouter()
        self.composer = composer or TemplateComposer()

    @traceable(name="agent.baseline", run_type="chain")
    def run(self, question: str) -> AgentResult:
        started = time.perf_counter()
        tool_calls: list[ToolCall] = []
        trace: list[TraceStep] = []

        route_started = time.perf_counter()
        route = self.router.route(question)
        trace.append(
            TraceStep(
                name="route_question",
                detail=f"intent={route.intent}, category={route.category}",
                latency_ms=_elapsed_ms(route_started),
            )
        )

        answer, tool_call, tool_trace = self._answer_for_route(question, route.intent, route.category, route.period)
        if tool_call is not None:
            tool_calls.append(tool_call)
            trace.append(tool_trace)

        format_started = time.perf_counter()
        trace.append(
            TraceStep(
                name="format_answer",
                detail="deterministic template",
                latency_ms=_elapsed_ms(format_started),
            )
        )

        return AgentResult(
            architecture="baseline",
            answer=answer,
            intent=route.intent,
            tool_calls=tool_calls,
            trace=trace,
            latency_ms=_elapsed_ms(started),
        )

    def _answer_for_route(
        self,
        question: str,
        intent: str,
        category: str | None,
        period: Period = Period.LAST_7_DAYS,
    ) -> tuple[str, ToolCall | None, TraceStep]:
        tool_started = time.perf_counter()

        match intent:
            case Intent.CATEGORY_SPENDING if category:
                tool_name = ToolName.SPENDING_FOR_CATEGORY
                start, end = period_range(self.transactions, period)
                summary = spending_for_category(self.transactions, category, start=start, end=end)
                return (
                    self.composer.compose(question, intent, tool_name, summary),
                    ToolCall(tool_name, {"category": category, "period": str(period)}),
                    TraceStep(tool_name, f"total={summary.total}, count={summary.count}", _elapsed_ms(tool_started)),
                )

            case Intent.TOP_CATEGORIES:
                tool_name = ToolName.TOP_SPENDING_CATEGORIES
                categories = top_spending_categories(self.transactions, limit=5)
                return (
                    self.composer.compose(question, intent, tool_name, categories),
                    ToolCall(tool_name, {"limit": 5}),
                    TraceStep(tool_name, f"items={len(categories)}", _elapsed_ms(tool_started)),
                )

            case Intent.DELIVERY:
                tool_name = ToolName.DELIVERY_LATE_NIGHT_SUMMARY
                summary = delivery_late_night_summary(self.transactions)
                return (
                    self.composer.compose(question, intent, tool_name, summary),
                    ToolCall(tool_name),
                    TraceStep(tool_name, f"late_night_share={summary.late_night_share}", _elapsed_ms(tool_started)),
                )

            case Intent.CASHFLOW:
                tool_name = ToolName.CASHFLOW_FOR_PERIOD
                start, end = default_period(self.transactions)
                summary = cashflow_for_period(self.transactions, start=start, end=end)
                return (
                    self.composer.compose(question, intent, tool_name, summary),
                    ToolCall(tool_name, {"period": "last_7_days"}),
                    TraceStep(tool_name, f"net={summary.net}", _elapsed_ms(tool_started)),
                )

            case Intent.SAVINGS:
                tool_name = ToolName.SAVINGS_OPPORTUNITIES
                opportunities = savings_opportunities(self.transactions)
                return (
                    self.composer.compose(question, intent, tool_name, opportunities),
                    ToolCall(tool_name),
                    TraceStep(tool_name, f"items={len(opportunities)}", _elapsed_ms(tool_started)),
                )

            case Intent.SUBSCRIPTIONS:
                tool_name = ToolName.SUBSCRIPTIONS_SUMMARY
                summaries = subscriptions_summary(self.transactions)
                return (
                    self.composer.compose(question, intent, tool_name, summaries),
                    ToolCall(tool_name),
                    TraceStep(tool_name, f"items={len(summaries)}", _elapsed_ms(tool_started)),
                )

            case Intent.FRAUD:
                tool_name = ToolName.SUSPICIOUS_TRANSACTIONS
                transactions_found = suspicious_transactions(self.transactions)
                return (
                    self.composer.compose(question, intent, tool_name, transactions_found),
                    ToolCall(tool_name),
                    TraceStep(tool_name, f"items={len(transactions_found)}", _elapsed_ms(tool_started)),
                )

            case _:
                return (
                    self.composer.compose(question, intent, None, None),
                    None,
                    TraceStep("no_tool", "unknown intent", _elapsed_ms(tool_started)),
                )


def default_period(transactions: list[Transaction]) -> tuple[datetime, datetime]:
    return period_range(transactions, Period.LAST_7_DAYS)


def period_range(transactions: list[Transaction], period: Period) -> tuple[datetime, datetime]:
    if not transactions:
        now = datetime.now()
        if period == Period.CURRENT_MONTH:
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), now
        return now - timedelta(days=7), now

    reference = max(transaction.date for transaction in transactions)
    if period == Period.CURRENT_MONTH:
        start = reference.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = reference - timedelta(days=7)
    return start, reference


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)
