from abc import ABC, abstractmethod
from collections.abc import Iterator

from backend.app.providers.types import (
    ChatCompletionRequest,
    ChatCompletionResult,
    ProviderStatus,
    StreamChunk,
)


class ChatProvider(ABC):
    name: str

    @abstractmethod
    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        raise NotImplementedError

    def complete_stream(self, request: ChatCompletionRequest) -> Iterator[StreamChunk]:
        result = self.complete(request)
        yield ("delta", result.content)
        yield ("usage", result.usage)

    @abstractmethod
    def status(self) -> ProviderStatus:
        raise NotImplementedError
