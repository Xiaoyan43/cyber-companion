from __future__ import annotations

import base64
import binascii
import os
import uuid
from typing import Any

import httpx

from backend.app.tts.base import TextToSpeechProvider
from backend.app.tts.exceptions import TTSConfigError, TTSError
from backend.app.tts.types import SynthesisRequest, SynthesisResult, TTSProviderStatus
from backend.app.tts.wav_utils import parse_wav_duration_ms

# Volcano Engine / Doubao speech HTTP TTS (non-streaming v1).
# Docs: https://www.volcengine.com/docs/6561/1257584
#       https://www.volcengine.com/docs/6561/79820
TTS_HTTP_ENDPOINT = "https://openspeech.bytedance.com/api/v1/tts"
SUCCESS_CODE = 3000

ENV_APPID = "DOUBAO_TTS_APPID"
ENV_ACCESS_TOKEN = "DOUBAO_TTS_ACCESS_TOKEN"
ENV_CLUSTER = "DOUBAO_TTS_CLUSTER"
ENV_VOICE_TYPE = "DOUBAO_TTS_VOICE_TYPE"

ENCODING_TO_MIME: dict[str, str] = {
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
        encoding: str = "wav",
        uid: str = "cyber-companion",
        timeout_s: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._enabled = enabled
        self._encoding = encoding
        self._uid = uid
        self._timeout_s = timeout_s
        self._http_client = http_client

    def _env(self, key: str) -> str | None:
        value = os.getenv(key, "").strip()
        return value or None

    def _credentials(self) -> dict[str, str] | None:
        appid = self._env(ENV_APPID)
        access_token = self._env(ENV_ACCESS_TOKEN)
        cluster = self._env(ENV_CLUSTER)
        voice_type = self._env(ENV_VOICE_TYPE)
        if not appid or not access_token or not cluster or not voice_type:
            return None
        return {
            "appid": appid,
            "access_token": access_token,
            "cluster": cluster,
            "voice_type": voice_type,
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
            api_key_present=creds is not None,
            placeholder=False,
            cloud=True,
        )

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        creds = self._credentials()
        if not creds:
            raise TTSConfigError(
                "Doubao TTS is selected but DOUBAO_TTS_APPID, DOUBAO_TTS_ACCESS_TOKEN, "
                "DOUBAO_TTS_CLUSTER, and DOUBAO_TTS_VOICE_TYPE must all be configured."
            )

        text = request.text.strip()
        if not text:
            raise TTSError("Text payload is empty.", provider=self.name, status_code=400)

        payload = self._build_request_payload(text, creds)
        headers = {
            "Authorization": f"Bearer;{creds['access_token']}",
            "Content-Type": "application/json",
        }

        try:
            response = self._post_json(payload, headers)
        except httpx.HTTPError as error:
            raise TTSError(
                f"Doubao TTS network error: {error}",
                provider=self.name,
            ) from error

        if response.status_code in {401, 403}:
            raise TTSError(
                "Doubao TTS authentication failed. Check DOUBAO_TTS_APPID and DOUBAO_TTS_ACCESS_TOKEN.",
                provider=self.name,
                status_code=503,
            )

        try:
            body = response.json()
        except ValueError as error:
            raise TTSError(
                "Doubao TTS returned a non-JSON response.",
                provider=self.name,
            ) from error

        if response.status_code >= 400:
            message = _response_message(body) or f"HTTP {response.status_code}"
            raise TTSError(
                f"Doubao TTS request failed: {message}",
                provider=self.name,
                status_code=502,
            )

        code = body.get("code")
        if code != SUCCESS_CODE:
            message = _response_message(body) or f"error code {code}"
            status_code = 503 if _looks_like_auth_or_quota_error(message) else 502
            raise TTSError(
                f"Doubao TTS synthesis failed: {message}",
                provider=self.name,
                status_code=status_code,
            )

        audio_b64 = body.get("data")
        if not isinstance(audio_b64, str) or not audio_b64.strip():
            raise TTSError(
                "Doubao TTS returned no audio data.",
                provider=self.name,
            )

        try:
            audio_bytes = base64.b64decode(audio_b64, validate=True)
        except (ValueError, binascii.Error) as error:
            raise TTSError(
                "Doubao TTS returned invalid base64 audio.",
                provider=self.name,
            ) from error

        if not audio_bytes:
            raise TTSError(
                "Doubao TTS returned empty audio.",
                provider=self.name,
            )

        mime_type = ENCODING_TO_MIME.get(self._encoding, "application/octet-stream")
        duration_ms = _duration_from_response(body)
        if duration_ms is None and self._encoding == "wav":
            try:
                duration_ms = parse_wav_duration_ms(audio_bytes)
            except ValueError:
                duration_ms = None
        if duration_ms is None:
            duration_ms = max(1, len(text) * 45)

        return SynthesisResult(
            provider=self.name,
            model=creds["voice_type"],
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            duration_ms=duration_ms,
            mock=False,
        )

    def _build_request_payload(self, text: str, creds: dict[str, str]) -> dict[str, Any]:
        return {
            "app": {
                "appid": creds["appid"],
                "token": creds["access_token"],
                "cluster": creds["cluster"],
            },
            "user": {
                "uid": self._uid,
            },
            "audio": {
                "voice_type": creds["voice_type"],
                "encoding": self._encoding,
                "speed_ratio": 1.0,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "operation": "query",
            },
        }

    def _post_json(self, payload: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
        if self._http_client is not None:
            return self._http_client.post(
                TTS_HTTP_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=self._timeout_s,
            )

        with httpx.Client(timeout=self._timeout_s) as client:
            return client.post(
                TTS_HTTP_ENDPOINT,
                json=payload,
                headers=headers,
            )


def _response_message(body: dict[str, Any]) -> str | None:
    message = body.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()
    return None


def _duration_from_response(body: dict[str, Any]) -> int | None:
    addition = body.get("addition")
    if not isinstance(addition, dict):
        return None
    raw = addition.get("duration")
    if raw is None:
        return None
    try:
        return max(1, int(str(raw)))
    except ValueError:
        return None


def _looks_like_auth_or_quota_error(message: str) -> bool:
    lowered = message.lower()
    markers = (
        "authenticate",
        "auth",
        "grant",
        "access denied",
        "quota exceeded",
        "quota",
    )
    return any(marker in lowered for marker in markers)
