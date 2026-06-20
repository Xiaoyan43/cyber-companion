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
    "同样的 mood 下不同的句子应该有不同的标签选择。\n"
    "4. 两类标签精度要求不同：\n"
    "   - 音效/生理反应类（如 [sigh] [gasp] [laughing] [sobbing] [clears throat]）会让模型真的"
    "发出这个声音，必须紧贴它实际发生的那个词，位置错了就是一声突兀的怪声。\n"
    "   - 语气/情绪/节奏类（如 [whispering] [angry] [pause]）只改变接下来怎么说，位置容错更高。\n"
    "5. 不要堆叠太多标签——一个放对位置的标签就能改变整句感觉，效果不够才加更多；"
    "生理反应类标签可以配一个情绪标签一起用增加真实感（如 [panting] [tired]）。\n"
    "6. 标签必须用英文方括号写。\n"
    "7. 情绪强度可以用程度词修饰，不必只用基础词——如 [slightly sad] [very excited] "
    "[extremely worried]，强度应该匹配这句话实际的情绪烈度，不要每次都用最强的词。\n"
    "\n"
    "可用标签（S2-Pro 支持自由文本描述，以下是效果稳定的种子词表，情绪类可在语义合理范围内自行扩展）：\n"
    "呼吸/生理反应：[sigh] [inhale] [exhale] [gasp] [panting] [clears throat] [breathing]\n"
    "嗓音/发声：[laughing] [chuckling] [giggle] [sobbing] [crying] [groan] [moaning]\n"
    "节奏：[pause] [short pause] [long pause]\n"
    "音色风格：[whispering] [soft voice] [low voice] [loud voice] [shouting]\n"
    "情绪（基础）：[excited] [angry] [sad] [happy] [calm] [disdainful] [sarcastic] [nostalgic] "
    "[anxious] [lonely] [worried] [determined]\n"
    "情绪（扩展，同样有效，可按需选用或自行扩展类似的自然描述）：[surprised] [delighted] [satisfied] "
    "[disappointed] [embarrassed] [proud] [grateful] [curious] [confused] [guilty] [hopeful] "
    "[bored] [sympathetic] [compassionate] [resigned] [indifferent]\n"
    "其他：[emphasis]（重读紧跟其后的词）\n"
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
