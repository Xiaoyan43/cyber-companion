from backend.app.stt.base import SpeechToTextProvider
from backend.app.stt.config import STTConfig, STTProviderConfigEntry
from backend.app.stt.doubao import DoubaoASRProvider
from backend.app.stt.faster_whisper import FasterWhisperProvider
from backend.app.stt.mock import MockSTTProvider
from backend.app.stt.openai_whisper import OpenAIWhisperProvider


def build_stt_provider(entry: STTProviderConfigEntry) -> SpeechToTextProvider:
    if entry.name == "mock":
        return MockSTTProvider(model=entry.model)

    if entry.name == "faster_whisper":
        return FasterWhisperProvider(
            model=entry.model,
            enabled=entry.enabled,
        )

    if entry.name == "openai_whisper":
        return OpenAIWhisperProvider(
            model=entry.model,
            api_key_env=entry.api_key_env or "OPENAI_API_KEY",
            enabled=entry.enabled,
            placeholder=entry.placeholder,
        )

    if entry.name == "doubao":
        return DoubaoASRProvider(
            model=entry.model,
            enabled=entry.enabled,
        )

    return MockSTTProvider(model=entry.model)


def build_stt_providers(config: STTConfig) -> dict[str, SpeechToTextProvider]:
    return {name: build_stt_provider(entry) for name, entry in config.providers.items()}
