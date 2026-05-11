import json
from contextlib import contextmanager, nullcontext
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .config import Settings


_initialized = False


def init_phoenix(settings: Settings) -> None:
    global _initialized
    if _initialized or not settings.phoenix_enabled:
        return

    try:
        from phoenix.otel import register

        register(
            project_name=settings.phoenix_project_name,
            endpoint=settings.phoenix_collector_endpoint,
            protocol="http/protobuf",
            batch=False,
        )
        _initialized = True
    except Exception as error:
        print(f"Phoenix tracing disabled: {error}")


def tracing_enabled(settings: Settings) -> bool:
    return bool(settings.phoenix_enabled and _initialized)


def tracing_initialized() -> bool:
    return _initialized


def _json_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


@contextmanager
def start_span(name: str, kind: str, input_value: Any | None = None, **attributes: Any):
    tracer = trace.get_tracer("lesson-10-rag-api")

    try:
        with tracer.start_as_current_span(name) as span:
            span.set_attribute("openinference.span.kind", kind.upper())
            if input_value is not None:
                span.set_attribute("input.value", _json_value(input_value))
            for key, value in attributes.items():
                if value is not None:
                    span.set_attribute(key, value)
            yield span
    except Exception as error:
        span = trace.get_current_span()
        span.set_status(Status(StatusCode.ERROR, str(error)))
        span.record_exception(error)
        raise


def set_output(span, output: Any) -> None:
    if span is None:
        return
    span.set_attribute("output.value", _json_value(output))


def set_attribute(span, key: str, value: Any) -> None:
    if span is None or value is None:
        return
    span.set_attribute(key, value)


def maybe_span(settings: Settings, name: str, kind: str, input_value: Any | None = None, **attributes: Any):
    if not tracing_enabled(settings):
        return nullcontext(None)
    return start_span(name, kind, input_value, **attributes)
