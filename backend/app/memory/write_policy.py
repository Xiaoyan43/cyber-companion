from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.behavior.rules import is_low_value_input
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.database import MemoryRecord
from backend.app.memory.retrieval import tokenize
from backend.app.memory.store import MemoryStore

_MIN_WRITE_CONFIDENCE = 0.6

_REMEMBER_PATTERN = re.compile(
    r"(?:记住|记得|别忘了|提醒[我这]?|remind me(?: to)?|remember (?:that|to))\s*(.+)",
    re.IGNORECASE,
)
_PROFILE_PATTERN = re.compile(
    r"(?:我(?:叫|是)|i am|my name is)\s*([^，。！？!?\n]{2,60})",
    re.IGNORECASE,
)
_PROJECT_PATTERN = re.compile(
    r"(?:我在做|正在做|side project|working on|building)\s*([^，。！？!?\n]{3,80})",
    re.IGNORECASE,
)
_PREFERENCE_PATTERN = re.compile(
    r"(?:说话[别]?[太]?|回复[别]?[太]?|prefer|别对我)\s*([^，。！？!?\n]{3,80})",
    re.IGNORECASE,
)
_JOB_TOPIC_PATTERN = re.compile(
    r"(?:求职|简历|面试|投递|offer|resume|\bjob\b)",
    re.IGNORECASE,
)
_JOB_ACTION_PATTERN = re.compile(
    r"(?:投递|面试|改简历|sent|applied|interview|offer|follow[- ]?up)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MemoryWriteCandidate:
    type: str
    content: str
    importance: float
    confidence: float
    tags: tuple[str, ...] = ()


def _clip_content(text: str, *, limit: int = 200) -> str:
    clipped = text.strip().replace("\n", " ")
    if len(clipped) <= limit:
        return clipped
    return clipped[: limit - 3] + "..."


def _is_similar_content(left: str, right: str) -> bool:
    left_norm = left.strip().lower()
    right_norm = right.strip().lower()
    if not left_norm or not right_norm:
        return False

    shorter, longer = (
        (left_norm, right_norm)
        if len(left_norm) <= len(right_norm)
        else (right_norm, left_norm)
    )
    if shorter in longer:
        return True

    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return False

    overlap = left_tokens & right_tokens
    smaller = min(len(left_tokens), len(right_tokens))
    return len(overlap) >= max(2, (smaller * 2 + 2) // 3)


def _find_similar_memory(store: MemoryStore, memory_type: str, content: str):
    for memory in store.list_memories(type=memory_type, limit=50):
        if _is_similar_content(memory.content, content):
            return memory
    return None


def extract_memory_candidates(user_input: str) -> list[MemoryWriteCandidate]:
    stripped = user_input.strip()
    if not stripped or is_low_value_input(stripped):
        return []

    candidates: list[MemoryWriteCandidate] = []

    remember_match = _REMEMBER_PATTERN.search(stripped)
    has_explicit_remember = False
    if remember_match:
        detail = _clip_content(remember_match.group(1))
        if len(detail) >= 4:
            has_explicit_remember = True
            candidates.append(
                MemoryWriteCandidate(
                    type="reminder",
                    content=detail,
                    importance=0.75,
                    confidence=0.85,
                    tags=("user-confirmed",),
                )
            )

    profile_match = _PROFILE_PATTERN.search(stripped)
    if profile_match:
        detail = _clip_content(profile_match.group(1))
        if len(detail) >= 2:
            candidates.append(
                MemoryWriteCandidate(
                    type="stable_profile",
                    content=f"User profile: {detail}",
                    importance=0.8,
                    confidence=0.8,
                    tags=("profile",),
                )
            )

    project_match = _PROJECT_PATTERN.search(stripped)
    if project_match:
        detail = _clip_content(project_match.group(1))
        if len(detail) >= 3:
            candidates.append(
                MemoryWriteCandidate(
                    type="project",
                    content=f"Project: {detail}",
                    importance=0.7,
                    confidence=0.7,
                    tags=("project",),
                )
            )

    preference_match = _PREFERENCE_PATTERN.search(stripped)
    if preference_match:
        detail = _clip_content(preference_match.group(1))
        if len(detail) >= 3:
            candidates.append(
                MemoryWriteCandidate(
                    type="behavior_preference",
                    content=f"Preference: {detail}",
                    importance=0.65,
                    confidence=0.75,
                    tags=("preference",),
                )
            )

    if (
        not has_explicit_remember
        and _JOB_TOPIC_PATTERN.search(stripped)
        and _JOB_ACTION_PATTERN.search(stripped)
    ):
        candidates.append(
            MemoryWriteCandidate(
                type="job_progress",
                content=_clip_content(stripped),
                importance=0.7,
                confidence=0.65,
                tags=("job-search",),
            )
        )

    return [
        candidate
        for candidate in candidates
        if candidate.confidence >= _MIN_WRITE_CONFIDENCE
    ]


def _persist_candidate(
    store: MemoryStore,
    candidate: MemoryWriteCandidate,
    *,
    source_message_id: int | None,
) -> MemoryRecord:
    existing = _find_similar_memory(store, candidate.type, candidate.content)
    if existing is None:
        return store.create_memory(
            type=candidate.type,
            content=candidate.content,
            tags=list(candidate.tags),
            importance=candidate.importance,
            confidence=candidate.confidence,
            source_message_id=source_message_id,
            metadata={"writer": "rule_based"},
        )

    return store.update_memory(
        existing.id,
        content=candidate.content,
        tags=list(candidate.tags),
        importance=max(existing.importance, candidate.importance),
        confidence=max(existing.confidence, candidate.confidence),
        metadata={**existing.metadata, "writer": "rule_based", "updated_from_turn": True},
    )


def maybe_write_memories_from_turn(
    store: MemoryStore,
    *,
    user_input: str,
    source_message_id: int | None,
    budget: BudgetConfig | None = None,
) -> list[MemoryRecord]:
    config = budget or BudgetConfig()
    if not config.auto_memory_write:
        return []

    written: list[MemoryRecord] = []
    for candidate in extract_memory_candidates(user_input):
        written.append(
            _persist_candidate(
                store,
                candidate,
                source_message_id=source_message_id,
            )
        )
    return written
