import os

from backend.app.providers.base import ChatProvider
from backend.app.providers.claude import ClaudeProvider
from backend.app.providers.config import ProviderConfigEntry, ProvidersConfig
from backend.app.providers.deepseek import DeepSeekProvider
from backend.app.providers.local import LocalModelProvider
from backend.app.providers.mock import MockProvider
from backend.app.providers.openai import OpenAIProvider
from backend.app.providers.openrouter import OpenRouterProvider
from backend.app.providers.venice import VeniceProvider


TAGGER_API_KEY_ENV = "OPENROUTER_TAGGER_API_KEY"
LEGACY_TAGGER_API_KEY_ENV = "OPENROUTER_GEMINI_API_KEY"


def _tagger_api_key_env(configured: str | None) -> str:
    """Prefer the neutral env name while keeping existing local setups working."""
    selected = configured or TAGGER_API_KEY_ENV
    if (
        selected == TAGGER_API_KEY_ENV
        and not os.getenv(TAGGER_API_KEY_ENV, "").strip()
        and os.getenv(LEGACY_TAGGER_API_KEY_ENV, "").strip()
    ):
        return LEGACY_TAGGER_API_KEY_ENV
    return selected


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

    if entry.name == "openrouter":
        return OpenRouterProvider(
            model=entry.model,
            base_url=entry.base_url or "https://openrouter.ai/api/v1",
            api_key_env=entry.api_key_env or "OPENROUTER_API_KEY",
            enabled=entry.enabled,
        )

    if entry.name in {"tagger", "gemini"}:
        # Dedicated auxiliary model routed through OpenRouter. "gemini" remains a config
        # alias for backward compatibility with local deployments created before the
        # provider stopped being tied to a specific model family.
        return OpenRouterProvider(
            model=entry.model,
            base_url=entry.base_url or "https://openrouter.ai/api/v1",
            api_key_env=_tagger_api_key_env(entry.api_key_env),
            enabled=entry.enabled,
        )

    return MockProvider(model=entry.model)


def build_providers(config: ProvidersConfig) -> dict[str, ChatProvider]:
    return {name: build_provider(entry) for name, entry in config.providers.items()}
