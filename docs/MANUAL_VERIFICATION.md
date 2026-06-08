# Manual Verification Checklist

Use this after UI-facing changes, especially Phase 2 pixel character work.

## Setup

```bash
npm install
PYTHON_BIN=.venv/bin/python npm run check
npm run dev
```

Open `http://127.0.0.1:5173/` in a desktop browser. Repeat key checks at a 390px-wide viewport.

Dev servers bind to localhost only (`127.0.0.1`). Do not expose Vite or Uvicorn on `0.0.0.0` without reviewing `docs/SECURITY_AND_PERMISSIONS.md`.

If Vite falls back to another local port (for example `5174`), the backend already allows `5173` and `5174` on `127.0.0.1` / `localhost`. For any other dev origin, set `CYBER_COMPANION_CORS_ORIGINS` to a comma-separated explicit list (no wildcards), then restart the API.

## Companion Panel

- [ ] Default state is `idle` with trapped-in-box motion, not a static pose.
- [ ] Status line updates when avatar state changes.
- [ ] In dev mode, avatar debug buttons appear; in production build they stay hidden unless `VITE_SHOW_AVATAR_DEBUG=1`.

## Chat Flow

- [ ] Sending a normal message appends the user bubble immediately.
- [ ] Avatar goes `thinking`, then `talking` when Boxi replies, then returns to `idle`.
- [ ] Sending an empty message briefly shows backend-driven `silent`/`annoyed` behavior, then returns to `idle`.
- [ ] Message list scrolls to the latest message after send.
- [ ] With `CYBER_COMPANION_PROVIDER_MODE=mock`, `/chat/complete` returns a mock Boxi reply through the local API.
- [ ] Frontend chat no longer uses hardcoded shell text when the backend is reachable.
- [ ] Refreshing the page reloads stored chat history from `/memory/messages`.
- [ ] Last-turn token/cost metadata appears after a successful chat turn.
- [ ] Stored assistant messages show provider/token/cost metadata when reloaded.

## Memory

- [ ] First backend startup creates `data/cyber_companion.db` locally.
- [ ] `POST /chat/complete` persists the user turn and assistant reply into SQLite.
- [ ] `GET /memory/messages` returns stored chat messages.
- [ ] `POST /memory/memories` and `GET /memory/memories` work for supported memory types.
- [ ] `GET /memory/mood` returns the default mood row; `PUT /memory/mood` updates it.

## Context Assembly

- [ ] `GET /memory/context/preview?user_input=...` shows compact context, not full transcript.
- [ ] `/chat/complete` ignores extra client history and only uses stored recent turns plus current input.
- [ ] Job/resume related input can surface `job_progress` memories in preview metadata.

## Behavior

- [ ] Empty or low-value input can return local `silent` / `mutter` without provider calls.
- [ ] Refusal patterns return local `refuse` lines and `angry` avatar state.
- [ ] Long rambling input triggers `interrupt` and still allows provider reply when configured.
- [ ] Stale `job_progress` memory plus casual input can trigger local `proactive` nudges.
- [ ] After ~2 minutes idle with API online, proactive tick may nudge stale job progress (no LLM).
- [ ] After extended idle, avatar may briefly show `sleepy` or deliver a local `mutter` line (no LLM).
- [ ] Tick-initiated `mutter` / `proactive` lines persist to SQLite and survive page refresh.
- [ ] `/chat/complete` response includes `avatar_state`, `decision`, and `should_call_llm`.

## Layout

- [ ] No horizontal overflow at 390px width.
- [ ] Chat input and send button remain usable on narrow screens.
- [ ] API status badge still renders; offline is acceptable when backend is not running.

## Voice

- [ ] With STT enabled in config, the chat form shows a hold-to-talk button.
- [ ] Holding the mic button shows a visible recording state; releasing stops capture.
- [ ] Mock STT returns transcribed text and the result enters the normal chat path.
- [ ] Setting `enabled: false` in `config/stt.json` hides push-to-talk UI.
- [ ] Cloud STT remains blocked unless `allow_cloud_stt` is true in budget config.

## TTS

- [ ] With TTS enabled in config, the chat header shows a mute/unmute toggle.
- [ ] Short replies (`decision=reply`, under `max_speech_chars`) can trigger mock TTS playback.
- [ ] Long replies are skipped by selective policy and stay text-only.
- [ ] `silent` / `mutter` / `observe` decisions do not trigger speech.
- [ ] Avatar stays in `talking` while TTS audio plays, then returns to `idle`.
- [ ] TTS mute preference persists in local storage across refresh.
- [ ] Cloud TTS remains blocked unless `allow_cloud_tts` is true in budget config.

## Automated Checks

```bash
PYTHON_BIN=.venv/bin/python npm run check
npm run build:frontend
```

With the local API on `18000` and frontend on `5173`, browser smoke can be run as:

```bash
CYBER_VERIFY_API_URL=http://127.0.0.1:18000 node scripts/ui_verify.mjs
```

Latest verified state: **36/36 passed** (Session 18), including delayed TTS synthesis, refuse synthesize handoff, and overlapping chat-round avatar regression checks.
