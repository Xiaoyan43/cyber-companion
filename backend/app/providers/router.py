from collections.abc import Iterator

from backend.app.providers.base import ChatProvider
from backend.app.providers.config import ProvidersConfig, load_providers_config
from backend.app.providers.exceptions import ProviderConfigError, ProviderError
from backend.app.providers.registry import build_providers
from backend.app.providers.types import (
    ChatCompletionRequest,
    ChatCompletionResult,
    ProviderStatus,
    StreamChunk,
)


class ProviderRouter:
    def __init__(self, config: ProvidersConfig, providers: dict[str, ChatProvider]) -> None:
        self.config = config
        self.providers = providers

    @classmethod
    def from_config(cls, config: ProvidersConfig | None = None) -> "ProviderRouter":
        loaded = config or load_providers_config()
        return cls(loaded, build_providers(loaded))

    def resolve_provider_name(self, requested: str | None = None) -> str:
        if self.config.force_mock:
            return "mock"

        provider_name = requested or self.config.default_provider
        if provider_name not in self.providers:
            raise ProviderConfigError(f"Unknown provider: {provider_name}")

        return provider_name

    def get_provider(self, requested: str | None = None) -> ChatProvider:
        provider_name = self.resolve_provider_name(requested)
        return self.providers[provider_name]

    def list_status(self) -> list[ProviderStatus]:
        return [provider.status() for provider in self.providers.values()]

    def complete(
        self,
        request: ChatCompletionRequest,
        *,
        provider_name: str | None = None,
    ) -> ChatCompletionResult:
        provider = self.get_provider(provider_name)
        return provider.complete(request)

    def complete_stream(
        self,
        request: ChatCompletionRequest,
        *,
        provider_name: str | None = None,
    ) -> Iterator[StreamChunk]:
        provider = self.get_provider(provider_name)
        yield from provider.complete_stream(request)


_router: ProviderRouter | None = None


def get_provider_router() -> ProviderRouter:
    global _router
    if _router is None:
        _router = ProviderRouter.from_config()
    return _router


def reset_provider_router() -> None:
    global _router
    _router = None
