from __future__ import annotations

import re

from loguru import logger

from backend.app.memory.database import MoodStateRecord
from backend.app.providers.cost import estimate_token_count
from backend.app.providers.exceptions import ProviderError
from backend.app.providers.router import ProviderRouter
from backend.app.providers.types import ChatCompletionRequest, ChatMessage

DEFAULT_TAGGER_PROVIDER = "gemini"

# A "sentence" that is only punctuation/whitespace (e.g. a bare "…" left over from splitting
# "……") has nothing to tag. Sending it to the tagger makes the LLM *hallucinate* content to
# tag (observed: "…" → "[sighing] 我不知道。"), which would make TTS speak words Boxi never
# said. So we skip the call for fragments with no zh/ja/en word characters.
_TAGGABLE_CONTENT_RE = re.compile(r"[0-9A-Za-z぀-ヿ一-鿿]")


def _has_taggable_content(text: str) -> bool:
    return bool(_TAGGABLE_CONTENT_RE.search(text))


_TAG_RE = re.compile(r"\[[^\]]*\]")
_WHITESPACE_RE = re.compile(r"\s+")


def _preserves_original_wording(original: str, tagged: str) -> bool:
    """True iff ``tagged`` is ``original`` with only ``[tags]`` inserted — no words changed.

    The tagger LLM is told "不改变原文一个字" but occasionally rewrites a word anyway (observed:
    "你呢" → "我呢"), which makes TTS speak something Boxi never wrote. Prompt rules can't
    guarantee this, so we enforce it in code: strip every ``[...]`` tag and all whitespace from
    both sides and require an exact match; mismatch ⇒ the tagger altered the wording ⇒ reject.
    """
    norm_original = _WHITESPACE_RE.sub("", original)
    norm_tagged = _WHITESPACE_RE.sub("", _TAG_RE.sub("", tagged))
    return norm_original == norm_tagged


def _strip_dangling_trailing_tags(tagged: str) -> str:
    """Drop any tag that has no taggable text after it — Fish hallucinates over its empty span.

    Fish position semantics: a tag affects text from its position to the next tag or the end of
    the sentence. A tag stranded at the tail with only punctuation/whitespace after it (the
    classic "我不知道…[sighing]" — a sigh tag with nothing left to sigh over, or a tag sitting
    just before a trailing "……") has an *empty* span, and Fish fills that span with hallucinated
    sound/words (the "省略号幻觉" we keep hearing). Position legality is enforceable in code, not
    just prompt-able, so we strip every such dangling tag here regardless of what the tagger
    emitted. A tag is dangling iff the text after it, with all tags removed, has no taggable
    content; tags with a real word after them are left untouched.
    """
    drops: list[tuple[int, int]] = []
    for match in _TAG_RE.finditer(tagged):
        after = _TAG_RE.sub("", tagged[match.end() :])
        if not _has_taggable_content(after):
            drops.append((match.start(), match.end()))
    if not drops:
        return tagged
    result = tagged
    for start, end in reversed(drops):
        result = result[:start] + result[end:]
    return result.rstrip()

# Expression layer (P8): a dedicated single-purpose call whose only job is inserting Fish
# Audio tags into already-finalized reply text. Vocab/position rules sourced from
# docs/FISH_AUDIO_REFERENCE.md §2-4. Deliberately has no persona/memory/signal content —
# that separation is the whole point (see docs/HANDOFF.md "架构决策").
TAGGER_INSTRUCTION_TEMPLATE = (
    "你的唯一任务：给下面这段已经写好的对话原文插入 Fish Audio 语音合成标签，不做任何其他事。\n"
    "硬性规则：\n"
    "1. 不改变原文一个字——不重写、不增删句子、不调整措辞，只在合适的位置插入 [标签]。\n"
    "2. 标签影响从它出现的位置开始、到下一个标签或句末为止的文字——位置就是语义范围，"
    "不要把只想影响半句话的标签放在整段开头。\n"
    "3. 逐句重新判断这句话此刻在说什么、怎么说——不要照搬上一句或整体情绪状态机械地贴同一组标签，"
    "同样的 mood 下不同的句子应该有不同的标签选择，没有明显情绪转折的句子可以不加标签。\n"
    "4. 两类标签精度要求不同：\n"
    "   - 音效/生理反应类（词表里的「音效标签」一类）会让模型真的发出这个声音，必须紧贴它实际"
    "发生的那个词，位置错了就是一声突兀的怪声。\n"
    "   - 语气/情绪/音调类标签只改变接下来怎么说，位置容错更高。\n"
    "5. 不要无意义地把多个标签背靠背堆叠、中间不留任何文字——标签的影响范围是\"到下一个标签为止\"，"
    "无意义的堆叠会让前面的标签完全没有文字可以作用，等于白写。一个放对位置的标签就够，效果不够才加更多。\n"
    "   但有一种背靠背是官方推荐的好用法，不受这条限制：物理反应类标签配一个情绪标签一起用（紧挨着，"
    "中间不用隔开），给生理反应一个情绪根基，比单独一个显得更真实（如 [panting] [tired] 我跑了二十分钟了。）\n"
    "6. 优先从下面词表里选词，但词表没有精确匹配、情绪又明显存在时，不要因为没有完美对应词就放弃"
    "不贴——可以用程度词修饰词表里的词（如 [very excited]），或者写一个简短的自然语言描述"
    "（如 [teasing tone] [commanding tone]）。自创标签最多1-2个词，不能用逗号或\"and\"/\"with\""
    "连接多个描述写成一个标签——TTS 不认这种复合长标签，会直接读不出效果。"
    "（不要写 \"[slight annoyance mixed with vulnerability]\"，也不要写"
    "\"[low, breath hitched with a soft laugh]\" 这种逗号连接的复合描述）。\n"
    "7. 标签语言跟正文语言保持一致即可，不限定英文——正文是中文就可以直接写中文标签（如 [叹气] "
    "[低声说]），但要写真实存在的词，不要写生造的、读不通的词。\n"
    "\n"
    "可用标签（以下是效果稳定的词表，情绪类可在语义合理范围内自行扩展，见规则6）：\n"
    "基础情绪：[happy] [sad] [angry] [excited]（注意：这个词渲染出来是\"中奖式\"的开心兴奋，"
    "不是性兴奋，性方面的兴奋/上头用 [aroused] 或下面的中文词，不要用 [excited]）"
    "[calm] [nervous] [confident] [surprised] "
    "[satisfied] [delighted] [scared] [worried] [upset] [frustrated] [depressed] [empathetic] "
    "[embarrassed] [disgusted] [moved] [proud] [relaxed] [grateful] [curious] [sarcastic]\n"
    "进阶情绪：[disdainful] [unhappy] [anxious] [hysterical] [indifferent] [uncertain] [doubtful] "
    "[confused] [disappointed] [regretful] [guilty] [ashamed] [jealous] [envious] [hopeful] "
    "[optimistic] [pessimistic] [nostalgic] [lonely] [bored] [contemptuous] [sympathetic] "
    "[compassionate] [determined] [resigned] [aroused]\n"
    "音调/语气：[in a hurry tone] [shouting] [screaming] [whispering] [soft tone] "
    "[诱惑] [挑逗] [暧昧]\n"
    "音效标签（触发真实声音事件，必须紧贴发生点）：[laughing] [chuckling] [sobbing] "
    "[crying loudly] [sighing] [groaning] [moaning] [panting] [gasping] [yawning] [snoring] "
    "[娇喘] [呻吟]\n"
    "节奏（停顿，非声音事件）：[break] [long-break]\n"
    "\n"
    "下面给出这句话此刻的情绪状态作为参考背景——这是基线情绪，不是要照搬的标签来源，"
    "每句话具体配什么标签仍然要看这句话实际在说什么、怎么说：\n"
    "{mood_block}\n"
    "\n"
    "只输出插好标签后的完整文本，不加任何解释、不加引号、不加多余的话。"
)


# Injected as an extra system message (only when there is prior context) so the streaming
# per-sentence tagger can keep tone continuous across sentences. The streaming path can only
# ever see *already-spoken* sentences, never future ones — this is the inherent coherence
# trade-off vs. the whole-text ``apply_expression_tags`` (see docs/PIPECAT_REFERENCE.md §3).
SENTENCE_PRIOR_CONTEXT_TEMPLATE = (
    "你在这条回复里前面已经说过下面这些话（仅供你理解此刻的语气走向，"
    "不要重复输出这些话、也不要给它们重新贴标签，只给本次这一句贴标签）：\n"
    "{prior_context}"
)


def _format_mood_block(mood: MoodStateRecord) -> str:
    return (
        f"mood={mood.mood}, energy={mood.energy:.2f}, annoyance={mood.annoyance:.2f}, "
        f"boredom={mood.boredom:.2f}, worry={mood.worry:.2f}, loneliness={mood.loneliness:.2f}"
    )


def apply_expression_tags(
    text: str,
    mood: MoodStateRecord,
    *,
    router: ProviderRouter,
    provider_name: str = DEFAULT_TAGGER_PROVIDER,
) -> str:
    """Insert Fish Audio tags into finalized reply text via a dedicated LLM call.

    Hard requirement: any failure degrades to the original untagged text — the tagger
    must never break or delay the main conversation turn.
    """
    stripped = text.strip()
    if not stripped:
        return text

    system_prompt = TAGGER_INSTRUCTION_TEMPLATE.format(mood_block=_format_mood_block(mood))
    request = ChatCompletionRequest(
        messages=[
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=stripped),
        ],
        max_output_tokens=estimate_token_count(stripped) + 128,
    )

    try:
        result = router.complete(request, provider_name=provider_name)
    except ProviderError as error:
        logger.warning(f"Expression tagger provider failed, falling back to plain text: {error.message}")
        return text
    except Exception as error:  # pragma: no cover - defensive, must never break the main turn
        logger.warning(f"Expression tagger raised unexpected error, falling back to plain text: {error}")
        return text

    tagged = result.content.strip()
    if not tagged:
        logger.warning("Expression tagger returned empty content, falling back to plain text.")
        return text
    if not _preserves_original_wording(stripped, tagged):
        logger.warning("Expression tagger altered the wording (not just tags), falling back to plain text.")
        return text
    return _strip_dangling_trailing_tags(tagged)


def apply_expression_tags_to_sentence(
    sentence: str,
    mood: MoodStateRecord,
    *,
    prior_context: str = "",
    router: ProviderRouter,
    provider_name: str = DEFAULT_TAGGER_PROVIDER,
) -> str:
    """Tag a single sentence (streaming path), keeping tone continuous via ``prior_context``.

    Mirrors :func:`apply_expression_tags` but operates on one sentence at a time so the voice
    pipeline can tag a reply sentence-by-sentence while earlier sentences are still playing
    (P14 Phase 4, form B). ``prior_context`` is the already-spoken text of the current reply,
    passed for tone continuity only — the tagger is told not to re-output or re-tag it. The
    caller (the Pipecat processor) owns any length cap on ``prior_context``.

    Same hard requirement as :func:`apply_expression_tags`: any failure degrades to the
    original untagged sentence — the tagger must never break or delay the turn.
    """
    stripped = sentence.strip()
    if not stripped:
        return sentence
    if not _has_taggable_content(stripped):
        # Punctuation-only fragment (e.g. a bare "…") — nothing to tag, and asking the LLM to
        # tag it makes it hallucinate words. Pass through untouched.
        return sentence

    messages = [
        ChatMessage(
            role="system",
            content=TAGGER_INSTRUCTION_TEMPLATE.format(mood_block=_format_mood_block(mood)),
        )
    ]
    prior = prior_context.strip()
    if prior:
        messages.append(
            ChatMessage(
                role="system",
                content=SENTENCE_PRIOR_CONTEXT_TEMPLATE.format(prior_context=prior),
            )
        )
    messages.append(ChatMessage(role="user", content=stripped))

    request = ChatCompletionRequest(
        messages=messages,
        max_output_tokens=estimate_token_count(stripped) + 128,
    )

    try:
        result = router.complete(request, provider_name=provider_name)
    except ProviderError as error:
        logger.warning(f"Sentence tagger provider failed, falling back to plain text: {error.message}")
        return sentence
    except Exception as error:  # pragma: no cover - defensive, must never break the main turn
        logger.warning(f"Sentence tagger raised unexpected error, falling back to plain text: {error}")
        return sentence

    tagged = result.content.strip()
    if not tagged:
        logger.warning("Sentence tagger returned empty content, falling back to plain text.")
        return sentence
    if not _preserves_original_wording(stripped, tagged):
        logger.warning("Sentence tagger altered the wording (not just tags), falling back to plain text.")
        return sentence
    return _strip_dangling_trailing_tags(tagged)
