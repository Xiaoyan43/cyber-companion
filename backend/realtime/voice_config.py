"""Env-overridable voice latency + terseness knobs (realtime layer only)."""

from __future__ import annotations

import os


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return float(raw)


def _env_optional_float(name: str) -> float | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return int(raw)


# Turn-finalize (conservative defaults — dial back via env if endpointing clips).
DEFAULT_VAD_STOP_SECS = 0.4
# Doubao BigASR server-side endpointing silence window. 300ms cut users off mid-sentence
# on a normal breath (P14 Phase 3, user-confirmed); 800ms validated real-machine
# 2026-06-23. Note: pure silence window has a ceiling — a long thinking pause still trips
# it; semantic endpointing (Doubao AIVAD, on the RTC-AIGC product, not BigASR) is the
# real fix, deferred to a future ASR-selection decision.
DEFAULT_ASR_END_WINDOW_MS = 800

# Spoken reply cap (room for ~1–2 sentences + signals trailer).
DEFAULT_VOICE_MAX_TOKENS = 200

ENV_VAD_STOP_SECS = "CYBER_COMPANION_VOICE_VAD_STOP_SECS"
ENV_ASR_END_WINDOW_MS = "CYBER_COMPANION_VOICE_ASR_END_WINDOW_MS"
ENV_MAX_TOKENS = "CYBER_COMPANION_VOICE_MAX_TOKENS"
ENV_VOICE_MODE = "CYBER_COMPANION_VOICE_MODE"
ENV_VOICE_OUTPUT_MODE = "CYBER_COMPANION_VOICE_OUTPUT_MODE"
# Kill-switch for the P14 Phase 4 two-stage expression tagger (set to 0/off to bypass it and
# send the brain's plain text straight to TTS — used to A/B first-audio latency tagger on vs off).
ENV_EXPRESSION_TAGGER = "CYBER_COMPANION_VOICE_EXPRESSION_TAGGER"
# Fish Audio Pipecat TTS tuning. Empty means "do not pass the setting", preserving the
# current Pipecat/Fish default for the baseline A/B group.
ENV_FISH_NORMALIZE = "CYBER_COMPANION_VOICE_FISH_NORMALIZE"
ENV_FISH_TEMPERATURE = "CYBER_COMPANION_VOICE_FISH_TEMPERATURE"
ENV_FISH_TOP_P = "CYBER_COMPANION_VOICE_FISH_TOP_P"
ENV_FISH_PROSODY_SPEED = "CYBER_COMPANION_VOICE_FISH_PROSODY_SPEED"
ENV_FISH_PROSODY_VOLUME = "CYBER_COMPANION_VOICE_FISH_PROSODY_VOLUME"
# Kill-switch for barge-in (set to 0/off to fall back to no-interruption behavior).
ENV_BARGE_IN_ENABLED = "CYBER_COMPANION_VOICE_BARGE_IN"
# Minimum sustained user speech, on top of the VAD's own ~0.2s start_secs debounce already
# baked into VADUserStartedSpeakingFrame, before a barge-in is committed — filters out
# coughs/breaths/mic noise while Boxi is talking. Stacked with VAD start_secs this lands
# total user-perceived barge-in latency around 0.5s, matching LiveKit Agents'
# InterruptionOptions.min_duration production default (2026-06-30 web research, see HANDOFF).
ENV_BARGE_IN_MIN_SECS = "CYBER_COMPANION_VOICE_BARGE_IN_MIN_SECS"

DEFAULT_VOICE_MODE = "pipeline"
DEFAULT_VOICE_OUTPUT_MODE = 0
DEFAULT_EXPRESSION_TAGGER = True
DEFAULT_BARGE_IN_ENABLED = True
DEFAULT_BARGE_IN_MIN_SECS = 0.3


def load_vad_stop_secs() -> float:
    return _env_float(ENV_VAD_STOP_SECS, DEFAULT_VAD_STOP_SECS)


def load_asr_end_window_ms() -> int:
    return _env_int(ENV_ASR_END_WINDOW_MS, DEFAULT_ASR_END_WINDOW_MS)


def load_voice_max_tokens() -> int:
    return _env_int(ENV_MAX_TOKENS, DEFAULT_VOICE_MAX_TOKENS)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "on", "yes"}:
        return True
    if raw in {"0", "false", "off", "no"}:
        return False
    raise ValueError(f"{name} must be one of: on, off, true, false, 1, 0")


def load_expression_tagger_enabled() -> bool:
    return _env_bool(ENV_EXPRESSION_TAGGER, DEFAULT_EXPRESSION_TAGGER)


def load_barge_in_enabled() -> bool:
    return _env_bool(ENV_BARGE_IN_ENABLED, DEFAULT_BARGE_IN_ENABLED)


def load_barge_in_min_secs() -> float:
    return _env_float(ENV_BARGE_IN_MIN_SECS, DEFAULT_BARGE_IN_MIN_SECS)


def load_fish_normalize() -> bool | None:
    raw = os.getenv(ENV_FISH_NORMALIZE, "").strip()
    if not raw:
        return None
    return _env_bool(ENV_FISH_NORMALIZE, False)


def load_fish_temperature() -> float | None:
    return _env_optional_float(ENV_FISH_TEMPERATURE)


def load_fish_top_p() -> float | None:
    return _env_optional_float(ENV_FISH_TOP_P)


def load_fish_prosody_speed() -> float | None:
    return _env_optional_float(ENV_FISH_PROSODY_SPEED)


def load_fish_prosody_volume() -> int | None:
    raw = os.getenv(ENV_FISH_PROSODY_VOLUME, "").strip()
    if not raw:
        return None
    return int(raw)


def load_voice_mode() -> str:
    raw = os.getenv(ENV_VOICE_MODE, DEFAULT_VOICE_MODE).strip().lower()
    if raw not in {"pipeline", "realtime"}:
        raise ValueError(f"{ENV_VOICE_MODE} must be one of: pipeline, realtime")
    return raw


def load_voice_output_mode() -> int:
    raw = os.getenv(ENV_VOICE_OUTPUT_MODE, "").strip()
    if not raw:
        return DEFAULT_VOICE_OUTPUT_MODE
    mode = int(raw)
    if mode not in {0, 1}:
        raise ValueError(f"{ENV_VOICE_OUTPUT_MODE} must be 0 (pure) or 1 (hybrid)")
    return mode
