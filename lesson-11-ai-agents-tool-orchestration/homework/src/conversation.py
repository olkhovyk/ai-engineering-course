from __future__ import annotations

from dataclasses import dataclass

from src.constants import Intent, Period
from src.routing import Route, Router


@dataclass
class ConversationContext:
    last_route: Route | None = None

    def remember(self, route: Route) -> None:
        if route.intent != Intent.UNKNOWN:
            self.last_route = route

    def resolve_followup(self, question: str) -> Route | None:
        if self.last_route is None:
            return None

        normalized = question.casefold().strip()
        if any(phrase in normalized for phrase in ["за місяць", "місяць", "month"]):
            return Route(
                intent=self.last_route.intent,
                category=self.last_route.category,
                period=Period.CURRENT_MONTH,
            )

        return None


class ContextualRouter:
    def __init__(self, base_router: Router, context: ConversationContext):
        self.base_router = base_router
        self.context = context
        self.last_route: Route | None = None

    def route(self, question: str) -> Route:
        followup_route = self.context.resolve_followup(question)
        if followup_route is not None:
            self.last_route = followup_route
            return followup_route
        route = self.base_router.route(question)
        self.last_route = route
        return route
