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


@pytest.mark.parametrize("latency", ["balanced", "normal"])
def test_build_tts_accepts_supported_latency(monkeypatch, latency) -> None:
    """run_voice._build_tts accepts the documented Fish latency values."""
    from backend.realtime.run_voice import _build_tts

    monkeypatch.setenv("FISH_AUDIO_API_KEY", "test-key")
    monkeypatch.setenv("FISH_AUDIO_REFERENCE_ID", "test-reference-id")
    monkeypatch.setenv("CYBER_COMPANION_VOICE_TTS_LATENCY", latency)

    svc, sample_rate = _build_tts("fish_audio")
    assert svc._settings.latency == latency
    assert sample_rate == 44_100


def test_build_tts_rejects_low_latency(monkeypatch) -> None:
    """`low` is undefined passthrough for the official service and must be rejected (P14 Phase 5)."""
    from backend.realtime.run_voice import _build_tts

    monkeypatch.setenv("FISH_AUDIO_API_KEY", "test-key")
    monkeypatch.setenv("FISH_AUDIO_REFERENCE_ID", "test-reference-id")
    monkeypatch.setenv("CYBER_COMPANION_VOICE_TTS_LATENCY", "low")

    with pytest.raises(SystemExit, match="normal, balanced"):
        _build_tts("fish_audio")
