from __future__ import annotations

import time
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from src.baseline_agent import AgentResult, ToolCall, TraceStep, default_period, period_range
from src.composer import AnswerComposer, TemplateComposer
from src.constants import Intent, Period, ToolName
from src.finance_data import Transaction
from src.langsmith_tracing import traceable
from src.routing import Route, Router, RuleBasedRouter
from src.tools import (
    cashflow_for_period,
    delivery_late_night_summary,
    savings_opportunities,
    spending_for_category,
    subscriptions_summary,
    suspicious_transactions,
    top_spending_categories,
)


class FinanceCrewState(TypedDict, total=False):
    question: str
    route: Route
    intent: Intent
    category: str | None
    period: Period
    answer: str
    tool_name: ToolName | None
    tool_result: Any
    tool_calls: list[ToolCall]
    trace: list[TraceStep]


class LangGraphCrewCoordinator:
    def __init__(
        self,
        transactions: list[Transaction],
        router: Router | None = None,
        composer: AnswerComposer | None = None,
    ):
        self.transactions = transactions
        self.router = router or RuleBasedRouter()
        self.composer = composer or TemplateComposer()
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(FinanceCrewState)
        builder.add_node("route", self._route_node)
        builder.add_node("stats_agent", self._stats_agent_node)
        builder.add_node("savings_agent", self._savings_agent_node)
        builder.add_node("risk_agent", self._risk_agent_node)
        builder.add_node("compose", self._compose_node)

        builder.add_edge(START, "route")
        builder.add_conditional_edges(
            "route",
            self._select_agent,
            {
                "stats_agent": "stats_agent",
                "savings_agent": "savings_agent",
                "risk_agent": "risk_agent",
            },
        )
        builder.add_edge("stats_agent", "compose")
        builder.add_edge("savings_agent", "compose")
        builder.add_edge("risk_agent", "compose")
        builder.add_edge("compose", END)
        return builder.compile()

    @traceable(name="langgraph.crew", run_type="chain")
    def run(self, question: str) -> AgentResult:
        started = time.perf_counter()
        final_state = self.graph.invoke(
            {
                "question": question,
                "tool_calls": [],
                "trace": [],
            }
        )

        trace = list(final_state.get("trace", []))
        trace.append(
            TraceStep(
                "langgraph.finalize",
                "compiled StateGraph completed",
                _elapsed_ms(started),
            )
        )

        return AgentResult(
            architecture="crew",
            answer=final_state.get("answer", ""),
            intent=final_state.get("intent", Intent.UNKNOWN),
            tool_calls=list(final_state.get("tool_calls", [])),
            trace=trace,
            latency_ms=_elapsed_ms(started),
        )

    @traceable(name="langgraph.route", run_type="chain")
    def _route_node(self, state: FinanceCrewState) -> dict[str, Any]:
        started = time.perf_counter()
        route = self.router.route(state["question"])
        return {
            "route": route,
            "intent": route.intent,
            "category": route.category,
            "period": route.period,
            "trace": state.get("trace", [])
            + [
                TraceStep(
                    "langgraph.route",
                    f"intent={route.intent}, category={route.category}",
                    _elapsed_ms(started),
                )
            ],
        }

    def _select_agent(
        self,
        state: FinanceCrewState,
    ) -> Literal["stats_agent", "savings_agent", "risk_agent"]:
        match state["intent"]:
            case Intent.FRAUD | Intent.UNKNOWN:
                return "risk_agent"
            case Intent.SAVINGS:
                return "savings_agent"
            case _:
                return "stats_agent"

    @traceable(name="langgraph.stats_agent", run_type="chain")
    def _stats_agent_node(self, state: FinanceCrewState) -> dict[str, Any]:
        started = time.perf_counter()
        question = state["question"]
        intent = state["intent"]
        category = state.get("category")
        period = state.get("period", Period.LAST_7_DAYS)

        match intent:
            case Intent.CATEGORY_SPENDING if category:
                tool_name = ToolName.SPENDING_FOR_CATEGORY
                start, end = period_range(self.transactions, period)
                tool_result = spending_for_category(self.transactions, category, start=start, end=end)
                tool_calls = [ToolCall(tool_name, {"category": category, "period": str(period)})]
                detail = f"total={tool_result.total}, count={tool_result.count}"

            case Intent.TOP_CATEGORIES:
                tool_name = ToolName.TOP_SPENDING_CATEGORIES
                tool_result = top_spending_categories(self.transactions, limit=5)
                tool_calls = [ToolCall(tool_name, {"limit": 5})]
                detail = f"items={len(tool_result)}"

            case Intent.DELIVERY:
                tool_name = ToolName.DELIVERY_LATE_NIGHT_SUMMARY
                tool_result = delivery_late_night_summary(self.transactions)
                tool_calls = [ToolCall(tool_name)]
                detail = f"late_night_share={tool_result.late_night_share}"

            case Intent.CASHFLOW:
                tool_name = ToolName.CASHFLOW_FOR_PERIOD
                start, end = default_period(self.transactions)
                tool_result = cashflow_for_period(self.transactions, start=start, end=end)
                tool_calls = [ToolCall(tool_name, {"period": "last_7_days"})]
                detail = f"net={tool_result.net}"

            case Intent.SUBSCRIPTIONS:
                tool_name = ToolName.SUBSCRIPTIONS_SUMMARY
                tool_result = subscriptions_summary(self.transactions)
                tool_calls = [ToolCall(tool_name)]
                detail = f"items={len(tool_result)}"

            case _:
                tool_name = None
                tool_result = None
                tool_calls = []
                detail = "unsupported stats intent"

        return self._tool_update(question, intent, tool_name, tool_result, tool_calls, state, "langgraph.stats_agent", detail, started)

    @traceable(name="langgraph.savings_agent", run_type="chain")
    def _savings_agent_node(self, state: FinanceCrewState) -> dict[str, Any]:
        started = time.perf_counter()
        tool_name = ToolName.SAVINGS_OPPORTUNITIES
        tool_result = savings_opportunities(self.transactions)
        return self._tool_update(
            state["question"],
            state["intent"],
            tool_name,
            tool_result,
            [ToolCall(tool_name)],
            state,
            "langgraph.savings_agent",
            f"items={len(tool_result)}",
            started,
        )

    @traceable(name="langgraph.risk_agent", run_type="chain")
    def _risk_agent_node(self, state: FinanceCrewState) -> dict[str, Any]:
        started = time.perf_counter()
        intent = state["intent"]

        if intent == Intent.FRAUD:
            tool_name = ToolName.SUSPICIOUS_TRANSACTIONS
            tool_result = suspicious_transactions(self.transactions)
            return self._tool_update(
                state["question"],
                intent,
                tool_name,
                tool_result,
                [ToolCall(tool_name)],
                state,
                "langgraph.risk_agent",
                f"items={len(tool_result)}",
                started,
            )

        return self._tool_update(
            state["question"],
            intent,
            None,
            None,
            [],
            state,
            "langgraph.risk_agent",
            "unknown or out-of-scope request",
            started,
        )

    def _tool_update(
        self,
        question: str,
        intent: Intent,
        tool_name: ToolName | None,
        tool_result: Any,
        tool_calls: list[ToolCall],
        state: FinanceCrewState,
        trace_name: str,
        detail: str,
        started: float,
    ) -> dict[str, Any]:
        return {
            "tool_name": tool_name,
            "tool_result": tool_result,
            "tool_calls": tool_calls,
            "trace": state.get("trace", [])
            + [
                TraceStep(trace_name, f"intent={intent}", 0.0),
                TraceStep(tool_name or "no_tool", detail, _elapsed_ms(started)),
            ],
        }

    @traceable(name="langgraph.compose", run_type="chain")
    def _compose_node(self, state: FinanceCrewState) -> dict[str, Any]:
        started = time.perf_counter()
        answer = self.composer.compose(
            state["question"],
            state["intent"],
            state.get("tool_name"),
            state.get("tool_result"),
        )
        return {
            "answer": answer,
            "trace": state.get("trace", [])
            + [
                TraceStep(
                    "langgraph.compose",
                    "formatted final answer",
                    _elapsed_ms(started),
                )
            ],
        }


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)
