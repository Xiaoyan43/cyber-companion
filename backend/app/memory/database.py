from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from backend.app.memory.schema import MEMORY_TYPES, SCHEMA_SQL, SCHEMA_VERSION


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_db_path(db_path: Path | None = None) -> Path:
    if db_path is not None:
        return db_path.expanduser().resolve()

    data_dir = os.getenv("CYBER_COMPANION_DATA_DIR", "./data")
    return (Path(data_dir).expanduser().resolve() / "cyber_companion.db")


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_database(db_path: Path | None = None) -> Path:
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with connect(path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.execute(
            """
            INSERT INTO schema_meta(key, value)
            VALUES ('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(SCHEMA_VERSION),),
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO mood_state (id)
            VALUES (1)
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO relationship_state (id)
            VALUES (1)
            """
        )
        _maybe_backfill_relationship_trust(connection)

    return path


def _maybe_backfill_relationship_trust(connection: sqlite3.Connection) -> None:
    existing = connection.execute(
        "SELECT 1 FROM schema_meta WHERE key = 'relationship_trust_backfilled'"
    ).fetchone()
    if existing is not None:
        return

    mood_row = connection.execute("SELECT trust FROM mood_state WHERE id = 1").fetchone()
    rel_row = connection.execute("SELECT trust FROM relationship_state WHERE id = 1").fetchone()
    if mood_row is not None and rel_row is not None:
        mood_trust = float(mood_row["trust"])
        rel_trust = float(rel_row["trust"])
        if abs(rel_trust - 0.5) < 1e-6 and abs(mood_trust - 0.5) > 1e-6:
            connection.execute(
                "UPDATE relationship_state SET trust = ? WHERE id = 1",
                (mood_trust,),
            )

    connection.execute(
        """
        INSERT INTO schema_meta(key, value)
        VALUES ('relationship_trust_backfilled', '1')
        ON CONFLICT(key) DO NOTHING
        """
    )


def dumps_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def loads_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


@dataclass(frozen=True)
class MessageRecord:
    id: int
    created_at: str
    role: str
    content: str
    source: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class MemoryRecord:
    id: int
    created_at: str
    updated_at: str
    type: str
    content: str
    tags: list[str]
    importance: float
    confidence: float
    expires_at: str | None
    source_message_id: int | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class MoodStateRecord:
    updated_at: str
    mood: str
    energy: float
    annoyance: float
    boredom: float
    worry: float
    trust: float
    loneliness: float
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RelationshipStateRecord:
    updated_at: str
    trust: float
    closeness: float
    familiarity: float
    tension: float
    last_meaningful_interaction_at: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ReminderRecord:
    id: int
    created_at: str
    due_at: str | None
    title: str
    details: str
    status: str
    source_message_id: int | None


@dataclass(frozen=True)
class ConversationSummaryRecord:
    id: int
    created_at: str
    range_start_message_id: int
    range_end_message_id: int
    summary: str
    keywords: list[str]


@dataclass(frozen=True)
class FileAccessLogRecord:
    id: int
    created_at: str
    operation: str
    requested_path: str
    resolved_path: str
    allowed: bool
    reason: str


def _row_to_message(row: sqlite3.Row) -> MessageRecord:
    return MessageRecord(
        id=row["id"],
        created_at=row["created_at"],
        role=row["role"],
        content=row["content"],
        source=row["source"],
        metadata=loads_json(row["metadata_json"], {}),
    )


def _row_to_memory(row: sqlite3.Row) -> MemoryRecord:
    return MemoryRecord(
        id=row["id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        type=row["type"],
        content=row["content"],
        tags=loads_json(row["tags_json"], []),
        importance=float(row["importance"]),
        confidence=float(row["confidence"]),
        expires_at=row["expires_at"],
        source_message_id=row["source_message_id"],
        metadata=loads_json(row["metadata_json"], {}),
    )


def _row_to_mood(row: sqlite3.Row) -> MoodStateRecord:
    return MoodStateRecord(
        updated_at=row["updated_at"],
        mood=row["mood"],
        energy=float(row["energy"]),
        annoyance=float(row["annoyance"]),
        boredom=float(row["boredom"]),
        worry=float(row["worry"]),
        trust=float(row["trust"]),
        loneliness=float(row["loneliness"]),
        metadata=loads_json(row["metadata_json"], {}),
    )


def _row_to_relationship(row: sqlite3.Row) -> RelationshipStateRecord:
    return RelationshipStateRecord(
        updated_at=row["updated_at"],
        trust=float(row["trust"]),
        closeness=float(row["closeness"]),
        familiarity=float(row["familiarity"]),
        tension=float(row["tension"]),
        last_meaningful_interaction_at=row["last_meaningful_interaction_at"],
        metadata=loads_json(row["metadata_json"], {}),
    )
