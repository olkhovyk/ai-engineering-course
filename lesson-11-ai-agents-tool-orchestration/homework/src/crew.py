from __future__ import annotations

import time

from src.baseline_agent import AgentResult, ToolCall, TraceStep, default_period
from src.composer import AnswerComposer, TemplateComposer
from src.constants import Intent, ToolName
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


class CrewCoordinator:
    def __init__(
        self,
        transactions: list[Transaction],
        router: Router | None = None,
        composer: AnswerComposer | None = None,
    ):
        self.transactions = transactions
        self.router = router or RuleBasedRouter()
        self.composer = composer or TemplateComposer()
        self.stats_agent = StatsAgent(transactions, self.composer)
        self.savings_agent = SavingsAgent(transactions, self.composer)
        self.risk_agent = RiskAgent(transactions, self.composer)

    @traceable(name="crew.coordinator", run_type="chain")
    def run(self, question: str) -> AgentResult:
        started = time.perf_counter()

        route_started = time.perf_counter()
        route = self.router.route(question)
        trace = [
            TraceStep(
                "coordinator.route",
                f"intent={route.intent}, category={route.category}",
                _elapsed_ms(route_started),
            )
        ]

        match route.intent:
            case Intent.FRAUD | Intent.UNKNOWN:
                answer, tool_calls, agent_trace = self.risk_agent.run(question, route.intent, route.category)
            case Intent.SAVINGS:
                answer, tool_calls, agent_trace = self.savings_agent.run(question, route.intent, route.category)
            case _:
                answer, tool_calls, agent_trace = self.stats_agent.run(question, route.intent, route.category)

        trace.extend(agent_trace)

        finalize_started = time.perf_counter()
        trace.append(
            TraceStep(
                "coordinator.finalize",
                "merged specialist result",
                _elapsed_ms(finalize_started),
            )
        )

        return AgentResult(
            architecture="crew",
            answer=answer,
            intent=route.intent,
            tool_calls=tool_calls,
            trace=trace,
            latency_ms=_elapsed_ms(started),
        )


class StatsAgent:
    def __init__(self, transactions: list[Transaction], composer: AnswerComposer):
        self.transactions = transactions
        self.composer = composer

    @traceable(name="crew.stats_agent", run_type="chain")
    def run(
        self,
        question: str,
        intent: str,
        category: str | None,
    ) -> tuple[str, list[ToolCall], list[TraceStep]]:
        trace = [TraceStep("stats_agent.run", f"intent={intent}", 0.0)]
        tool_started = time.perf_counter()

        match intent:
            case Intent.CATEGORY_SPENDING if category:
                tool_name = ToolName.SPENDING_FOR_CATEGORY
                start, end = default_period(self.transactions)
                summary = spending_for_category(self.transactions, category, start=start, end=end)
                answer = self.composer.compose(question, intent, tool_name, summary)
                trace.append(TraceStep(tool_name, f"total={summary.total}, count={summary.count}", _elapsed_ms(tool_started)))
                return answer, [ToolCall(tool_name, {"category": category, "period": "last_7_days"})], trace

            case Intent.TOP_CATEGORIES:
                tool_name = ToolName.TOP_SPENDING_CATEGORIES
                categories = top_spending_categories(self.transactions, limit=5)
                trace.append(TraceStep(tool_name, f"items={len(categories)}", _elapsed_ms(tool_started)))
                return self.composer.compose(question, intent, tool_name, categories), [ToolCall(tool_name, {"limit": 5})], trace

            case Intent.DELIVERY:
                tool_name = ToolName.DELIVERY_LATE_NIGHT_SUMMARY
                summary = delivery_late_night_summary(self.transactions)
                answer = self.composer.compose(question, intent, tool_name, summary)
                trace.append(TraceStep(tool_name, f"late_night_share={summary.late_night_share}", _elapsed_ms(tool_started)))
                return answer, [ToolCall(tool_name)], trace

            case Intent.CASHFLOW:
                tool_name = ToolName.CASHFLOW_FOR_PERIOD
                start, end = default_period(self.transactions)
                summary = cashflow_for_period(self.transactions, start=start, end=end)
                answer = self.composer.compose(question, intent, tool_name, summary)
                trace.append(TraceStep(tool_name, f"net={summary.net}", _elapsed_ms(tool_started)))
                return answer, [ToolCall(tool_name, {"period": "last_7_days"})], trace

            case Intent.SUBSCRIPTIONS:
                tool_name = ToolName.SUBSCRIPTIONS_SUMMARY
                summaries = subscriptions_summary(self.transactions)
                trace.append(TraceStep(tool_name, f"items={len(summaries)}", _elapsed_ms(tool_started)))
                return self.composer.compose(question, intent, tool_name, summaries), [ToolCall(tool_name)], trace

            case _:
                trace.append(TraceStep("no_tool", "unsupported stats intent", _elapsed_ms(tool_started)))
                return self.composer.compose(question, intent, None, None), [], trace


class SavingsAgent:
    def __init__(self, transactions: list[Transaction], composer: AnswerComposer):
        self.transactions = transactions
        self.composer = composer

    @traceable(name="crew.savings_agent", run_type="chain")
    def run(
        self,
        question: str,
        intent: str,
        category: str | None,
    ) -> tuple[str, list[ToolCall], list[TraceStep]]:
        trace = [TraceStep("savings_agent.run", f"intent={intent}", 0.0)]
        tool_started = time.perf_counter()
        tool_name = ToolName.SAVINGS_OPPORTUNITIES
        opportunities = savings_opportunities(self.transactions)
        trace.append(TraceStep(tool_name, f"items={len(opportunities)}", _elapsed_ms(tool_started)))
        return self.composer.compose(question, intent, tool_name, opportunities), [ToolCall(tool_name)], trace


class RiskAgent:
    def __init__(self, transactions: list[Transaction], composer: AnswerComposer):
        self.transactions = transactions
        self.composer = composer

    @traceable(name="crew.risk_agent", run_type="chain")
    def run(
        self,
        question: str,
        intent: str,
        category: str | None,
    ) -> tuple[str, list[ToolCall], list[TraceStep]]:
        trace = [TraceStep("risk_agent.run", f"intent={intent}", 0.0)]
        tool_started = time.perf_counter()

        match intent:
            case Intent.FRAUD:
                tool_name = ToolName.SUSPICIOUS_TRANSACTIONS
                transactions_found = suspicious_transactions(self.transactions)
                trace.append(TraceStep(tool_name, f"items={len(transactions_found)}", _elapsed_ms(tool_started)))
                return (
                    self.composer.compose(question, intent, tool_name, transactions_found),
                    [ToolCall(tool_name)],
                    trace,
                )

            case _:
                trace.append(TraceStep("no_tool", "unknown or out-of-scope request", _elapsed_ms(tool_started)))
                return (
                    "Це поза моїм фінансовим скоупом. Я можу допомогти з витратами, підписками, cashflow та підозрілими транзакціями.",
                    [],
                    trace,
                )


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)
