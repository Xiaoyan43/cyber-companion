from __future__ import annotations

import json
import os
from collections.abc import Iterator

import httpx

from backend.app.providers.base import ChatProvider
from backend.app.providers.cost import estimate_cost, estimate_usage
from backend.app.providers.exceptions import ProviderNotConfiguredError, ProviderRequestError
from backend.app.providers.types import (
    ChatCompletionRequest,
    ChatCompletionResult,
    ProviderStatus,
    StreamChunk,
    TokenUsage,
)

DEFAULT_TIMEOUT_S = 30.0


class VeniceProvider(ChatProvider):
    name = "venice"

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "https://api.venice.ai/api/v1",
        api_key_env: str = "VENICE_API_KEY",
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

    def _client(self) -> httpx.Client:
        if self._http_client is not None:
            return self._http_client
        try:
            return httpx.Client(timeout=self._timeout_s, http2=True)
        except ImportError:
            return httpx.Client(timeout=self._timeout_s)

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
                "Venice provider is disabled in config.",
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
            response = self._client().post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.HTTPError as error:
            raise ProviderRequestError(
                f"Venice request failed: {error}",
                provider=self.name,
            ) from error

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise ProviderRequestError(
                f"Venice returned HTTP {response.status_code}: {detail}",
                provider=self.name,
            )

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderRequestError(
                "Venice response did not include assistant content.",
                provider=self.name,
            ) from error

        usage_payload = data.get("usage") or {}
        if usage_payload:
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

    def complete_stream(self, request: ChatCompletionRequest) -> Iterator[StreamChunk]:
        if not self._enabled:
            raise ProviderNotConfiguredError(
                "Venice provider is disabled in config.",
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
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        try:
            with self._client().stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    detail = response.read().decode("utf-8", errors="replace").strip() or response.reason_phrase
                    raise ProviderRequestError(
                        f"Venice returned HTTP {response.status_code}: {detail}",
                        provider=self.name,
                    )

                accumulated: list[str] = []
                usage: TokenUsage | None = None

                for raw_line in response.iter_lines():
                    if not raw_line.startswith("data:"):
                        continue

                    data_str = raw_line[len("data:"):].strip()
                    if not data_str or data_str == "[DONE]":
                        continue

                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError as error:
                        raise ProviderRequestError(
                            "Venice stream returned invalid JSON chunk.",
                            provider=self.name,
                        ) from error

                    choices = chunk.get("choices") or []
                    if choices:
                        delta = choices[0].get("delta") or {}
                        text_content = delta.get("content")
                        if text_content:
                            text = str(text_content)
                            accumulated.append(text)
                            yield ("delta", text)

                    usage_payload = chunk.get("usage")
                    if usage_payload:
                        usage = TokenUsage(
                            input_tokens=int(usage_payload.get("prompt_tokens", 0)),
                            output_tokens=int(usage_payload.get("completion_tokens", 0)),
                            total_tokens=int(usage_payload.get("total_tokens", 0)),
                        )
        except httpx.HTTPError as error:
            raise ProviderRequestError(
                f"Venice request failed: {error}",
                provider=self.name,
            ) from error

        if usage is None:
            full_text = "".join(accumulated)
            usage = estimate_usage([message.content for message in request.messages], full_text)

        yield ("usage", usage)
