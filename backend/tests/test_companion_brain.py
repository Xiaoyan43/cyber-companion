import asyncio


from backend.app.behavior.parser import SIGNALS_SENTINEL
from backend.app.memory.store import get_memory_store, reset_memory_store
from backend.app.providers.router import reset_provider_router
from backend.realtime.companion_brain import VOICE_MODE_INSTRUCTION, CompanionBrain


async def _collect_turn_events(brain: CompanionBrain, user_text: str):
    return [event async for event in brain.stream_turn(user_text)]


def test_append_voice_mode_instruction_adds_system_message() -> None:
    from backend.app.providers.types import ChatMessage

    messages = [ChatMessage(role="user", content="你好")]
    augmented = CompanionBrain.append_voice_mode_instruction(messages)

    assert augmented[-1].role == "system"
    assert augmented[-1].content == VOICE_MODE_INSTRUCTION


def test_voice_mode_instruction_tells_brain_to_write_plain_text_no_tags() -> None:
    # P14 Phase 4 (form B): the brain writes plain spoken text only; a downstream
    # ExpressionTaggerProcessor adds Fish Audio tags. So the instruction must NOT carry tag
    # vocabulary/rules, and must explicitly forbid the brain from writing its own tags.
    assert "不要自己写任何语音合成标签" in VOICE_MODE_INSTRUCTION
    assert "BOXI_SIGNALS" in VOICE_MODE_INSTRUCTION
    # Guard against regressing to the old single-stage tagging instruction.
    assert "[sighing]" not in VOICE_MODE_INSTRUCTION
    assert "最前" not in VOICE_MODE_INSTRUCTION


def test_stream_turn_local_reply_without_llm() -> None:
    reset_memory_store()
    reset_provider_router()
    store = get_memory_store()
    brain = CompanionBrain(store)

    events = asyncio.run(_collect_turn_events(brain, "   "))

    assert events[-1][0] == "done"
    outcome = events[-1][1]
    assert outcome.final_decision == "silent"
    assert outcome.called_llm is False
    assert not any(event[0] == "delta" for event in events)


def test_stream_turn_strips_signal_trailer_from_spoken_deltas() -> None:
    reset_memory_store()
    reset_provider_router()
    store = get_memory_store()
    brain = CompanionBrain(store)

    class _DeltaProvider:
        def status(self):
            from backend.app.providers.types import ProviderStatus

            return ProviderStatus(
                name="mock",
                model="mock-boxi",
                enabled=True,
                configured=True,
                api_key_present=False,
            )

        def complete_stream(self, request, provider_name=None):
            visible = "行吧，记住了。"
            trailer = (
                f'\n{SIGNALS_SENTINEL}\n{{"avatar_state":"talking","decision":"reply",'
                f'"memory":[{{"type":"profile","content":"用户叫小明"}}]}}'
            )
            yield ("delta", visible + trailer)
            from backend.app.providers.types import TokenUsage

            yield ("usage", TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15))

    brain._router.providers["mock"] = _DeltaProvider()  # type: ignore[assignment]
    brain._provider_name = "mock"

    async def _run() -> tuple[list[str], object | None]:
        deltas: list[str] = []
        outcome = None
        async for kind, value in brain.stream_turn("我叫小明"):
            if kind == "delta":
                deltas.append(value)
            else:
                outcome = value
        return deltas, outcome

    deltas, outcome = asyncio.run(_run())

    assert len(deltas) == 1
    assert "行吧，记住了。" in deltas[0]
    assert SIGNALS_SENTINEL not in deltas[0]
    assert outcome is not None
    assert SIGNALS_SENTINEL not in "".join(deltas)
    assert outcome.called_llm is True
    assert outcome.reply_signals is not None


def _run_turn_with_usage(output_tokens: int, max_output_tokens: int):
    reset_memory_store()
    reset_provider_router()
    store = get_memory_store()
    brain = CompanionBrain(store, max_output_tokens=max_output_tokens)

    class _CapProvider:
        def status(self):
            from backend.app.providers.types import ProviderStatus

            return ProviderStatus(
                name="mock",
                model="mock-boxi",
                enabled=True,
                configured=True,
                api_key_present=False,
            )

        def complete_stream(self, request, provider_name=None):
            from backend.app.providers.types import TokenUsage

            yield ("delta", "讲个故事然后到这里")
            yield ("usage", TokenUsage(input_tokens=10, output_tokens=output_tokens, total_tokens=10 + output_tokens))

    brain._router.providers["mock"] = _CapProvider()  # type: ignore[assignment]
    brain._provider_name = "mock"

    events = asyncio.run(_collect_turn_events(brain, "讲个长故事"))
    return events[-1][1]


def test_stream_turn_marks_truncated_when_output_hits_token_cap() -> None:
    # output_tokens == max_output_tokens → cut off by the cap → truncated.
    outcome = _run_turn_with_usage(output_tokens=5, max_output_tokens=5)
    assert outcome.called_llm is True
    assert outcome.truncated is True


def test_stream_turn_not_truncated_when_under_token_cap() -> None:
    # Stopped naturally before the cap → not truncated.
    outcome = _run_turn_with_usage(output_tokens=4, max_output_tokens=5)
    assert outcome.called_llm is True
    assert outcome.truncated is False
