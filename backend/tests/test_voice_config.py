import os

from backend.realtime import voice_config


def test_voice_config_defaults(monkeypatch) -> None:
    monkeypatch.delenv(voice_config.ENV_VAD_STOP_SECS, raising=False)
    monkeypatch.delenv(voice_config.ENV_ASR_END_WINDOW_MS, raising=False)
    monkeypatch.delenv(voice_config.ENV_MAX_TOKENS, raising=False)
    monkeypatch.delenv(voice_config.ENV_HALF_DUPLEX, raising=False)

    assert voice_config.load_vad_stop_secs() == 0.4
    assert voice_config.load_asr_end_window_ms() == 300
    assert voice_config.load_voice_max_tokens() == 200
    assert voice_config.load_half_duplex_enabled() is True


def test_voice_config_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv(voice_config.ENV_VAD_STOP_SECS, "0.55")
    monkeypatch.setenv(voice_config.ENV_ASR_END_WINDOW_MS, "450")
    monkeypatch.setenv(voice_config.ENV_MAX_TOKENS, "180")
    monkeypatch.setenv(voice_config.ENV_HALF_DUPLEX, "off")

    assert voice_config.load_vad_stop_secs() == 0.55
    assert voice_config.load_asr_end_window_ms() == 450
    assert voice_config.load_voice_max_tokens() == 180
    assert voice_config.load_half_duplex_enabled() is False


def test_voice_mode_defaults(monkeypatch) -> None:
    monkeypatch.delenv(voice_config.ENV_VOICE_MODE, raising=False)
    monkeypatch.delenv(voice_config.ENV_VOICE_OUTPUT_MODE, raising=False)
    assert voice_config.load_voice_mode() == "pipeline"
    assert voice_config.load_voice_output_mode() == 0


def test_voice_mode_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv(voice_config.ENV_VOICE_MODE, "realtime")
    monkeypatch.setenv(voice_config.ENV_VOICE_OUTPUT_MODE, "0")
    assert voice_config.load_voice_mode() == "realtime"
    assert voice_config.load_voice_output_mode() == 0
