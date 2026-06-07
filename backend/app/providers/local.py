from backend.app.providers.base import ChatProvider
from backend.app.providers.exceptions import ProviderNotConfiguredError
from backend.app.providers.types import ChatCompletionRequest, ChatCompletionResult, ProviderStatus


class LocalModelProvider(ChatProvider):
    name = "local"

    def __init__(self, *, model: str, base_url: str, enabled: bool = False) -> None:
        self._model = model
        self._base_url = base_url
        self._enabled = enabled

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            enabled=self._enabled,
            model=self._model,
            configured=False,
            api_key_present=False,
            placeholder=True,
        )

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        raise ProviderNotConfiguredError(
            "Local model provider adapter is a placeholder and not implemented yet.",
            provider=self.name,
        )
