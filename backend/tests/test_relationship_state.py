from pathlib import Path

import pytest

from backend.app.behavior.kernel import apply_signals_to_kernel
from backend.app.behavior.mood import apply_idle_tick_mood_delta, choose_tone_mode
from backend.app.memory.context_builder import build_provider_context
from backend.app.memory.database import MoodStateRecord, RelationshipStateRecord, connect, init_database
from backend.app.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "relationship.db")


def test_relationship_state_seeded_with_defaults(store: MemoryStore) -> None:
    rel = store.get_relationship_state()
    assert rel.trust == 0.5
    assert rel.closeness == 0.2
    assert rel.familiarity == 0.0
    assert rel.tension == 0.0


def test_update_relationship_state_partial_persist(store: MemoryStore) -> None:
    before = store.get_relationship_state()
    updated = store.update_relationship_state(trust=0.62, closeness=0.31)
    assert updated.trust == 0.62
    assert updated.closeness == 0.31
    assert updated.familiarity == before.familiarity
    assert updated.updated_at >= before.updated_at


def test_trust_backfill_from_mood_state(tmp_path: Path) -> None:
    db_path = tmp_path / "backfill.db"
    init_database(db_path)
    with connect(db_path) as connection:
        connection.execute("UPDATE mood_state SET trust = 0.73 WHERE id = 1")
        connection.execute("DELETE FROM schema_meta WHERE key = 'relationship_trust_backfilled'")

    init_database(db_path)
    store = MemoryStore(db_path=db_path)
    assert store.get_relationship_state().trust == pytest.approx(0.73)


def test_kernel_positive_appraisal_raises_closeness_and_trust(store: MemoryStore) -> None:
    store.update_relationship_state(trust=0.4, closeness=0.2, familiarity=0.0, tension=0.2)
    apply_signals_to_kernel(
        store,
        {"appraisal": {"valence": 0.8, "goal_relevance": 0.9}},
    )
    rel = store.get_relationship_state()
    assert rel.closeness >= 0.22
    assert rel.trust >= 0.41
    assert rel.familiarity == pytest.approx(0.01)


def test_kernel_negative_appraisal_raises_worry(store: MemoryStore) -> None:
    store.update_mood_state(worry=0.2)
    apply_signals_to_kernel(
        store,
        {"appraisal": {"valence": -0.8, "goal_relevance": 0.9}},
    )
    assert store.get_mood_state().worry > 0.2


def test_kernel_tension_decays_without_rel_delta(store: MemoryStore) -> None:
    store.update_relationship_state(tension=0.4)
    apply_signals_to_kernel(store, {})
    assert store.get_relationship_state().tension == pytest.approx(0.36, abs=0.001)


def test_kernel_clamps_large_relationship_delta(store: MemoryStore) -> None:
    store.update_relationship_state(trust=0.5)
    apply_signals_to_kernel(store, {"relationship": {"trust": 0.9}})
    assert store.get_relationship_state().trust == pytest.approx(0.6, abs=0.001)


def test_kernel_meaningful_interaction_drops_loneliness(store: MemoryStore) -> None:
    store.update_mood_state(loneliness=0.5)
    apply_signals_to_kernel(store, {"appraisal": {"valence": 0.6, "goal_relevance": 0.2}})
    mood = store.get_mood_state()
    rel = store.get_relationship_state()
    assert mood.loneliness == pytest.approx(0.4, abs=0.001)
    assert rel.last_meaningful_interaction_at is not None


def test_choose_tone_mode_tease_requires_relationship_gates() -> None:
    mood = MoodStateRecord(
        updated_at="2020-01-01T00:00:00+00:00",
        mood="annoyed",
        energy=0.5,
        annoyance=0.7,
        boredom=0.2,
        worry=0.2,
        trust=0.5,
        loneliness=0.3,
        metadata={},
    )
    low_trust = RelationshipStateRecord(
        updated_at="2020-01-01T00:00:00+00:00",
        trust=0.3,
        closeness=0.5,
        familiarity=0.5,
        tension=0.1,
        last_meaningful_interaction_at=None,
        metadata={},
    )
    ready = RelationshipStateRecord(
        updated_at="2020-01-01T00:00:00+00:00",
        trust=0.5,
        closeness=0.5,
        familiarity=0.4,
        tension=0.2,
        last_meaningful_interaction_at=None,
        metadata={},
    )
    tense = RelationshipStateRecord(
        updated_at="2020-01-01T00:00:00+00:00",
        trust=0.5,
        closeness=0.5,
        familiarity=0.4,
        tension=0.6,
        last_meaningful_interaction_at=None,
        metadata={},
    )

    assert choose_tone_mode(mood, low_trust, overwhelmed=False) == "normal"
    assert choose_tone_mode(mood, ready, overwhelmed=False) == "tease"
    assert choose_tone_mode(mood, tense, overwhelmed=False) == "normal"
    assert choose_tone_mode(mood, ready, overwhelmed=True) == "comfort"


def test_idle_tick_loneliness_grows_more_when_closeness_low() -> None:
    mood = MoodStateRecord(
        updated_at="2020-01-01T00:00:00+00:00",
        mood="idle",
        energy=0.5,
        annoyance=0.2,
        boredom=0.2,
        worry=0.2,
        trust=0.5,
        loneliness=0.3,
        metadata={},
    )
    low = apply_idle_tick_mood_delta(mood, closeness=0.0)
    high = apply_idle_tick_mood_delta(mood, closeness=1.0)
    assert low.loneliness > high.loneliness


def test_context_builder_includes_relationship_block(store: MemoryStore) -> None:
    built = build_provider_context(store, user_input="hello")
    system = built.messages[0].content
    assert "[Relationship]" in system
    assert "trust=" in system
    assert "[Impression]" not in system


def test_context_builder_includes_impression_when_memory_exists(store: MemoryStore) -> None:
    store.create_memory(type="relationship_state", content="We are cautiously warming up.")
    built = build_provider_context(store, user_input="hello")
    system = built.messages[0].content
    assert "[Impression]" in system
    assert "cautiously warming up" in system
