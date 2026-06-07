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
