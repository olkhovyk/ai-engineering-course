from __future__ import annotations

import asyncio
import inspect
import os
from dataclasses import asdict, is_dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, TypeVar


F = TypeVar("F", bound=Callable[..., Any])
TRUE_VALUES = {"1", "true", "yes", "on"}


def is_langsmith_enabled() -> bool:
    tracing_enabled = os.getenv("LANGSMITH_TRACING", "").casefold() in TRUE_VALUES
    return tracing_enabled and bool(os.getenv("LANGSMITH_API_KEY"))


def traceable(
    *,
    name: str,
    run_type: str = "chain",
    metadata: dict[str, Any] | None = None,
) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not is_langsmith_enabled():
                return func(*args, **kwargs)

            try:
                from langsmith import traceable as langsmith_traceable
            except ModuleNotFoundError:
                return func(*args, **kwargs)

            traced_func = langsmith_traceable(
                name=name,
                run_type=run_type,
                metadata=metadata,
                process_inputs=serialize_for_langsmith,
                process_outputs=serialize_for_langsmith,
            )(func)
            return traced_func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def flush_langsmith() -> None:
    if not is_langsmith_enabled():
        return

    try:
        from langsmith import Client
    except ModuleNotFoundError:
        return

    result = Client().flush()
    if inspect.isawaitable(result):
        asyncio.run(result)


def serialize_for_langsmith(value: Any) -> Any:
    if is_dataclass(value):
        return serialize_for_langsmith(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {
            str(serialize_for_langsmith(key)): serialize_for_langsmith(item)
            for key, item in value.items()
            if key not in {"self"}
        }
    if isinstance(value, list):
        return [serialize_for_langsmith(item) for item in value]
    if isinstance(value, tuple):
        return [serialize_for_langsmith(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "__class__") and value.__class__.__name__ in {
        "BaselineAgent",
        "CrewCoordinator",
        "StatsAgent",
        "SavingsAgent",
        "RiskAgent",
        "RuleBasedRouter",
        "LLMRouter",
        "TemplateComposer",
        "LLMComposer",
        "OpenRouterClient",
    }:
        return value.__class__.__name__
    return value
