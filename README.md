# Cyber Companion

Low-cost AI desktop companion prototype.

The MVP is a desktop software prototype before hardware integration. It presents a pixel-style character that feels like a small person trapped inside a box, with chat, configurable LLM providers, local long-term memory, personality, and eventually voice.

## Current Direction

- Personality: `毒舌被困小人 + low-dose companionship`
- First platform: local desktop/web prototype
- Default provider: DeepSeek
- Optional providers: OpenAI, local models
- Memory: SQLite plus JSON configuration
- Voice: staged after text MVP
- Filesystem access: explicit sandbox folders only

## Start Here

Read these files in order:

1. `docs/PROJECT_BRIEF.md`
2. `docs/ARCHITECTURE.md`
3. `docs/MVP_ROADMAP.md`
4. `docs/SESSION_PROTOCOL.md`
5. `docs/TODO.md`
6. `docs/SESSION_LOG.md`
7. `docs/OPEN_SOURCE_REUSE.md`

When opening a new AI coding session, the user can say `推进`. The agent should then read the files above and continue from the next unfinished task.

## Development Setup

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
npm run dev:backend
```

Frontend:

```bash
npm install
npm run dev:frontend
```

Run lightweight checks:

```bash
npm run check
```

Check a running backend:

```bash
npm run health
```

Local endpoints:

- Frontend: `http://127.0.0.1:5173`
- Backend health check: `http://127.0.0.1:8000/health`
