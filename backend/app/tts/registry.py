from backend.app.tts.base import TextToSpeechProvider
from backend.app.tts.config import TTSConfig, TTSProviderConfigEntry
from backend.app.tts.mock import MockTTSProvider
from backend.app.tts.openai_tts import OpenAITTSProvider


def build_tts_provider(entry: TTSProviderConfigEntry) -> TextToSpeechProvider:
    if entry.name == "mock":
        return MockTTSProvider(model=entry.model)

    if entry.name == "openai_tts":
        return OpenAITTSProvider(
            model=entry.model,
            voice=entry.voice or "alloy",
            api_key_env=entry.api_key_env or "OPENAI_API_KEY",
            enabled=entry.enabled,
            placeholder=entry.placeholder,
        )

    return MockTTSProvider(model=entry.model)


def build_tts_providers(config: TTSConfig) -> dict[str, TextToSpeechProvider]:
    return {name: build_tts_provider(entry) for name, entry in config.providers.items()}
