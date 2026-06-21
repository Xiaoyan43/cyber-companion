from __future__ import annotations

import random
from datetime import datetime

from backend.app.behavior.local_responses import local_response_for_decision
from backend.app.behavior.longing import (
    check_proactive_availability,
    clear_proactive_pending,
    mark_proactive_check,
    mark_proactive_fired,
    should_fire_longing,
    snapshot_longing,
)
from backend.app.behavior.proactive_reason import fallback_line_for_reason, pick_proactive_reason
from backend.app.behavior.mood import (
    apply_idle_tick_mood_delta,
    apply_user_message_mood_delta,
    find_stale_job_memory,
)
from backend.app.behavior.tone import in_positive_zone, next_positive_streak, project_tone
from backend.app.behavior.tick_policy import mark_local_line_spoken, recently_spoke_locally
from backend.app.behavior.rules import (
    is_empty_input,
    is_low_value_input,
    is_rambling,
    matches_refuse_pattern,
    mentions_job_topic,
    mentions_overwhelmed,
)
from backend.app.behavior.types import BehaviorDecision, BehaviorEvent
from backend.app.memory.budget import BudgetConfig, load_budget_config
from backend.app.memory.store import MemoryStore


def evaluate_behavior(
    store: MemoryStore,
    event: BehaviorEvent,
    *,
    budget: BudgetConfig | None = None,
    rng: random.Random | None = None,
    now: datetime | None = None,
) -> BehaviorDecision:
    if event.event_type == "user_message":
        return _evaluate_user_message(store, event.user_input)

    if event.event_type == "proactive_check":
        force_proactive = bool(event.metadata.get("force_proactive"))
        return _evaluate_proactive_check(
            store,
            budget=budget,
            rng=rng,
            now=now,
            force_proactive=force_proactive,
        )

    if event.event_type == "idle_tick":
        return _evaluate_idle_tick(store)

    return BehaviorDecision(
        decision="observe",
        avatar_state="idle",
        should_call_llm=False,
        reason=f"unsupported_event:{event.event_type}",
    )


def _evaluate_user_message(store: MemoryStore, user_input: str) -> BehaviorDecision:
    mood = store.get_mood_state()
    relationship = store.get_relationship_state()
    cleared_metadata = clear_proactive_pending(mood.metadata)
    if cleared_metadata is not mood.metadata:
        store.update_mood_state(metadata=cleared_metadata)
        mood = store.get_mood_state()
    empty = is_empty_input(user_input)
    low_value = is_low_value_input(user_input)
    rambling = is_rambling(user_input)
    overwhelmed = mentions_overwhelmed(user_input)
    refused = matches_refuse_pattern(user_input)

    updated_mood = apply_user_message_mood_delta(
        mood,
        empty=empty,
        low_value=low_value,
        rambling=rambling,
        overwhelmed=overwhelmed,
        refused=refused,
    )
    # Felt-vs-shown projection: arm playful teasing only after a streak of clean
    # positive-zone reply turns, so it reads as a mood, not a per-turn glitch.
    # Any negative message event (empty / low-value / rambling / overwhelmed /
    # refusal) resets the streak immediately. (spec paired slice)
    clean_turn = not (empty or low_value or rambling or overwhelmed or refused)
    positive_turn = clean_turn and in_positive_zone(
        mood, relationship, overwhelmed=overwhelmed
    )
    streak_metadata, performative_active = next_positive_streak(
        updated_mood.metadata, positive_turn=positive_turn
    )
    projection = project_tone(
        mood,
        relationship,
        overwhelmed=overwhelmed,
        performative_active=performative_active,
    )
    tone_mode = projection.tone_mode
    store.update_mood_state(
        mood=updated_mood.mood,
        energy=updated_mood.energy,
        annoyance=updated_mood.annoyance,
        boredom=updated_mood.boredom,
        worry=updated_mood.worry,
        loneliness=updated_mood.loneliness,
        metadata=streak_metadata,
    )

    if empty:
        return BehaviorDecision(
            decision="silent",
            avatar_state="silent",
            should_call_llm=False,
            reason="empty_user_input",
            local_response=local_response_for_decision("silent"),
            tone_mode=tone_mode,
            tone=projection,
        )

    if refused:
        store.update_relationship_state(
            tension=min(1.0, relationship.tension + 0.08),
            trust=max(0.0, relationship.trust - 0.05),
        )
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
            tone=projection,
        )

    if rambling:
        return BehaviorDecision(
            decision="interrupt",
            avatar_state="annoyed",
            should_call_llm=True,
            reason="user_rambling",
            tone_mode=tone_mode,
            tone=projection,
        )

    if overwhelmed:
        store.update_relationship_state(trust=min(1.0, relationship.trust + 0.04))

    avatar_state = "thinking" if tone_mode == "normal" else "worried" if tone_mode == "comfort" else "idle"
    return BehaviorDecision(
        decision="reply",
        avatar_state=avatar_state,
        should_call_llm=True,
        reason="user_message_needs_response",
        tone_mode=tone_mode,
        tone=projection,
    )


def _evaluate_proactive_check(
    store: MemoryStore,
    *,
    budget: BudgetConfig | None = None,
    rng: random.Random | None = None,
    now: datetime | None = None,
    force_proactive: bool = False,
) -> BehaviorDecision:
    config = budget or load_budget_config()
    mood = store.get_mood_state()
    relationship = store.get_relationship_state()

    if not force_proactive and recently_spoke_locally(mood):
        return BehaviorDecision(
            decision="observe",
            avatar_state="idle",
            should_call_llm=False,
            reason="local_line_cooldown",
        )

    gate = check_proactive_availability(
        budget=config,
        mood=mood,
        relationship=relationship,
        last_user_message_at=store.get_last_user_chat_created_at(),
        now=now,
        skip_timing_gates=force_proactive,
    )
    if gate.blocked:
        return BehaviorDecision(
            decision="observe",
            avatar_state="idle",
            should_call_llm=False,
            reason=gate.reason or "proactive_gate",
        )

    longing = snapshot_longing(
        closeness=relationship.closeness,
        loneliness=mood.loneliness,
        last_meaningful_interaction_at=relationship.last_meaningful_interaction_at,
        metadata=mood.metadata,
        budget=config,
        now=now,
    )

    aware_now = now if now is not None else datetime.now().astimezone()
    check_metadata = mark_proactive_check(mood.metadata, now=aware_now)
    store.update_mood_state(metadata=check_metadata)

    fired = force_proactive or should_fire_longing(longing, rng=rng)
    if not fired:
        return BehaviorDecision(
            decision="observe",
            avatar_state="idle",
            should_call_llm=False,
            reason="longing_poisson_miss",
        )

    stale_job = find_stale_job_memory(store.list_memories(limit=100))
    fired_metadata = mark_proactive_fired(check_metadata, now=aware_now)
    fired_metadata = mark_local_line_spoken(fired_metadata)
    store.update_mood_state(metadata=fired_metadata)

    proactive_reason = pick_proactive_reason(
        store,
        longing_intensity=longing.intensity,
        now=aware_now,
    )
    return BehaviorDecision(
        decision="proactive",
        avatar_state=proactive_reason.avatar_state,
        should_call_llm=True,
        reason=proactive_reason.kind,
        local_response=fallback_line_for_reason(proactive_reason),
        tone_mode="normal",
        proactive_reason=proactive_reason,
    )


# Temporarily disabled (2026-06-21, see docs/TASK_QUEUE.md "P9"): this fired the same
# hardcoded line every 3-min cooldown window once boredom/loneliness crossed 0.55, with
# no variation — produced 200 identical persisted messages over one idle session. Off
# until the proactive/idle-behavior redesign (P9) replaces it; flip back to True only as
# a stopgap, not a fix.
_IDLE_MUTTER_ENABLED = False


def _evaluate_idle_tick(store: MemoryStore) -> BehaviorDecision:
    mood = store.get_mood_state()
    relationship = store.get_relationship_state()
    updated_mood = apply_idle_tick_mood_delta(mood, closeness=relationship.closeness)
    store.update_mood_state(
        mood=updated_mood.mood,
        energy=updated_mood.energy,
        boredom=updated_mood.boredom,
        loneliness=updated_mood.loneliness,
        metadata=updated_mood.metadata,
    )

    if recently_spoke_locally(updated_mood):
        return BehaviorDecision(
            decision="observe",
            avatar_state=updated_mood.mood if updated_mood.mood in {"sleepy", "annoyed"} else "idle",
            should_call_llm=False,
            reason="local_line_cooldown",
        )

    if _IDLE_MUTTER_ENABLED and (updated_mood.boredom >= 0.55 or updated_mood.loneliness >= 0.55):
        store.update_mood_state(metadata=mark_local_line_spoken(updated_mood.metadata))
        return BehaviorDecision(
            decision="mutter",
            avatar_state="annoyed",
            should_call_llm=False,
            reason="idle_boredom_threshold",
            local_response=local_response_for_decision("mutter"),
            tone_mode="normal",
        )

    if updated_mood.boredom >= 0.4 or updated_mood.energy <= 0.35:
        return BehaviorDecision(
            decision="observe",
            avatar_state="sleepy",
            should_call_llm=False,
            reason="idle_low_energy",
        )

    return BehaviorDecision(
        decision="observe",
        avatar_state="idle",
        should_call_llm=False,
        reason="idle_tick",
    )
