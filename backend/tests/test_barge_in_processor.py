from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("pipecat")

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    InterruptionFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.tests.utils import SleepFrame, run_test

from backend.realtime.barge_in_processor import BargeInProcessor


def _has_interruption(frames) -> bool:
    return any(isinstance(frame, InterruptionFrame) for frame in frames)


def test_no_interruption_when_bot_silent() -> None:
    async def run() -> None:
        processor = BargeInProcessor(enabled=True, min_speech_secs=0.02)
        down, up = await run_test(
            processor,
            frames_to_send=[VADUserStartedSpeakingFrame(), SleepFrame(sleep=0.1)],
        )
        assert not _has_interruption(down)
        assert not _has_interruption(up)

    asyncio.run(run())


def test_interrupts_after_debounce_while_bot_speaking() -> None:
    async def run() -> None:
        processor = BargeInProcessor(enabled=True, min_speech_secs=0.02)
        down, up = await run_test(
            processor,
            frames_to_send=[
                BotStartedSpeakingFrame(),
                VADUserStartedSpeakingFrame(),
                SleepFrame(sleep=0.1),
            ],
        )
        assert _has_interruption(down)
        assert _has_interruption(up)

    asyncio.run(run())


def test_user_stopping_before_debounce_cancels_interruption() -> None:
    async def run() -> None:
        processor = BargeInProcessor(enabled=True, min_speech_secs=0.2)
        down, up = await run_test(
            processor,
            frames_to_send=[
                BotStartedSpeakingFrame(),
                VADUserStartedSpeakingFrame(),
                SleepFrame(sleep=0.02),
                VADUserStoppedSpeakingFrame(),
                SleepFrame(sleep=0.3),
            ],
        )
        assert not _has_interruption(down)
        assert not _has_interruption(up)

    asyncio.run(run())


def test_bot_stopping_before_debounce_cancels_interruption() -> None:
    async def run() -> None:
        processor = BargeInProcessor(enabled=True, min_speech_secs=0.2)
        down, up = await run_test(
            processor,
            frames_to_send=[
                BotStartedSpeakingFrame(),
                VADUserStartedSpeakingFrame(),
                SleepFrame(sleep=0.02),
                BotStoppedSpeakingFrame(),
                SleepFrame(sleep=0.3),
            ],
        )
        assert not _has_interruption(down)
        assert not _has_interruption(up)

    asyncio.run(run())


def test_disabled_never_interrupts() -> None:
    async def run() -> None:
        processor = BargeInProcessor(enabled=False, min_speech_secs=0.02)
        down, up = await run_test(
            processor,
            frames_to_send=[
                BotStartedSpeakingFrame(),
                VADUserStartedSpeakingFrame(),
                SleepFrame(sleep=0.1),
            ],
        )
        assert not _has_interruption(down)
        assert not _has_interruption(up)

    asyncio.run(run())
