
from backend.realtime import voice_config


def test_voice_config_defaults(monkeypatch) -> None:
    monkeypatch.delenv(voice_config.ENV_VAD_STOP_SECS, raising=False)
    monkeypatch.delenv(voice_config.ENV_ASR_END_WINDOW_MS, raising=False)
    monkeypatch.delenv(voice_config.ENV_MAX_TOKENS, raising=False)
    monkeypatch.delenv(voice_config.ENV_HALF_DUPLEX, raising=False)
    monkeypatch.delenv(voice_config.ENV_FISH_NORMALIZE, raising=False)
    monkeypatch.delenv(voice_config.ENV_FISH_TEMPERATURE, raising=False)
    monkeypatch.delenv(voice_config.ENV_FISH_TOP_P, raising=False)
    monkeypatch.delenv(voice_config.ENV_FISH_PROSODY_SPEED, raising=False)
    monkeypatch.delenv(voice_config.ENV_FISH_PROSODY_VOLUME, raising=False)

    assert voice_config.load_vad_stop_secs() == 0.4
    assert voice_config.load_asr_end_window_ms() == 800
    assert voice_config.load_voice_max_tokens() == 200
    assert voice_config.load_half_duplex_enabled() is True
    assert voice_config.load_fish_normalize() is None
    assert voice_config.load_fish_temperature() is None
    assert voice_config.load_fish_top_p() is None
    assert voice_config.load_fish_prosody_speed() is None
    assert voice_config.load_fish_prosody_volume() is None


def test_voice_config_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv(voice_config.ENV_VAD_STOP_SECS, "0.55")
    monkeypatch.setenv(voice_config.ENV_ASR_END_WINDOW_MS, "450")
    monkeypatch.setenv(voice_config.ENV_MAX_TOKENS, "180")
    monkeypatch.setenv(voice_config.ENV_HALF_DUPLEX, "off")
    monkeypatch.setenv(voice_config.ENV_FISH_NORMALIZE, "false")
    monkeypatch.setenv(voice_config.ENV_FISH_TEMPERATURE, "0.8")
    monkeypatch.setenv(voice_config.ENV_FISH_TOP_P, "0.72")
    monkeypatch.setenv(voice_config.ENV_FISH_PROSODY_SPEED, "0.94")
    monkeypatch.setenv(voice_config.ENV_FISH_PROSODY_VOLUME, "-1")

    assert voice_config.load_vad_stop_secs() == 0.55
    assert voice_config.load_asr_end_window_ms() == 450
    assert voice_config.load_voice_max_tokens() == 180
    assert voice_config.load_half_duplex_enabled() is False
    assert voice_config.load_fish_normalize() is False
    assert voice_config.load_fish_temperature() == 0.8
    assert voice_config.load_fish_top_p() == 0.72
    assert voice_config.load_fish_prosody_speed() == 0.94
    assert voice_config.load_fish_prosody_volume() == -1


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
