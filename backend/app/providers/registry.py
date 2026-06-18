from backend.app.providers.base import ChatProvider
from backend.app.providers.claude import ClaudeProvider
from backend.app.providers.config import ProviderConfigEntry, ProvidersConfig
from backend.app.providers.deepseek import DeepSeekProvider
from backend.app.providers.local import LocalModelProvider
from backend.app.providers.mock import MockProvider
from backend.app.providers.openai import OpenAIProvider
from backend.app.providers.venice import VeniceProvider


def build_provider(entry: ProviderConfigEntry) -> ChatProvider:
    if entry.name == "mock":
        return MockProvider(model=entry.model)

    if entry.name == "deepseek":
        return DeepSeekProvider(
            model=entry.model,
            base_url=entry.base_url or "https://api.deepseek.com",
            api_key_env=entry.api_key_env or "DEEPSEEK_API_KEY",
            enabled=entry.enabled,
        )

    if entry.name == "openai":
        return OpenAIProvider(
            model=entry.model,
            enabled=entry.enabled,
            api_key_env=entry.api_key_env or "OPENAI_API_KEY",
        )

    if entry.name == "local":
        return LocalModelProvider(
            model=entry.model,
            base_url=entry.base_url or "http://localhost:11434",
            enabled=entry.enabled,
        )

    if entry.name == "venice":
        return VeniceProvider(
            model=entry.model,
            base_url=entry.base_url or "https://api.venice.ai/api/v1",
            api_key_env=entry.api_key_env or "VENICE_API_KEY",
            enabled=entry.enabled,
        )

    if entry.name == "claude":
        return ClaudeProvider(
            model=entry.model,
            base_url=entry.base_url or "https://api.anthropic.com/v1",
            api_key_env=entry.api_key_env or "ANTHROPIC_API_KEY",
            enabled=entry.enabled,
        )

    return MockProvider(model=entry.model)


def build_providers(config: ProvidersConfig) -> dict[str, ChatProvider]:
    return {name: build_provider(entry) for name, entry in config.providers.items()}
