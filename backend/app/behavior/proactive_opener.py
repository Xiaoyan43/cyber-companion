from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from backend.app.behavior.proactive_reason import (
    ProactiveReason,
    fallback_line_for_reason,
    format_reason_block,
    record_share_fingerprint,
)
from backend.app.behavior.types import BehaviorDecision
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.context_builder import _format_impression_block, _format_relationship_block
from backend.app.memory.database import MoodStateRecord
from backend.app.memory.persona import load_chinese_persona_prompt
from backend.app.memory.store import MemoryStore
from backend.app.memory.usage_guard import evaluate_llm_budget_gate
from backend.app.providers.exceptions import ProviderError
from backend.app.providers.router import ProviderRouter
from backend.app.providers.types import ChatCompletionRequest, ChatCompletionResult, ChatMessage

_PROACTIVE_OPENER_INSTRUCTION = (
    "[Proactive opener task]\n"
    "You are reaching out on your own — NOT replying to a user message.\n"
    "Write ONE short line in Chinese (max ~25 chars), in Boxi's voice: sharp but warm, "
    "like someone trapped in a box who actually cares — NOT a notification, NOT guilt, "
    "NOT nagging, NOT a lecture.\n"
    "Good example: 记得周四面试吧？别又熬夜。\n"
    "Output ONLY the spoken line. No JSON, no marker, no quotes, no stage directions."
)


def _aware_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _proactive_llm_count_today(metadata: dict[str, object], *, now: datetime) -> int:
    today = now.date().isoformat()
    if metadata.get("proactive_llm_daily_date") != today:
        return 0
    raw = metadata.get("proactive_llm_daily_count", 0)
    try:
        return max(0, int(raw))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def mark_proactive_llm_used(metadata: dict[str, object], *, now: datetime) -> dict[str, object]:
    updated = dict(metadata)
    today = now.date().isoformat()
    if updated.get("proactive_llm_daily_date") != today:
        updated["proactive_llm_daily_date"] = today
        updated["proactive_llm_daily_count"] = 1
    else:
        updated["proactive_llm_daily_count"] = _proactive_llm_count_today(updated, now=now) + 1
    return updated


_FINGERPRINT_KEY = "proactive_recent_fingerprints"


def _fingerprint(reason: ProactiveReason) -> str:
    return f"{reason.kind}:{reason.longing_tier}"


def is_repeated_fingerprint(metadata: dict[str, object], reason: ProactiveReason) -> bool:
    """True if the most recent opener used the same (kind, tier) combo."""
    history = metadata.get(_FINGERPRINT_KEY)
    if not isinstance(history, list) or not history:
        return False
    return history[-1] == _fingerprint(reason)


def record_proactive_fingerprint(
    metadata: dict[str, object],
    reason: ProactiveReason,
    *,
    max_size: int,
) -> dict[str, object]:
    updated = dict(metadata)
    history = updated.get(_FINGERPRINT_KEY)
    history_list = list(history) if isinstance(history, list) else []
    history_list.append(_fingerprint(reason))
    cap = max(1, max_size)
    updated[_FINGERPRINT_KEY] = history_list[-cap:]
    return updated


def proactive_llm_allowed(
    budget: BudgetConfig,
    mood: MoodStateRecord,
    *,
    now: datetime | None = None,
) -> bool:
    if not budget.proactive_llm:
        return False
    aware = _aware_now(now)
    daily_max = max(0, budget.proactive_llm_daily_max)
    if daily_max <= 0:
        return True
    return _proactive_llm_count_today(mood.metadata, now=aware) < daily_max


def build_proactive_messages(store: MemoryStore, reason: ProactiveReason) -> list[ChatMessage]:
    persona = load_chinese_persona_prompt()
    relationship = store.get_relationship_state()
    mood = store.get_mood_state()

    blocks = [
        persona,
        _format_relationship_block(relationship),
        f"[Current mood]\nmood={mood.mood}, loneliness={mood.loneliness:.2f}",
        format_reason_block(reason),
        _PROACTIVE_OPENER_INSTRUCTION,
    ]
    impression = _format_impression_block(store)
    if impression:
        blocks.insert(2, impression)

    system_content = "\n\n".join(blocks)
    user_content = "[Initiate contact now based on the reason above.]"
    return [
        ChatMessage(role="system", content=system_content),
        ChatMessage(role="user", content=user_content),
    ]


def _sanitize_opener_line(raw: str) -> str:
    line = raw.strip().strip('"').strip("'").strip("「」")
    if not line:
        return ""
    first = line.splitlines()[0].strip()
    if len(first) > 120:
        first = first[:120].rstrip()
    return first


def _pick_proactive_provider(router: ProviderRouter, provider_name: str | None) -> str:
    if provider_name:
        return provider_name
    preferred = router.resolve_provider_name(None)
    if preferred == "mock":
        return "mock"
    try:
        status = router.get_provider(preferred).status()
        if status.configured and status.api_key_present and not status.placeholder:
            return preferred
    except ProviderError:
        pass
    return "mock"


def generate_proactive_opener(
    store: MemoryStore,
    reason: ProactiveReason,
    *,
    budget: BudgetConfig,
    router: ProviderRouter,
    provider_name: str | None = None,
) -> ChatCompletionResult | None:
    messages = build_proactive_messages(store, reason)
    request = ChatCompletionRequest(
        messages=messages,
        max_output_tokens=max(32, budget.proactive_max_output_tokens),
    )
    resolved_provider = _pick_proactive_provider(router, provider_name)
    result = router.complete(request, provider_name=resolved_provider)
    line = _sanitize_opener_line(result.content)
    if not line:
        return None
    return replace(result, content=line)


def resolve_proactive_opener(
    store: MemoryStore,
    decision: BehaviorDecision,
    *,
    budget: BudgetConfig,
    router: ProviderRouter,
    provider_name: str | None = None,
    now: datetime | None = None,
) -> BehaviorDecision:
    """Route-layer orchestration: try soul-authored opener, else keep canned fallback."""
    reason = decision.proactive_reason
    if decision.decision != "proactive" or reason is None:
        return decision

    fallback = (decision.local_response or "").strip() or fallback_line_for_reason(reason)
    mood = store.get_mood_state()
    aware = _aware_now(now)

    if not proactive_llm_allowed(budget, mood, now=now):
        return replace(decision, local_response=fallback, proactive_llm_used=False)

    try:
        target_model = router.get_provider(provider_name).status().model
    except ProviderError:
        target_model = "mock-boxi"

    gate = evaluate_llm_budget_gate(store, budget, target_model=target_model, now=aware)
    if not gate.allowed:
        return replace(decision, local_response=fallback, proactive_llm_used=False)

    try:
        completion = generate_proactive_opener(
            store,
            reason,
            budget=budget,
            router=router,
            provider_name=provider_name,
        )
    except Exception:
        return replace(decision, local_response=fallback, proactive_llm_used=False)

    if completion is None:
        return replace(decision, local_response=fallback, proactive_llm_used=False)

    updated_metadata = mark_proactive_llm_used(mood.metadata, now=aware)
    updated_metadata = record_proactive_fingerprint(
        updated_metadata,
        reason,
        max_size=budget.proactive_fingerprint_history_size,
    )
    if reason.kind == "share" and reason.memory_id is not None:
        updated_metadata = record_share_fingerprint(
            updated_metadata,
            reason.memory_id,
            max_size=budget.share_fingerprint_history_size,
        )
    store.update_mood_state(metadata=updated_metadata)
    return replace(
        decision,
        local_response=completion.content,
        proactive_llm_used=True,
        proactive_completion=completion,
    )
