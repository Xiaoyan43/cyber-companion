from __future__ import annotations

from backend.app.memory.budget import BudgetConfig, load_budget_config
from backend.app.stt.base import SpeechToTextProvider
from backend.app.stt.config import STTConfig, load_stt_config
from backend.app.stt.exceptions import STTConfigError, STTDisabledError, STTError
from backend.app.stt.registry import build_stt_providers
from backend.app.stt.types import STTProviderStatus, TranscriptionRequest, TranscriptionResult


class STTRouter:
    def __init__(
        self,
        config: STTConfig,
        providers: dict[str, SpeechToTextProvider],
        budget: BudgetConfig,
    ) -> None:
        self.config = config
        self.providers = providers
        self.budget = budget

    @classmethod
    def from_config(
        cls,
        config: STTConfig | None = None,
        budget: BudgetConfig | None = None,
    ) -> "STTRouter":
        loaded = config or load_stt_config()
        return cls(loaded, build_stt_providers(loaded), budget or load_budget_config())

    def is_enabled(self) -> bool:
        return self.config.enabled

    def resolve_provider_name(self, requested: str | None = None) -> str:
        if not self.config.enabled:
            raise STTDisabledError()

        if self.config.force_mock:
            return "mock"

        provider_name = requested or self.config.default_provider
        if provider_name not in self.providers:
            raise STTConfigError(f"Unknown STT provider: {provider_name}")

        return provider_name

    def get_provider(self, requested: str | None = None) -> SpeechToTextProvider:
        provider_name = self.resolve_provider_name(requested)
        provider = self.providers[provider_name]

        if provider.cloud and not self.budget.allow_cloud_stt:
            raise STTDisabledError("Cloud STT is disabled by budget config.")

        if provider.cloud and not provider.is_configured():
            raise STTConfigError(
                f"Cloud STT provider `{provider_name}` is not configured."
            )

        return provider

    def list_status(self) -> list[STTProviderStatus]:
        return [provider.status() for provider in self.providers.values()]

    def transcribe(
        self,
        request: TranscriptionRequest,
        *,
        provider_name: str | None = None,
    ) -> TranscriptionResult:
        if not request.audio_bytes:
            raise STTError("Audio payload is empty.", status_code=400)

        provider = self.get_provider(provider_name)
        return provider.transcribe(request)


_router: STTRouter | None = None


def get_stt_router() -> STTRouter:
    global _router
    if _router is None:
        _router = STTRouter.from_config()
    return _router


def reset_stt_router() -> None:
    global _router
    _router = None
