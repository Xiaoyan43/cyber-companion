from __future__ import annotations

from backend.app.behavior.local_responses import local_response_for_decision
from backend.app.behavior.mood import (
    apply_user_message_mood_delta,
    choose_tone_mode,
    find_stale_job_memory,
)
from backend.app.behavior.rules import (
    is_empty_input,
    is_low_value_input,
    is_rambling,
    matches_refuse_pattern,
    mentions_job_topic,
    mentions_overwhelmed,
)
from backend.app.behavior.types import BehaviorDecision, BehaviorEvent
from backend.app.memory.store import MemoryStore


def evaluate_behavior(store: MemoryStore, event: BehaviorEvent) -> BehaviorDecision:
    if event.event_type == "user_message":
        return _evaluate_user_message(store, event.user_input)

    if event.event_type == "proactive_check":
        return _evaluate_proactive_check(store)

    return BehaviorDecision(
        decision="observe",
        avatar_state="idle",
        should_call_llm=False,
        reason=f"unsupported_event:{event.event_type}",
    )


def _evaluate_user_message(store: MemoryStore, user_input: str) -> BehaviorDecision:
    mood = store.get_mood_state()
    empty = is_empty_input(user_input)
    low_value = is_low_value_input(user_input)
    rambling = is_rambling(user_input)
    overwhelmed = mentions_overwhelmed(user_input)
    refused = matches_refuse_pattern(user_input)
    tone_mode = choose_tone_mode(mood, overwhelmed=overwhelmed)

    updated_mood = apply_user_message_mood_delta(
        mood,
        empty=empty,
        low_value=low_value,
        rambling=rambling,
        overwhelmed=overwhelmed,
        refused=refused,
    )
    store.update_mood_state(
        mood=updated_mood.mood,
        energy=updated_mood.energy,
        annoyance=updated_mood.annoyance,
        boredom=updated_mood.boredom,
        worry=updated_mood.worry,
        trust=updated_mood.trust,
        loneliness=updated_mood.loneliness,
        metadata=updated_mood.metadata,
    )

    if empty:
        return BehaviorDecision(
            decision="silent",
            avatar_state="silent",
            should_call_llm=False,
            reason="empty_user_input",
            local_response=local_response_for_decision("silent"),
            tone_mode=tone_mode,
        )

    if refused:
        return BehaviorDecision(
            decision="refuse",
            avatar_state="angry",
            should_call_llm=False,
            reason="refused_request_pattern",
            local_response=local_response_for_decision("refuse"),
            tone_mode="normal",
        )

    stale_job = find_stale_job_memory(store.list_memories(limit=100))
    casual = len(user_input.strip()) <= 48 and not rambling and not overwhelmed
    if stale_job and not mentions_job_topic(user_input) and casual:
        return BehaviorDecision(
            decision="proactive",
            avatar_state="worried",
            should_call_llm=False,
            reason="stale_job_progress",
            local_response=local_response_for_decision("proactive"),
            tone_mode=tone_mode,
        )

    if low_value:
        return BehaviorDecision(
            decision="silent" if updated_mood.annoyance >= 0.55 else "mutter",
            avatar_state="annoyed",
            should_call_llm=False,
            reason="low_value_user_input",
            local_response=local_response_for_decision(
                "silent" if updated_mood.annoyance >= 0.55 else "mutter",
            ),
            tone_mode=tone_mode,
        )

    if rambling:
        return BehaviorDecision(
            decision="interrupt",
            avatar_state="annoyed",
            should_call_llm=True,
            reason="user_rambling",
            tone_mode=tone_mode,
        )

    avatar_state = "thinking" if tone_mode == "normal" else "worried" if tone_mode == "comfort" else "idle"
    return BehaviorDecision(
        decision="reply",
        avatar_state=avatar_state,
        should_call_llm=True,
        reason="user_message_needs_response",
        tone_mode=tone_mode,
    )


def _evaluate_proactive_check(store: MemoryStore) -> BehaviorDecision:
    stale_job = find_stale_job_memory(store.list_memories(limit=100))
    if stale_job is None:
        return BehaviorDecision(
            decision="observe",
            avatar_state="idle",
            should_call_llm=False,
            reason="no_stale_job_progress",
        )

    return BehaviorDecision(
        decision="proactive",
        avatar_state="worried",
        should_call_llm=False,
        reason="stale_job_progress",
        local_response=local_response_for_decision("proactive"),
        tone_mode="normal",
    )
