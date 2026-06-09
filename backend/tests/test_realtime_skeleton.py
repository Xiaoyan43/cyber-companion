import pytest

import backend.realtime
from backend.app.memory.store import get_memory_store, reset_memory_store
from backend.realtime.companion_brain import CompanionBrain


def test_realtime_package_imports() -> None:
    assert backend.realtime.CompanionBrain is CompanionBrain


def test_companion_brain_stub_raises_not_implemented() -> None:
    reset_memory_store()
    store = get_memory_store()
    brain = CompanionBrain(store)

    with pytest.raises(NotImplementedError, match="V2 Phase 1"):
        brain.decide("hello")

    with pytest.raises(NotImplementedError, match="V2 Phase 1"):
        brain.respond("hello")

    with pytest.raises(NotImplementedError, match="V2 Phase 1"):
        brain.remember("hello", signals=None)
