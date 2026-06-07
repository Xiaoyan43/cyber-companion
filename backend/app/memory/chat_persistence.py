from __future__ import annotations

from typing import Any

from backend.app.memory.store import MemoryStore
from backend.app.providers.types import ChatCompletionResult
from backend.app.schemas import ChatMessageSchema


def persist_chat_turn(
    store: MemoryStore,
    request_messages: list[ChatMessageSchema],
    result: ChatCompletionResult,
    *,
    decision: str | None = None,
    avatar_state: str | None = None,
    should_call_llm: bool | None = None,
) -> list[int]:
    saved_ids: list[int] = []

    for message in request_messages:
        if message.role == "user":
            if not message.content.strip():
                continue
            saved = store.create_message(
                role=message.role,
                content=message.content,
                source="chat",
                metadata={"phase": "user_turn"},
            )
            saved_ids.append(saved.id)

    assistant_metadata: dict[str, Any] = {
        "provider": result.provider,
        "model": result.model,
        "mock": result.mock,
        "usage": {
            "input_tokens": result.usage.input_tokens,
            "output_tokens": result.usage.output_tokens,
            "total_tokens": result.usage.total_tokens,
        },
        "cost": {
            "input_usd": result.cost.input_usd,
            "output_usd": result.cost.output_usd,
            "total_usd": result.cost.total_usd,
            "pricing_source": result.cost.pricing_source,
        },
    }
    if decision is not None:
        assistant_metadata["decision"] = decision
    if avatar_state is not None:
        assistant_metadata["avatar_state"] = avatar_state
    if should_call_llm is not None:
        assistant_metadata["should_call_llm"] = should_call_llm
    assistant_message = store.create_message(
        role="assistant",
        content=result.content,
        source="chat",
        metadata=assistant_metadata,
    )
    saved_ids.append(assistant_message.id)
    return saved_ids
