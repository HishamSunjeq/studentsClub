"""Static pricing table for cost estimation in telemetry.

Phase 2 will move this into the `ai_models` registry; for Phase 1 we hardcode
the small set of models we currently use so `ai_runs.cost_usd` is populated.

Prices are USD per million tokens (Mtokens), input/output.
"""

from decimal import Decimal

PRICING: dict[str, tuple[Decimal, Decimal]] = {
    # Anthropic Claude 4.x
    "claude-opus-4-7": (Decimal("15.00"), Decimal("75.00")),
    "claude-opus-4-6": (Decimal("15.00"), Decimal("75.00")),
    "claude-sonnet-4-6": (Decimal("3.00"), Decimal("15.00")),
    "claude-haiku-4-5": (Decimal("1.00"), Decimal("5.00")),
    "claude-haiku-4-5-20251001": (Decimal("1.00"), Decimal("5.00")),
    # OpenAI
    "gpt-4o": (Decimal("2.50"), Decimal("10.00")),
    "gpt-4o-mini": (Decimal("0.15"), Decimal("0.60")),
    "gpt-4o-2024-08-06": (Decimal("2.50"), Decimal("10.00")),
    # Embeddings (output cost = 0)
    "text-embedding-3-small": (Decimal("0.02"), Decimal("0.00")),
    "text-embedding-3-large": (Decimal("0.13"), Decimal("0.00")),
    # Mock provider (free)
    "mock": (Decimal("0.00"), Decimal("0.00")),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Return total cost in USD for a single LLM call. Unknown models default to 0.

    The caller is responsible for logging unknown models so we can add them
    here over time. Phase 2 reads from the `ai_models` table instead.
    """
    if model not in PRICING:
        # Try to match by prefix for versioned models (e.g. claude-opus-4-7-20260101).
        for key in PRICING:
            if model.startswith(key):
                in_price, out_price = PRICING[key]
                break
        else:
            return Decimal("0")
    else:
        in_price, out_price = PRICING[model]

    cost = (Decimal(input_tokens) * in_price + Decimal(output_tokens) * out_price) / Decimal("1000000")
    # Round to 6 decimal places to match the column precision.
    return cost.quantize(Decimal("0.000001"))
