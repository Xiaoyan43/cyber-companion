from pathlib import Path

import pytest

from backend.app.memory.budget import BudgetConfig
from backend.app.memory.context_builder import _TRAILER_REMINDER, build_provider_context
from backend.app.memory.chat_persistence import persist_chat_turn
from backend.app.memory.store import MemoryStore
from backend.app.providers.cost import estimate_token_count
from backend.app.providers.types import ChatCompletionResult, CostEstimate, TokenUsage
from backend.app.schemas import ChatMessageSchema


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(db_path=tmp_path / "truncate.db")


def _completion_result() -> ChatCompletionResult:
    usage = TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15)
    cost = CostEstimate(input_usd=0.0, output_usd=0.0, total_usd=0.0, pricing_source="test")
    return ChatCompletionResult(
        provider="mock",
        model="mock-boxi",
        content="ok",
        usage=usage,
        cost=cost,
        mock=True,
    )


def test_build_provider_context_truncates_oversized_user_input(store: MemoryStore) -> None:
    long_input = "长" * 5000
    budget = BudgetConfig(max_user_input_tokens=100)

    built = build_provider_context(store, user_input=long_input, budget=budget)

    provider_user = built.messages[-1].content
    system_message = built.messages[0].content
    assert _TRAILER_REMINDER.strip() in system_message
    assert " …[truncated]" in provider_user
    assert "系统提醒" not in provider_user
    assert len(provider_user) < len(long_input)
    assert estimate_token_count(provider_user) <= budget.max_user_input_tokens + 10


def test_persist_chat_turn_keeps_full_user_input(store: MemoryStore) -> None:
    long_input = "paste-" + ("x" * 6000)
    request_messages = [ChatMessageSchema(role="user", content=long_input)]

    persist_chat_turn(store, request_messages, _completion_result())

    messages = store.list_messages(limit=5)
    assert len(messages) == 2
    assert messages[0].content == long_input
