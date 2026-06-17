"""Doubao TTS 2.0 bidirectional WebSocket TTS as a Pipecat TTSService (PCM 24 kHz).

Replaces the HTTP-per-sentence DoubaoTTSService with a persistent WebSocket connection.
Each sentence gets its own session, but all sentences within the same LLM utterance
(same context_id) share a section_id so the server maintains prosody continuity.

Protocol: wss://openspeech.bytedance.com/api/v3/tts/bidirection (TTS 2.0 bidirection).
Auth: X-Api-Key (new-console) + X-Api-Resource-Id (auto-resolved from voice type).
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from collections.abc import AsyncGenerator, AsyncIterator

from loguru import logger

from pipecat.frames.frames import ErrorFrame, Frame
from pipecat.services.settings import TTSSettings
from pipecat.services.tts_service import TTSService
from pipecat.utils.tracing.service_decorators import traced_tts

from backend.app.tts.doubao import resolve_resource_id
from backend.app.tts.text_cleanup import clean_text_for_tts, extract_voice_instruction
from backend.realtime.doubao_bidirection_tts_protocol import (
    EVENT_CONNECTION_STARTED,
    EVENT_FINISH_CONNECTION,
    EVENT_SESSION_FAILED,
    EVENT_SESSION_STARTED,
    EVENT_START_CONNECTION,
    EVENT_TTS_RESPONSE,
    build_connection_frame,
    build_finish_session,
    build_start_session,
    build_task_request,
    parse_tts_frame,
)

WS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
SAMPLE_RATE = 24_000

ENV_API_KEY = "DOUBAO_TTS_API_KEY"
ENV_ACCESS_TOKEN = "DOUBAO_TTS_ACCESS_TOKEN"
ENV_VOICE_TYPE = "DOUBAO_TTS_VOICE_TYPE"
ENV_RESOURCE_ID = "DOUBAO_TTS_RESOURCE_ID"


async def _single_chunk(data: bytes) -> AsyncIterator[bytes]:
    """Yield a single bytes object as an async iterator."""
    yield data


class DoubaoStreamingTTSService(TTSService):
    """Pipecat TTS backed by Doubao TTS 2.0 bidirectional WebSocket.

    Connection lifecycle:
      - One persistent WebSocket per service instance (established on first use).
      - Each run_tts() = one TTS session (StartSession → TaskRequest → FinishSession).
      - All sentences in the same context_id share a section_id, so the TTS server
        preserves prosody and emotion continuity across sentence boundaries.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(
            push_start_frame=True,
            push_stop_frames=True,
            sample_rate=SAMPLE_RATE,
            settings=TTSSettings(model=None, voice=None, language=None),
            **kwargs,
        )
        api_key = os.environ.get(ENV_API_KEY) or os.environ.get(ENV_ACCESS_TOKEN)
        voice_type = os.environ.get(ENV_VOICE_TYPE)
        if not api_key or not voice_type:
            raise RuntimeError(
                "DoubaoStreamingTTSService requires DOUBAO_TTS_API_KEY and "
                "DOUBAO_TTS_VOICE_TYPE environment variables."
            )
        self._api_key = api_key
        self._voice_type = voice_type
        self._resource_id = resolve_resource_id(
            voice_type, os.environ.get(ENV_RESOURCE_ID)
        )
        self._ws: object | None = None  # websockets.ClientConnection at runtime
        self._ws_lock = asyncio.Lock()
        self._context_id: str | None = None
        self._section_id: str | None = None

    # ── Connection management ────────────────────────────────────────────────

    async def _ensure_connected(self) -> object:
        async with self._ws_lock:
            if self._ws is not None:
                try:
                    await self._ws.ping()  # type: ignore[union-attr]
                    return self._ws
                except Exception:
                    logger.warning(f"{self}: ping failed, reconnecting")
                    self._ws = None

            try:
                from websockets.asyncio.client import connect as ws_connect
            except ImportError as exc:
                raise RuntimeError("websockets package is required") from exc

            headers = {
                "X-Api-Key": self._api_key,
                "X-Api-Resource-Id": self._resource_id,
                "X-Api-Connect-Id": uuid.uuid4().hex,
            }
            ws = await ws_connect(WS_URL, additional_headers=headers)
            await ws.send(build_connection_frame(EVENT_START_CONNECTION))
            for _ in range(20):
                raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                tts_frame = parse_tts_frame(raw)
                if tts_frame.is_connection_started:
                    logger.debug(f"{self}: WebSocket connected (resource={self._resource_id})")
                    self._ws = ws
                    return ws
                if tts_frame.is_error:
                    await ws.close()
                    raise RuntimeError(f"TTS connection failed: {tts_frame.json_payload}")
            await ws.close()
            raise RuntimeError("TTS ConnectionStarted not received after 20 frames")

    async def _close_connection(self) -> None:
        async with self._ws_lock:
            ws = self._ws
            self._ws = None
        if ws is None:
            return
        try:
            await ws.send(build_connection_frame(EVENT_FINISH_CONNECTION))  # type: ignore[union-attr]
        except Exception:
            pass
        try:
            await ws.close()  # type: ignore[union-attr]
        except Exception:
            pass

    # ── Pipecat TTSService interface ─────────────────────────────────────────

    @traced_tts
    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        instruction, text_body = extract_voice_instruction(text)
        cleaned = clean_text_for_tts(text_body)
        if not cleaned.strip():
            return

        logger.debug(f"{self}: TTS [{cleaned[:60]}]")

        if context_id != self._context_id:
            self._context_id = context_id
            self._section_id = uuid.uuid4().hex

        additions: dict[str, object] = {"section_id": self._section_id}
        if instruction:
            additions["context_texts"] = [instruction]

        session_id = uuid.uuid4().hex
        tts_params = {
            "user": {"uid": "boxi"},
            "event": 100,
            "req_params": {
                "text": cleaned,
                "speaker": self._voice_type,
                "audio_params": {
                    "format": "pcm",
                    "sample_rate": SAMPLE_RATE,
                },
                "additions": json.dumps(additions),
            },
        }

        t0 = time.monotonic()
        try:
            ws = await self._ensure_connected()
        except Exception as exc:
            logger.error(f"{self}: connection error: {exc}")
            yield ErrorFrame(error=f"Doubao streaming TTS connection failed: {exc}")
            return
        t_connected = time.monotonic()

        try:
            await self.start_tts_usage_metrics(cleaned)
            # Pipeline all three control frames without waiting for SessionStarted —
            # the server queues them in order; we handle SessionStarted in the read loop.
            await ws.send(build_start_session(session_id, tts_params))  # type: ignore[union-attr]
            await ws.send(build_task_request(session_id, cleaned))  # type: ignore[union-attr]
            await ws.send(build_finish_session(session_id))  # type: ignore[union-attr]
            t_sent = time.monotonic()

            first_audio = True

            async def _ws_audio_chunks() -> AsyncIterator[bytes]:
                nonlocal first_audio
                async for raw in ws:  # type: ignore[union-call]
                    tts_frame = parse_tts_frame(raw)
                    if tts_frame.is_error:
                        raise RuntimeError(
                            f"TTS error {tts_frame.error_code}: {tts_frame.json_payload}"
                        )
                    if tts_frame.is_session_started:
                        logger.info(
                            f"{self}: [TIMING] connect={t_connected-t0:.3f}s "
                            f"send={t_sent-t_connected:.3f}s "
                            f"session_started={time.monotonic()-t_sent:.3f}s"
                        )
                        continue  # pipelined — already sent task request
                    if tts_frame.event == EVENT_TTS_RESPONSE and tts_frame.audio_bytes:
                        if first_audio:
                            first_audio = False
                            logger.info(
                                f"{self}: [TIMING] first_audio={time.monotonic()-t0:.3f}s total"
                            )
                        yield tts_frame.audio_bytes
                    if tts_frame.is_session_finished:
                        if tts_frame.event == EVENT_SESSION_FAILED:
                            logger.warning(f"{self}: session failed: {tts_frame.json_payload}")
                        return

            async for audio_frame in self._stream_audio_frames_from_iterator(
                _ws_audio_chunks(),
                in_sample_rate=SAMPLE_RATE,
                context_id=context_id,
            ):
                await self.stop_ttfb_metrics()
                yield audio_frame

        except Exception as exc:
            logger.error(f"{self}: TTS failed: {exc}")
            self._ws = None
            yield ErrorFrame(error=f"Doubao streaming TTS failed: {exc}")
        finally:
            await self.stop_ttfb_metrics()
            logger.debug(f"{self}: done [{cleaned[:40]}]")

    async def cleanup(self) -> None:
        await self._close_connection()
        await super().cleanup()
