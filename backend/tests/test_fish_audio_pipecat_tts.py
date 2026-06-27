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


def test_build_tts_accepts_balanced_latency(monkeypatch) -> None:
    """run_voice._build_tts accepts `balanced` (the only allowed value, P14 Phase 5 P1)."""
    from backend.realtime.run_voice import _build_tts

    monkeypatch.setenv("FISH_AUDIO_API_KEY", "test-key")
    monkeypatch.setenv("FISH_AUDIO_REFERENCE_ID", "test-reference-id")
    monkeypatch.setenv("CYBER_COMPANION_VOICE_TTS_LATENCY", "balanced")

    svc, sample_rate = _build_tts("fish_audio")
    assert svc._settings.latency == "balanced"
    assert sample_rate == 44_100


def test_build_tts_defaults_to_balanced(monkeypatch) -> None:
    """With no latency env set, the default is `balanced`."""
    from backend.realtime.run_voice import _build_tts

    monkeypatch.setenv("FISH_AUDIO_API_KEY", "test-key")
    monkeypatch.setenv("FISH_AUDIO_REFERENCE_ID", "test-reference-id")
    monkeypatch.delenv("CYBER_COMPANION_VOICE_TTS_LATENCY", raising=False)
    monkeypatch.delenv("CYBER_COMPANION_VOICE_FISH_NORMALIZE", raising=False)
    monkeypatch.delenv("CYBER_COMPANION_VOICE_FISH_TEMPERATURE", raising=False)
    monkeypatch.delenv("CYBER_COMPANION_VOICE_FISH_TOP_P", raising=False)
    monkeypatch.delenv("CYBER_COMPANION_VOICE_FISH_PROSODY_SPEED", raising=False)
    monkeypatch.delenv("CYBER_COMPANION_VOICE_FISH_PROSODY_VOLUME", raising=False)

    svc, _ = _build_tts("fish_audio")
    assert svc._settings.latency == "balanced"
    assert svc._settings.normalize is True
    assert svc._settings.temperature is None
    assert svc._settings.top_p is None
    assert svc._settings.prosody_speed == 1.0
    assert svc._settings.prosody_volume == 0


def test_build_tts_applies_optional_fish_settings(monkeypatch) -> None:
    """Fish Pipecat tuning env vars are opt-in and land on the official Settings object."""
    from backend.realtime.run_voice import _build_tts

    monkeypatch.setenv("FISH_AUDIO_API_KEY", "test-key")
    monkeypatch.setenv("FISH_AUDIO_REFERENCE_ID", "test-reference-id")
    monkeypatch.setenv("CYBER_COMPANION_VOICE_TTS_LATENCY", "balanced")
    monkeypatch.setenv("CYBER_COMPANION_VOICE_FISH_NORMALIZE", "false")
    monkeypatch.setenv("CYBER_COMPANION_VOICE_FISH_TEMPERATURE", "0.8")
    monkeypatch.setenv("CYBER_COMPANION_VOICE_FISH_TOP_P", "0.7")
    monkeypatch.setenv("CYBER_COMPANION_VOICE_FISH_PROSODY_SPEED", "0.94")
    monkeypatch.setenv("CYBER_COMPANION_VOICE_FISH_PROSODY_VOLUME", "-1")

    svc, _ = _build_tts("fish_audio")
    assert svc._settings.normalize is False
    assert svc._settings.temperature == 0.8
    assert svc._settings.top_p == 0.7
    assert svc._settings.prosody_speed == 0.94
    assert svc._settings.prosody_volume == -1


@pytest.mark.parametrize("latency", ["low", "normal"])
def test_build_tts_rejects_non_balanced_latency(monkeypatch, latency) -> None:
    """`low` (undefined passthrough) and `normal` (batch render → 3s dead air + P13 silence,
    A/B verdict: not worth it) are both rejected; only `balanced` streams (P14 Phase 5)."""
    from backend.realtime.run_voice import _build_tts

    monkeypatch.setenv("FISH_AUDIO_API_KEY", "test-key")
    monkeypatch.setenv("FISH_AUDIO_REFERENCE_ID", "test-reference-id")
    monkeypatch.setenv("CYBER_COMPANION_VOICE_TTS_LATENCY", latency)

    with pytest.raises(SystemExit, match="balanced"):
        _build_tts("fish_audio")
