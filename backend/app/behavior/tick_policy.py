from __future__ import annotations

from datetime import datetime, timezone

from backend.app.memory.database import MoodStateRecord

_LOCAL_LINE_COOLDOWN_SECONDS = 180


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


def recently_spoke_locally(mood: MoodStateRecord, *, within_seconds: int = _LOCAL_LINE_COOLDOWN_SECONDS) -> bool:
    last_spoke = _parse_iso_timestamp(mood.metadata.get("last_local_line_at"))
    if last_spoke is None:
        return False

    elapsed = datetime.now(timezone.utc) - last_spoke.astimezone(timezone.utc)
    return elapsed.total_seconds() < within_seconds


def mark_local_line_spoken(metadata: dict[str, object]) -> dict[str, object]:
    updated = dict(metadata)
    updated["last_local_line_at"] = datetime.now(timezone.utc).isoformat()
    return updated
