from __future__ import annotations

from dataclasses import dataclass
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
    "commitment_followup",
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


@dataclass(frozen=True)
class ProactiveReason:
    kind: ProactiveReasonKind
    avatar_state: str
    summary: str
    detail: str
    reminder_id: int | None = None
    memory_id: int | None = None
    longing_intensity: float = 0.0


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
    now: datetime | None = None,
) -> ProactiveReason:
    aware = _aware_now(now)

    due = _pick_due_reminder(store, now=aware)
    if due is not None:
        return due

    commitment = _pick_commitment_followup(store, now=aware)
    if commitment is not None:
        return commitment

    callback = _pick_memory_callback(store, now=aware)
    if callback is not None:
        return callback

    return ProactiveReason(
        kind="check_in",
        avatar_state="worried",
        summary="想念/check-in",
        detail=f"longing={longing_intensity:.2f}",
        longing_intensity=longing_intensity,
    )


def fallback_line_for_reason(reason: ProactiveReason) -> str:
    if reason.kind == "due_reminder":
        title = reason.summary.strip() or "那件事"
        return f"喂，{title}到期了。别装没看见。"
    if reason.kind == "commitment_followup":
        if "求职" in reason.summary or reason.memory_id is not None:
            return local_response_for_decision("proactive")
        return "你说过的那件事呢？别又拖没了。"
    if reason.kind == "memory_callback":
        return "突然想到你之前说的那档子事。还在吗？"
    return proactive_checkin_line()


def format_reason_block(reason: ProactiveReason) -> str:
    if reason.kind == "due_reminder":
        return (
            "[Proactive reason: due reminder]\n"
            f"title={reason.summary}\n"
            f"details={reason.detail}"
        )
    if reason.kind == "commitment_followup":
        return (
            "[Proactive reason: commitment / follow-up]\n"
            f"context={reason.detail}"
        )
    if reason.kind == "memory_callback":
        return (
            "[Proactive reason: memory callback]\n"
            f"memory={reason.detail}"
        )
    return (
        "[Proactive reason: check-in]\n"
        f"longing_intensity={reason.longing_intensity:.2f}\n"
        "Nothing specific — she misses the user."
    )
