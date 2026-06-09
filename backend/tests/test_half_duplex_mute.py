import asyncio

import pytest

pytest.importorskip("pipecat")

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    InputAudioRawFrame,
    TranscriptionFrame,
    VADUserStartedSpeakingFrame,
)

from backend.realtime.half_duplex_mute_processor import HalfDuplexMuteGate


def test_mute_gate_silences_audio_but_keeps_frame() -> None:
    async def run() -> None:
        gate = HalfDuplexMuteGate(resume_guard_ms=0)
        await gate.on_frame(BotStartedSpeakingFrame())
        assert gate.user_is_muted is True

        frame = InputAudioRawFrame(audio=b"\x01\x02\x03\x04", sample_rate=16_000, num_channels=1)
        silenced = gate.silence_if_muted(frame)
        assert silenced.audio == b"\x00\x00\x00\x00"
        assert gate.should_suppress_input(frame) is False

    asyncio.run(run())


def test_mute_gate_blocks_vad_and_transcripts_while_bot_speaks() -> None:
    async def run() -> None:
        gate = HalfDuplexMuteGate(resume_guard_ms=0)
        await gate.on_frame(BotStartedSpeakingFrame())

        assert gate.should_suppress_input(VADUserStartedSpeakingFrame()) is True
        assert gate.should_suppress_stt_out(TranscriptionFrame("回声", "", "", None)) is True

        await gate.on_frame(BotStoppedSpeakingFrame())
        assert gate.user_is_muted is False

    asyncio.run(run())
