from backend.app.providers.base import ChatProvider
from backend.app.providers.exceptions import ProviderNotConfiguredError
from backend.app.providers.types import ChatCompletionRequest, ChatCompletionResult, ProviderStatus


class OpenAIProvider(ChatProvider):
    name = "openai"

    def __init__(self, *, model: str, enabled: bool = False, api_key_env: str = "OPENAI_API_KEY") -> None:
        self._model = model
        self._enabled = enabled
        self._api_key_env = api_key_env

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
            "OpenAI provider adapter is a placeholder and not implemented yet.",
            provider=self.name,
        )
