# Cyber Companion · 赛博伴侣

> A low-cost AI desktop companion — *a small person trapped in a box* — that remembers you,
> has moods, lets a relationship with you evolve, and reaches out to you on her own.

Most AI "companions" are a pretty shell over a stateless chatbot. This is the opposite: the
investment is in the **soul** — persistent memory, an emotional/relationship kernel, and
proactive behaviour — so it feels less like a tool you query and more like *someone who's there*.

Her name is **Boxi**. Default personality: `毒舌被困小人` — sharp-tongued and a little trapped,
but under the edge she actually cares.

<!-- ![Boxi screenshot](docs/assets/screenshot.png) -->
<!-- TODO: add a screenshot or short demo GIF of the chat UI / voice call here -->

## What makes it different — the "soul"

- **A subjectivity kernel.** Boxi has a private mood (annoyance, worry, loneliness, energy) and a
  *relationship state* with you that moves over time — trust, closeness, familiarity, tension. Her
  tone is a function of both.
- **Real long-term memory.** Typed memories in SQLite (profile, projects, reminders, events…),
  LLM-based extraction with a deterministic fallback, background reflection that consolidates and
  forms impressions, and cross-memory links — not "stuff the whole transcript into the prompt."
- **Proactive initiation.** She reaches out *on her own timeline* — a "longing" model
  (closeness × silence, stochastic Poisson timing), about a real reason (a due reminder, something
  you said you'd do, a memory worth recalling), in her own voice, with genuine restraint: quiet
  hours, daily caps, and an ignore-backoff so she never nags.
- **A behaviour engine, not a yes-man.** She can reply, stay silent, refuse, mutter, or interrupt —
  decided locally before any model call.
- **Voice.** A cascaded speech pipeline (streaming STT → the soul → streaming TTS) plus realtime
  explorations, with the soul authoring her words.

## Tech highlights

- **Stateful memory pipeline.** LLM-based memory extraction with a deterministic regex fallback,
  typed records (profile/project/reminder/event…) in SQLite, background reflection that
  consolidates raw memories into impressions, and cross-memory linking — plus an optional
  VikingDB-backed long-term store for cross-session recall in realtime voice.
- **Emotion/relationship kernel driving tone in real time.** A mood vector (annoyance, worry,
  loneliness, energy) and a relationship vector (trust, closeness, familiarity, tension) are
  projected into speaking style and TTS prosody (`context_texts` + `speech_rate`) on every turn —
  including the realtime voice path (RTC join-time `speaking_style`).
- **Proactive initiation model.** A "longing" score (closeness × silence) drives Poisson-timed
  outreach, gated by quiet hours, daily caps, and ignore-backoff, so she reaches out without
  nagging.
- **Local-first behaviour engine.** Reply/silence/refuse/mutter/interrupt decisions are made
  deterministically *before* any LLM call, keeping behaviour auditable and cheap.
- **Provider abstraction with mock mode.** DeepSeek (chat) and Doubao/Volcengine (voice) sit
  behind a swappable provider layer with budget gating, so the whole stack runs fully offline
  against mock providers for dev/testing.

## Architecture

- **Frontend:** React + TypeScript (Vite) — pixel-style character + chat.
- **Backend:** Python + FastAPI — provider abstraction, memory engine, behaviour engine,
  file-permission gateway.
- **Storage:** SQLite (memory) + JSON config (persona, providers, budgets, permissions).
- **Models:** DeepSeek (chat) and Doubao / Volcengine (voice) behind a provider layer; mock
  providers for offline dev.
- Secrets are environment-only; cloud calls are budget-gated; file access is sandboxed to explicit
  allowed folders.

## Status

A working **text + voice MVP** with the full soul stack (memory, kernel, behaviour, proactive
initiation, reflection). The visual direction (*"a being with a world"*) and the hardware form
(an old iPhone as the "box") are in exploration. This is a personal prototype — expect rough edges.

## Quickstart

Requires Python 3.11+, Node 18+, and a `DEEPSEEK_API_KEY` (or run fully offline in mock mode).

```bash
# backend env
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cp .env.example .env   # add DEEPSEEK_API_KEY, or set CYBER_COMPANION_PROVIDER_MODE=mock

# run
npm install
npm run dev:backend     # FastAPI on :8000
npm run dev:frontend    # Vite on :5173
npm run check           # typecheck + tests
```

Then open `http://127.0.0.1:5173`.

## Design record

The [`docs/`](docs/) folder is the full design history — architecture, memory design, and the
soul-deepening / proactive-initiation specs, plus a detailed session log. It also documents *how*
this was built: an AI pair-programming workflow (an implementer, a reviewer/architect, and a UI
agent) running a written spec → review → checkpoint loop.

## License

MIT © 2026 Chris Wang — see [LICENSE](LICENSE). Third-party components and their licenses are
tracked in [docs/OPEN_SOURCE_REUSE.md](docs/OPEN_SOURCE_REUSE.md).
