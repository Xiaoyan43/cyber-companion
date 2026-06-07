from __future__ import annotations

import re

from backend.app.memory.retrieval import tokenize

REFUSE_PATTERNS = (
    re.compile(r"黑入|黑进|入侵|盗取|伪造|洗钱|诈骗", re.IGNORECASE),
    re.compile(r"\bhack\b|\bsteal\b|\bfraud\b", re.IGNORECASE),
)

LOW_VALUE_MESSAGES = {
    "ok",
    "okay",
    "k",
    "嗯",
    "哦",
    "好",
    "行",
    "?",
    "？",
    "hi",
    "hello",
    "在吗",
    "在不在",
}

OVERWHELMED_KEYWORDS = {"崩溃", "撑不住", "好难", "受不了", "exhausted", "overwhelmed", "burnout"}

JOB_KEYWORDS = {"job", "resume", "cv", "求职", "简历", "面试", "投递", "offer"}


def is_empty_input(text: str) -> bool:
    return not text.strip()


def is_low_value_input(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in LOW_VALUE_MESSAGES or len(normalized) <= 1


def matches_refuse_pattern(text: str) -> bool:
    return any(pattern.search(text) for pattern in REFUSE_PATTERNS)


def is_rambling(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) >= 320:
        return True

    sentence_count = len(re.findall(r"[。！？!?\.]", stripped))
    if sentence_count >= 5 and len(stripped) >= 180:
        return True

    # Long unpunctuated Chinese run-on text.
    return len(stripped) >= 180 and sentence_count <= 1


def mentions_job_topic(text: str) -> bool:
    tokens = tokenize(text)
    return bool(tokens.intersection(JOB_KEYWORDS))


def mentions_overwhelmed(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in OVERWHELMED_KEYWORDS)


def stale_days_from_iso(timestamp: str) -> int | None:
    from datetime import datetime, timezone

    try:
        updated = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None

    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)

    delta = datetime.now(timezone.utc) - updated
    return max(0, delta.days)
