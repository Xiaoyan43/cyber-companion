from __future__ import annotations

import base64
import binascii
import json
import os
import uuid
from typing import Any, Iterator

import httpx

from backend.app.tts.base import TextToSpeechProvider
from backend.app.tts.exceptions import TTSConfigError, TTSError
from backend.app.tts.types import SynthesisRequest, SynthesisResult, TTSProviderStatus

# Volcano Engine / Doubao speech HTTP TTS V3 (unidirectional chunked).
# Docs: https://www.volcengine.com/docs/6561/1598757
TTS_HTTP_ENDPOINT = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
STREAM_DONE_CODE = 20_000_000
STREAM_AUDIO_CODE = 0

ENV_API_KEY = "DOUBAO_TTS_API_KEY"
ENV_ACCESS_TOKEN = "DOUBAO_TTS_ACCESS_TOKEN"  # legacy alias for API key
ENV_VOICE_TYPE = "DOUBAO_TTS_VOICE_TYPE"
ENV_RESOURCE_ID = "DOUBAO_TTS_RESOURCE_ID"

DEFAULT_RESOURCE_ID = "seed-tts-1.0"
DEFAULT_FORMAT = "mp3"

FORMAT_TO_MIME: dict[str, str] = {
    "wav": "audio/wav",
    "pcm": "audio/pcm",
    "mp3": "audio/mpeg",
    "ogg_opus": "audio/ogg",
}


class DoubaoTTSProvider(TextToSpeechProvider):
    name = "doubao"
    cloud = True

    def __init__(
        self,
        *,
        enabled: bool = False,
        audio_format: str = DEFAULT_FORMAT,
        resource_id: str | None = None,
        uid: str = "cyber-companion",
        timeout_s: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._enabled = enabled
        self._audio_format = audio_format
        self._resource_id = resource_id
        self._uid = uid
        self._timeout_s = timeout_s
        self._http_client = http_client

    def _env(self, key: str) -> str | None:
        value = os.getenv(key, "").strip()
        return value or None

    def _api_key(self) -> str | None:
        return self._env(ENV_API_KEY) or self._env(ENV_ACCESS_TOKEN)

    def _credentials(self) -> dict[str, str] | None:
        api_key = self._api_key()
        voice_type = self._env(ENV_VOICE_TYPE)
        if not api_key or not voice_type:
            return None
        return {
            "api_key": api_key,
            "voice_type": voice_type,
            "resource_id": self._env(ENV_RESOURCE_ID) or self._resource_id or DEFAULT_RESOURCE_ID,
        }

    def is_configured(self) -> bool:
        return self._credentials() is not None

    def status(self) -> TTSProviderStatus:
        creds = self._credentials()
        voice_type = creds["voice_type"] if creds else (self._env(ENV_VOICE_TYPE) or "doubao-tts")
        return TTSProviderStatus(
            name=self.name,
            enabled=self._enabled,
            model=voice_type,
            configured=creds is not None,
            api_key_present=self._api_key() is not None,
            placeholder=False,
            cloud=True,
        )

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        creds = self._credentials()
        if not creds:
            raise TTSConfigError(
                "Doubao TTS is selected but DOUBAO_TTS_API_KEY (or DOUBAO_TTS_ACCESS_TOKEN) "
                "and DOUBAO_TTS_VOICE_TYPE must be configured."
            )

        text = request.text.strip()
        if not text:
            raise TTSError("Text payload is empty.", provider=self.name, status_code=400)

        payload = self._build_request_payload(text, creds)
        headers = self._build_request_headers(creds)

        try:
            audio_bytes = self._stream_synthesis(payload, headers)
        except httpx.HTTPError as error:
            raise TTSError(
                f"Doubao TTS network error: {error}",
                provider=self.name,
            ) from error

        if not audio_bytes:
            raise TTSError(
                "Doubao TTS returned empty audio.",
                provider=self.name,
            )

        mime_type = FORMAT_TO_MIME.get(self._audio_format, "application/octet-stream")
        duration_ms = max(1, len(text) * 45)

        return SynthesisResult(
            provider=self.name,
            model=creds["voice_type"],
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            duration_ms=duration_ms,
            mock=False,
        )

    def _build_request_headers(self, creds: dict[str, str]) -> dict[str, str]:
        return {
            "X-Api-Key": creds["api_key"],
            "X-Api-Resource-Id": creds["resource_id"],
            "X-Api-Request-Id": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }

    def _build_request_payload(self, text: str, creds: dict[str, str]) -> dict[str, Any]:
        return {
            "user": {
                "uid": self._uid,
            },
            "req_params": {
                "text": text,
                "speaker": creds["voice_type"],
                "audio_params": {
                    "format": self._audio_format,
                    "sample_rate": 24_000,
                },
            },
        }

    def _stream_synthesis(self, payload: dict[str, Any], headers: dict[str, str]) -> bytes:
        if self._http_client is not None:
            with self._http_client.stream(
                "POST",
                TTS_HTTP_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=self._timeout_s,
            ) as response:
                return self._read_streamed_audio(response)

        with httpx.Client(timeout=self._timeout_s) as client:
            with client.stream(
                "POST",
                TTS_HTTP_ENDPOINT,
                json=payload,
                headers=headers,
            ) as response:
                return self._read_streamed_audio(response)

    def _read_streamed_audio(self, response: httpx.Response) -> bytes:
        if response.status_code in {401, 403}:
            raise TTSError(
                "Doubao TTS authentication failed. Check DOUBAO_TTS_API_KEY.",
                provider=self.name,
                status_code=503,
            )

        if response.status_code >= 400:
            raise TTSError(
                f"Doubao TTS request failed with HTTP {response.status_code}.",
                provider=self.name,
                status_code=502,
            )

        audio_parts: list[bytes] = []
        for line in _iter_response_lines(response):
            chunk = _parse_stream_chunk(line)
            if chunk is None:
                continue

            code = chunk.get("code")
            if code == STREAM_AUDIO_CODE:
                data = chunk.get("data")
                if isinstance(data, str) and data:
                    try:
                        audio_parts.append(base64.b64decode(data, validate=True))
                    except (ValueError, binascii.Error) as error:
                        raise TTSError(
                            "Doubao TTS returned invalid base64 audio.",
                            provider=self.name,
                        ) from error
                continue

            if code == STREAM_DONE_CODE:
                return b"".join(audio_parts)

            message = _response_message(chunk) or f"error code {code}"
            status_code = 503 if _looks_like_auth_or_quota_error(message) else 502
            raise TTSError(
                f"Doubao TTS synthesis failed: {message}",
                provider=self.name,
                status_code=status_code,
            )

        if audio_parts:
            return b"".join(audio_parts)

        raise TTSError(
            "Doubao TTS stream ended without audio data.",
            provider=self.name,
        )


def _iter_response_lines(response: httpx.Response) -> Iterator[str]:
    for raw_line in response.iter_lines():
        if not raw_line:
            continue
        if isinstance(raw_line, bytes):
            yield raw_line.decode("utf-8")
        else:
            yield raw_line


def _parse_stream_chunk(line: str) -> dict[str, Any] | None:
    payload = line.strip()
    if not payload:
        return None
    if payload.startswith("data:"):
        payload = payload[5:].strip()
    if not payload:
        return None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _response_message(body: dict[str, Any]) -> str | None:
    message = body.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()
    return None


def _looks_like_auth_or_quota_error(message: str) -> bool:
    lowered = message.lower()
    markers = (
        "authenticate",
        "auth",
        "grant",
        "access denied",
        "permission denied",
        "quota exceeded",
        "quota",
        "invalid x-api",
        "api key",
    )
    return any(marker in lowered for marker in markers)
