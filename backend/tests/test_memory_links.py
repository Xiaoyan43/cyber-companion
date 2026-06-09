from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.memory.budget import BudgetConfig
from backend.app.memory.context_builder import build_provider_context
from backend.app.memory.database import utc_now_iso
from backend.app.memory.store import MemoryStore, reset_memory_store
from backend.app.providers.router import reset_provider_router
from backend.app.reflection import jobs as reflection_jobs


@pytest.fixture(autouse=True)
def reset_singletons() -> None:
    reset_provider_router()
    reset_memory_store()
    yield
    reset_provider_router()
    reset_memory_store()


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "memory-links.db")


# --- Task 2: store methods -------------------------------------------------


def test_add_memory_link_bidirectional_and_idempotent(store: MemoryStore) -> None:
    a = store.create_memory(type="project", content="Acme platform migration")
    b = store.create_memory(type="job_progress", content="Acme platform interview")

    store.add_memory_link(a.id, b.id)

    assert store.get_linked_memory_ids(a.id) == [b.id]
    assert store.get_linked_memory_ids(b.id) == [a.id]
    assert store.count_memory_links() == 2

    # Idempotent: re-adding does not duplicate either direction.
    store.add_memory_link(a.id, b.id)
    store.add_memory_link(b.id, a.id)
    assert store.count_memory_links() == 2


def test_add_memory_link_rejects_self_link(store: MemoryStore) -> None:
    a = store.create_memory(type="project", content="Acme platform migration")

    store.add_memory_link(a.id, a.id)

    assert store.count_memory_links() == 0
    assert store.get_linked_memory_ids(a.id) == []


def test_memory_link_cascades_on_delete(store: MemoryStore) -> None:
    a = store.create_memory(type="project", content="Acme platform migration")
    b = store.create_memory(type="job_progress", content="Acme platform interview")
    store.add_memory_link(a.id, b.id)

    assert store.delete_memory(b.id) is True

    assert store.count_memory_links() == 0
    assert store.get_linked_memory_ids(a.id) == []


# --- Task 3: deterministic linker -----------------------------------------


def test_linker_links_cross_type_strong_overlap(store: MemoryStore) -> None:
    proj = store.create_memory(type="project", content="Acme platform migration")
    job = store.create_memory(type="job_progress", content="Interview at Acme platform team")

    reflection_jobs.link_related_memories(store, BudgetConfig())

    assert store.get_linked_memory_ids(proj.id) == [job.id]
    assert store.get_linked_memory_ids(job.id) == [proj.id]


def test_linker_skips_same_type_pairs(store: MemoryStore) -> None:
    one = store.create_memory(type="project", content="Acme platform migration")
    two = store.create_memory(type="project", content="Acme platform rollout")

    reflection_jobs.link_related_memories(store, BudgetConfig())

    assert store.count_memory_links() == 0
    assert store.get_linked_memory_ids(one.id) == []
    assert store.get_linked_memory_ids(two.id) == []


def test_linker_skips_weak_overlap(store: MemoryStore) -> None:
    store.create_memory(type="project", content="Acme platform migration")
    store.create_memory(type="job_progress", content="Rejected by Globex finance")

    reflection_jobs.link_related_memories(store, BudgetConfig())

    assert store.count_memory_links() == 0


def test_linker_links_chinese_cross_type_shared_noun(store: MemoryStore) -> None:
    proj = store.create_memory(type="project", content="张伟的副业项目叫acme")
    job = store.create_memory(type="job_progress", content="副业项目面试安排")

    reflection_jobs.link_related_memories(store, BudgetConfig())

    assert store.get_linked_memory_ids(proj.id) == [job.id]
    assert store.get_linked_memory_ids(job.id) == [proj.id]


def test_linker_skips_unrelated_chinese_pairs(store: MemoryStore) -> None:
    store.create_memory(type="project", content="今天天气很好适合散步")
    store.create_memory(type="job_progress", content="明天去超市买菜")

    reflection_jobs.link_related_memories(store, BudgetConfig())

    assert store.count_memory_links() == 0


def test_linker_respects_cap(
    store: MemoryStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Three cross-type memories that all share "acme platform" -> three linkable
    # pairs. With the per-pass cap at 1, only one logical link (2 rows) is created.
    monkeypatch.setattr(reflection_jobs, "_LINK_MAX_NEW_PER_PASS", 1)
    store.create_memory(type="stable_profile", content="Acme platform user")
    store.create_memory(type="project", content="Acme platform project")
    store.create_memory(type="job_progress", content="Acme platform job")

    reflection_jobs.link_related_memories(store, BudgetConfig())

    assert store.count_memory_links() == 2


def test_linker_idempotent_across_passes(store: MemoryStore) -> None:
    store.create_memory(type="project", content="Acme platform migration")
    store.create_memory(type="job_progress", content="Interview at Acme platform team")

    reflection_jobs.link_related_memories(store, BudgetConfig())
    first = store.count_memory_links()
    reflection_jobs.link_related_memories(store, BudgetConfig())

    assert store.count_memory_links() == first == 2


# --- Task 5: consolidation candidate polish --------------------------------


def test_factual_candidates_excludes_non_factual_types(store: MemoryStore) -> None:
    job = store.create_memory(type="job_progress", content="Interview at Acme")
    store.create_memory(type="relationship_state", content="Sharp but tired impression")
    store.create_memory(type="conversation_summary", content="They talked about work")
    store.create_memory(type="emotion_state", content="Feeling anxious today")

    candidates = reflection_jobs._factual_candidates(store, 40)

    assert [memory.id for memory in candidates] == [job.id]


# --- Task 4: 1-hop retrieval expansion -------------------------------------


def test_retrieval_pulls_one_hop_linked_memory(store: MemoryStore) -> None:
    ranked = store.create_memory(
        type="job_progress",
        content="Acme interview scheduled",
        importance=0.8,
        confidence=0.8,
    )
    linked = store.create_memory(
        type="stable_profile",
        content="Likes backend python work",
        importance=0.5,
        confidence=0.5,
    )
    store.add_memory_link(ranked.id, linked.id)

    built = build_provider_context(
        store,
        user_input="Acme interview",
        budget=BudgetConfig(max_memories_per_turn=1),
    )

    assert ranked.id in built.included_memory_ids
    # linked would not rank into the top-1 on its own, but rides the link.
    assert linked.id in built.included_memory_ids
    assert "Likes backend python work" in built.messages[0].content


def test_retrieval_skips_expired_linked_memory(store: MemoryStore) -> None:
    ranked = store.create_memory(
        type="job_progress",
        content="Acme interview scheduled",
        importance=0.8,
        confidence=0.8,
    )
    expired = store.create_memory(
        type="stable_profile",
        content="Stale linked profile",
        importance=0.5,
        confidence=0.5,
        expires_at=utc_now_iso(),
    )
    store.add_memory_link(ranked.id, expired.id)

    built = build_provider_context(
        store,
        user_input="Acme interview",
        budget=BudgetConfig(max_memories_per_turn=1),
    )

    assert ranked.id in built.included_memory_ids
    assert expired.id not in built.included_memory_ids


def test_retrieval_link_expansion_respects_cap(store: MemoryStore) -> None:
    ranked = store.create_memory(
        type="job_progress",
        content="Acme interview scheduled",
        importance=0.9,
        confidence=0.9,
    )
    extras = [
        store.create_memory(
            type="stable_profile",
            content=f"Unrelated profile fact number {index}",
            importance=0.4,
            confidence=0.4,
        )
        for index in range(5)
    ]
    for extra in extras:
        store.add_memory_link(ranked.id, extra.id)

    built = build_provider_context(
        store,
        user_input="Acme interview",
        budget=BudgetConfig(max_memories_per_turn=1),
    )

    # max_memories_per_turn=1 -> link_extra_cap = max(2, 0) = 2; ranked + 2 linked.
    pulled_extras = [memory_id for memory_id in built.included_memory_ids if memory_id != ranked.id]
    assert len(pulled_extras) == 2
    assert ranked.id in built.included_memory_ids
