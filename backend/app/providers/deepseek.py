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

DEFAULT_TIMEOUT_S = 30.0

_shared_http_client: httpx.Client | None = None
_shared_http_client_timeout: float | None = None


def _create_http_client(timeout_s: float) -> httpx.Client:
    try:
        return httpx.Client(timeout=timeout_s, http2=True)
    except ImportError:
        return httpx.Client(timeout=timeout_s)


def get_shared_http_client(timeout_s: float = DEFAULT_TIMEOUT_S) -> httpx.Client:
    global _shared_http_client, _shared_http_client_timeout
    _install_reset_provider_router_hook()
    if _shared_http_client is None or _shared_http_client_timeout != timeout_s:
        close_deepseek_http_client()
        _shared_http_client = _create_http_client(timeout_s)
        _shared_http_client_timeout = timeout_s
    return _shared_http_client


def close_deepseek_http_client() -> None:
    global _shared_http_client, _shared_http_client_timeout
    if _shared_http_client is not None:
        _shared_http_client.close()
        _shared_http_client = None
        _shared_http_client_timeout = None


def _install_reset_provider_router_hook() -> None:
    import sys

    router_mod = sys.modules.get("backend.app.providers.router")
    if router_mod is None:
        return

    original_reset = getattr(router_mod, "reset_provider_router", None)
    if original_reset is None or getattr(original_reset, "_closes_deepseek_http_client", False):
        return

    def reset_provider_router() -> None:
        close_deepseek_http_client()
        original_reset()

    reset_provider_router._closes_deepseek_http_client = True  # type: ignore[attr-defined]
    router_mod.reset_provider_router = reset_provider_router


class DeepSeekProvider(ChatProvider):
    name = "deepseek"

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key_env: str,
        enabled: bool = True,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._api_key_env = api_key_env
        self._enabled = enabled
        self._timeout_s = timeout_s
        self._http_client = http_client

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

        client = (
            self._http_client
            if self._http_client is not None
            else get_shared_http_client(self._timeout_s)
        )

        try:
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
