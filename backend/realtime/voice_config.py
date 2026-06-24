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
# Doubao BigASR server-side endpointing silence window (also reused as half-duplex
# resume_guard via run_voice). 300ms cut users off mid-sentence on a normal breath
# (P14 Phase 3, user-confirmed); 800ms validated real-machine 2026-06-23. Note: pure
# silence window has a ceiling — a long thinking pause still trips it; semantic
# endpointing (Doubao AIVAD, on the RTC-AIGC product, not BigASR) is the real fix,
# deferred to a future ASR-selection decision.
DEFAULT_ASR_END_WINDOW_MS = 800

# Spoken reply cap (room for ~1–2 sentences + signals trailer).
DEFAULT_VOICE_MAX_TOKENS = 200

ENV_VAD_STOP_SECS = "CYBER_COMPANION_VOICE_VAD_STOP_SECS"
ENV_ASR_END_WINDOW_MS = "CYBER_COMPANION_VOICE_ASR_END_WINDOW_MS"
ENV_MAX_TOKENS = "CYBER_COMPANION_VOICE_MAX_TOKENS"
ENV_HALF_DUPLEX = "CYBER_COMPANION_VOICE_HALF_DUPLEX"
ENV_VOICE_MODE = "CYBER_COMPANION_VOICE_MODE"
ENV_VOICE_OUTPUT_MODE = "CYBER_COMPANION_VOICE_OUTPUT_MODE"
# Kill-switch for the P14 Phase 4 two-stage expression tagger (set to 0/off to bypass it and
# send the brain's plain text straight to TTS — used to A/B first-audio latency tagger on vs off).
ENV_EXPRESSION_TAGGER = "CYBER_COMPANION_VOICE_EXPRESSION_TAGGER"

DEFAULT_HALF_DUPLEX = True
DEFAULT_VOICE_MODE = "pipeline"
DEFAULT_VOICE_OUTPUT_MODE = 0
DEFAULT_EXPRESSION_TAGGER = True


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


def load_half_duplex_enabled() -> bool:
    return _env_bool(ENV_HALF_DUPLEX, DEFAULT_HALF_DUPLEX)


def load_expression_tagger_enabled() -> bool:
    return _env_bool(ENV_EXPRESSION_TAGGER, DEFAULT_EXPRESSION_TAGGER)


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
