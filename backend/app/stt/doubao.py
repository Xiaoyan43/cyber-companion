from __future__ import annotations

import base64
import io
import os
import uuid
import wave
from typing import Any

import httpx
import numpy as np

from backend.app.stt.base import SpeechToTextProvider
from backend.app.stt.exceptions import STTConfigError, STTError
from backend.app.stt.faster_whisper import decode_audio_bytes
from backend.app.stt.types import STTProviderStatus, TranscriptionRequest, TranscriptionResult

# Volcano Engine / Doubao ASR flash (one-shot, lowest latency for short clips).
# Docs: https://www.volcengine.com/docs/6561/1631584
ASR_FLASH_ENDPOINT = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
DEFAULT_RESOURCE_ID = "volc.bigasr.auc_turbo"
DEFAULT_MODEL_NAME = "bigmodel"
SUCCESS_STATUS_CODE = "20000000"
SILENT_STATUS_CODE = "20000003"

ENV_API_KEY = "DOUBAO_API_KEY"
ENV_RESOURCE_ID = "DOUBAO_ASR_RESOURCE_ID"

TARGET_SAMPLE_RATE = 16_000

LANGUAGE_ALIASES: dict[str, str] = {
    "zh": "zh-CN",
    "en": "en-US",
    "ja": "ja-JP",
    "yue": "yue-CN",
}

_shared_http_client: httpx.Client | None = None
_shared_http_client_timeout: float | None = None


def _create_http_client(timeout_s: float) -> httpx.Client:
    try:
        return httpx.Client(timeout=timeout_s, http2=True)
    except ImportError:
        return httpx.Client(timeout=timeout_s)


def get_shared_http_client(timeout_s: float) -> httpx.Client:
    global _shared_http_client, _shared_http_client_timeout
    _install_reset_stt_router_hook()
    if _shared_http_client is None or _shared_http_client_timeout != timeout_s:
        close_doubao_http_client()
        _shared_http_client = _create_http_client(timeout_s)
        _shared_http_client_timeout = timeout_s
    return _shared_http_client


def close_doubao_http_client() -> None:
    global _shared_http_client, _shared_http_client_timeout
    if _shared_http_client is not None:
        _shared_http_client.close()
        _shared_http_client = None
        _shared_http_client_timeout = None


def _install_reset_stt_router_hook() -> None:
    import sys

    router_mod = sys.modules.get("backend.app.stt.router")
    if router_mod is None:
        return

    original_reset = getattr(router_mod, "reset_stt_router", None)
    if original_reset is None or getattr(original_reset, "_closes_doubao_http_client", False):
        return

    def reset_stt_router() -> None:
        close_doubao_http_client()
        original_reset()

    reset_stt_router._closes_doubao_http_client = True  # type: ignore[attr-defined]
    router_mod.reset_stt_router = reset_stt_router


def _float32_to_wav_bytes(audio: np.ndarray, sample_rate: int = TARGET_SAMPLE_RATE) -> bytes:
    clipped = np.clip(audio, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())
    return buffer.getvalue()


def _normalize_language(language: str | None) -> str | None:
    if not language:
        return None
    trimmed = language.strip()
    if not trimmed:
        return None
    lowered = trimmed.lower()
    return LANGUAGE_ALIASES.get(lowered, trimmed)


def prepare_audio_for_asr(audio_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    normalized_mime = mime_type.split(";", maxsplit=1)[0].strip().lower()

    if normalized_mime in {"audio/wav", "audio/x-wav", "audio/wave"}:
        return audio_bytes, "wav"
    if normalized_mime in {"audio/mpeg", "audio/mp3"}:
        return audio_bytes, "mp3"
    if normalized_mime in {"audio/ogg", "audio/opus"}:
        return audio_bytes, "ogg"

    pcm = decode_audio_bytes(audio_bytes)
    return _float32_to_wav_bytes(pcm), "wav"


class DoubaoASRProvider(SpeechToTextProvider):
    name = "doubao"
    cloud = True

    def __init__(
        self,
        *,
        enabled: bool = True,
        model: str = DEFAULT_MODEL_NAME,
        resource_id: str | None = None,
        uid: str = "cyber-companion",
        timeout_s: float = 60.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._enabled = enabled
        self._model = model
        self._configured_resource_id = resource_id
        self._uid = uid
        self._timeout_s = timeout_s
        self._http_client = http_client

    def _env(self, key: str) -> str | None:
        value = os.getenv(key, "").strip()
        return value or None

    def _api_key(self) -> str | None:
        return self._env(ENV_API_KEY)

    def _resolve_resource_id(self) -> str:
        return self._env(ENV_RESOURCE_ID) or self._configured_resource_id or DEFAULT_RESOURCE_ID

    def is_configured(self) -> bool:
        return self._api_key() is not None

    def status(self) -> STTProviderStatus:
        api_key_present = self._api_key() is not None
        return STTProviderStatus(
            name=self.name,
            enabled=self._enabled,
            model=self._model,
            configured=api_key_present,
            api_key_present=api_key_present,
            placeholder=False,
            cloud=True,
        )

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        api_key = self._api_key()
        if not api_key:
            raise STTConfigError(
                "Doubao ASR is selected but DOUBAO_API_KEY is not configured."
            )

        try:
            audio_bytes, audio_format = prepare_audio_for_asr(
                request.audio_bytes,
                request.mime_type,
            )
        except STTError:
            raise
        except Exception as error:
            raise STTError(
                f"Could not prepare audio for Doubao ASR: {error}",
                provider=self.name,
                status_code=400,
            ) from error

        payload = self._build_request_payload(
            audio_bytes,
            audio_format,
            language=_normalize_language(request.language),
        )
        headers = self._build_request_headers(api_key)

        try:
            response = self._post_recognize(payload, headers)
        except httpx.HTTPError as error:
            raise STTError(
                f"Doubao ASR network error: {error}",
                provider=self.name,
            ) from error

        return self._parse_response(response)

    def _build_request_headers(self, api_key: str) -> dict[str, str]:
        return {
            "X-Api-Key": api_key,
            "X-Api-Resource-Id": self._resolve_resource_id(),
            "X-Api-Request-Id": str(uuid.uuid4()),
            "X-Api-Sequence": "-1",
            "Content-Type": "application/json",
        }

    def _build_request_payload(
        self,
        audio_bytes: bytes,
        audio_format: str,
        *,
        language: str | None,
    ) -> dict[str, Any]:
        audio: dict[str, Any] = {
            "format": audio_format,
            "data": base64.b64encode(audio_bytes).decode("ascii"),
        }
        if language:
            audio["language"] = language

        return {
            "user": {"uid": self._uid},
            "audio": audio,
            "request": {
                "model_name": self._model,
                "enable_itn": True,
                "enable_punc": True,
            },
        }

    def _post_recognize(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> httpx.Response:
        client = (
            self._http_client
            if self._http_client is not None
            else get_shared_http_client(self._timeout_s)
        )
        return client.post(
            ASR_FLASH_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=self._timeout_s,
        )

    def _parse_response(self, response: httpx.Response) -> TranscriptionResult:
        status_code = response.headers.get("X-Api-Status-Code", "")
        status_message = response.headers.get("X-Api-Message", "")

        if response.status_code in {401, 403}:
            raise STTError(
                "Doubao ASR authentication failed. Check DOUBAO_API_KEY.",
                provider=self.name,
                status_code=503,
            )

        if response.status_code >= 400 and not status_code:
            raise STTError(
                f"Doubao ASR HTTP {response.status_code}: {response.text[:200]}",
                provider=self.name,
                status_code=502,
            )

        if status_code == SILENT_STATUS_CODE:
            raise STTError(
                "No speech detected in the recording.",
                provider=self.name,
                status_code=400,
            )

        if status_code and status_code != SUCCESS_STATUS_CODE:
            raise STTError(
                f"Doubao ASR failed ({status_code}): {status_message or response.text[:200]}",
                provider=self.name,
                status_code=502,
            )

        try:
            body = response.json()
        except ValueError as error:
            raise STTError(
                "Doubao ASR returned a non-JSON response.",
                provider=self.name,
                status_code=502,
            ) from error

        result = body.get("result") if isinstance(body, dict) else None
        text = ""
        if isinstance(result, dict):
            text = str(result.get("text", "")).strip()

        if not text:
            raise STTError(
                "Doubao ASR returned empty transcription.",
                provider=self.name,
                status_code=400,
            )

        language = None
        if isinstance(result, dict):
            additions = result.get("additions")
            if isinstance(additions, dict):
                lid = additions.get("lid_lang")
                if isinstance(lid, str) and lid:
                    language = lid

        return TranscriptionResult(
            provider=self.name,
            model=self._model,
            text=text,
            mock=False,
            language=language,
        )
