from __future__ import annotations

import os

import httpx

from backend.app.providers.base import ChatProvider
from backend.app.providers.cost import estimate_cost, estimate_usage
from backend.app.providers.exceptions import ProviderNotConfiguredError, ProviderRequestError
from backend.app.providers.types import (
    ChatCompletionRequest,
    ChatCompletionResult,
    ProviderStatus,
)


class DeepSeekProvider(ChatProvider):
    name = "deepseek"

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key_env: str,
        enabled: bool = True,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._api_key_env = api_key_env
        self._enabled = enabled

    @property
    def api_key(self) -> str | None:
        value = os.getenv(self._api_key_env, "").strip()
        return value or None

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            enabled=self._enabled,
            model=self._model,
            configured=True,
            api_key_present=self.api_key is not None,
            placeholder=False,
        )

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        if not self._enabled:
            raise ProviderNotConfiguredError(
                "DeepSeek provider is disabled in config.",
                provider=self.name,
            )

        api_key = self.api_key
        if not api_key:
            raise ProviderNotConfiguredError(
                f"Missing API key env var: {self._api_key_env}",
                provider=self.name,
            )

        payload = {
            "model": self._model,
            "messages": [{"role": message.role, "content": message.content} for message in request.messages],
            "max_tokens": request.max_output_tokens,
            "stream": False,
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as error:
            raise ProviderRequestError(
                f"DeepSeek request failed: {error}",
                provider=self.name,
            ) from error

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise ProviderRequestError(
                f"DeepSeek returned HTTP {response.status_code}: {detail}",
                provider=self.name,
            )

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderRequestError(
                "DeepSeek response did not include assistant content.",
                provider=self.name,
            ) from error

        usage_payload = data.get("usage") or {}
        if usage_payload:
            from backend.app.providers.types import TokenUsage

            usage = TokenUsage(
                input_tokens=int(usage_payload.get("prompt_tokens", 0)),
                output_tokens=int(usage_payload.get("completion_tokens", 0)),
                total_tokens=int(usage_payload.get("total_tokens", 0)),
            )
        else:
            usage = estimate_usage([message.content for message in request.messages], content)

        cost = estimate_cost(self._model, usage)
        return ChatCompletionResult(
            provider=self.name,
            model=self._model,
            content=str(content),
            usage=usage,
            cost=cost,
            mock=False,
        )
