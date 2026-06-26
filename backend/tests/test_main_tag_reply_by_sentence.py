from __future__ import annotations

import time

from backend.app.main import _tag_reply_by_sentence
from backend.app.memory.database import MoodStateRecord
from backend.app.providers.types import ChatCompletionRequest, ChatCompletionResult, CostEstimate, TokenUsage


def _mood(**overrides: float | str) -> MoodStateRecord:
    base = dict(
        updated_at="2026-06-20T00:00:00+00:00",
        mood="idle",
        energy=0.5,
        annoyance=0.0,
        boredom=0.0,
        worry=0.0,
        trust=0.5,
        loneliness=0.0,
    )
    base.update(overrides)
    return MoodStateRecord(**base)  # type: ignore[arg-type]


class _PerSentenceFakeRouter:
    """Routes ``router.complete`` calls by the sentence text in the last user message.

    ``responses`` maps an exact (stripped) sentence to the tagger's reply for that sentence.
    ``delays`` optionally maps a sentence to an artificial processing delay, used to prove the
    rejoin keeps original sentence order even when calls finish out of order under concurrency.
    """

    def __init__(self, responses: dict[str, str], delays: dict[str, float] | None = None) -> None:
        self._responses = responses
        self._delays = delays or {}

    def complete(
        self,
        request: ChatCompletionRequest,
        *,
        provider_name: str | None = None,
    ) -> ChatCompletionResult:
        sentence = request.messages[-1].content
        delay = self._delays.get(sentence, 0.0)
        if delay:
            time.sleep(delay)
        content = self._responses[sentence]
        return ChatCompletionResult(
            provider="fake",
            model="fake-model",
            content=content,
            usage=TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15),
            cost=CostEstimate(input_usd=0.0, output_usd=0.0, total_usd=0.0, pricing_source="test"),
            mock=True,
        )


def test_tag_reply_by_sentence_isolates_single_sentence_failure() -> None:
    # Middle sentence's tagger call alters the wording ("第二句" -> "我句"), which
    # _preserves_original_wording must reject -> that sentence alone degrades to plain text.
    # The other two sentences keep their tags. This is the core fix: under the old whole-text
    # call, one bad sentence used to wipe out every tag in the reply.
    router = _PerSentenceFakeRouter(
        responses={
            "第一句。": "[happy]第一句。",
            "第二句！": "我句！",
            "第三句？": "[sad]第三句？",
        }
    )

    result = _tag_reply_by_sentence("第一句。第二句！第三句？", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "[happy]第一句。第二句！[sad]第三句？"


def test_tag_reply_by_sentence_preserves_original_wording() -> None:
    router = _PerSentenceFakeRouter(
        responses={
            "第一句。": "[happy]第一句。",
            "第二句！": "[excited]第二句！",
            "第三句？": "[curious]第三句？",
        }
    )

    result = _tag_reply_by_sentence("第一句。第二句！第三句？", _mood(), router=router)  # type: ignore[arg-type]

    stripped_of_tags = result.replace("[happy]", "").replace("[excited]", "").replace("[curious]", "")
    assert stripped_of_tags == "第一句。第二句！第三句？"


def test_tag_reply_by_sentence_preserves_order_despite_out_of_order_completion() -> None:
    # The first sentence is the slowest to "come back" from the tagger; if the rejoin logic
    # relied on completion order instead of original sentence order, this would scramble.
    router = _PerSentenceFakeRouter(
        responses={
            "第一句。": "[a]第一句。",
            "第二句！": "[b]第二句！",
            "第三句？": "[c]第三句？",
        },
        delays={"第一句。": 0.05},
    )

    result = _tag_reply_by_sentence("第一句。第二句！第三句？", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "[a]第一句。[b]第二句！[c]第三句？"


def test_tag_reply_by_sentence_single_sentence_skips_thread_pool() -> None:
    router = _PerSentenceFakeRouter(responses={"只有一句。": "[calm]只有一句。"})

    result = _tag_reply_by_sentence("只有一句。", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "[calm]只有一句。"


def test_tag_reply_by_sentence_blank_text_passthrough() -> None:
    router = _PerSentenceFakeRouter(responses={})

    result = _tag_reply_by_sentence("   ", _mood(), router=router)  # type: ignore[arg-type]

    assert result == "   "
