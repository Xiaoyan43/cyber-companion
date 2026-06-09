from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.behavior.rules import is_low_value_input
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.database import MemoryRecord
from backend.app.memory.retrieval import tokenize
from backend.app.memory.schema import MEMORY_TYPES
from backend.app.memory.store import MemoryStore

# Writes below this confidence are dropped. Explicit user cues (remember, name,
# imperative preference) sit at >= 0.75; inferred project cues stay at 0.55 so
# they do not auto-persist without stronger signals.
_MIN_WRITE_CONFIDENCE = 0.6
_MAX_SIGNAL_MEMORIES_PER_TURN = 5

_REMEMBER_PATTERN = re.compile(
    r"(?:记住|记得|别忘了|提醒[我这]?|remind me(?: to)?|remember (?:that|to))\s*(.+)",
    re.IGNORECASE,
)
_PROFILE_PATTERN = re.compile(
    r"(?:我叫|我的名字是|my name is|i'm called)\s*([^，。！？!?\n]{2,60})",
    re.IGNORECASE,
)
_PROJECT_PATTERN = re.compile(
    r"(?:我在做|正在做|side project|working on|building)\s*([^，。！？!?\n]{3,80})",
    re.IGNORECASE,
)
_PREFERENCE_PATTERN = re.compile(
    r"(?:"
    r"^(?:请|希望你?|别(?:再)?)"
    r"|(?:^|[。！？!?\s])i prefer(?: to)?"
    r")\s*([^，。！？!?\n]{3,80})",
    re.IGNORECASE | re.MULTILINE,
)
_JOB_TOPIC_PATTERN = re.compile(
    r"(?:求职|简历|面试|投递|offer|resume|\bjob\b)",
    re.IGNORECASE,
)
_JOB_ACTION_PATTERN = re.compile(
    r"(?:投递|面试|改简历|sent|applied|interview|offer|follow[- ]?up)",
    re.IGNORECASE,
)
_JOB_ACTION_TOPIC_PATTERN = re.compile(
    r"(?:投递|sent|applied)(?:了)?(?:\d+份)?\s*([^，。！？!?\n]{2,40})",
    re.IGNORECASE,
)
_JOB_INTERVIEW_TOPIC_PATTERN = re.compile(
    r"(?:(?:约了|安排|scheduled)?\s*)?"
    r"((?:周[一二三四五六日天]|明天|后天|下周|today|tomorrow)[^，。！？!?\n]{0,12})?"
    r"\s*面试",
    re.IGNORECASE,
)
_JOB_REVISE_TOPIC_PATTERN = re.compile(
    r"改\s*([^，。！？!?\n]{2,30}简历)",
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


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _as_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _validate_signal_memory(raw: object) -> MemoryWriteCandidate | None:
    if not isinstance(raw, dict):
        return None
    mem_type = raw.get("type")
    if mem_type not in MEMORY_TYPES:
        return None
    content = _clip_content(str(raw.get("content", "")))
    if len(content) < 4:
        return None
    importance = _clamp01(_as_float(raw.get("importance"), 0.5))
    confidence = _clamp01(_as_float(raw.get("confidence"), 0.5))
    tags_raw = raw.get("tags", [])
    tags: tuple[str, ...] = ()
    if isinstance(tags_raw, list):
        tags = tuple(str(tag) for tag in tags_raw if isinstance(tag, str))[:6]
    return MemoryWriteCandidate(
        type=str(mem_type),
        content=content,
        importance=importance,
        confidence=confidence,
        tags=tags,
    )


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


def _normalize_job_action(action: str) -> str:
    lowered = action.lower()
    mapping = {
        "sent": "sent",
        "applied": "applied",
        "interview": "interview",
        "offer": "offer",
        "follow-up": "follow-up",
        "follow up": "follow-up",
        "改简历": "改简历",
        "投递": "投递",
        "面试": "面试",
    }
    return mapping.get(lowered, action)


def _build_job_progress_fact(text: str) -> str | None:
    action_match = _JOB_ACTION_PATTERN.search(text)
    if action_match is None:
        return None

    action = _normalize_job_action(action_match.group(0))
    action_lower = action.lower()

    if action in {"投递", "sent", "applied"}:
        topic_match = _JOB_ACTION_TOPIC_PATTERN.search(text)
        if topic_match:
            topic = _clip_content(topic_match.group(1).strip(), limit=40)
            if topic:
                return f"{action}: {topic}"

    if action in {"面试", "interview"}:
        topic_match = _JOB_INTERVIEW_TOPIC_PATTERN.search(text)
        if topic_match:
            when = (topic_match.group(1) or "").strip()
            topic = _clip_content(when or "scheduled", limit=40)
            return f"{action}: {topic}"

    if action == "改简历":
        topic_match = _JOB_REVISE_TOPIC_PATTERN.search(text)
        if topic_match:
            topic = _clip_content(topic_match.group(1).strip(), limit=40)
            return f"{action}: {topic}"

    topic_match = _JOB_TOPIC_PATTERN.search(text)
    if topic_match:
        return f"{action}: {topic_match.group(0)}"

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
                    confidence=0.55,
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

    if not has_explicit_remember:
        job_fact = _build_job_progress_fact(stripped)
        if job_fact and _JOB_TOPIC_PATTERN.search(stripped):
            candidates.append(
                MemoryWriteCandidate(
                    type="job_progress",
                    content=job_fact,
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
    writer: str = "rule_based",
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
            metadata={"writer": writer},
        )

    return store.update_memory(
        existing.id,
        content=candidate.content,
        tags=list(candidate.tags),
        importance=max(existing.importance, candidate.importance),
        confidence=max(existing.confidence, candidate.confidence),
        metadata={**existing.metadata, "writer": writer, "updated_from_turn": True},
    )


def write_memories_from_signals(
    store: MemoryStore,
    signal_memories: list,
    *,
    source_message_id: int | None,
    budget: BudgetConfig | None = None,
) -> list[MemoryRecord]:
    config = budget or BudgetConfig()
    if not config.auto_memory_write:
        return []

    written: list[MemoryRecord] = []
    for raw in signal_memories[:_MAX_SIGNAL_MEMORIES_PER_TURN]:
        candidate = _validate_signal_memory(raw)
        if candidate is None or candidate.confidence < _MIN_WRITE_CONFIDENCE:
            continue
        written.append(
            _persist_candidate(
                store,
                candidate,
                source_message_id=source_message_id,
                writer="llm",
            )
        )
    return written


def record_turn_memories(
    store: MemoryStore,
    *,
    user_input: str,
    signals: dict | None,
    source_message_id: int | None,
    budget: BudgetConfig | None = None,
) -> list[MemoryRecord]:
    config = budget or BudgetConfig()
    if not config.auto_memory_write:
        return []
    if config.llm_memory_extraction and isinstance(signals, dict):
        sig_mem = signals.get("memory")
        if isinstance(sig_mem, list) and sig_mem:
            written = write_memories_from_signals(
                store,
                sig_mem,
                source_message_id=source_message_id,
                budget=config,
            )
            if written:
                return written
            # Every LLM memory item was rejected (type not whitelisted, content
            # too short, or confidence below threshold). Fall through to the regex
            # M2 path so the turn does not silently lose its memory write.
    return maybe_write_memories_from_turn(
        store,
        user_input=user_input,
        source_message_id=source_message_id,
        budget=config,
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
