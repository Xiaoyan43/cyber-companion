import os

from backend.realtime import voice_config


def test_voice_config_defaults(monkeypatch) -> None:
    monkeypatch.delenv(voice_config.ENV_VAD_STOP_SECS, raising=False)
    monkeypatch.delenv(voice_config.ENV_ASR_END_WINDOW_MS, raising=False)
    monkeypatch.delenv(voice_config.ENV_MAX_TOKENS, raising=False)

    assert voice_config.load_vad_stop_secs() == 0.4
    assert voice_config.load_asr_end_window_ms() == 300
    assert voice_config.load_voice_max_tokens() == 200


def test_voice_config_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv(voice_config.ENV_VAD_STOP_SECS, "0.55")
    monkeypatch.setenv(voice_config.ENV_ASR_END_WINDOW_MS, "450")
    monkeypatch.setenv(voice_config.ENV_MAX_TOKENS, "180")

    assert voice_config.load_vad_stop_secs() == 0.55
    assert voice_config.load_asr_end_window_ms() == 450
    assert voice_config.load_voice_max_tokens() == 180
