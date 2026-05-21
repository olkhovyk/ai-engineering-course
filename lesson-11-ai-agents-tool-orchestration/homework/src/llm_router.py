from __future__ import annotations

import json
import os
from typing import Protocol

from src.constants import Category, Intent
from src.langsmith_tracing import traceable
from src.routing import Route, RuleBasedRouter


VALID_INTENTS = {intent.value for intent in Intent}
VALID_CATEGORIES = {category.value for category in Category}


class RouterLLMClient(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        ...


class LLMRouter:
    def __init__(
        self,
        client: RouterLLMClient,
        fallback_router: RuleBasedRouter | None = None,
    ):
        self.client = client
        self.fallback_router = fallback_router or RuleBasedRouter()

    @traceable(name="router.llm", run_type="chain")
    def route(self, question: str) -> Route:
        try:
            response = self.client.complete(_system_prompt(), question)
            return parse_route_json(response)
        except ValueError:
            return self.fallback_router.route(question)


class OpenRouterClient(RouterLLMClient):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int = 80,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("OPENROUTER_ROUTER_MODEL", "mistralai/mistral-nemo")
        self.max_tokens = max_tokens
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required for --router llm")

    @traceable(name="openrouter.complete", run_type="llm")
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""


def parse_route_json(text: str) -> Route:
    try:
        data = json.loads(_strip_code_fence(text))
    except json.JSONDecodeError as error:
        raise ValueError("Router response is not valid JSON") from error

    intent = data.get("intent")
    category = data.get("category")

    if intent not in VALID_INTENTS:
        raise ValueError(f"Unsupported intent: {intent}")
    if category is not None and category not in VALID_CATEGORIES:
        raise ValueError(f"Unsupported category: {category}")
    if intent == Intent.CATEGORY_SPENDING and category is None:
        raise ValueError("category_spending requires category")

    return Route(
        intent=Intent(intent),
        category=Category(category) if category is not None else None,
    )


def _system_prompt() -> str:
    return (
        "You are an intent router for a personal finance assistant. "
        "Return only JSON. No markdown. "
        "Use valid intents: category_spending, top_categories, subscriptions, "
        "delivery, cashflow, savings, fraud, unknown. "
        "Use category only when needed. Valid categories: coffee, groceries, "
        "restaurants, delivery, transport, entertainment, shopping, health, "
        "subscriptions, utilities, salary, credit_payment, travel. "
        'Output format: {"intent": "...", "category": null}.'
    )


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped
