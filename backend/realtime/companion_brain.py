"""Companion Brain — custom LLM slot inside the Pipecat pipeline (V2 Phase 3).

Mirrors the soul seam used by ``/chat/complete`` in ``backend.app.main``:
behavior → context → provider stream → signal-strip → persist → memory write.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any, Literal

from loguru import logger

from backend.app.behavior.completion import build_budget_block_completion, build_local_completion
from backend.app.behavior.engine import evaluate_behavior
from backend.app.behavior.kernel import apply_signals_to_kernel
from backend.app.behavior.parser import SignalStreamFilter, parse_structured_assistant_response
from backend.app.behavior.types import BehaviorDecision, BehaviorEvent
from backend.app.memory.budget import BudgetConfig, load_budget_config
from backend.app.memory.chat_persistence import persist_chat_turn
from backend.app.memory.context_builder import build_provider_context
from backend.app.memory.store import MemoryStore
from backend.app.memory.summary_policy import maybe_update_conversation_summary
from backend.app.memory.usage_guard import evaluate_llm_budget_gate
from backend.app.memory.write_policy import record_turn_memories
from backend.app.providers.cost import estimate_cost
from backend.app.providers.exceptions import ProviderError
from backend.app.providers.router import ProviderRouter, get_provider_router
from backend.app.providers.types import ChatCompletionRequest, ChatCompletionResult, ChatMessage, StreamChunk
from backend.app.schemas import ChatMessageSchema

# P14 Phase 4 (form B): the brain writes PLAIN spoken text only — a dedicated downstream
# expression tagger (ExpressionTaggerProcessor → Gemini) adds Fish Audio tags sentence by
# sentence. So this instruction must NOT carry any tag vocabulary/rules; that separation is
# the whole point (single-stage tagging degrades on long replies, see docs/HANDOFF.md probe).
VOICE_MODE_INSTRUCTION = (
    "语音对话模式：口语化、自然。默认简短（1-3 句），但内容需要展开时（讲故事、深聊、安慰、解释）"
    "就展开，跟着内容走，不要为了简短砍掉该说的话，也不要为了显得有内容硬拉长。\n"
    "只写自然的对话正文，不要自己写任何语音合成标签或方括号情绪标注（如 [happy]、[叹气]）——"
    "语气和声音由专门的环节处理，你写的方括号内容反而会被念出来。\n"
    "正文之后按协议输出 <<<BOXI_SIGNALS>>> 行。"
)

BrainStreamEvent = (
    tuple[Literal["delta"], str]
    | tuple[Literal["done"], "VoiceTurnOutcome"]
)


@dataclass(frozen=True)
class VoiceTurnOutcome:
    user_text: str
    behavior: BehaviorDecision
    final_decision: str
    avatar_state: str
    called_llm: bool
    raw_reply: str
    reply_signals: dict[str, Any] | None
    result: ChatCompletionResult


class CompanionBrain:
    """Pipecat LLM-step wrapper around the existing Python soul."""

    def __init__(
        self,
        store: MemoryStore,
        *,
        router: ProviderRouter | None = None,
        budget: BudgetConfig | None = None,
        provider_name: str | None = None,
        max_output_tokens: int | None = None,
    ) -> None:
        self._store = store
        self._router = router or get_provider_router()
        self._budget = budget or load_budget_config()
        self._provider_name = provider_name
        self._max_output_tokens = max_output_tokens

    def decide(self, user_text: str) -> BehaviorDecision:
        return evaluate_behavior(
            self._store,
            BehaviorEvent(event_type="user_message", user_input=user_text),
        )

    @staticmethod
    def append_voice_mode_instruction(messages: list[ChatMessage]) -> list[ChatMessage]:
        """Realtime-only terseness lever — does not touch soul persona."""
        return [*messages, ChatMessage(role="system", content=VOICE_MODE_INSTRUCTION)]

    async def stream_turn(self, user_text: str) -> AsyncIterator[BrainStreamEvent]:
        """One finalized utterance — mirrors ``/chat/complete`` + streaming deltas."""
        decision = self.decide(user_text)
        final_decision = decision.decision
        called_llm = False
        reply_signals: dict[str, Any] | None = None
        avatar_state = decision.avatar_state
        accumulated_parts: list[str] = []
        result: ChatCompletionResult | None = None

        if decision.should_call_llm:
            try:
                target_model = self._router.get_provider(self._provider_name).status().model
            except ProviderError as error:
                logger.error(f"CompanionBrain provider status failed: {error.message}")
                result = build_local_completion(decision, user_input=user_text)
                avatar_state = "annoyed"
                final_decision = "refuse"
                if result.content.strip():
                    yield ("delta", result.content)
                yield (
                    "done",
                    VoiceTurnOutcome(
                        user_text=user_text,
                        behavior=decision,
                        final_decision=final_decision,
                        avatar_state=avatar_state,
                        called_llm=False,
                        raw_reply=result.content,
                        reply_signals=None,
                        result=result,
                    ),
                )
                return

            gate = evaluate_llm_budget_gate(self._store, self._budget, target_model=target_model)
            if not gate.allowed:
                result = build_budget_block_completion(gate.block_line or "预算用完了，先省着点。")
                avatar_state = "annoyed"
                final_decision = "refuse"
                if result.content.strip():
                    yield ("delta", result.content)
            else:
                built = build_provider_context(
                    self._store,
                    user_input=user_text,
                    budget=self._budget,
                    behavior=decision,
                )
                voice_messages = self.append_voice_mode_instruction(built.messages)
                max_tokens = (
                    self._max_output_tokens
                    if self._max_output_tokens is not None
                    else self._budget.max_output_tokens_per_turn
                )
                logger.debug(
                    "CompanionBrain provider context: "
                    f"{len(voice_messages)} messages, "
                    f"~{built.estimated_input_tokens} input tokens, "
                    f"truncated={built.truncated}, "
                    f"memories={len(built.included_memory_ids)}, "
                    f"history_turns={len(built.included_message_ids)}, "
                    f"max_output_tokens={max_tokens}, voice_mode=on"
                )
                completion_request = ChatCompletionRequest(
                    messages=voice_messages,
                    max_output_tokens=max_tokens,
                )
                provider_status = self._router.get_provider(self._provider_name).status()
                signal_filter = SignalStreamFilter()
                stream_usage = None
                provider_failed = False
                try:
                    async for chunk_kind, chunk_value in self._async_complete_stream(completion_request):
                        if chunk_kind == "delta":
                            accumulated_parts.append(chunk_value)
                            visible = signal_filter.feed(chunk_value)
                            if visible:
                                yield ("delta", visible)
                        elif chunk_kind == "usage":
                            stream_usage = chunk_value
                except ProviderError as error:
                    provider_failed = True
                    logger.error(f"CompanionBrain provider stream failed: {error.message}")
                finally:
                    tail = signal_filter.flush()
                    if tail:
                        yield ("delta", tail)

                if provider_failed or stream_usage is None:
                    logger.error("CompanionBrain provider stream ended without usage")
                    result = build_local_completion(decision, user_input=user_text)
                    avatar_state = "annoyed"
                    final_decision = "refuse"
                    if result.content.strip():
                        yield ("delta", result.content)
                else:
                    accumulated_text = "".join(accumulated_parts)
                    parsed = parse_structured_assistant_response(accumulated_text)
                    reply_signals = parsed.signals
                    avatar_state = parsed.avatar_state or (
                        "talking"
                        if decision.decision in {"reply", "interrupt"}
                        else decision.avatar_state
                    )
                    if parsed.decision:
                        final_decision = parsed.decision
                    called_llm = True
                    result = ChatCompletionResult(
                        provider=provider_status.name,
                        model=provider_status.model,
                        content=parsed.content,
                        usage=stream_usage,
                        cost=estimate_cost(provider_status.model, stream_usage),
                        mock=provider_status.name == "mock",
                    )
        else:
            result = build_local_completion(decision, user_input=user_text)
            avatar_state = decision.avatar_state
            if decision.decision != "silent" and result.content.strip():
                yield ("delta", result.content)

        assert result is not None
        yield (
            "done",
            VoiceTurnOutcome(
                user_text=user_text,
                behavior=decision,
                final_decision=final_decision,
                avatar_state=avatar_state,
                called_llm=called_llm,
                raw_reply=result.content,
                reply_signals=reply_signals,
                result=result,
            ),
        )

    async def _async_complete_stream(
        self,
        request: ChatCompletionRequest,
    ) -> AsyncIterator[StreamChunk]:
        iterator = self._router.complete_stream(request, provider_name=self._provider_name)

        def _next_chunk(it: Iterator[StreamChunk]) -> StreamChunk | None:
            try:
                return next(it)
            except StopIteration:
                return None

        while True:
            chunk = await asyncio.to_thread(_next_chunk, iterator)
            if chunk is None:
                break
            yield chunk

    def remember(self, outcome: VoiceTurnOutcome) -> None:
        """Persist turn memories and kernel updates — off the spoken path."""
        if outcome.called_llm:
            try:
                apply_signals_to_kernel(self._store, outcome.reply_signals)
            except Exception:
                pass

        saved_ids = persist_chat_turn(
            self._store,
            [ChatMessageSchema(role="user", content=outcome.user_text)],
            outcome.result,
            decision=outcome.final_decision,
            avatar_state=outcome.avatar_state,
            should_call_llm=outcome.called_llm,
        )
        user_message_id = saved_ids[0] if outcome.user_text.strip() and saved_ids else None
        try:
            record_turn_memories(
                self._store,
                user_input=outcome.user_text,
                signals=outcome.reply_signals,
                source_message_id=user_message_id,
                budget=self._budget,
            )
        except Exception:
            pass
        maybe_update_conversation_summary(self._store, budget=self._budget)
        if outcome.called_llm:
            self._store.note_llm_turn()
