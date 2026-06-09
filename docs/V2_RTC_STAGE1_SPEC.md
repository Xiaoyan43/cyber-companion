# Spec — V2 RTC Stage 1: Soul as an OpenAI-compatible LLM endpoint

Part of the RTC + OutputMode-1 (hybrid) work. **Claude spec → Cursor builds → Claude review
→ checkpoint.** Backend-only, reuses the soul; **no RTC yet** (Stage 2). Independently
testable with `curl`. Needs no new credentials.

## Why
Volcengine's AIGC-RTC server (OutputMode 1) orchestrates ASR → **a custom LLM** → TTS. To
keep Boxi's soul as the brain, the "custom LLM" must be **our** endpoint, **OpenAI-compatible**
(`POST /v1/chat/completions`, streaming). This wraps the existing `CompanionBrain` so the soul
(compact memory context + DeepSeek + persona + behavior + signal-strip + memory write) runs
inside RTC's pipeline. This endpoint is the linchpin of OutputMode-1-over-RTC.

## Goal
A small streaming **OpenAI-compatible** HTTP server that the AIGC-RTC server can call as its
LLM, backed by `CompanionBrain`. Spoken text streams out as OpenAI-format deltas; memory/
kernel writes happen off the response path.

## Tasks
1. **`backend/realtime/soul_llm_server.py`** — a dedicated FastAPI app (separate from V1
   `backend/app/main.py`; reuses the soul):
   - `POST /v1/chat/completions` accepting the OpenAI schema (`model`, `messages`, `stream`).
   - Take the **latest user message** from `messages[]` as the utterance. (The AIGC server
     manages turn history; we build our *own* compact context from the soul, so we mostly
     ignore the inbound history except the latest user turn — confirm against the AIGC custom-
     LLM contract in Stage 2; for Stage 1, latest-user-message is the input.)
   - Drive `CompanionBrain.stream_turn(user_text)` (already does context → DeepSeek stream →
     `SignalStreamFilter` trailer-strip → off-path `remember`). Emit **only the clean spoken
     text** as OpenAI SSE deltas: `data: {"choices":[{"delta":{"content": "<chunk>"}}]}` …
     terminating with `data: [DONE]`. Non-streaming mode: return one assembled message.
   - Map the brain's decision: `silent` → empty/he minimal reply; `reply/interrupt` → the
     streamed text. Keep the signals trailer **out** of the response (already stripped).
   - Off-path memory/kernel via the brain's existing `remember()` (don't block the stream).
2. **Auth (simple):** a shared bearer token from env `SOUL_LLM_API_KEY` (the AIGC server will
   send it as the LLM API key). If unset, accept localhost only. No secrets in code.
3. **Run target:** a `__main__` / uvicorn entry (e.g. `python -m backend.realtime.soul_llm_server`,
   configurable host/port via env). Document in `backend/realtime/README.md`.
4. **Tests** (`backend/tests/test_soul_llm_server.py`, `importorskip` if needed): with the
   **mock** provider, `POST /v1/chat/completions` (stream + non-stream) returns OpenAI-shaped
   output with clean text (no `<<<BOXI_SIGNALS>>>`); a memory row is written. Keep the V1 gate
   green.

## Done criteria
1. `PYTHON_BIN=.venv/bin/python npm run check` green; V1 untouched; new tests pass.
2. `curl` the endpoint OpenAI-style (stream + non-stream) → clean Boxi reply, trailer stripped,
   memory written off-path. (Mock provider for the gate; real DeepSeek for a manual smoke.)
3. Diff confined to `backend/realtime/**`, `backend/tests/test_soul_llm_server.py`,
   `docs/SESSION_LOG.md`, `docs/TODO.md`. **No `backend/app/**`** (soul reused, not edited)
   **or `frontend/**`**.

## Boundaries
- Reuse `CompanionBrain` exactly; do not edit `backend/app/**`. The server is a thin
  OpenAI-compatible shim around the brain.
- Keep V1 + the Pipecat S2S paths working untouched.
- Keys env-only. The exact AIGC custom-LLM request/response contract is verified in **Stage 2**
  against the official docs (6348/1558163) — Stage 1 targets the standard OpenAI shape, which
  is what AIGC custom-LLM expects.
- Stage 2 note (not now): Volcengine's **cloud** AIGC server must reach this endpoint → it needs
  a public URL (tunnel) in local dev; and `StartVoiceChat` needs account **AK/SK**.
