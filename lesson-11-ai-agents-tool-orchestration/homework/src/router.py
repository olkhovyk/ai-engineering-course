from __future__ import annotations

from src.routing import Route, RuleBasedRouter


def route_question(question: str) -> Route:
    return RuleBasedRouter().route(question)
