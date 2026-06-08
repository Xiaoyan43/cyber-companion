from backend.app.behavior.types import BehaviorDecision
from backend.app.providers.cost import estimate_cost, estimate_usage
from backend.app.providers.types import ChatCompletionResult


def build_local_completion(
    decision: BehaviorDecision,
    *,
    user_input: str,
) -> ChatCompletionResult:
    content = decision.local_response or "……"
    usage = estimate_usage([user_input], content)
    cost = estimate_cost("mock-boxi", usage)
    return ChatCompletionResult(
        provider="local-behavior",
        model="behavior-local",
        content=content,
        usage=usage,
        cost=cost,
        mock=True,
    )


def build_budget_block_completion(message: str) -> ChatCompletionResult:
    # Answered locally because a spend brake (daily turns / monthly USD /
    # reasoning model) tripped, so this turn never reaches a provider and costs
    # nothing.
    usage = estimate_usage([], message)
    cost = estimate_cost("mock-boxi", usage)
    return ChatCompletionResult(
        provider="local-budget",
        model="budget-guard",
        content=message,
        usage=usage,
        cost=cost,
        mock=True,
    )
