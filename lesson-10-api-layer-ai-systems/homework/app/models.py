from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    id: str
    input_price_per_million: float
    output_price_per_million: float


MODEL_CATALOG = {
    "openrouter/free": ModelInfo(
        id="openrouter/free",
        input_price_per_million=0.0,
        output_price_per_million=0.0,
    ),
    "meta-llama/llama-3.2-3b-instruct:free": ModelInfo(
        id="meta-llama/llama-3.2-3b-instruct:free",
        input_price_per_million=0.0,
        output_price_per_million=0.0,
    ),
    "google/gemma-4-26b-a4b-it:free": ModelInfo(
        id="google/gemma-4-26b-a4b-it:free",
        input_price_per_million=0.0,
        output_price_per_million=0.0,
    ),
    "mistralai/mistral-nemo": ModelInfo(
        id="mistralai/mistral-nemo",
        input_price_per_million=0.02,
        output_price_per_million=0.03,
    ),
    "meta-llama/llama-3.1-8b-instruct": ModelInfo(
        id="meta-llama/llama-3.1-8b-instruct",
        input_price_per_million=0.02,
        output_price_per_million=0.05,
    ),
    "google/gemma-3-4b-it": ModelInfo(
        id="google/gemma-3-4b-it",
        input_price_per_million=0.04,
        output_price_per_million=0.08,
    ),
    "openai/gpt-4o-mini": ModelInfo(
        id="openai/gpt-4o-mini",
        input_price_per_million=0.15,
        output_price_per_million=0.60,
    ),
    "anthropic/claude-3.5-haiku": ModelInfo(
        id="anthropic/claude-3.5-haiku",
        input_price_per_million=0.80,
        output_price_per_million=4.00,
    ),
    "mistralai/mistral-large": ModelInfo(
        id="mistralai/mistral-large",
        input_price_per_million=2.00,
        output_price_per_million=6.00,
    ),
}


def get_model(model_id: str) -> ModelInfo:
    return MODEL_CATALOG.get(
        model_id,
        ModelInfo(id=model_id, input_price_per_million=0.0, output_price_per_million=0.0),
    )

