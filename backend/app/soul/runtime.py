"""Single turn orchestrator for the Shared Soul Layer (docs/SOUL_RUNTIME_ARCH.md §3).

Phase 1 收敛的第一刀：把 `/chat/complete`（text non-stream）的回合编排搬进
``SoulTurnRuntime.run_turn()``，行为与原 ``main.chat_complete`` 逐字节等价。stream /
Pipecat surface 在后续子步骤接入；本文件先服务 text non-stream，并把表达层的
逐句标签 helper（``tag_reply_by_sentence``）收拢为单一源（main 仍以同名别名复用）。
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from backend.app.behavior.completion import (
    build_budget_block_completion,
    build_local_completion,
)
from backend.app.behavior.parser import parse_structured_assistant_response
from backend.app.behavior.types import BehaviorDecision
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.database import MoodStateRecord
from backend.app.memory.store import MemoryStore
from backend.app.providers.cost import estimate_cost
from backend.app.providers.router import ProviderRouter
from backend.app.providers.types import ChatCompletionRequest, ChatCompletionResult
from backend.app.soul.adapters import NoopEventLogPort, SoulPorts, ports_from_store
from backend.app.soul.ports import EventLogPort, MemoryPort, SoulEvent, StatePort
from backend.app.tts.expression_tagger import (
    apply_expression_tags_to_sentence,
    build_prior_context,
    split_complete_sentences,
    suppress_repeated_leading_tags,
)
from backend.app.tts.translator import translate_to_chinese


_TAGGER_PRIOR_CONTEXT_CHAR_CAP = 800


def tag_reply_by_sentence(text: str, mood: MoodStateRecord, *, router: ProviderRouter) -> str:
    """Tag ``text`` sentence-by-sentence instead of as one whole-text call.

    Mirrors the voice pipeline's per-sentence tagging (``ExpressionTaggerProcessor``): a single
    sentence's tagger failure (truncation/altered wording/dropped clause) only degrades that
    sentence, not the entire reply — the failure mode that made long text-chat replies lose
    every tag at once (see docs/HANDOFF.md 第六十四轮). Sentences are tagged concurrently via a
    thread pool (``router.complete`` is blocking I/O) so latency tracks the slowest sentence
    rather than the sum of all of them, then rejoined in original order.
    """
    if not text.strip():
        return text
    sentences, remainder = split_complete_sentences(text)
    if remainder.strip():
        sentences.append(remainder)
    if not sentences:
        return text
    if len(sentences) == 1:
        return apply_expression_tags_to_sentence(sentences[0], mood, router=router)

    priors = [
        build_prior_context(sentences[:index], _TAGGER_PRIOR_CONTEXT_CHAR_CAP)
        for index in range(len(sentences))
    ]
    with ThreadPoolExecutor(max_workers=len(sentences)) as executor:
        tagged = list(
            executor.map(
                lambda pair: apply_expression_tags_to_sentence(
                    pair[0], mood, prior_context=pair[1], router=router
                ),
                zip(sentences, priors),
            )
        )
    return suppress_repeated_leading_tags("".join(tagged))


@dataclass(frozen=True)
class PerceivedEvent:
    """Normalized turn input across surfaces (§2). Phase 1 only carries what text needs."""

    event_type: str
    user_input: str
    surface: str = "text"
    provider: str | None = None
    target_language: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TurnOutcome:
    """Result of one ``run_turn`` (§3). ``called_llm`` drives note_llm_turn + reflection."""

    result: ChatCompletionResult
    avatar_state: str
    decision: str
    called_llm: bool
    translation: str | None = None


class SoulTurnRuntime:
    """The唯一回合编排 (§3). Surfaces are thin adapters that build a ``PerceivedEvent``,
    call ``run_turn``, and frame the ``TurnOutcome`` for their transport.

    ``budget`` is passed in (not loaded here) so the caller's ``load_budget_config``
    binding — including test monkeypatches on ``main.load_budget_config`` — stays
    authoritative for the whole turn.
    """

    def __init__(
        self,
        *,
        store: MemoryStore | None = None,
        router: ProviderRouter,
        budget: BudgetConfig,
        memory_port: MemoryPort | None = None,
        state_port: StatePort | None = None,
        event_log_port: EventLogPort | None = None,
        ports: SoulPorts | None = None,
    ) -> None:
        self.router = router
        self.budget = budget
        if ports is None:
            if memory_port is not None and state_port is not None:
                ports = SoulPorts(
                    memory=memory_port,
                    state=state_port,
                    event_log=event_log_port or NoopEventLogPort(),
                )
            elif store is not None:
                ports = ports_from_store(store)
            else:
                raise ValueError("SoulTurnRuntime requires either store or ports")
        self.memory = ports.memory
        self.state = ports.state
        self.event_log = ports.event_log

    def decide(self, user_input: str) -> BehaviorDecision:
        """Perception → behavior decision (§3 step 1). Shared by all surfaces."""
        return self.memory.decide_user_message(user_input)

    def run_turn(self, event: PerceivedEvent) -> TurnOutcome:
        memory = self.memory
        state = self.state
        router = self.router
        budget = self.budget
        user_input = event.user_input

        decision = memory.decide_user_message(user_input)
        final_decision = decision.decision
        called_llm = False
        reply_signals: dict | None = None
        translation: str | None = None

        if decision.should_call_llm:
            # Resolve the target model first so the spend brake can also veto pricier
            # reasoning models before any provider call happens. ProviderError here
            # propagates to the adapter, which maps it to the surface error shape.
            target_model = router.get_provider(event.provider).status().model

            gate = memory.check_llm_budget(budget, target_model=target_model)
            if not gate.allowed:
                # Spend brake tripped: answer locally, never touch the provider.
                result = build_budget_block_completion(gate.block_line or "预算用完了，先省着点。")
                avatar_state = "annoyed"
                final_decision = "refuse"
            else:
                built = memory.build_context(
                    user_input=user_input,
                    budget=budget,
                    behavior=decision,
                    target_language=event.target_language,
                )
                completion_request = ChatCompletionRequest(
                    messages=built.messages,
                    max_output_tokens=budget.max_output_tokens_per_turn,
                )

                result = router.complete(completion_request, provider_name=event.provider)

                parsed = parse_structured_assistant_response(result.content)
                reply_signals = parsed.signals
                if event.target_language:
                    translation = translate_to_chinese(parsed.content, router=router)
                avatar_state = parsed.avatar_state or (
                    "talking" if decision.decision in {"reply", "interrupt"} else decision.avatar_state
                )
                if parsed.decision:
                    final_decision = parsed.decision
                called_llm = True
                try:
                    state.apply_signals(parsed.signals)
                except Exception:
                    pass
                tagged_content = tag_reply_by_sentence(
                    parsed.content,
                    state.get_mood(),
                    router=router,
                )
                result = type(result)(
                    provider=result.provider,
                    model=result.model,
                    content=tagged_content,
                    usage=result.usage,
                    cost=result.cost,
                    mock=result.mock,
                )
        else:
            result = build_local_completion(decision, user_input=user_input)
            avatar_state = decision.avatar_state

        saved_ids = memory.persist_turn(
            user_input=user_input,
            result=result,
            decision=final_decision,
            avatar_state=avatar_state,
            should_call_llm=called_llm,
            translation=translation,
        )
        user_message_id = saved_ids[0] if user_input.strip() and saved_ids else None
        try:
            memory.record_turn_memories(
                user_input=user_input,
                signals=reply_signals,
                source_message_id=user_message_id,
                budget=budget,
            )
        except Exception:
            pass
        memory.maybe_update_summary(budget)

        if called_llm:
            memory.note_llm_turn()

        self._append_turn_event(
            surface=event.surface,
            event_type=event.event_type,
            user_input=user_input,
            result=result,
            decision=final_decision,
            avatar_state=avatar_state,
            called_llm=called_llm,
            signals=reply_signals,
            message_ids=saved_ids,
            translation=translation,
            metadata=event.metadata,
        )

        return TurnOutcome(
            result=result,
            avatar_state=avatar_state,
            decision=final_decision,
            called_llm=called_llm,
            translation=translation,
        )

    def finalize_streamed_turn(
        self,
        *,
        user_input: str,
        accumulated_text: str,
        provider_name: str,
        model: str,
        usage,
        mock: bool,
        decision: str,
        avatar_state: str,
        should_call_llm: bool,
        target_language: str | None = None,
    ) -> tuple[ChatCompletionResult, str | None]:
        """Commit segment (§3 step 7-9) for the streaming text surface.

        The adapter streams deltas itself, then hands the accumulated raw text here
        to parse → apply signals → tag → persist → record memories → summarize. Kept
        byte-equivalent to the former ``main._finalize_streamed_turn``; ``self.router``
        is the same singleton the route resolved at request start.
        """
        memory = self.memory
        state = self.state
        budget = self.budget
        router = self.router
        cost = estimate_cost(model, usage)
        result = ChatCompletionResult(
            provider=provider_name,
            model=model,
            content=accumulated_text,
            usage=usage,
            cost=cost,
            mock=mock,
        )
        parsed = parse_structured_assistant_response(result.content)
        try:
            state.apply_signals(parsed.signals)
        except Exception:
            pass
        final_avatar_state = parsed.avatar_state or avatar_state
        final_decision = parsed.decision or decision
        final_content = tag_reply_by_sentence(
            parsed.content,
            state.get_mood(),
            router=router,
        )
        translation: str | None = None
        if target_language:
            translation = translate_to_chinese(parsed.content, router=router)
        result = ChatCompletionResult(
            provider=result.provider,
            model=result.model,
            content=final_content,
            usage=result.usage,
            cost=result.cost,
            mock=result.mock,
        )
        saved_ids = memory.persist_turn(
            user_input=user_input,
            result=result,
            decision=final_decision,
            avatar_state=final_avatar_state,
            should_call_llm=should_call_llm,
            translation=translation,
        )
        user_message_id = saved_ids[0] if user_input.strip() and saved_ids else None
        try:
            memory.record_turn_memories(
                user_input=user_input,
                signals=parsed.signals,
                source_message_id=user_message_id,
                budget=budget,
            )
        except Exception:
            pass
        memory.maybe_update_summary(budget)
        self._append_turn_event(
            surface="text_stream",
            event_type="user_message",
            user_input=user_input,
            result=result,
            decision=final_decision,
            avatar_state=final_avatar_state,
            called_llm=should_call_llm,
            signals=parsed.signals,
            message_ids=saved_ids,
            translation=translation,
        )
        return (
            ChatCompletionResult(
                provider=result.provider,
                model=result.model,
                content=result.content,
                usage=result.usage,
                cost=result.cost,
                mock=result.mock,
            ),
            translation,
        )

    def commit_turn(
        self,
        *,
        user_input: str,
        result: ChatCompletionResult,
        decision: str,
        avatar_state: str,
        called_llm: bool,
        signals: dict | None,
        translation: str | None = None,
        apply_signals: bool = False,
    ) -> list[int]:
        """Off-path commit (§3 step 9) for surfaces whose persist runs outside the
        spoken/streamed path — currently Pipecat ``CompanionBrain.remember``.

        Persists the turn, writes turn memories, refreshes the summary, and notes the
        LLM turn (only when ``called_llm``). ``apply_signals`` lets the caller mirror
        its own kernel-update gating; the kernel write is best-effort like the inline
        text commits. Byte-equivalent to the former ``remember`` body.
        """
        memory = self.memory
        state = self.state
        budget = self.budget
        if apply_signals:
            try:
                state.apply_signals(signals)
            except Exception:
                pass
        saved_ids = memory.persist_turn(
            user_input=user_input,
            result=result,
            decision=decision,
            avatar_state=avatar_state,
            should_call_llm=called_llm,
            translation=translation,
        )
        user_message_id = saved_ids[0] if user_input.strip() and saved_ids else None
        try:
            memory.record_turn_memories(
                user_input=user_input,
                signals=signals,
                source_message_id=user_message_id,
                budget=budget,
            )
        except Exception:
            pass
        memory.maybe_update_summary(budget)
        if called_llm:
            memory.note_llm_turn()
        self._append_turn_event(
            surface="pipecat",
            event_type="user_message",
            user_input=user_input,
            result=result,
            decision=decision,
            avatar_state=avatar_state,
            called_llm=called_llm,
            signals=signals,
            message_ids=saved_ids,
            translation=translation,
        )
        return saved_ids

    def _append_turn_event(
        self,
        *,
        surface: str,
        event_type: str,
        user_input: str,
        result: ChatCompletionResult,
        decision: str,
        avatar_state: str,
        called_llm: bool,
        signals: dict | None,
        message_ids: list[int],
        translation: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "surface": surface,
            "event_type": event_type,
            "decision": decision,
            "avatar_state": avatar_state,
            "called_llm": called_llm,
            "message_ids": message_ids,
            "provider": result.provider,
            "model": result.model,
            "mock": result.mock,
            "has_user_input": bool(user_input.strip()),
            "has_signals": bool(signals),
            "translated": translation is not None,
        }
        if metadata:
            payload["metadata"] = metadata
        try:
            self.event_log.append(SoulEvent(kind="turn.committed", payload=payload))
        except Exception:
            pass
