"""Half-duplex gating — mute user input while Boxi speaks (laptop speaker echo).

Pipecat 1.3.0 removed ``STTMuteFilter``; the replacement is ``AlwaysUserMuteStrategy``
(``pipecat.turns.user_mute``), normally wired through ``LLMUserAggregatorParams``. Our
pipeline uses a standalone VAD step instead, so this processor reuses Pipecat's strategy
and mirrors ``LLMUserAggregator._maybe_mute_frame`` frame suppression.

Streaming ASR (Doubao WebSocket) must keep receiving PCM packets while muted — the legacy
``STTMuteFilter`` explicitly kept audio flowing to STT for that reason. We substitute silence
for mic audio before VAD/STT and drop turn/transcript frames instead of starving the socket.
"""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Literal

from loguru import logger

from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    InputAudioRawFrame,
    InterimTranscriptionFrame,
    InterruptionFrame,
    StartFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.turns.user_mute import AlwaysUserMuteStrategy

from backend.realtime.voice_config import load_asr_end_window_ms

HalfDuplexMuteRole = Literal["input", "stt_out"]

_VAD_TURN_FRAME_TYPES = (
    InterruptionFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)

_TRANSCRIPT_FRAME_TYPES = (
    InterimTranscriptionFrame,
    TranscriptionFrame,
)


class HalfDuplexMuteGate:
    """Shared mute state for multiple ``HalfDuplexMuteProcessor`` instances in one pipeline."""

    def __init__(self, *, resume_guard_ms: int | None = None) -> None:
        self._strategy = AlwaysUserMuteStrategy()
        self._user_is_muted = False
        self._resume_guard_until: float | None = None
        self._resume_guard_secs = (resume_guard_ms if resume_guard_ms is not None else load_asr_end_window_ms()) / 1000.0

    @property
    def user_is_muted(self) -> bool:
        return self._user_is_muted

    async def setup(self, task_manager) -> None:
        await self._strategy.setup(task_manager)

    async def cleanup(self) -> None:
        await self._strategy.cleanup()

    async def on_frame(self, frame: Frame) -> None:
        if isinstance(frame, (StartFrame, EndFrame, CancelFrame)):
            return

        should_mute = await self._strategy.process_frame(frame)
        if should_mute == self._user_is_muted:
            return

        self._user_is_muted = should_mute
        if self._user_is_muted:
            logger.debug("Half-duplex: user muted (bot speaking)")
        else:
            self._resume_guard_until = time.monotonic() + self._resume_guard_secs
            logger.debug(
                f"Half-duplex: user unmuted (resume guard {self._resume_guard_secs:.2f}s)"
            )

    def should_suppress_input(self, frame: Frame) -> bool:
        return self._user_is_muted and isinstance(frame, _VAD_TURN_FRAME_TYPES)

    def should_suppress_stt_out(self, frame: Frame) -> bool:
        if self._user_is_muted and isinstance(frame, _TRANSCRIPT_FRAME_TYPES + (InterruptionFrame,)):
            return True

        if self._resume_guard_until is not None and time.monotonic() < self._resume_guard_until:
            if isinstance(frame, _TRANSCRIPT_FRAME_TYPES):
                return True

        return False

    def silence_if_muted(self, frame: Frame) -> Frame:
        if self._user_is_muted and isinstance(frame, InputAudioRawFrame):
            return replace(frame, audio=b"\x00" * len(frame.audio))
        return frame


class HalfDuplexMuteProcessor(FrameProcessor):
    """Half-duplex gate — ``input`` role silences mic + blocks VAD; ``stt_out`` blocks transcripts."""

    def __init__(self, gate: HalfDuplexMuteGate, *, role: HalfDuplexMuteRole) -> None:
        super().__init__()
        self._gate = gate
        self._role = role

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, StartFrame):
            await self._gate.setup(self.task_manager)
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, (EndFrame, CancelFrame)):
            await self.push_frame(frame, direction)
            if isinstance(frame, EndFrame):
                await self._gate.cleanup()
            return

        await self._gate.on_frame(frame)

        if self._role == "input":
            if self._gate.should_suppress_input(frame):
                logger.trace(f"Half-duplex suppressed {frame.name}")
                return
            await self.push_frame(self._gate.silence_if_muted(frame), direction)
            return

        if self._gate.should_suppress_stt_out(frame):
            logger.trace(f"Half-duplex suppressed {frame.name}")
            return

        await self.push_frame(frame, direction)
