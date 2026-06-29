"""Shared pure helpers for the MemoryStore mixins (no DB access)."""

from __future__ import annotations

from datetime import datetime, timezone

_LINK_SNIPPET_MAX_LEN = 80


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _normalize_aware_timestamp(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty ISO 8601 timestamp")

    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return parsed.astimezone(timezone.utc).isoformat()


def _clip_link_snippet(content: str, max_len: int = _LINK_SNIPPET_MAX_LEN) -> str:
    trimmed = content.strip()
    if len(trimmed) <= max_len:
        return trimmed
    return trimmed[: max_len - 1].rstrip() + "…"
