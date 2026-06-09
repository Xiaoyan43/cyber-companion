"""Pipecat ``FrameProcessor`` that occupies the LLM slot with the Companion Brain."""

from __future__ import annotations

import asyncio

from loguru import logger

from pipecat.frames.frames import (
    Frame,
    InterimTranscriptionFrame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from backend.app.memory.budget import load_budget_config
from backend.app.reflection.runner import run_reflection_if_due
from backend.realtime.companion_brain import CompanionBrain, VoiceTurnOutcome


class CompanionBrainProcessor(FrameProcessor):
    """Consumes finalized ``TranscriptionFrame``s and streams soul replies to TTS."""

    def __init__(self, brain: CompanionBrain) -> None:
        super().__init__()
        self._brain = brain
        self._turn_task: asyncio.Task | None = None

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, InterruptionFrame):
            if self._turn_task:
                await self.cancel_task(self._turn_task)
                self._turn_task = None
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, TranscriptionFrame):
            text = frame.text.strip()
            if text:
                if self._turn_task:
                    await self.cancel_task(self._turn_task)
                self._turn_task = self.create_task(
                    self._handle_turn(text),
                    name="companion_brain_turn",
                )
            return

        if isinstance(frame, InterimTranscriptionFrame):
            return

        await self.push_frame(frame, direction)

    async def _handle_turn(self, user_text: str) -> None:
        await self.push_frame(LLMFullResponseStartFrame())
        try:
            async for event in self._brain.stream_turn(user_text):
                if event[0] == "delta":
                    chunk = event[1]
                    if not chunk:
                        continue
                    text_frame = LLMTextFrame(chunk)
                    text_frame.includes_inter_frame_spaces = True
                    await self.push_frame(text_frame)
                else:
                    outcome = event[1]
                    self._log_outcome(outcome)
                    self._schedule_off_path_work(outcome)
        except Exception as error:
            logger.exception(f"{self}: turn failed")
            await self.push_error(
                error_msg=f"CompanionBrain turn failed: {error}",
                exception=error,
            )
        finally:
            await self.push_frame(LLMFullResponseEndFrame())
            self._turn_task = None

    def _log_outcome(self, outcome: VoiceTurnOutcome) -> None:
        logger.info(
            f"Boxi decision={outcome.final_decision} "
            f"avatar_state={outcome.avatar_state} "
            f"called_llm={outcome.called_llm}"
        )

    def _schedule_off_path_work(self, outcome: VoiceTurnOutcome) -> None:
        self.create_task(
            asyncio.to_thread(self._brain.remember, outcome),
            name="companion_brain_remember",
        )
        if outcome.called_llm:
            budget = load_budget_config()
            self.create_task(
                asyncio.to_thread(run_reflection_if_due, self._brain._store, budget),
                name="companion_brain_reflection",
            )
