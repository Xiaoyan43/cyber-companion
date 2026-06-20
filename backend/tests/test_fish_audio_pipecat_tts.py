"""Smoke tests for the pipecat Fish Audio TTS integration (official service)."""

import pytest


def test_official_fish_audio_service_importable() -> None:
    from pipecat.services.fish.tts import FishAudioTTSService

    assert FishAudioTTSService is not None


def test_official_service_initializes_with_valid_key() -> None:
    from pipecat.services.fish.tts import FishAudioTTSService

    svc = FishAudioTTSService(
        api_key="test-key",
        settings=FishAudioTTSService.Settings(
            voice="test-reference-id",
            model="s2-pro",
            latency="balanced",
        ),
        output_format="pcm",
        sample_rate=44_100,
    )
    assert svc._api_key == "test-key"
    assert svc._settings.voice == "test-reference-id"
    assert svc._settings.model == "s2-pro"
    assert svc._settings.latency == "balanced"
    assert svc._output_format == "pcm"
