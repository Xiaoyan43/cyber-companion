from __future__ import annotations

from loguru import logger

from backend.app.memory.database import MoodStateRecord
from backend.app.providers.cost import estimate_token_count
from backend.app.providers.exceptions import ProviderError
from backend.app.providers.router import ProviderRouter
from backend.app.providers.types import ChatCompletionRequest, ChatMessage

DEFAULT_TAGGER_PROVIDER = "deepseek"

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
    "5. 不要把多个标签背靠背连续堆叠、中间不留任何文字——标签的影响范围是\"到下一个标签为止\"，"
    "背靠背堆叠会让前面的标签完全没有文字可以作用，等于白写。一个放对位置的标签就够，效果不够才加更多。\n"
    "6. 只能从下面词表中逐字选用标签，不允许自创新词、不允许写描述性短语或组合句（例如不允许写"
    "\"[slight annoyance mixed with vulnerability]\"这种自创组合），也不允许在词后加程度修饰"
    "（不要写\"[very sad]\"，词表里没有对应强度就换词表里语义最接近的词）。\n"
    "7. 标签必须用英文方括号写。\n"
    "\n"
    "可用标签（严格限定于以下列表，不可超出）：\n"
    "基础情绪：[happy] [sad] [angry] [excited] [calm] [nervous] [confident] [surprised] "
    "[satisfied] [delighted] [scared] [worried] [upset] [frustrated] [depressed] [empathetic] "
    "[embarrassed] [disgusted] [moved] [proud] [relaxed] [grateful] [curious] [sarcastic]\n"
    "进阶情绪：[disdainful] [unhappy] [anxious] [hysterical] [indifferent] [uncertain] [doubtful] "
    "[confused] [disappointed] [regretful] [guilty] [ashamed] [jealous] [envious] [hopeful] "
    "[optimistic] [pessimistic] [nostalgic] [lonely] [bored] [contemptuous] [sympathetic] "
    "[compassionate] [determined] [resigned]\n"
    "音调/语气：[in a hurry tone] [shouting] [screaming] [whispering] [soft tone]\n"
    "音效标签（触发真实声音事件，必须紧贴发生点）：[laughing] [chuckling] [sobbing] "
    "[crying loudly] [sighing] [groaning] [panting] [gasping] [yawning] [snoring]\n"
    "节奏（停顿，非声音事件）：[break] [long-break]\n"
    "\n"
    "下面给出这句话此刻的情绪状态作为参考背景——这是基线情绪，不是要照搬的标签来源，"
    "每句话具体配什么标签仍然要看这句话实际在说什么、怎么说：\n"
    "{mood_block}\n"
    "\n"
    "只输出插好标签后的完整文本，不加任何解释、不加引号、不加多余的话。"
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
    return tagged
