from .models import get_model


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    model_info = get_model(model)
    input_cost = input_tokens * model_info.input_price_per_million / 1_000_000
    output_cost = output_tokens * model_info.output_price_per_million / 1_000_000
    return round(input_cost + output_cost, 8)
