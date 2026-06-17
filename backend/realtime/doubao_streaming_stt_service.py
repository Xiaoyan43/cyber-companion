"""Doubao streaming WebSocket ASR as a continuous Pipecat ``STTService``.

Opens the Volcengine BigASR streaming WebSocket
(``wss://openspeech.bytedance.com/api/v3/sauc/bigmodel``), feeds mic PCM as it
arrives, and emits ``InterimTranscriptionFrame`` (partials) + ``TranscriptionFrame``
(finals) so the transcript is ready almost the instant the user stops talking —
the latency fix over the one-shot flash path (``DoubaoFlashSTTService``).

Auth reuses the flash adapter's shape: new-console ``X-Api-Key`` = ``DOUBAO_API_KEY``.
The streaming resource id differs from flash (``volc.bigasr.auc_turbo``) and defaults
to ``volc.bigasr.sauc.duration`` (override via ``DOUBAO_ASR_RESOURCE_ID``). Binary
framing per the official docs lives in :mod:`backend.realtime.doubao_streaming_protocol`.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

from loguru import logger

from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    InterimTranscriptionFrame,
    StartFrame,
    TranscriptionFrame,
)
from pipecat.services.settings import STTSettings
from pipecat.services.stt_service import STTService
from pipecat.transcriptions.language import Language
from pipecat.utils.time import time_now_iso8601
from pipecat.utils.tracing.service_decorators import traced_stt

from backend.realtime.doubao_streaming_protocol import (
    SUCCESS_CODE,
    build_audio_request,
    build_full_client_request,
    parse_response,
)
from backend.realtime.voice_config import load_asr_end_window_ms

WS_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async"
DEFAULT_RESOURCE_ID = "volc.seedasr.sauc.duration"
INPUT_SAMPLE_RATE = 16_000

ENV_API_KEY = "DOUBAO_API_KEY"
ENV_RESOURCE_ID = "DOUBAO_ASR_RESOURCE_ID"
SESSION_TIMEOUT_CODE = 45000081


class DoubaoStreamingSTTService(STTService):
    """Continuous cloud streaming ASR over Doubao's BigASR WebSocket."""

    def __init__(
        self,
        *,
        resource_id: str | None = None,
        uid: str = "cyber-companion",
        end_window_size_ms: int | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            sample_rate=INPUT_SAMPLE_RATE,
            settings=STTSettings(model="bigmodel", language=None),
            **kwargs,
        )
        self._api_key = os.getenv(ENV_API_KEY, "").strip()
        if not self._api_key:
            raise RuntimeError("Doubao streaming ASR is not configured. Set DOUBAO_API_KEY.")
        self._resource_id = (
            resource_id or os.getenv(ENV_RESOURCE_ID, "").strip() or DEFAULT_RESOURCE_ID
        )
        self._uid = uid
        self._end_window_size_ms = (
            end_window_size_ms
            if end_window_size_ms is not None
            else load_asr_end_window_ms()
        )
        logger.debug(f"{self.__class__.__name__} end_window_size_ms={self._end_window_size_ms}")

        self._websocket = None
        self._receive_task = None
        self._connected = False
        self._last_final_text = ""
        self._last_interim_text = ""

    def can_generate_metrics(self) -> bool:
        return True

    def _request_params(self) -> dict:
        return {
            "user": {"uid": self._uid},
            "audio": {
                "format": "pcm",
                "codec": "raw",
                "rate": INPUT_SAMPLE_RATE,
                "bits": 16,
                "channel": 1,
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
                "show_utterances": True,
                "result_type": "single",
                "end_window_size": self._end_window_size_ms,
                "enable_ddc": True,
            },
        }

    def _headers(self) -> dict[str, str]:
        return {
            "X-Api-Key": self._api_key,
            "X-Api-Resource-Id": self._resource_id,
            "X-Api-Request-Id": str(uuid.uuid4()),
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }

    async def start(self, frame: StartFrame) -> None:
        await super().start(frame)
        await self._connect()

    async def stop(self, frame: EndFrame) -> None:
        await super().stop(frame)
        await self._finish_stream()
        await self._disconnect()

    async def cancel(self, frame: CancelFrame) -> None:
        await super().cancel(frame)
        await self._disconnect()

    async def _connect(self) -> None:
        if self._connected:
            return
        try:
            from websockets.asyncio.client import connect as websocket_connect
        except ModuleNotFoundError as error:  # pragma: no cover - dep guard
            logger.error(f"{self} requires the `websockets` package: {error}")
            await self.push_error("websockets is not installed", exception=error)
            return

        try:
            self._websocket = await websocket_connect(
                WS_URL,
                additional_headers=self._headers(),
                max_size=None,
            )
            logid = self._websocket.response.headers.get("X-Tt-Logid", "")
            logger.debug(f"{self} connected (X-Tt-Logid={logid})")
            await self._websocket.send(build_full_client_request(self._request_params()))
            self._connected = True
            self._last_final_text = ""
            self._last_interim_text = ""
            self._receive_task = self.create_task(self._receive_task_handler())
        except Exception as error:
            self._websocket = None
            self._connected = False
            logger.error(f"{self} failed to connect: {error}")
            await self.push_error(
                f"Doubao streaming ASR connect failed: {error}", exception=error
            )

    async def _disconnect(self) -> None:
        self._connected = False
        if self._receive_task:
            await self.cancel_task(self._receive_task)
            self._receive_task = None
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as error:  # pragma: no cover - best-effort close
                logger.debug(f"{self} error while closing websocket: {error}")
            self._websocket = None

    async def _reconnect(self) -> None:
        await self._disconnect()
        await self._connect()

    async def _finish_stream(self) -> None:
        """Send the negative (last) packet so the server flushes the final result."""
        if self._connected and self._websocket:
            try:
                await self._websocket.send(build_audio_request(b"", last=True))
            except Exception as error:  # pragma: no cover - best-effort flush
                logger.debug(f"{self} error sending final packet: {error}")

    @traced_stt
    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame | None, None]:
        if self._connected and self._websocket:
            try:
                await self._websocket.send(build_audio_request(audio, last=False))
            except Exception as error:
                logger.warning(f"{self} websocket send failed: {error}")
                self._connected = False
        yield None

    async def _receive_task_handler(self) -> None:
        assert self._websocket is not None
        try:
            async for message in self._websocket:
                if not isinstance(message, (bytes, bytearray)):
                    continue
                await self._handle_message(bytes(message))
        except Exception as error:  # pragma: no cover - network teardown path
            logger.debug(f"{self} receive loop ended: {error}")

    async def _handle_message(self, raw: bytes) -> None:
        try:
            response = parse_response(raw)
        except Exception as error:
            logger.warning(f"{self} failed to parse response: {error}")
            return

        if response.is_error:
            logger.error(f"{self} server error {response.code}: {response.payload}")
            if response.code == SESSION_TIMEOUT_CODE:
                logger.warning(f"{self} streaming session timed out — reconnecting")
                await self._reconnect()
            else:
                await self.push_error(f"Doubao streaming ASR error {response.code}")
            return

        if response.code is not None and response.code != SUCCESS_CODE:
            logger.warning(f"{self} non-success code {response.code}")
            return

        text = response.text
        if not text:
            return

        if response.has_definite or response.is_last:
            if text == self._last_final_text:
                return
            self._last_final_text = text
            self._last_interim_text = ""
            await self.stop_ttfb_metrics()
            logger.info(f"🗣  你说(final): {text}")
            await self.push_frame(
                TranscriptionFrame(text, self._user_id, time_now_iso8601(), Language.ZH)
            )
        else:
            if text == self._last_interim_text:
                return
            self._last_interim_text = text
            logger.info(f"…  你说(partial): {text}")
            await self.push_frame(
                InterimTranscriptionFrame(text, self._user_id, time_now_iso8601(), Language.ZH)
            )
