from __future__ import annotations

from loguru import logger

from backend.app.providers.cost import estimate_token_count
from backend.app.providers.exceptions import ProviderError
from backend.app.providers.router import ProviderRouter
from backend.app.providers.types import ChatCompletionRequest, ChatMessage

DEFAULT_TRANSLATOR_PROVIDER = "gemini"

# P11: a dedicated single-purpose call that only translates an already-finalized reply
# into Chinese — mirrors expression_tagger.py's decoupling pattern so the main LLM never
# has to carry a second task in the same generation.
TRANSLATOR_INSTRUCTION = (
    "你的唯一任务：把下面这段文本翻译成中文，不做任何其他事。\n"
    "硬性规则：\n"
    "1. 只翻译，不解读、不评论、不补充、不删减。\n"
    "2. 保留原文的语气和情绪色彩，不要翻译得比原文更正式或更随意。\n"
    "3. 只输出翻译结果，不加引号、不加任何解释或前后缀。"
)


def translate_to_chinese(
    text: str,
    *,
    router: ProviderRouter,
    provider_name: str = DEFAULT_TRANSLATOR_PROVIDER,
) -> str | None:
    """Translate already-finalized reply text into Chinese via a dedicated LLM call.

    Hard requirement: any failure degrades to None — the translator must never break
    or delay the main conversation turn; the caller falls back to showing only the
    original-language reply.
    """
    stripped = text.strip()
    if not stripped:
        return None

    request = ChatCompletionRequest(
        messages=[
            ChatMessage(role="system", content=TRANSLATOR_INSTRUCTION),
            ChatMessage(role="user", content=stripped),
        ],
        max_output_tokens=estimate_token_count(stripped) + 128,
    )

    try:
        result = router.complete(request, provider_name=provider_name)
    except ProviderError as error:
        logger.warning(f"Translator provider failed, skipping translation: {error.message}")
        return None
    except Exception as error:  # pragma: no cover - defensive, must never break the main turn
        logger.warning(f"Translator raised unexpected error, skipping translation: {error}")
        return None

    translated = result.content.strip()
    if not translated:
        logger.warning("Translator returned empty content, skipping translation.")
        return None
    return translated
