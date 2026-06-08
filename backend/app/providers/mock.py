from collections.abc import Iterator

from backend.app.providers.base import ChatProvider
from backend.app.providers.cost import estimate_cost, estimate_usage
from backend.app.providers.types import (
    ChatCompletionRequest,
    ChatCompletionResult,
    ProviderStatus,
    StreamChunk,
)


class MockProvider(ChatProvider):
    name = "mock"

    def __init__(self, model: str = "mock-boxi") -> None:
        self._model = model

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        latest = next(
            (message.content for message in reversed(request.messages) if message.role == "user"),
            "",
        )
        content = (
            f"收到：{latest}。"
            "现在还是 mock provider，在盒子里假装思考过了。"
            "真正的 DeepSeek 还没接密钥，别指望我已经联网成精。"
        )
        usage = estimate_usage([message.content for message in request.messages], content)
        cost = estimate_cost(self._model, usage)
        return ChatCompletionResult(
            provider=self.name,
            model=self._model,
            content=content,
            usage=usage,
            cost=cost,
            mock=True,
        )

    def complete_stream(self, request: ChatCompletionRequest) -> Iterator[StreamChunk]:
        result = self.complete(request)
        content = result.content
        midpoint = max(1, len(content) // 2)
        yield ("delta", content[:midpoint])
        if midpoint < len(content):
            yield ("delta", content[midpoint:])
        yield ("usage", result.usage)

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            enabled=True,
            model=self._model,
            configured=True,
            api_key_present=False,
            placeholder=False,
        )
