"""Detects barge-in: Boxi stops talking when the user starts talking over her.

Pipecat's VAD/STT/TTS/output components already react correctly to a broadcast
``InterruptionFrame`` (TTS stops synthesizing, the output transport flushes its audio
queue, ``CompanionBrainProcessor`` cancels the in-flight turn — all confirmed by reading
the installed Pipecat 1.3.0 source, see docs/HANDOFF.md P0-OSS-4 barge-in spike). What
this pipeline is missing is a component that decides *when* to call
``self.broadcast_interruption()`` in the first place: nothing currently turns
``VADUserStartedSpeakingFrame`` into an interruption.
"""

from __future__ import annotations

import asyncio

from loguru import logger

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from backend.realtime.voice_config import load_barge_in_enabled, load_barge_in_min_secs


class BargeInProcessor(FrameProcessor):
    """Interrupts Boxi's TTS playback when the user keeps talking over her.

    Sits between ``vad`` and ``stt`` in the pipeline so it sees
    ``VADUserStartedSpeakingFrame``/``VADUserStoppedSpeakingFrame`` flowing downstream
    (from ``vad``) and ``BotStartedSpeakingFrame``/``BotStoppedSpeakingFrame`` flowing
    upstream (broadcast by the output transport, both directions, per Pipecat's
    ``BaseOutputTransport``). Only interrupts when Boxi is actually speaking — the
    user's own turn-opening speech never triggers this.

    The VAD's own ``start_secs`` (Pipecat default 0.2s) already gates
    ``VADUserStartedSpeakingFrame`` itself; this processor adds a second, independent
    debounce (``min_speech_secs``) on top before committing to an interruption, mirroring
    LiveKit Agents' ``InterruptionOptions.min_duration`` (default 0.5s) — the two
    debounces stack to roughly the same total user-perceived latency.
    """

    def __init__(self, *, enabled: bool | None = None, min_speech_secs: float | None = None) -> None:
        super().__init__()
        self._enabled = enabled if enabled is not None else load_barge_in_enabled()
        self._min_speech_secs = (
            min_speech_secs if min_speech_secs is not None else load_barge_in_min_secs()
        )
        self._bot_speaking = False
        self._pending_barge_in: asyncio.Task | None = None

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, BotStartedSpeakingFrame):
            self._bot_speaking = True
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._bot_speaking = False
            await self._cancel_pending_barge_in()
        elif isinstance(frame, VADUserStartedSpeakingFrame):
            if self._enabled and self._bot_speaking and self._pending_barge_in is None:
                self._pending_barge_in = self.create_task(
                    self._debounce_then_interrupt(), name="barge_in_debounce"
                )
        elif isinstance(frame, VADUserStoppedSpeakingFrame):
            await self._cancel_pending_barge_in()

        await self.push_frame(frame, direction)

    async def _debounce_then_interrupt(self) -> None:
        await asyncio.sleep(self._min_speech_secs)
        logger.info(
            f"{self}: barge-in threshold reached (min_speech_secs={self._min_speech_secs}s) "
            "— interrupting Boxi"
        )
        self._pending_barge_in = None
        await self.broadcast_interruption()

    async def _cancel_pending_barge_in(self) -> None:
        if self._pending_barge_in is not None:
            await self.cancel_task(self._pending_barge_in)
            self._pending_barge_in = None
