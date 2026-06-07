from __future__ import annotations

import os

from backend.app.tts.base import TextToSpeechProvider
from backend.app.tts.exceptions import TTSConfigError
from backend.app.tts.types import SynthesisRequest, SynthesisResult, TTSProviderStatus


class OpenAITTSProvider(TextToSpeechProvider):
    name = "openai_tts"
    cloud = True

    def __init__(
        self,
        *,
        model: str = "tts-1",
        voice: str = "alloy",
        api_key_env: str = "OPENAI_API_KEY",
        enabled: bool = False,
        placeholder: bool = True,
    ) -> None:
        self._model = model
        self._voice = voice
        self._api_key_env = api_key_env
        self._enabled = enabled
        self._placeholder = placeholder

    def _api_key(self) -> str | None:
        value = os.getenv(self._api_key_env, "").strip()
        return value or None

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        if self._placeholder:
            raise TTSConfigError(
                "OpenAI TTS adapter is a placeholder in this MVP pass. "
                "Use mock TTS or implement the cloud adapter explicitly."
            )

        api_key = self._api_key()
        if not api_key:
            raise TTSConfigError(
                f"OpenAI TTS is selected but `{self._api_key_env}` is not configured."
            )

        raise TTSConfigError("Cloud OpenAI TTS synthesis is not wired in this MVP pass.")

    def status(self) -> TTSProviderStatus:
        api_key_present = self._api_key() is not None
        return TTSProviderStatus(
            name=self.name,
            enabled=self._enabled,
            model=self._model,
            configured=not self._placeholder and api_key_present,
            api_key_present=api_key_present,
            placeholder=self._placeholder,
            cloud=True,
        )
