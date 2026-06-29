"""Doubao Dialog S2S (OutputMode 0) as a Pipecat processor — mic PCM up, TTS PCM down.

Opens ``wss://openspeech.bytedance.com/api/v3/realtime/dialogue``, injects Boxi persona
via ``system_role`` / ``bot_name`` / ``speaking_style``, and streams bidirectional audio.
The cloud model owns VAD, endpointing, and barge-in (ASRInfo → ``InterruptionFrame``).

Auth: ``DOUBAO_RT_APP_ID`` + ``DOUBAO_RT_ACCESS_TOKEN`` (env only).
"""

from __future__ import annotations

import asyncio
import os
import struct
import time
import uuid
from loguru import logger

from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    InputAudioRawFrame,
    InterruptionFrame,
    OutputAudioRawFrame,
    StartFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from backend.app.memory.persona import (
    load_persona_name,
    load_rtc_speaking_style,
    load_rtc_system_role,
)
from backend.realtime import doubao_realtime_protocol as proto

WS_URL = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"
RESOURCE_ID = "volc.speech.dialog"
APP_KEY = "PlgvMymc7f3tQnJ6"

INPUT_SAMPLE_RATE = 16_000
OUTPUT_SAMPLE_RATE = 24_000

ENV_APP_ID = "DOUBAO_RT_APP_ID"
ENV_ACCESS_TOKEN = "DOUBAO_RT_ACCESS_TOKEN"
ENV_SPEAKER = "DOUBAO_RT_SPEAKER"
ENV_MODEL = "DOUBAO_RT_MODEL"
ENV_AUDIO_FORMAT = "DOUBAO_RT_AUDIO_FORMAT"

DEFAULT_SPEAKER = "zh_male_yunzhou_jupiter_bigtts"
DEFAULT_MODEL = "1.2.1.1"  # O2.0 — supports system_role / bot_name / speaking_style
ENV_ENABLE_MUSIC = "DOUBAO_RT_ENABLE_MUSIC"
# Pipecat LocalAudioTransport plays 16-bit PCM (paInt16). Dialog ``pcm`` = 32-bit float → noise.
DEFAULT_AUDIO_FORMAT = "pcm_s16le"


def _load_audio_format() -> str:
    fmt = os.getenv(ENV_AUDIO_FORMAT, "").strip() or DEFAULT_AUDIO_FORMAT
    if fmt not in {"pcm_s16le", "pcm"}:
        raise ValueError(f"{ENV_AUDIO_FORMAT} must be pcm_s16le or pcm")
    return fmt


def _prepare_tts_pcm(audio: bytes, *, warned_ogg: bool) -> tuple[bytes | None, bool]:
    """Normalize Dialog TTS bytes for Pipecat's 16-bit PCM output transport."""
    if not audio:
        return None, warned_ogg
    if audio.startswith(b"OggS"):
        if not warned_ogg:
            logger.error(
                "Doubao Dialog returned Ogg/Opus audio — set tts.audio_config.format to "
                f"{DEFAULT_AUDIO_FORMAT} (current request may have been ignored)."
            )
        return None, True
    fmt = _load_audio_format()
    if fmt == "pcm_s16le":
        return audio, warned_ogg
    # ``pcm`` in Dialog docs = 32-bit float LE; convert for paInt16 playback.
    if len(audio) % 4 != 0:
        logger.warning(f"Doubao Dialog float PCM size {len(audio)} is not 4-byte aligned")
        return None, warned_ogg
    floats = struct.unpack(f"<{len(audio) // 4}f", audio)
    clipped = [max(-1.0, min(1.0, sample)) for sample in floats]
    return struct.pack(f"<{len(clipped)}h", *(int(sample * 32767.0) for sample in clipped)), warned_ogg


def _enable_music() -> bool:
    raw = os.getenv(ENV_ENABLE_MUSIC, "").strip()
    if not raw:
        return True
    return raw.lower() in {"1", "true", "yes", "on"}


def build_start_session_payload() -> dict:
    """StartSession JSON with Boxi persona injected."""
    dialog_extra: dict[str, object] = {
        "strict_audit": False,
        "input_mod": "audio",
        "model": os.getenv(ENV_MODEL, "").strip() or DEFAULT_MODEL,
    }
    if _enable_music():
        dialog_extra["enable_music"] = True
    return {
        "asr": {
            "extra": {
                # Smart sentence break: longer smooth window + twopass ASR (volc S2S docs).
                "end_smooth_window_ms": 1000,
                "enable_custom_vad": True,
                "enable_asr_twopass": True,
            },
        },
        "tts": {
            "speaker": os.getenv(ENV_SPEAKER, "").strip() or DEFAULT_SPEAKER,
            "audio_config": {
                "channel": 1,
                "format": _load_audio_format(),
                "sample_rate": OUTPUT_SAMPLE_RATE,
            },
        },
        "dialog": {
            "bot_name": load_persona_name(),
            "system_role": load_rtc_system_role(),
            "speaking_style": load_rtc_speaking_style(),
            "extra": dialog_extra,
        },
    }


class DoubaoRealtimeService(FrameProcessor):
    """End-to-end Dialog S2S — replaces STT + brain + TTS in pure (OutputMode 0) mode."""

    def __init__(self, *, session_id: str | None = None) -> None:
        super().__init__()
        self._app_id = os.getenv(ENV_APP_ID, "").strip()
        self._access_token = os.getenv(ENV_ACCESS_TOKEN, "").strip()
        if not self._app_id or not self._access_token:
            raise RuntimeError(
                "Doubao realtime Dialog is not configured. "
                f"Set {ENV_APP_ID} and {ENV_ACCESS_TOKEN}."
            )

        self._session_id = session_id or str(uuid.uuid4())
        self._connect_id = str(uuid.uuid4())
        self._websocket = None
        self._receive_task: asyncio.Task | None = None
        self._connected = False
        self._session_ready = asyncio.Event()

        self._user_text = ""
        self._bot_text = ""
        self._user_end_at: float | None = None
        self._first_audio_at: float | None = None
        self._turn_started_at: float | None = None
        self._warned_ogg_tts = False

    def _headers(self) -> dict[str, str]:
        return {
            "X-Api-App-ID": self._app_id,
            "X-Api-Access-Key": self._access_token,
            "X-Api-Resource-Id": RESOURCE_ID,
            "X-Api-App-Key": APP_KEY,
            "X-Api-Connect-Id": self._connect_id,
        }

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, StartFrame):
            await self._connect()
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, (EndFrame, CancelFrame)):
            await self._teardown()
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, InputAudioRawFrame) and self._connected:
            await self._send_audio(frame.audio)
            return

        await self.push_frame(frame, direction)

    async def _connect(self) -> None:
        if self._connected:
            return
        try:
            from websockets.asyncio.client import connect as websocket_connect
        except ModuleNotFoundError as error:  # pragma: no cover
            logger.error(f"{self} requires the `websockets` package: {error}")
            return

        try:
            self._websocket = await websocket_connect(
                WS_URL,
                additional_headers=self._headers(),
                max_size=None,
                ping_interval=None,
            )
            logid = self._websocket.response.headers.get("X-Tt-Logid", "")
            logger.info(f"Doubao Dialog connected (X-Tt-Logid={logid})")

            await self._websocket.send(proto.build_connect_event(proto.EVENT_START_CONNECTION))
            await self._wait_for_event(proto.EVENT_CONNECTION_STARTED)

            payload = build_start_session_payload()
            await self._websocket.send(
                proto.build_session_event(proto.EVENT_START_SESSION, self._session_id, payload)
            )
            await self._wait_for_event(proto.EVENT_SESSION_STARTED)

            self._connected = True
            self._session_ready.set()
            self._receive_task = self.create_task(self._receive_loop(), name="doubao_dialog_recv")
            logger.info(
                f"Doubao Dialog session ready (bot={payload['dialog']['bot_name']}, "
                f"speaker={payload['tts']['speaker']}, model={payload['dialog']['extra']['model']})"
            )
        except Exception as error:
            self._websocket = None
            self._connected = False
            logger.error(f"Doubao Dialog connect failed: {error}")
            raise

    async def _wait_for_event(self, expected: int, *, timeout: float = 15.0) -> proto.DoubaoDialogResponse:
        assert self._websocket is not None
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            raw = await asyncio.wait_for(self._websocket.recv(), timeout=deadline - time.monotonic())
            if not isinstance(raw, (bytes, bytearray)):
                continue
            parsed = proto.parse_response(bytes(raw))
            if parsed.is_error:
                raise RuntimeError(f"Doubao Dialog error {parsed.code}: {parsed.payload_json}")
            if parsed.event == proto.EVENT_CONNECTION_FAILED:
                raise RuntimeError(f"ConnectionFailed: {parsed.payload_json}")
            if parsed.event == proto.EVENT_SESSION_FAILED:
                raise RuntimeError(f"SessionFailed: {parsed.payload_json}")
            if parsed.event == expected:
                return parsed
        raise TimeoutError(f"Timed out waiting for Dialog event {expected}")

    async def _send_audio(self, pcm: bytes) -> None:
        if not pcm or not self._websocket:
            return
        try:
            await self._websocket.send(proto.build_task_request(self._session_id, pcm))
        except Exception as error:
            logger.warning(f"Doubao Dialog audio send failed: {error}")
            self._connected = False

    async def _receive_loop(self) -> None:
        assert self._websocket is not None
        try:
            async for message in self._websocket:
                if not isinstance(message, (bytes, bytearray)):
                    continue
                await self._handle_server_message(bytes(message))
        except asyncio.CancelledError:
            raise
        except Exception as error:  # pragma: no cover — network teardown
            logger.debug(f"Doubao Dialog receive loop ended: {error}")

    async def _handle_server_message(self, raw: bytes) -> None:
        try:
            parsed = proto.parse_response(raw)
        except Exception as error:
            logger.warning(f"Doubao Dialog parse error: {error}")
            return

        if parsed.is_error:
            logger.error(f"Doubao Dialog server error {parsed.code}: {parsed.payload_json}")
            return

        event = parsed.event
        if event == proto.EVENT_ASR_INFO:
            logger.debug("Doubao Dialog ASRInfo — barge-in")
            await self.push_frame(InterruptionFrame())
            self._first_audio_at = None
            return

        if event == proto.EVENT_ASR_RESPONSE:
            text = parsed.asr_text
            if text:
                results = (parsed.payload_json or {}).get("results") or []
                is_interim = (
                    bool(results[0].get("is_interim"))
                    if results and isinstance(results[0], dict)
                    else False
                )
                if not is_interim:
                    self._user_text = text
                    self._turn_started_at = time.monotonic()
                    logger.info(f"🗣  你说: {text}")
            return

        if event == proto.EVENT_ASR_ENDED:
            self._user_end_at = time.monotonic()
            logger.debug("Doubao Dialog ASREnded (user turn finalized)")
            return

        if event == proto.EVENT_TTS_SENTENCE_START:
            payload = parsed.payload_json or {}
            tts_text = str(payload.get("text") or "").strip()
            if tts_text:
                logger.info(f"🔊 Boxi(TTS start): {tts_text}")
            return

        if event == proto.EVENT_TTS_RESPONSE:
            if parsed.payload_bytes:
                pcm, self._warned_ogg_tts = _prepare_tts_pcm(
                    parsed.payload_bytes,
                    warned_ogg=self._warned_ogg_tts,
                )
                if not pcm:
                    return
                if self._first_audio_at is None:
                    self._first_audio_at = time.monotonic()
                    self._log_latency()
                await self.push_frame(
                    OutputAudioRawFrame(
                        audio=pcm,
                        sample_rate=OUTPUT_SAMPLE_RATE,
                        num_channels=1,
                    )
                )
            return

        if event == proto.EVENT_CHAT_RESPONSE:
            text = parsed.chat_text
            if text:
                self._bot_text = text
                logger.info(f"💬 Boxi(text): {text}")
            return

        if event == proto.EVENT_TTS_ENDED:
            self._reset_turn_latency()
            return

        if event == proto.EVENT_CHAT_ENDED:
            return

        if event == proto.EVENT_DIALOG_ERROR:
            logger.error(f"Doubao Dialog error event: {parsed.payload_json}")
            return

        if event is not None:
            logger.trace(f"Doubao Dialog event {event}: {parsed.payload_json}")

    def _log_latency(self) -> None:
        if self._first_audio_at is None:
            return
        parts: list[str] = []
        if self._user_end_at is not None:
            ms = int((self._first_audio_at - self._user_end_at) * 1000)
            parts.append(f"user_end→first_audio={ms}ms")
        if self._turn_started_at is not None:
            ms = int((self._first_audio_at - self._turn_started_at) * 1000)
            parts.append(f"first_asr→first_audio={ms}ms")
        if parts:
            logger.info(f"Doubao realtime latency: {', '.join(parts)}")

    def _reset_turn_latency(self) -> None:
        self._user_end_at = None
        self._first_audio_at = None
        self._turn_started_at = None

    async def _teardown(self) -> None:
        self._connected = False
        if self._receive_task:
            await self.cancel_task(self._receive_task)
            self._receive_task = None
        if self._websocket:
            try:
                await self._websocket.send(
                    proto.build_session_event(proto.EVENT_FINISH_SESSION, self._session_id)
                )
                await self._websocket.send(proto.build_connect_event(proto.EVENT_FINISH_CONNECTION))
            except Exception as error:  # pragma: no cover
                logger.debug(f"Doubao Dialog finish events failed: {error}")
            try:
                await self._websocket.close()
            except Exception as error:  # pragma: no cover
                logger.debug(f"Doubao Dialog close failed: {error}")
            self._websocket = None
