from __future__ import annotations

import re
from datetime import datetime, timezone

from backend.app.memory.database import MemoryRecord

TOKEN_PATTERN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)

TYPE_KEYWORDS: dict[str, set[str]] = {
    "job_progress": {"job", "resume", "cv", "offer", "interview", "求职", "简历", "面试", "投递"},
    "project": {"project", "side", "build", "项目", "开发", "prototype"},
    "reminder": {"remind", "remember", "提醒", "记得", "别忘"},
    "stable_profile": {"who", "about", "profile", "背景", "介绍"},
    "behavior_preference": {"prefer", "style", "习惯", "偏好", "说话"},
    "relationship_state": {"trust", "关系", "信任"},
    "recent_event": {"today", "yesterday", "今天", "昨天", "刚刚"},
    "emotion_state": {"feel", "mood", "情绪", "心情", "焦虑"},
}


def _parse_iso_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_expired(memory: MemoryRecord, now_iso: str) -> bool:
    if memory.expires_at is None:
        return False

    expires_at = _parse_iso_timestamp(memory.expires_at)
    now = _parse_iso_timestamp(now_iso)
    if expires_at is None or now is None:
        return False

    return expires_at.astimezone(timezone.utc) <= now.astimezone(timezone.utc)


def tokenize(text: str) -> set[str]:
    tokens = {match.group(0).lower() for match in TOKEN_PATTERN.finditer(text.lower())}
    return {token for token in tokens if len(token) >= 2}


def boosted_memory_types(query: str) -> set[str]:
    query_tokens = tokenize(query)
    boosted: set[str] = set()

    for memory_type, keywords in TYPE_KEYWORDS.items():
        if query_tokens.intersection(keywords):
            boosted.add(memory_type)

    return boosted


def score_memory(memory: MemoryRecord, query: str) -> float:
    query_tokens = tokenize(query)
    content_lower = memory.content.lower()
    score = memory.importance * memory.confidence

    if memory.type in boosted_memory_types(query):
        score += 0.75

    if memory.type in {"stable_profile", "relationship_state"}:
        score += 0.2

    for tag in memory.tags:
        if tag.lower() in query_tokens:
            score += 0.35

    for token in query_tokens:
        if token in content_lower:
            score += 0.15

    return round(score, 4)


def rank_memories(memories: list[MemoryRecord], query: str) -> list[MemoryRecord]:
    return sorted(
        memories,
        key=lambda memory: (score_memory(memory, query), memory.importance, memory.updated_at),
        reverse=True,
    )
