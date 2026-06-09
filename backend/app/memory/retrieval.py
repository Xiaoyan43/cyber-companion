from __future__ import annotations

import re
from datetime import datetime, timezone

from backend.app.memory.database import MemoryRecord

TOKEN_PATTERN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
ASCII_WORD_PATTERN = re.compile(r"[a-z0-9_]+")
CJK_RUN_PATTERN = re.compile(r"[\u4e00-\u9fff]+")

CJK_STOPWORDS = {
    "我们",
    "你们",
    "这个",
    "那个",
    "什么",
    "怎么",
    "因为",
    "所以",
    "但是",
    "然后",
    "就是",
    "已经",
}

_jieba_module = None
_jieba_import_failed = False

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


def _get_jieba():
    global _jieba_module, _jieba_import_failed

    if _jieba_import_failed:
        return None
    if _jieba_module is not None:
        return _jieba_module

    try:
        import jieba

        _jieba_module = jieba
        return jieba
    except ImportError:
        _jieba_import_failed = True
        return None


def _tokenize_fallback(text: str) -> set[str]:
    tokens = {match.group(0).lower() for match in TOKEN_PATTERN.finditer(text.lower())}
    return {token for token in tokens if len(token) >= 2}


def tokenize(text: str) -> set[str]:
    jieba = _get_jieba()
    if jieba is None:
        return _tokenize_fallback(text)

    lowered = text.lower()
    tokens: set[str] = set()

    for match in ASCII_WORD_PATTERN.finditer(lowered):
        word = match.group(0)
        if len(word) >= 2:
            tokens.add(word)

    for match in CJK_RUN_PATTERN.finditer(text):
        for segment in jieba.lcut(match.group(0), cut_all=False):
            segment = segment.strip()
            if len(segment) < 2:
                continue
            if segment in CJK_STOPWORDS:
                continue
            tokens.add(segment.lower())

    return tokens


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
