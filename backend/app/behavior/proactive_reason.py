from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Literal

from backend.app.behavior.local_responses import local_response_for_decision
from backend.app.behavior.longing import proactive_checkin_line
from backend.app.behavior.mood import find_stale_job_memory
from backend.app.behavior.tick_policy import _parse_iso_timestamp
from backend.app.memory.database import MemoryRecord, ReminderRecord
from backend.app.memory.retrieval import is_expired

if TYPE_CHECKING:
    from backend.app.memory.store import MemoryStore

ProactiveReasonKind = Literal[
    "due_reminder",
    "open_loop",
    "commitment_followup",
    "share",
    "memory_callback",
    "check_in",
]

_COMMITMENT_MEMORY_TYPES = ("job_progress", "recent_event", "project", "reminder")
_CALLBACK_MEMORY_TYPES = (
    "stable_profile",
    "recent_event",
    "project",
    "job_progress",
    "reminder",
)
_RECENT_DAYS = 14
_CALLBACK_IMPORTANCE_MIN = 0.65
_COMMITMENT_IMPORTANCE_MIN = 0.4

_SHARE_MEMORY_TYPE = "idle_experience"
_SHARE_FINGERPRINT_KEY = "share_recent_memory_ids"


def is_share_repeated(metadata: dict[str, object], memory_id: int) -> bool:
    """True if this idle_experience memory was used as a share opener recently."""
    history = metadata.get(_SHARE_FINGERPRINT_KEY)
    if not isinstance(history, list):
        return False
    return memory_id in history


def record_share_fingerprint(
    metadata: dict[str, object],
    memory_id: int,
    *,
    max_size: int,
) -> dict[str, object]:
    updated = dict(metadata)
    history = updated.get(_SHARE_FINGERPRINT_KEY)
    history_list = list(history) if isinstance(history, list) else []
    history_list.append(memory_id)
    cap = max(1, max_size)
    updated[_SHARE_FINGERPRINT_KEY] = history_list[-cap:]
    return updated


LongingTier = Literal["bored", "longing", "sulk"]

_TIER_VOICE_BLOCKS: dict[LongingTier, str] = {
    "bored": (
        "[Longing tier: bored]\nMild boredom — casual, low-stakes tone. Not urgent, not needy."
    ),
    "longing": (
        "[Longing tier: longing]\nShe's been missing the user — warmer, a little wistful, "
        "but still light. Not desperate, not accusatory."
    ),
    "sulk": (
        "[Longing tier: sulk]\nShe's sulking — sharp, a bit prickly, classic 傲娇 (won't admit "
        "she waited, but obviously did). The line should land on relief that the user is "
        "finally here — NOT coldness, NOT indifference, NOT withdrawal. Sulking is still "
        "wanting them close."
    ),
}


@dataclass(frozen=True)
class ProactiveReason:
    kind: ProactiveReasonKind
    avatar_state: str
    summary: str
    detail: str
    reminder_id: int | None = None
    memory_id: int | None = None
    open_loop_id: int | None = None
    longing_intensity: float = 0.0
    longing_tier: LongingTier = "bored"


def _aware_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _memory_is_recent(memory: MemoryRecord, *, now: datetime, max_days: int) -> bool:
    parsed = _parse_iso_timestamp(memory.updated_at)
    if parsed is None:
        return False
    age = now - parsed.astimezone(timezone.utc)
    return age <= timedelta(days=max_days)


def _pick_due_reminder(store: MemoryStore, *, now: datetime) -> ProactiveReason | None:
    due = store.find_due_reminder(now=now)
    if due is None:
        return None
    detail = due.details.strip() or due.title
    return ProactiveReason(
        kind="due_reminder",
        avatar_state="worried",
        summary=due.title,
        detail=detail,
        reminder_id=due.id,
    )


def _pick_open_loop(store: MemoryStore, *, now: datetime) -> ProactiveReason | None:
    """Surface a due/overdue open loop (agenda, Phase 3B) as a proactive reason.

    Only loops whose ``due_at`` has passed are eligible — open-but-not-yet-due
    loops do not trigger proactive contact (that's deferred to the Phase 6
    motivation rework). ``list_open_loops`` already orders earliest-due first.
    """
    now_iso = now.astimezone(timezone.utc).isoformat()
    due = store.list_open_loops(status="open", due_before=now_iso, limit=1)
    if not due:
        return None
    loop = due[0]
    detail = loop.summary.strip() or loop.title
    return ProactiveReason(
        kind="open_loop",
        avatar_state="worried",
        summary=loop.title,
        detail=detail,
        open_loop_id=loop.id,
    )


def _pick_commitment_followup(store: MemoryStore, *, now: datetime) -> ProactiveReason | None:
    now_iso = now.astimezone(timezone.utc).isoformat()
    stale_job = find_stale_job_memory(store.list_memories(limit=100))
    if stale_job is not None and not is_expired(stale_job, now_iso):
        return ProactiveReason(
            kind="commitment_followup",
            avatar_state="worried",
            summary="求职/待办跟进",
            detail=stale_job.content,
            memory_id=stale_job.id,
        )

    candidates = [
        memory
        for memory in store.list_memories(limit=100)
        if memory.type in _COMMITMENT_MEMORY_TYPES
        and not is_expired(memory, now_iso)
        and memory.importance >= _COMMITMENT_IMPORTANCE_MIN
        and _memory_is_recent(memory, now=now, max_days=_RECENT_DAYS)
    ]
    if not candidates:
        return None

    chosen = max(candidates, key=lambda item: (item.importance, item.updated_at))
    return ProactiveReason(
        kind="commitment_followup",
        avatar_state="annoyed",
        summary="近期承诺/待办",
        detail=chosen.content,
        memory_id=chosen.id,
    )


def _pick_share(store: MemoryStore, *, now: datetime) -> ProactiveReason | None:
    metadata = store.get_mood_state().metadata
    candidates = [
        memory
        for memory in store.list_memories(type=_SHARE_MEMORY_TYPE, limit=50)
        if not is_share_repeated(metadata, memory.id)
    ]
    if not candidates:
        return None

    chosen = candidates[0]  # already ordered newest-first by list_memories
    return ProactiveReason(
        kind="share",
        avatar_state="happy",
        summary="想分享的小事",
        detail=chosen.content,
        memory_id=chosen.id,
    )


def _pick_memory_callback(store: MemoryStore, *, now: datetime) -> ProactiveReason | None:
    now_iso = now.astimezone(timezone.utc).isoformat()
    candidates = [
        memory
        for memory in store.list_memories(limit=100)
        if memory.type in _CALLBACK_MEMORY_TYPES
        and not is_expired(memory, now_iso)
        and memory.importance >= _CALLBACK_IMPORTANCE_MIN
        and _memory_is_recent(memory, now=now, max_days=30)
    ]
    if not candidates:
        return None

    chosen = max(candidates, key=lambda item: (item.importance, item.updated_at))
    return ProactiveReason(
        kind="memory_callback",
        avatar_state="idle",
        summary="记忆回响",
        detail=chosen.content,
        memory_id=chosen.id,
    )


def pick_proactive_reason(
    store: MemoryStore,
    *,
    longing_intensity: float = 0.0,
    longing_tier: LongingTier = "bored",
    now: datetime | None = None,
) -> ProactiveReason:
    aware = _aware_now(now)

    due = _pick_due_reminder(store, now=aware)
    if due is not None:
        return replace(due, longing_tier=longing_tier)

    open_loop = _pick_open_loop(store, now=aware)
    if open_loop is not None:
        return replace(open_loop, longing_tier=longing_tier)

    commitment = _pick_commitment_followup(store, now=aware)
    if commitment is not None:
        return replace(commitment, longing_tier=longing_tier)

    share = _pick_share(store, now=aware)
    if share is not None:
        return replace(share, longing_tier=longing_tier)

    callback = _pick_memory_callback(store, now=aware)
    if callback is not None:
        return replace(callback, longing_tier=longing_tier)

    return ProactiveReason(
        kind="check_in",
        avatar_state="worried",
        summary="想念/check-in",
        detail=f"longing={longing_intensity:.2f}",
        longing_intensity=longing_intensity,
        longing_tier=longing_tier,
    )


def fallback_line_for_reason(reason: ProactiveReason) -> str:
    if reason.kind == "due_reminder":
        title = reason.summary.strip() or "那件事"
        return f"喂，{title}到期了。别装没看见。"
    if reason.kind == "open_loop":
        title = reason.summary.strip() or "那件事"
        return f"那个「{title}」该收尾了吧？别一直挂着。"
    if reason.kind == "commitment_followup":
        if "求职" in reason.summary or reason.memory_id is not None:
            return local_response_for_decision("proactive")
        return "你说过的那件事呢？别又拖没了。"
    if reason.kind == "memory_callback":
        return "突然想到你之前说的那档子事。还在吗？"
    if reason.kind == "share":
        return "刚刚自己瞎想了点事，想跟你说说。"
    return proactive_checkin_line()


def format_reason_block(reason: ProactiveReason) -> str:
    tier_block = _TIER_VOICE_BLOCKS[reason.longing_tier]
    if reason.kind == "due_reminder":
        block = (
            "[Proactive reason: due reminder]\n"
            f"title={reason.summary}\n"
            f"details={reason.detail}"
        )
    elif reason.kind == "open_loop":
        block = (
            "[Proactive reason: open loop — an unfinished thread that's now due]\n"
            f"title={reason.summary}\n"
            f"context={reason.detail}"
        )
    elif reason.kind == "commitment_followup":
        block = (
            "[Proactive reason: commitment / follow-up]\n"
            f"context={reason.detail}"
        )
    elif reason.kind == "share":
        block = (
            "[Proactive reason: share — something she noticed on her own]\n"
            f"her_experience={reason.detail}\n"
            "This is HER own idle moment, not a fact about the user. Bring it up like "
            "she genuinely wants to tell the user about it — not a report, not asking "
            "for permission."
        )
    elif reason.kind == "memory_callback":
        block = (
            "[Proactive reason: memory callback]\n"
            f"memory={reason.detail}"
        )
    else:
        block = (
            "[Proactive reason: check-in]\n"
            f"longing_intensity={reason.longing_intensity:.2f}\n"
            "Nothing specific — she misses the user."
        )
    return f"{block}\n\n{tier_block}"
