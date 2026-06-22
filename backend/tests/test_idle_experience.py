from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.app.behavior.idle_experience import (
    idle_experience_allowed,
    mark_idle_experience_used,
    pick_material,
    record_material_fingerprint,
    resolve_idle_experience_write,
)
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.database import MoodStateRecord
from backend.app.memory.store import MemoryStore
from backend.app.providers.router import ProviderRouter


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "idle_experience.db")


def _mood(metadata: dict[str, object] | None = None) -> MoodStateRecord:
    return MoodStateRecord(
        updated_at="2026-06-22T00:00:00+00:00",
        mood="idle",
        energy=0.6,
        annoyance=0.0,
        boredom=0.1,
        worry=0.0,
        trust=0.5,
        loneliness=0.1,
        metadata=metadata or {},
    )


def _now() -> datetime:
    return datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc)


def test_idle_experience_disabled_blocks() -> None:
    budget = BudgetConfig(idle_experience_enabled=False)
    assert idle_experience_allowed(budget, _mood(), now=_now()) is False


def test_idle_experience_daily_cap_blocks() -> None:
    budget = BudgetConfig(idle_experience_enabled=True, idle_experience_daily_max=1)
    metadata = mark_idle_experience_used({}, now=_now())
    assert idle_experience_allowed(budget, _mood(metadata), now=_now()) is False


def test_idle_experience_min_gap_blocks() -> None:
    budget = BudgetConfig(idle_experience_enabled=True, idle_experience_min_gap_hours=6.0)
    metadata = mark_idle_experience_used({}, now=_now())
    soon = _now() + timedelta(hours=1)
    assert idle_experience_allowed(budget, _mood(metadata), now=soon) is False


def test_idle_experience_allowed_after_gap() -> None:
    budget = BudgetConfig(idle_experience_enabled=True, idle_experience_min_gap_hours=6.0)
    metadata = mark_idle_experience_used({}, now=_now())
    later = _now() + timedelta(hours=7)
    assert idle_experience_allowed(budget, _mood(metadata), now=later) is True


def test_pick_material_avoids_recent_fingerprint() -> None:
    pool = [{"id": "a"}, {"id": "b"}]
    metadata = record_material_fingerprint({}, "a", max_size=4)
    chosen = pick_material(pool, metadata)
    assert chosen is not None
    assert chosen["id"] == "b"


def test_pick_material_falls_back_when_all_recent() -> None:
    pool = [{"id": "a"}]
    metadata = record_material_fingerprint({}, "a", max_size=4)
    chosen = pick_material(pool, metadata)
    assert chosen is not None
    assert chosen["id"] == "a"


def test_pick_material_empty_pool_returns_none() -> None:
    assert pick_material([], {}) is None


def test_resolve_idle_experience_write_creates_memory(
    store: MemoryStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pool_path = tmp_path / "idle_material_pool.json"
    pool_path.write_text(
        '{"items": [{"id": "movie-x", "kind": "movie", "title": "X", "summary": "A safe test summary."}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "backend.app.behavior.idle_experience._config_dir", lambda: tmp_path
    )
    budget = BudgetConfig(idle_experience_enabled=True, idle_experience_daily_max=4)
    router = ProviderRouter.from_config()

    memory = resolve_idle_experience_write(store, budget=budget, router=router, now=_now())

    assert memory is not None
    assert memory.type == "idle_experience"
    assert memory.content
    mood = store.get_mood_state()
    assert mood.metadata.get("idle_experience_daily_count") == 1
    assert mood.metadata.get("idle_experience_recent_material_ids") == ["movie-x"]


def test_resolve_idle_experience_write_respects_gate(
    store: MemoryStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pool_path = tmp_path / "idle_material_pool.json"
    pool_path.write_text(
        '{"items": [{"id": "movie-x", "kind": "movie", "title": "X", "summary": "A safe test summary."}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "backend.app.behavior.idle_experience._config_dir", lambda: tmp_path
    )
    budget = BudgetConfig(idle_experience_enabled=False)
    router = ProviderRouter.from_config()

    memory = resolve_idle_experience_write(store, budget=budget, router=router, now=_now())

    assert memory is None


def test_resolve_idle_experience_write_empty_pool_returns_none(
    store: MemoryStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "backend.app.behavior.idle_experience._config_dir", lambda: tmp_path
    )
    budget = BudgetConfig(idle_experience_enabled=True)
    router = ProviderRouter.from_config()

    memory = resolve_idle_experience_write(store, budget=budget, router=router, now=_now())

    assert memory is None
