from __future__ import annotations

from backend.app.providers.venice import VeniceProvider


class OpenRouterProvider(VeniceProvider):
    name = "openrouter"

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        api_key_env: str = "OPENROUTER_API_KEY",
        enabled: bool = True,
        **kwargs: object,
    ) -> None:
        super().__init__(
            model=model,
            base_url=base_url,
            api_key_env=api_key_env,
            enabled=enabled,
            **kwargs,
        )

    def _extra_payload_params(self) -> dict[str, object]:
        return {"provider": {"allow_fallbacks": False}}
