"""Unified felt-vs-shown tone projection (Direction C — the being).

One shared helper that every surface reads — text chat, cascaded voice, pure-E2E
RTC, and (later) the visual material — so Boxi suppresses and teases identically
everywhere. One personality, not per-surface drift.

The invariant (spec: ``docs/VISUAL_SPIKE_SPEC.md`` paired slice):

> The light **core** never lies — it is always the true inner feeling (``felt``).
> The **ink** is always the outward performance (``expressed_edge``).

``is_performative`` is the decoupler: when a warm core wears a sharp edge on
purpose, that is teasing (desync-2), not real annoyance. Suppression (desync-1)
falls out of precedence: real worry softens the *expression* while the core may
stay sharp underneath — felt and shown diverge honestly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from backend.app.behavior.types import ToneMode
from backend.app.memory.database import MoodStateRecord, RelationshipStateRecord

FeltState = Literal["warm", "sharp", "worried", "lonely", "neutral"]
ToneRegister = Literal["comfort", "real_sharp", "playful", "warm", "lonely", "neutral"]

# Shared kernel thresholds — previously duplicated across mood.py + state_block.py.
_MOOD_THRESHOLD = 0.5
_TENSION_SHARP = 0.55
_TENSION_CLOSE = 0.3
_CLOSENESS_HIGH = 0.67
_ENERGY_OK = 0.3
_ANNOYANCE_QUIET = 0.3  # positive zone needs annoyance well below the sharp line

# Outward edge crispness (the ink): 0.0 diffuse ↔ 1.0 crisp.
_EDGE_SOFT = 0.15
_EDGE_MID = 0.5
_EDGE_PLAYFUL = 0.85
_EDGE_SHARP = 0.9

# A positive-zone streak must hold this many turns before teasing arms, so it
# reads as a mood that persists — not a per-turn coin-flip that flickers.
PERFORMATIVE_STREAK_THRESHOLD = 2
POSITIVE_STREAK_KEY = "positive_zone_streak"

# register → cascaded/RTC emotion context_texts (base = moderate; RTC reads this only).
_EMOTION_BY_REGISTER: dict[ToneRegister, str | None] = {
    "comfort": "语气放软、关切、稍慢",
    "real_sharp": "更冲、更不耐烦但别凶",
    "playful": "嘴上凶、其实带笑、是逗ta",
    "warm": None,
    "lonely": "更热络一点",
    "neutral": None,
}

# Intense tier — cascaded only; replaces base when register intensity ≥ STRONG_THRESHOLD.
_EMOTION_INTENSE_BY_REGISTER: dict[ToneRegister, str] = {
    "comfort": "很担心、明显心疼、放慢、稳住ta",
    "real_sharp": "明显在火头上、很冲很不耐烦，但绝不人身攻击、不辱骂",
    "playful": "笑意更明显、损得更欢、明显在逗ta",
    "lonely": "明显想找人说话、更热络、黏一点",
}

STRONG_THRESHOLD = 0.75

# Any [bracket] tag is content-authored delivery control (the expression-tagger's whole
# job, see backend/app/tts/expression_tagger.py). When the reply already carries one,
# the mood-driven numeric speech_rate fallback should stay out of its way rather than
# fight it. This used to match a fixed 5-word seed list, which silently stopped working
# once the tagger vocabulary grew beyond those 5 words — match any tag instead so this
# stays correct regardless of how the tagger's vocabulary evolves.
_BRACKET_TAG_PATTERN = re.compile(r"\[[^\[\]]+\]")


def contains_tone_marker_tag(text: str) -> bool:
    """True if text already carries an LLM-authored delivery tag of any kind."""
    return bool(_BRACKET_TAG_PATTERN.search(text))


@dataclass(frozen=True)
class ToneProjection:
    felt: FeltState           # the core — always the true inner feeling
    expressed_edge: float     # the ink — crisp(1.0) ↔ diffuse(0.0)
    is_performative: bool     # True only when a warm core wears a sharp edge (teasing)
    register: ToneRegister    # semantic bucket every surface renders its own words from
    tone_mode: ToneMode       # back-compat enum for the text-chat behavior path


def _is_worried(mood: MoodStateRecord, *, overwhelmed: bool) -> bool:
    return overwhelmed or mood.worry >= _MOOD_THRESHOLD or mood.mood in {"sad", "worried"}


def _is_real_sharp(mood: MoodStateRecord, relationship: RelationshipStateRecord) -> bool:
    return mood.annoyance >= _MOOD_THRESHOLD or relationship.tension >= _TENSION_SHARP


def in_positive_zone(
    mood: MoodStateRecord,
    relationship: RelationshipStateRecord,
    *,
    overwhelmed: bool = False,
) -> bool:
    """Define the positive zone from absence-of-negatives + closeness (no 'happy' field)."""
    if _is_worried(mood, overwhelmed=overwhelmed) or _is_real_sharp(mood, relationship):
        return False
    return (
        mood.annoyance < _ANNOYANCE_QUIET
        and relationship.tension < _TENSION_CLOSE
        and relationship.closeness >= _CLOSENESS_HIGH
        and mood.energy >= _ENERGY_OK
    )


def project_tone(
    mood: MoodStateRecord,
    relationship: RelationshipStateRecord,
    *,
    overwhelmed: bool = False,
    performative_active: bool = False,
) -> ToneProjection:
    """Project kernel state onto (felt, expressed_edge, is_performative) + register.

    Precedence (real states always win): worry/comfort → real-sharp → positive
    zone (playful when armed, else warm) → lonely → neutral.
    """
    worried = _is_worried(mood, overwhelmed=overwhelmed)
    real_sharp = _is_real_sharp(mood, relationship)

    # Real worry wins the *expression* even over annoyance: soft ink. The core
    # still reflects the dominant inner state — annoyed underneath = desync-1.
    if worried:
        felt: FeltState = "sharp" if real_sharp else "worried"
        return ToneProjection(
            felt=felt,
            expressed_edge=_EDGE_SOFT,
            is_performative=False,
            register="comfort",
            tone_mode="comfort",
        )

    # Aligned real-sharp: crisp core, crisp ink. Trusting jab vs cold edge only
    # shifts the verbal register, never the honesty (not performative).
    if real_sharp:
        trusting = (
            relationship.trust >= 0.4
            and relationship.familiarity >= 0.3
            and relationship.tension < 0.5
        )
        return ToneProjection(
            felt="sharp",
            expressed_edge=_EDGE_SHARP,
            is_performative=False,
            register="real_sharp",
            tone_mode="tease" if trusting else "normal",
        )

    if in_positive_zone(mood, relationship, overwhelmed=overwhelmed):
        if performative_active:
            # desync-2 — warm core, sharp edge, on purpose. Teasing is TRUE here.
            return ToneProjection(
                felt="warm",
                expressed_edge=_EDGE_PLAYFUL,
                is_performative=True,
                register="playful",
                tone_mode="playful",
            )
        return ToneProjection(
            felt="warm",
            expressed_edge=_EDGE_MID,
            is_performative=False,
            register="warm",
            tone_mode="normal",
        )

    if mood.loneliness >= _MOOD_THRESHOLD:
        return ToneProjection(
            felt="lonely",
            expressed_edge=_EDGE_MID,
            is_performative=False,
            register="lonely",
            tone_mode="normal",
        )

    return ToneProjection(
        felt="neutral",
        expressed_edge=_EDGE_MID,
        is_performative=False,
        register="neutral",
        tone_mode="normal",
    )


def next_positive_streak(
    metadata: dict,
    *,
    positive_turn: bool,
) -> tuple[dict, bool]:
    """Advance the positive-turn streak; return (new_metadata, performative_active).

    A positive turn (clean reply in the positive zone) increments the streak; any
    non-positive turn resets it to 0 — a real negative breaks the playful mood
    immediately. Teasing arms once the streak reaches ``PERFORMATIVE_STREAK_THRESHOLD``.
    """
    current = metadata.get(POSITIVE_STREAK_KEY)
    current_int = current if isinstance(current, int) and current >= 0 else 0
    streak = current_int + 1 if positive_turn else 0
    updated = dict(metadata)
    updated[POSITIVE_STREAK_KEY] = streak
    return updated, streak >= PERFORMATIVE_STREAK_THRESHOLD


def performative_active_from_metadata(metadata: dict) -> bool:
    """Read the armed flag from persisted kernel metadata (surfaces that only read)."""
    current = metadata.get(POSITIVE_STREAK_KEY)
    return isinstance(current, int) and current >= PERFORMATIVE_STREAK_THRESHOLD


def base_emotion_context_text(register: ToneRegister) -> str | None:
    """Moderate-tier emotion phrase for a register (RTC + cascaded base)."""
    return _EMOTION_BY_REGISTER.get(register)


def register_intensity(
    mood: MoodStateRecord,
    relationship: RelationshipStateRecord,
    projection: ToneProjection,
    *,
    overwhelmed: bool = False,
) -> float:
    """Drive magnitude 0..1 for the active register."""
    register = projection.register
    if register == "comfort":
        return (
            1.0
            if overwhelmed
            else max(mood.worry, 0.8 if mood.mood in {"sad", "worried"} else 0.0)
        )
    if register == "real_sharp":
        return max(mood.annoyance, relationship.tension)
    if register == "playful":
        return relationship.closeness
    if register == "lonely":
        return mood.loneliness
    return 0.0


def tts_emotion_directive(
    projection: ToneProjection,
    *,
    intensity: float,
) -> tuple[list[str] | None, int]:
    """Cascaded Doubao context_texts + speech_rate from kernel projection."""
    base = _EMOTION_BY_REGISTER[projection.register]
    if base is None:
        return None, 0
    intense = _EMOTION_INTENSE_BY_REGISTER.get(projection.register)
    phrase = intense if (intense and intensity >= STRONG_THRESHOLD) else base
    sign = {"comfort": -1, "real_sharp": 1, "playful": 1, "lonely": 1}.get(
        projection.register, 0
    )
    clamped = max(0.0, min(1.0, intensity))
    rate = int(sign * round(6 + 14 * clamped))
    return [phrase], rate
