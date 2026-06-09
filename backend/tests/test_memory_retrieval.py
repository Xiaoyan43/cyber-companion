from pathlib import Path

import pytest

from backend.app.memory import retrieval
from backend.app.memory.context_builder import build_provider_context
from backend.app.memory.retrieval import is_expired, rank_memories, tokenize
from backend.app.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "retrieval.db")


def test_is_expired_respects_none_and_past_timestamp(store: MemoryStore) -> None:
    active = store.create_memory(type="project", content="still valid", expires_at=None)
    expired = store.create_memory(
        type="recent_event",
        content="old news",
        expires_at="2020-01-01T00:00:00+00:00",
    )

    now_iso = "2026-06-08T12:00:00+00:00"
    assert is_expired(active, now_iso) is False
    assert is_expired(expired, now_iso) is True


def test_context_builder_excludes_expired_memories(store: MemoryStore) -> None:
    store.create_memory(
        type="job_progress",
        content="Expired job note",
        importance=0.95,
        expires_at="2020-01-01T00:00:00+00:00",
    )
    active_memory = store.create_memory(
        type="job_progress",
        content="Active job note",
        importance=0.5,
        expires_at="2099-01-01T00:00:00+00:00",
    )

    built = build_provider_context(store, user_input="job progress update")

    assert active_memory.id in built.included_memory_ids
    assert "Active job note" in built.messages[0].content
    assert "Expired job note" not in built.messages[0].content


def test_chinese_query_tokenizes_and_boosts_job_progress(store: MemoryStore) -> None:
    query = "我今天投递了简历"
    tokens = tokenize(query)

    assert "投递" in tokens
    assert "简历" in tokens

    job = store.create_memory(type="job_progress", content="上周投递了字节简历")
    other = store.create_memory(type="project", content="周末做饭学新菜")

    ranked = rank_memories([other, job], query)

    assert ranked[0].id == job.id


def test_tokenize_falls_back_without_jieba(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retrieval, "_jieba_module", None)
    monkeypatch.setattr(retrieval, "_jieba_import_failed", False)

    def fail_jieba_import() -> None:
        retrieval._jieba_import_failed = True
        return None

    monkeypatch.setattr(retrieval, "_get_jieba", fail_jieba_import)

    tokens = tokenize("Acme platform migration")

    assert tokens == {"acme", "platform", "migration"}
