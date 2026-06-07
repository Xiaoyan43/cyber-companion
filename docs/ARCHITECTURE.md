# Architecture

## High-Level Shape

```text
Pixel Companion UI
  - character renderer
  - state animation
  - chat panel
  - later voice controls
        |
Local App API
  - dialogue controller
  - behavior engine
  - memory engine
  - provider router
  - file access gateway
        |
Local Storage
  - SQLite memory database
  - JSON config files
        |
LLM Providers
  - DeepSeek
  - OpenAI
  - local model adapter
```

## Recommended Stack

MVP stack:

- Frontend: React + TypeScript.
- Renderer: Canvas or PixiJS for pixel character animation.
- Local API: FastAPI.
- Memory DB: SQLite.
- Config: JSON files.
- Desktop packaging later: Tauri after the web prototype is stable.

Do not start with hardware, microphone always-on processing, or desktop packaging. Build the local web prototype first.

## Core Modules

### UI

Owns:

- Pixel character rendering.
- Character states and animation frames.
- Chat input/output.
- Status indicators.
- Later: push-to-talk button and voice indicators.

Does not own:

- Memory decisions.
- Provider calls.
- Filesystem permissions.

### Dialogue Controller

Owns the full turn flow:

1. Receive event.
2. Ask behavior engine whether to reply, stay silent, refuse, interrupt, or act proactively.
3. Retrieve relevant memory.
4. Build compact LLM context.
5. Call provider if needed.
6. Parse structured response.
7. Persist messages, summaries, and memory writes.
8. Emit UI state.

### Behavior Engine

Local decision layer. It should not rely only on prompt wording.

Decision output:

```json
{
  "decision": "reply",
  "avatar_state": "thinking",
  "should_call_llm": true,
  "reason": "user_message_needs_response"
}
```

Supported decisions:

- `reply`
- `silent`
- `mutter`
- `refuse`
- `interrupt`
- `proactive`
- `observe`

### Memory Engine

Owns:

- Memory schema.
- Retrieval.
- Summaries.
- Memory writes.
- Importance and confidence.
- Expiration.

It must avoid sending full chat history by default.

### Provider Router

Owns:

- DeepSeek adapter.
- OpenAI adapter.
- Local model adapter.
- Provider config.
- Token/cost estimation.
- Retry behavior.

Provider interface should be stable before implementing multiple providers.

### File Access Gateway

Owns all local file access.

Rules:

- Only configured allowed folders.
- Resolve real paths.
- Reject path traversal.
- Reject symlink escape.
- Log access.
- No direct shell access from the companion.

## Event Loop

The companion should feel always alive, but should not always call cloud services.

```text
app_tick
idle_tick
user_message
voice_detected
reminder_due
mood_tick
project_stale
job_search_stale
provider_error
network_error
```

Most idle and life events should be handled locally. Call the LLM only when natural language generation or deeper reasoning is needed.

