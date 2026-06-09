import pytest

import backend.realtime
from backend.app.memory.store import get_memory_store, reset_memory_store
from backend.realtime.companion_brain import CompanionBrain


def test_realtime_package_imports() -> None:
    assert backend.realtime.CompanionBrain is CompanionBrain


def test_companion_brain_decide_returns_behavior_decision() -> None:
    reset_memory_store()
    store = get_memory_store()
    brain = CompanionBrain(store)

    decision = brain.decide("你好")

    assert decision.decision in {"reply", "silent", "mutter", "refuse", "interrupt", "proactive", "observe"}
    assert decision.avatar_state


def test_companion_brain_decide_silent_on_empty_input() -> None:
    reset_memory_store()
    store = get_memory_store()
    brain = CompanionBrain(store)

    decision = brain.decide("   ")

    assert decision.decision == "silent"
    assert decision.should_call_llm is False


def test_companion_brain_processor_imports_with_pipecat() -> None:
    pytest.importorskip("pipecat")
    from backend.realtime.companion_brain_processor import CompanionBrainProcessor

    assert CompanionBrainProcessor is not None
