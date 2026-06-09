"""OpenAI-compatible streaming LLM shim for AIGC-RTC OutputMode 1 (V2 RTC Stage 1).

Wraps ``CompanionBrain`` so Volcengine's custom-LLM slot can call our soul without
touching ``backend/app/main.py``.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from backend.app.behavior.parser import SIGNALS_SENTINEL
from backend.app.memory.store import get_memory_store
from backend.realtime.companion_brain import CompanionBrain, VoiceTurnOutcome
from backend.realtime.voice_config import load_voice_max_tokens

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8100
DEFAULT_MODEL = "boxi-soul"
LOCALHOST_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})


class ChatMessagePayload(BaseModel):
    role: str
    content: str | list[dict[str, Any]] | None = None


class ChatCompletionRequestPayload(BaseModel):
    model: str = DEFAULT_MODEL
    messages: list[ChatMessagePayload] = Field(default_factory=list)
    stream: bool = False


def _env_str(name: str, default: str) -> str:
    raw = os.getenv(name, "").strip()
    return raw or default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return int(raw)


def load_soul_llm_api_key() -> str:
    return os.getenv("SOUL_LLM_API_KEY", "").strip()


def load_soul_llm_host() -> str:
    return _env_str("SOUL_LLM_HOST", DEFAULT_HOST)


def load_soul_llm_port() -> int:
    return _env_int("SOUL_LLM_PORT", DEFAULT_PORT)


def extract_latest_user_text(messages: list[ChatMessagePayload]) -> str:
    for message in reversed(messages):
        if message.role != "user":
            continue
        content = message.content
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(str(part.get("text", "")))
            return "".join(parts)
    return ""


def _is_localhost_client(request: Request) -> bool:
    client = request.client
    if client is None:
        return False
    return client.host in LOCALHOST_HOSTS


def verify_soul_llm_auth(request: Request) -> None:
    api_key = load_soul_llm_api_key()
    if api_key:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {api_key}":
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        return
    if not _is_localhost_client(request):
        raise HTTPException(
            status_code=403,
            detail="SOUL_LLM_API_KEY unset — localhost requests only",
        )


def _new_completion_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex[:24]}"


def _usage_payload(outcome: VoiceTurnOutcome | None) -> dict[str, int] | None:
    if outcome is None or outcome.result.usage is None:
        return None
    usage = outcome.result.usage
    return {
        "prompt_tokens": usage.input_tokens,
        "completion_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
    }


def _openai_stream_chunk(
    *,
    chunk_id: str,
    created: int,
    model: str,
    content: str | None = None,
    finish_reason: Literal["stop"] | None = None,
) -> str:
    delta: dict[str, str] = {}
    if content:
        delta["content"] = content
    payload = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            },
        ],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _remember_off_path(brain: CompanionBrain, outcome: VoiceTurnOutcome) -> None:
    await asyncio.to_thread(brain.remember, outcome)


async def _stream_openai_completion(
    brain: CompanionBrain,
    user_text: str,
    *,
    model: str,
) -> AsyncIterator[str]:
    chunk_id = _new_completion_id()
    created = int(time.time())
    outcome: VoiceTurnOutcome | None = None

    async for event_kind, event_value in brain.stream_turn(user_text):
        if event_kind == "delta":
            if event_value:
                yield _openai_stream_chunk(
                    chunk_id=chunk_id,
                    created=created,
                    model=model,
                    content=event_value,
                )
        else:
            outcome = event_value

    yield _openai_stream_chunk(
        chunk_id=chunk_id,
        created=created,
        model=model,
        finish_reason="stop",
    )
    yield "data: [DONE]\n\n"

    if outcome is not None:
        asyncio.create_task(_remember_off_path(brain, outcome))


def create_app() -> FastAPI:
    app = FastAPI(title="Boxi Soul LLM", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "soul-llm"}

    @app.post("/v1/chat/completions", response_model=None)
    async def chat_completions(
        payload: ChatCompletionRequestPayload,
        _: None = Depends(verify_soul_llm_auth),
    ) -> StreamingResponse | JSONResponse:
        user_text = extract_latest_user_text(payload.messages)
        store = get_memory_store()
        brain = CompanionBrain(store, max_output_tokens=load_voice_max_tokens())
        model = payload.model or DEFAULT_MODEL

        if payload.stream:
            return StreamingResponse(
                _stream_openai_completion(brain, user_text, model=model),
                media_type="text/event-stream",
            )

        spoken_parts: list[str] = []
        outcome: VoiceTurnOutcome | None = None
        async for event_kind, event_value in brain.stream_turn(user_text):
            if event_kind == "delta":
                spoken_parts.append(event_value)
            else:
                outcome = event_value

        content = "".join(spoken_parts)
        if outcome is not None:
            asyncio.create_task(_remember_off_path(brain, outcome))

        response_body: dict[str, Any] = {
            "id": _new_completion_id(),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                },
            ],
        }
        usage = _usage_payload(outcome)
        if usage is not None:
            response_body["usage"] = usage
        return JSONResponse(response_body)

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "backend.realtime.soul_llm_server:app",
        host=load_soul_llm_host(),
        port=load_soul_llm_port(),
        log_level=os.getenv("SOUL_LLM_LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
