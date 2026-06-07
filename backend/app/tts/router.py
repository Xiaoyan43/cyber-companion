from __future__ import annotations

from backend.app.memory.budget import BudgetConfig, load_budget_config
from backend.app.tts.base import TextToSpeechProvider
from backend.app.tts.config import TTSConfig, load_tts_config
from backend.app.tts.exceptions import TTSConfigError, TTSDisabledError, TTSError
from backend.app.tts.policy import evaluate_speech_policy
from backend.app.tts.registry import build_tts_providers
from backend.app.tts.types import (
    SpeechPolicyDecision,
    SynthesisRequest,
    SynthesisResult,
    TTSProviderStatus,
)


class TTSRouter:
    def __init__(
        self,
        config: TTSConfig,
        providers: dict[str, TextToSpeechProvider],
        budget: BudgetConfig,
    ) -> None:
        self.config = config
        self.providers = providers
        self.budget = budget

    @classmethod
    def from_config(
        cls,
        config: TTSConfig | None = None,
        budget: BudgetConfig | None = None,
    ) -> "TTSRouter":
        loaded = config or load_tts_config()
        return cls(loaded, build_tts_providers(loaded), budget or load_budget_config())

    def is_enabled(self) -> bool:
        return self.config.enabled

    def evaluate_policy(
        self,
        text: str,
        *,
        decision: str | None = None,
        avatar_state: str | None = None,
        force: bool = False,
    ) -> SpeechPolicyDecision:
        return evaluate_speech_policy(
            text,
            decision=decision,
            avatar_state=avatar_state,
            max_speech_chars=self.config.max_speech_chars,
            speak_decisions=self.config.speak_decisions,
            force=force,
        )

    def resolve_provider_name(self, requested: str | None = None) -> str:
        if not self.config.enabled:
            raise TTSDisabledError()

        if self.config.force_mock:
            return "mock"

        provider_name = requested or self.config.default_provider
        if provider_name not in self.providers:
            raise TTSConfigError(f"Unknown TTS provider: {provider_name}")

        return provider_name

    def get_provider(self, requested: str | None = None) -> TextToSpeechProvider:
        provider_name = self.resolve_provider_name(requested)
        provider = self.providers[provider_name]

        if provider.cloud and not self.budget.allow_cloud_tts:
            raise TTSDisabledError("Cloud TTS is disabled by budget config.")

        if provider.cloud and not provider.is_configured():
            raise TTSConfigError(
                f"Cloud TTS provider `{provider_name}` is not configured."
            )

        return provider

    def list_status(self) -> list[TTSProviderStatus]:
        return [provider.status() for provider in self.providers.values()]

    def synthesize(
        self,
        request: SynthesisRequest,
        *,
        provider_name: str | None = None,
    ) -> tuple[SpeechPolicyDecision, SynthesisResult | None]:
        if not request.text.strip():
            raise TTSError("Text payload is empty.", status_code=400)

        policy = self.evaluate_policy(
            request.text,
            decision=request.decision,
            avatar_state=request.avatar_state,
            force=request.force,
        )
        if not policy.should_speak:
            return policy, None

        provider = self.get_provider(provider_name)
        result = provider.synthesize(request)
        return policy, result


_router: TTSRouter | None = None


def get_tts_router() -> TTSRouter:
    global _router
    if _router is None:
        _router = TTSRouter.from_config()
    return _router


def reset_tts_router() -> None:
    global _router
    _router = None
