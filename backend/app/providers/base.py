from abc import ABC, abstractmethod

from backend.app.providers.types import ChatCompletionRequest, ChatCompletionResult, ProviderStatus


class ChatProvider(ABC):
    name: str

    @abstractmethod
    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> ProviderStatus:
        raise NotImplementedError
