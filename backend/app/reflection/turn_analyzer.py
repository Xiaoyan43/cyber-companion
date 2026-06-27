from __future__ import annotations

import json
import logging

from backend.app.behavior.parser import JSON_BLOCK_PATTERN
from backend.app.memory.budget import BudgetConfig
from backend.app.memory.store import MemoryStore
from backend.app.providers.exceptions import ProviderError
from backend.app.providers.router import get_provider_router
from backend.app.providers.types import (
    ChatCompletionRequest,
    ChatCompletionResult,
    ChatMessage,
    CostEstimate,
    TokenUsage,
)
from backend.app.reflection.runner import run_reflection_if_due
from backend.app.soul import SoulTurnRuntime

logger = logging.getLogger(__name__)

_TURNS_SINCE_ANALYSIS_KEY = "turns_since_analysis"
_ANALYZE_MAX_OUTPUT_TOKENS = 220
_VOICE_RESULT_PROVIDER = "doubao_realtime"
_VOICE_RESULT_MODEL = "doubao-rt"

_ANALYZE_SYSTEM_PROMPT = (
    "You analyze a voice companion exchange. Rate the exchange only; do not reply in character. "
    "Return ONE JSON object matching this schema (no markdown, no prose outside JSON):\n"
    '{"appraisal":{"valence":-1..1,"arousal":0..1,"goal_relevance":0..1,"note":"..."},'
    '"relationship":{"trust":-0.1..0.1,"closeness":-0.1..0.1,"tension":-0.1..0.1},'
    '"memory":[{"type":"<one of: stable_profile,recent_event,emotion_state,project,'
    'job_progress,reminder,relationship_state,behavior_preference>",'
    '"content":"...","importance":0..1,"confidence":0..1,"tags":[]}]}'
)


def _bump_turns_since_analysis(store: MemoryStore) -> int:
    current = int(store.get_meta(_TURNS_SINCE_ANALYSIS_KEY, "0"))
    new_count = current + 1
    store.set_meta(_TURNS_SINCE_ANALYSIS_KEY, str(new_count))
    return new_count


def _llm_analysis_due(store: MemoryStore, budget: BudgetConfig) -> bool:
    every = budget.analyze_every_n_turns
    if every <= 1:
        return True
    return _bump_turns_since_analysis(store) >= every


def _reset_analysis_counter(store: MemoryStore) -> None:
    store.set_meta(_TURNS_SINCE_ANALYSIS_KEY, "0")


def _llm_analyze_turn(user_text: str, bot_text: str) -> dict | None:
    user_prompt = f"User said:\n{user_text.strip()}\n\nCompanion replied:\n{bot_text.strip()}"
    try:
        router = get_provider_router()
        result = router.complete(
            ChatCompletionRequest(
                messages=[
                    ChatMessage(role="system", content=_ANALYZE_SYSTEM_PROMPT),
                    ChatMessage(role="user", content=user_prompt),
                ],
                max_output_tokens=_ANALYZE_MAX_OUTPUT_TOKENS,
            ),
        )
        match = JSON_BLOCK_PATTERN.search(result.content)
        if not match:
            return None
        payload = json.loads(match.group(0))
        if isinstance(payload, dict):
            return payload
    except (ProviderError, json.JSONDecodeError, TypeError, ValueError):
        return None
    return None


def _voice_completion_result(bot_text: str) -> ChatCompletionResult:
    return ChatCompletionResult(
        provider=_VOICE_RESULT_PROVIDER,
        model=_VOICE_RESULT_MODEL,
        content=bot_text,
        usage=TokenUsage(input_tokens=0, output_tokens=0, total_tokens=0),
        cost=CostEstimate(
            input_usd=0.0,
            output_usd=0.0,
            total_usd=0.0,
            pricing_source="none",
        ),
        mock=False,
    )


def analyze_turn(
    store: MemoryStore,
    *,
    user_text: str,
    bot_text: str,
    budget: BudgetConfig | None = None,
) -> None:
    """Off-path RTC pure-E2E: transcript -> appraisal -> commit (§3 step 9). Never raises.

    RTC-specific LLM appraisal stays here (decision 6); persist/memory/event-log reuse
    ``SoulTurnRuntime.commit_turn`` so kernel + SQLite side-effects match the main runtime.
    """
    try:
        config = budget or BudgetConfig()
        if not config.enable_turn_analyzer:
            return
        if not user_text.strip() and not bot_text.strip():
            return

        runtime = SoulTurnRuntime(
            store=store,
            router=get_provider_router(),
            budget=config,
        )

        # Local appraisal for the voice turn: same behavior evaluation as text chat, so
        # pure-E2E voice turns advance the felt-vs-shown positive-zone streak identically.
        runtime.decide(user_text)

        # A failed/skipped LLM appraisal must NOT drop the turn: still persist the
        # transcript; only the kernel update is skipped (no valid signals).
        signals: dict | None = None
        if _llm_analysis_due(store, config):
            signals = _llm_analyze_turn(user_text, bot_text)
            if signals is not None:
                _reset_analysis_counter(store)

        avatar_state = "talking"
        if isinstance(signals, dict):
            raw_avatar = signals.get("avatar_state")
            if isinstance(raw_avatar, str) and raw_avatar.strip():
                avatar_state = raw_avatar.strip()

        runtime.commit_turn(
            user_input=user_text,
            result=_voice_completion_result(bot_text),
            decision="reply",
            avatar_state=avatar_state,
            called_llm=signals is not None,
            signals=signals,
            apply_signals=isinstance(signals, dict),
            surface="rtc_off_path",
            update_summary=False,
            should_call_llm=True,
        )

        if signals is not None:
            run_reflection_if_due(store, config)
    except Exception:
        logger.exception("analyze_turn failed")
