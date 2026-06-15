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
from backend.app.tts.text_cleanup import clean_text_for_tts
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
# Big-model 灿灿 2.0 (V3 + X-Api-Key). Legacy BV700_streaming is small-model only.
CANCAN_BIGMODEL_SPEAKER = "zh_female_cancan_uranus_bigtts"

FORMAT_TO_MIME: dict[str, str] = {
    "wav": "audio/wav",
    "pcm": "audio/pcm",
    "mp3": "audio/mpeg",
    "ogg_opus": "audio/ogg",
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
    _install_reset_tts_router_hook()
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


def _install_reset_tts_router_hook() -> None:
    import sys

    router_mod = sys.modules.get("backend.app.tts.router")
    if router_mod is None:
        return

    original_reset = getattr(router_mod, "reset_tts_router", None)
    if original_reset is None or getattr(original_reset, "_closes_doubao_http_client", False):
        return

    def reset_tts_router() -> None:
        close_doubao_http_client()
        original_reset()

    reset_tts_router._closes_doubao_http_client = True  # type: ignore[attr-defined]
    router_mod.reset_tts_router = reset_tts_router


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
        explicit_resource = self._env(ENV_RESOURCE_ID) or self._resource_id
        return {
            "api_key": api_key,
            "voice_type": voice_type,
            "resource_id": resolve_resource_id(voice_type, explicit_resource),
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

        _validate_speaker_for_v3(creds["voice_type"])

        payload = self._build_request_payload(
            text,
            creds,
            context_texts=request.context_texts,
            speech_rate=request.speech_rate,
        )
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

    def synthesize_stream(self, request: SynthesisRequest) -> Iterator[bytes]:
        creds = self._credentials()
        if not creds:
            raise TTSConfigError(
                "Doubao TTS is selected but DOUBAO_TTS_API_KEY (or DOUBAO_TTS_ACCESS_TOKEN) "
                "and DOUBAO_TTS_VOICE_TYPE must be configured."
            )

        text = request.text.strip()
        if not text:
            raise TTSError("Text payload is empty.", provider=self.name, status_code=400)

        _validate_speaker_for_v3(creds["voice_type"])

        payload = self._build_request_payload(
            text,
            creds,
            context_texts=request.context_texts,
            speech_rate=request.speech_rate,
        )
        headers = self._build_request_headers(creds)

        try:
            yield from self._iter_stream_synthesis(payload, headers)
        except httpx.HTTPError as error:
            raise TTSError(
                f"Doubao TTS network error: {error}",
                provider=self.name,
            ) from error

    def _build_request_headers(self, creds: dict[str, str]) -> dict[str, str]:
        return {
            "X-Api-Key": creds["api_key"],
            "X-Api-Resource-Id": creds["resource_id"],
            "X-Api-Request-Id": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }

    def _build_request_payload(
        self,
        text: str,
        creds: dict[str, str],
        *,
        context_texts: list[str] | None = None,
        speech_rate: int = 0,
    ) -> dict[str, Any]:
        audio_params: dict[str, Any] = {
            "format": self._audio_format,
            "sample_rate": 24_000,
        }
        if speech_rate != 0:
            audio_params["speech_rate"] = speech_rate

        req_params: dict[str, Any] = {
            "text": clean_text_for_tts(text),
            "speaker": creds["voice_type"],
            "audio_params": audio_params,
        }
        if context_texts:
            req_params["additions"] = json.dumps({"context_texts": context_texts})

        return {
            "user": {
                "uid": self._uid,
            },
            "req_params": req_params,
        }

    def _stream_synthesis(self, payload: dict[str, Any], headers: dict[str, str]) -> bytes:
        return b"".join(self._iter_stream_synthesis(payload, headers))

    def _iter_stream_synthesis(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> Iterator[bytes]:
        client = (
            self._http_client
            if self._http_client is not None
            else get_shared_http_client(self._timeout_s)
        )
        with client.stream(
            "POST",
            TTS_HTTP_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=self._timeout_s,
        ) as response:
            yield from self._iter_streamed_audio_chunks(response)

    def _iter_streamed_audio_chunks(self, response: httpx.Response) -> Iterator[bytes]:
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

        yielded = False
        for line in _iter_response_lines(response):
            chunk = _parse_stream_chunk(line)
            if chunk is None:
                continue

            code = chunk.get("code")
            if code == STREAM_AUDIO_CODE:
                data = chunk.get("data")
                if isinstance(data, str) and data:
                    try:
                        decoded = base64.b64decode(data, validate=True)
                    except (ValueError, binascii.Error) as error:
                        raise TTSError(
                            "Doubao TTS returned invalid base64 audio.",
                            provider=self.name,
                        ) from error
                    yielded = True
                    yield decoded
                continue

            if code == STREAM_DONE_CODE:
                return

            message = _response_message(chunk) or f"error code {code}"
            status_code = 503 if _looks_like_auth_or_quota_error(message) else 502
            raise TTSError(
                f"Doubao TTS synthesis failed: {message}",
                provider=self.name,
                status_code=status_code,
            )

        if not yielded:
            raise TTSError(
                "Doubao TTS stream ended without audio data.",
                provider=self.name,
            )


def resolve_resource_id(speaker: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    if speaker.startswith("S_"):
        return "seed-icl-2.0"
    if "_uranus_" in speaker or speaker.startswith("saturn_"):
        return "seed-tts-2.0"
    if "_moon_bigtts" in speaker or "_mars_bigtts" in speaker or speaker.startswith("ICL_"):
        return "seed-tts-1.0"
    return DEFAULT_RESOURCE_ID


def _validate_speaker_for_v3(speaker: str) -> None:
    if speaker.endswith("_streaming") or (
        speaker.startswith("BV") and "_streaming" in speaker
    ):
        raise TTSError(
            f"Speaker `{speaker}` is a legacy small-model voice and does not work with "
            f"V3 X-Api-Key. Use big-model 灿灿 2.0 `{CANCAN_BIGMODEL_SPEAKER}` with "
            "`seed-tts-2.0`, or switch TTS back to `mac_say`.",
            provider="doubao",
            status_code=503,
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
        "resource id is mismatched",
        "quota exceeded",
        "quota",
        "invalid x-api",
        "api key",
    )
    return any(marker in lowered for marker in markers)
