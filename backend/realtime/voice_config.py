"""Env-overridable voice latency + terseness knobs (realtime layer only)."""

from __future__ import annotations

import os


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return int(raw)


# Turn-finalize (conservative defaults — dial back via env if endpointing clips).
DEFAULT_VAD_STOP_SECS = 0.4
DEFAULT_ASR_END_WINDOW_MS = 300

# Spoken reply cap (room for ~1–2 sentences + signals trailer).
DEFAULT_VOICE_MAX_TOKENS = 200

ENV_VAD_STOP_SECS = "CYBER_COMPANION_VOICE_VAD_STOP_SECS"
ENV_ASR_END_WINDOW_MS = "CYBER_COMPANION_VOICE_ASR_END_WINDOW_MS"
ENV_MAX_TOKENS = "CYBER_COMPANION_VOICE_MAX_TOKENS"


def load_vad_stop_secs() -> float:
    return _env_float(ENV_VAD_STOP_SECS, DEFAULT_VAD_STOP_SECS)


def load_asr_end_window_ms() -> int:
    return _env_int(ENV_ASR_END_WINDOW_MS, DEFAULT_ASR_END_WINDOW_MS)


def load_voice_max_tokens() -> int:
    return _env_int(ENV_MAX_TOKENS, DEFAULT_VOICE_MAX_TOKENS)
