from __future__ import annotations

import os
from typing import Any, Iterator

import httpx

from backend.app.tts.base import TextToSpeechProvider
from backend.app.tts.exceptions import TTSConfigError, TTSError
from backend.app.tts.text_cleanup import clean_text_for_tts
from backend.app.tts.types import SynthesisRequest, SynthesisResult, TTSProviderStatus

FISH_AUDIO_TTS_URL = "https://api.fish.audio/v1/tts"
DEFAULT_VOICE_ID = "fbe02f8306fc4d3d915e9871722a39d5"
DEFAULT_MODEL = "s2-pro"
DEFAULT_FORMAT = "opus"
# Nudged above the API default (0.7) for more expressive delivery — listening-test value,
# revisit if it trades too much stability for variety.
DEFAULT_TEMPERATURE = 0.85

ENV_API_KEY = "FISH_AUDIO_API_KEY"
ENV_VOICE_ID = "FISH_AUDIO_VOICE_ID"

FORMAT_TO_MIME: dict[str, str] = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
    "opus": "audio/ogg; codecs=opus",
}

_shared_http_client: httpx.Client | None = None


def get_shared_http_client() -> httpx.Client:
    global _shared_http_client
    if _shared_http_client is None:
        try:
            _shared_http_client = httpx.Client(timeout=30.0, http2=True)
        except ImportError:
            _shared_http_client = httpx.Client(timeout=30.0)
    return _shared_http_client


def speech_rate_to_speed(speech_rate: int) -> float:
    """Map internal speech_rate (-20..+20) to Fish Audio prosody.speed (0.5..2.0).

    Negative rate = slower (comfort register); positive = faster (sharp/playful).
    """
    return round(max(0.5, min(2.0, 1.0 + speech_rate * 0.025)), 2)


class FishAudioTTSProvider(TextToSpeechProvider):
    name = "fish_audio"
    cloud = True

    def __init__(
        self,
        *,
        enabled: bool = False,
        api_key_env: str = ENV_API_KEY,
        voice_id: str | None = None,
        audio_format: str = DEFAULT_FORMAT,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        timeout_s: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._enabled = enabled
        self._api_key_env = api_key_env
        self._voice_id = voice_id
        self._audio_format = audio_format
        self._model = model
        self._temperature = temperature
        self._timeout_s = timeout_s
        self._http_client = http_client

    def _api_key(self) -> str | None:
        value = os.getenv(self._api_key_env, "").strip()
        return value or None

    def _resolved_voice_id(self) -> str:
        return (
            self._voice_id
            or os.getenv(ENV_VOICE_ID, "").strip()
            or DEFAULT_VOICE_ID
        )

    def is_configured(self) -> bool:
        return self._api_key() is not None

    def status(self) -> TTSProviderStatus:
        return TTSProviderStatus(
            name=self.name,
            enabled=self._enabled,
            model=self._model,
            configured=self.is_configured(),
            api_key_present=self._api_key() is not None,
            placeholder=False,
            cloud=True,
        )

    def stream_mime_type(self) -> str:
        return FORMAT_TO_MIME.get(self._audio_format, "application/octet-stream")

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        audio_bytes = b"".join(self.synthesize_stream(request))
        if not audio_bytes:
            raise TTSError("Fish Audio returned empty audio.", provider=self.name)
        mime_type = FORMAT_TO_MIME.get(self._audio_format, "application/octet-stream")
        duration_ms = max(1, len(request.text.strip()) * 45)
        return SynthesisResult(
            provider=self.name,
            model=self._model,
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            duration_ms=duration_ms,
            mock=False,
        )

    def synthesize_stream(self, request: SynthesisRequest) -> Iterator[bytes]:
        api_key = self._api_key()
        if not api_key:
            raise TTSConfigError(
                f"Fish Audio TTS is selected but {self._api_key_env} is not set."
            )

        text = clean_text_for_tts(request.text.strip())
        if not text:
            raise TTSError("Text payload is empty.", provider=self.name, status_code=400)

        payload: dict[str, Any] = {
            "text": text,
            "reference_id": self._resolved_voice_id(),
            "format": self._audio_format,
            "latency": "balanced",
            "temperature": self._temperature,
        }
        # normalize_loudness defaults to true server-side, which flattens the volume
        # swing that [whispering]/[shouting]-style tags rely on to be audible.
        prosody: dict[str, Any] = {"normalize_loudness": False}
        if request.speech_rate != 0:
            prosody["speed"] = speech_rate_to_speed(request.speech_rate)
        payload["prosody"] = prosody

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "model": self._model,
        }

        client = self._http_client or get_shared_http_client()
        try:
            with client.stream(
                "POST",
                FISH_AUDIO_TTS_URL,
                json=payload,
                headers=headers,
                timeout=self._timeout_s,
            ) as response:
                if response.status_code in {401, 403}:
                    raise TTSError(
                        f"Fish Audio authentication failed. Check {self._api_key_env}.",
                        provider=self.name,
                        status_code=503,
                    )
                if response.status_code >= 400:
                    raise TTSError(
                        f"Fish Audio request failed with HTTP {response.status_code}.",
                        provider=self.name,
                        status_code=502,
                    )
                yielded = False
                for chunk in response.iter_bytes():
                    if chunk:
                        yielded = True
                        yield chunk
                if not yielded:
                    raise TTSError(
                        "Fish Audio stream ended without audio data.",
                        provider=self.name,
                    )
        except httpx.HTTPError as error:
            raise TTSError(
                f"Fish Audio network error: {error}",
                provider=self.name,
            ) from error
