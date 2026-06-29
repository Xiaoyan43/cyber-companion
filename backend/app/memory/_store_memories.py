"""Memories CRUD + memory-link methods for MemoryStore."""

from __future__ import annotations

from typing import Any

from backend.app.memory._store_helpers import _clip_link_snippet
from backend.app.memory.database import (
    MemoryLinkRecord,
    MemoryRecord,
    _row_to_memory,
    connect,
    dumps_json,
    utc_now_iso,
)
from backend.app.memory.schema import MEMORY_TYPES


class MemoriesMixin:
    def create_memory(
        self,
        *,
        type: str,
        content: str,
        tags: list[str] | None = None,
        importance: float = 0.5,
        confidence: float = 0.5,
        expires_at: str | None = None,
        source_message_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        if type not in MEMORY_TYPES:
            raise ValueError(f"Unsupported memory type: {type}")

        with connect(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO memories (
                  type, content, tags_json, importance, confidence,
                  expires_at, source_message_id, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    type,
                    content,
                    dumps_json(tags or []),
                    importance,
                    confidence,
                    expires_at,
                    source_message_id,
                    dumps_json(metadata or {}),
                ),
            )
            memory_id = int(cursor.lastrowid)
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        assert row is not None
        return _row_to_memory(row)

    def get_memory(self, memory_id: int) -> MemoryRecord | None:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return _row_to_memory(row) if row else None

    def list_memories(
        self,
        *,
        type: str | None = None,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        query = "SELECT * FROM memories"
        params: list[Any] = []

        if type is not None:
            if type not in MEMORY_TYPES:
                raise ValueError(f"Unsupported memory type: {type}")
            query += " WHERE type = ?"
            params.append(type)

        query += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)

        with connect(self.db_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_memory(row) for row in rows]

    def update_memory(
        self,
        memory_id: int,
        *,
        content: str | None = None,
        tags: list[str] | None = None,
        importance: float | None = None,
        confidence: float | None = None,
        expires_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord | None:
        existing = self.get_memory(memory_id)
        if existing is None:
            return None

        updated = MemoryRecord(
            id=existing.id,
            created_at=existing.created_at,
            updated_at=utc_now_iso(),
            type=existing.type,
            content=content if content is not None else existing.content,
            tags=tags if tags is not None else existing.tags,
            importance=importance if importance is not None else existing.importance,
            confidence=confidence if confidence is not None else existing.confidence,
            expires_at=expires_at if expires_at is not None else existing.expires_at,
            source_message_id=existing.source_message_id,
            metadata=metadata if metadata is not None else existing.metadata,
        )

        with connect(self.db_path) as connection:
            connection.execute(
                """
                UPDATE memories
                SET updated_at = ?, content = ?, tags_json = ?, importance = ?,
                    confidence = ?, expires_at = ?, metadata_json = ?
                WHERE id = ?
                """,
                (
                    updated.updated_at,
                    updated.content,
                    dumps_json(updated.tags),
                    updated.importance,
                    updated.confidence,
                    updated.expires_at,
                    dumps_json(updated.metadata),
                    memory_id,
                ),
            )
        return updated

    def delete_memory(self, memory_id: int) -> bool:
        with connect(self.db_path) as connection:
            cursor = connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        return cursor.rowcount > 0

    def add_memory_link(
        self,
        memory_id: int,
        related_memory_id: int,
        relation: str = "related",
    ) -> None:
        # Store both directions so a single-direction lookup suffices at read time.
        # INSERT OR IGNORE keeps it idempotent via the UNIQUE(memory_id,
        # related_memory_id) constraint. No self-links.
        if memory_id == related_memory_id:
            return
        with connect(self.db_path) as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO memory_links (memory_id, related_memory_id, relation)
                VALUES (?, ?, ?)
                """,
                (
                    (memory_id, related_memory_id, relation),
                    (related_memory_id, memory_id, relation),
                ),
            )

    def get_linked_memory_ids(self, memory_id: int) -> list[int]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT related_memory_id FROM memory_links WHERE memory_id = ? ORDER BY id",
                (memory_id,),
            ).fetchall()
        return [int(row["related_memory_id"]) for row in rows]

    def count_memory_links(self) -> int:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT COUNT(*) AS n FROM memory_links").fetchone()
        return int(row["n"]) if row else 0

    def list_memory_links(self, limit: int = 100) -> list[MemoryLinkRecord]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    ml.id,
                    ml.memory_id,
                    ml.related_memory_id,
                    ml.relation,
                    ml.created_at,
                    a.type AS memory_type,
                    a.content AS memory_content,
                    b.type AS related_type,
                    b.content AS related_content
                FROM memory_links ml
                JOIN memories a ON a.id = ml.memory_id
                JOIN memories b ON b.id = ml.related_memory_id
                WHERE ml.memory_id < ml.related_memory_id
                ORDER BY ml.id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            MemoryLinkRecord(
                id=int(row["id"]),
                memory_id=int(row["memory_id"]),
                related_memory_id=int(row["related_memory_id"]),
                relation=str(row["relation"]),
                created_at=str(row["created_at"]),
                memory_type=str(row["memory_type"]),
                memory_content=_clip_link_snippet(str(row["memory_content"])),
                related_type=str(row["related_type"]),
                related_content=_clip_link_snippet(str(row["related_content"])),
            )
            for row in rows
        ]
