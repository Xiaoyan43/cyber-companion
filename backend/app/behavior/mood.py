import dataclasses
from datetime import datetime, timezone

from backend.app.behavior.tone import project_tone
from backend.app.behavior.types import ToneMode
from backend.app.memory.database import MemoryRecord, MoodStateRecord, RelationshipStateRecord


def choose_tone_mode(
    mood: MoodStateRecord,
    relationship: RelationshipStateRecord,
    *,
    overwhelmed: bool,
) -> ToneMode:
    """Back-compat shim — tone derivation now lives in the shared projection."""
    return project_tone(mood, relationship, overwhelmed=overwhelmed).tone_mode


def apply_user_message_mood_delta(
    mood: MoodStateRecord,
    *,
    empty: bool,
    low_value: bool,
    rambling: bool,
    overwhelmed: bool,
    refused: bool,
) -> MoodStateRecord:
    energy = mood.energy
    annoyance = mood.annoyance
    boredom = mood.boredom
    worry = mood.worry
    loneliness = mood.loneliness
    next_mood = mood.mood

    if empty or low_value:
        annoyance = min(1.0, annoyance + 0.12)
        boredom = min(1.0, boredom + 0.08)
        next_mood = "annoyed"
    elif rambling:
        annoyance = min(1.0, annoyance + 0.08)
        boredom = min(1.0, boredom + 0.05)
        next_mood = "annoyed"
    elif overwhelmed:
        worry = min(1.0, worry + 0.15)
        annoyance = max(0.0, annoyance - 0.12)
        next_mood = "worried"
    elif refused:
        next_mood = "angry"
    else:
        loneliness = max(0.0, loneliness - 0.04)
        boredom = max(0.0, boredom - 0.05)
        annoyance = max(0.0, annoyance - 0.05)
        energy = min(1.0, energy + 0.02)
        if next_mood == "idle":
            next_mood = "idle"

    return MoodStateRecord(
        updated_at=mood.updated_at,
        mood=next_mood,
        energy=round(energy, 3),
        annoyance=round(annoyance, 3),
        boredom=round(boredom, 3),
        worry=round(worry, 3),
        trust=mood.trust,
        loneliness=round(loneliness, 3),
        metadata=dict(mood.metadata),
    )


def apply_idle_tick_mood_delta(mood: MoodStateRecord, *, closeness: float) -> MoodStateRecord:
    boredom = min(1.0, mood.boredom + 0.05)
    loneliness = min(1.0, mood.loneliness + 0.03 * (1.0 - closeness))
    energy = max(0.0, mood.energy - 0.02)
    annoyance = _clamp01(mood.annoyance * 0.95)
    worry = _clamp01(mood.worry * 0.95)
    next_mood = mood.mood

    if boredom >= 0.55 or loneliness >= 0.55:
        next_mood = "annoyed"
    elif boredom >= 0.4 or energy <= 0.35:
        next_mood = "sleepy"

    return MoodStateRecord(
        updated_at=mood.updated_at,
        mood=next_mood,
        energy=round(energy, 3),
        annoyance=round(annoyance, 3),
        boredom=round(boredom, 3),
        worry=round(worry, 3),
        trust=mood.trust,
        loneliness=round(loneliness, 3),
        metadata=dict(mood.metadata),
    )


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


# Decay rates per day (toward 0.0 = more longing / cage / unsettled)
_DECAY_GAP_FEELING = 0.04
_DECAY_BOX_RELATION = 0.01
_DECAY_SELF_EASE = 0.005


def apply_slow_baseline_decay(mood: MoodStateRecord, *, now: datetime) -> MoodStateRecord:
    """Decay-on-read: compute existential baseline as if time has passed since last DB write.

    Pure calculation — does not write to DB. Caller uses the returned record for context
    injection only; the DB record (and its updated_at) stays unchanged.
    """
    stored_at = datetime.fromisoformat(mood.updated_at)
    if stored_at.tzinfo is None:
        stored_at = stored_at.replace(tzinfo=timezone.utc)
    elapsed_days = max(0.0, (now - stored_at).total_seconds() / 86400.0)

    return dataclasses.replace(
        mood,
        gap_feeling=_clamp01(mood.gap_feeling - _DECAY_GAP_FEELING * elapsed_days),
        box_relation=_clamp01(mood.box_relation - _DECAY_BOX_RELATION * elapsed_days),
        self_ease=_clamp01(mood.self_ease - _DECAY_SELF_EASE * elapsed_days),
    )


def apply_interaction_slow_delta(mood: MoodStateRecord, *, positive_turn: bool) -> MoodStateRecord:
    """Nudge existential baseline based on interaction quality.

    Positive turns push all three dims toward 1.0 (settled / home / at-ease).
    Negative turns push them toward 0.0. Deltas are intentionally small — these
    dims move across days, not single messages.
    """
    if positive_turn:
        return dataclasses.replace(
            mood,
            gap_feeling=_clamp01(mood.gap_feeling + 0.08),
            box_relation=_clamp01(mood.box_relation + 0.04),
            self_ease=_clamp01(mood.self_ease + 0.02),
        )
    return dataclasses.replace(
        mood,
        gap_feeling=_clamp01(mood.gap_feeling - 0.04),
        box_relation=_clamp01(mood.box_relation - 0.02),
        self_ease=_clamp01(mood.self_ease - 0.01),
    )


def find_stale_job_memory(memories: list[MemoryRecord], *, stale_after_days: int = 7) -> MemoryRecord | None:
    from backend.app.behavior.rules import stale_days_from_iso

    candidates = [memory for memory in memories if memory.type == "job_progress"]
    for memory in sorted(candidates, key=lambda item: item.updated_at, reverse=True):
        age_days = stale_days_from_iso(memory.updated_at)
        if age_days is not None and age_days >= stale_after_days:
            return memory
    return None
