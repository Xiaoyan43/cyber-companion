from backend.app.behavior.types import BehaviorDecision, ToneMode
from backend.app.memory.database import MemoryRecord, MoodStateRecord


def choose_tone_mode(mood: MoodStateRecord, *, overwhelmed: bool) -> ToneMode:
    if overwhelmed or mood.worry >= 0.65 or mood.mood in {"sad", "worried"}:
        return "comfort"
    if mood.annoyance >= 0.6 and mood.trust >= 0.4:
        return "tease"
    return "normal"


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
    trust = mood.trust
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
        trust = min(1.0, trust + 0.04)
    elif refused:
        trust = max(0.0, trust - 0.05)
        next_mood = "angry"
    else:
        trust = min(1.0, trust + 0.03)
        loneliness = max(0.0, loneliness - 0.04)
        boredom = max(0.0, boredom - 0.05)
        if next_mood == "idle":
            next_mood = "idle"

    return MoodStateRecord(
        updated_at=mood.updated_at,
        mood=next_mood,
        energy=energy,
        annoyance=round(annoyance, 3),
        boredom=round(boredom, 3),
        worry=round(worry, 3),
        trust=round(trust, 3),
        loneliness=round(loneliness, 3),
        metadata=dict(mood.metadata),
    )


def find_stale_job_memory(memories: list[MemoryRecord], *, stale_after_days: int = 7) -> MemoryRecord | None:
    from backend.app.behavior.rules import stale_days_from_iso

    candidates = [memory for memory in memories if memory.type == "job_progress"]
    for memory in sorted(candidates, key=lambda item: item.updated_at, reverse=True):
        age_days = stale_days_from_iso(memory.updated_at)
        if age_days is not None and age_days >= stale_after_days:
            return memory
    return None
