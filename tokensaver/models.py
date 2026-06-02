"""Model metadata and pricing helpers.

Prices are expressed as USD per 1M tokens. Values are intentionally editable
local defaults, not a live pricing source.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    model: str
    input_per_million: float
    output_per_million: float
    notes: str = ""


MODEL_PRICES: dict[str, ModelPrice] = {
    "anthropic/claude-haiku-4-5": ModelPrice(
        model="anthropic/claude-haiku-4-5",
        input_per_million=1.0,
        output_per_million=5.0,
        notes="Placeholder local default. Verify before billing use.",
    ),
    "anthropic/claude-sonnet-4-6": ModelPrice(
        model="anthropic/claude-sonnet-4-6",
        input_per_million=3.0,
        output_per_million=15.0,
        notes="Placeholder local default. Verify before billing use.",
    ),
    "anthropic/claude-opus-4-6": ModelPrice(
        model="anthropic/claude-opus-4-6",
        input_per_million=15.0,
        output_per_million=75.0,
        notes="Placeholder local default. Verify before billing use.",
    ),
    "openai/gpt-4.1-mini": ModelPrice(
        model="openai/gpt-4.1-mini",
        input_per_million=0.4,
        output_per_million=1.6,
        notes="Placeholder local default. Verify before billing use.",
    ),
    "openai/gpt-4.1": ModelPrice(
        model="openai/gpt-4.1",
        input_per_million=2.0,
        output_per_million=8.0,
        notes="Placeholder local default. Verify before billing use.",
    ),
}


def get_model_price(model: str | None) -> ModelPrice | None:
    if not model:
        return None
    return MODEL_PRICES.get(model)


def estimate_cost_usd(
    *,
    model: str | None,
    input_tokens: int,
    output_tokens: int = 0,
) -> float | None:
    price = get_model_price(model)
    if not price:
        return None
    return (
        input_tokens / 1_000_000 * price.input_per_million
        + output_tokens / 1_000_000 * price.output_per_million
    )

