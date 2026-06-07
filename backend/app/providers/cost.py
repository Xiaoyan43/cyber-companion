from backend.app.providers.types import CostEstimate, TokenUsage

# Approximate list prices; verify against official provider pricing before budgeting.
PRICING_PER_MILLION_USD: dict[str, dict[str, float]] = {
    "deepseek-chat": {"input": 0.28, "output": 0.42, "source": "deepseek-list-price-2026-03"},
    "gpt-5.4-nano": {"input": 0.10, "output": 0.40, "source": "placeholder-openai-estimate"},
    "local-model": {"input": 0.0, "output": 0.0, "source": "local-assumed-free"},
    "mock-boxi": {"input": 0.0, "output": 0.0, "source": "mock-provider"},
}


def estimate_token_count(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0

    # Rough heuristic for mixed Chinese/English MVP budgeting.
    return max(1, len(stripped) // 3)


def estimate_usage(messages: list[str], output_text: str) -> TokenUsage:
    input_tokens = sum(estimate_token_count(message) for message in messages)
    output_tokens = estimate_token_count(output_text)
    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )


def estimate_cost(model: str, usage: TokenUsage) -> CostEstimate:
    pricing = PRICING_PER_MILLION_USD.get(
        model,
        {"input": 0.0, "output": 0.0, "source": "unknown-model"},
    )
    input_usd = usage.input_tokens * pricing["input"] / 1_000_000
    output_usd = usage.output_tokens * pricing["output"] / 1_000_000
    return CostEstimate(
        input_usd=round(input_usd, 8),
        output_usd=round(output_usd, 8),
        total_usd=round(input_usd + output_usd, 8),
        pricing_source=str(pricing["source"]),
    )
