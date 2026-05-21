from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.constants import Category, Intent, Period
from src.langsmith_tracing import traceable


@dataclass(frozen=True)
class Route:
    intent: Intent
    category: Category | None = None
    period: Period = Period.LAST_7_DAYS


class Router(Protocol):
    def route(self, question: str) -> Route:
        ...


class RuleBasedRouter:
    @traceable(name="router.rule", run_type="chain")
    def route(self, question: str) -> Route:
        normalized = question.casefold()

        if any(word in normalized for word in ["fraud", "підозр", "не робив", "не робила", "booking.com", "aliexpress"]):
            return Route(intent=Intent.FRAUD)

        if any(word in normalized for word in ["підпис", "subscription", "netflix", "spotify", "sportlife"]):
            return Route(intent=Intent.SUBSCRIPTIONS)

        if any(word in normalized for word in ["зеконом", "економ", "заощад", "скоротити", "скорот"]):
            return Route(intent=Intent.SAVINGS)

        if any(word in normalized for word in ["плюс", "мінус", "баланс", "cashflow", "кешфлоу"]):
            return Route(intent=Intent.CASHFLOW)

        if any(word in normalized for word in ["топ", "top", "категор"]):
            return Route(intent=Intent.TOP_CATEGORIES)

        if any(word in normalized for word in ["достав", "delivery", "glovo", "bolt food", "uber eats"]):
            return Route(intent=Intent.DELIVERY)

        if any(word in normalized for word in ["каву", "кава", "coffee"]):
            return Route(intent=Intent.CATEGORY_SPENDING, category=Category.COFFEE)

        return Route(intent=Intent.UNKNOWN)
