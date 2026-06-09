# Spec — V2 Phase 0: Foundation for the rebuild

Source of truth: `docs/ARCHITECTURE_V2.md` + `docs/REBUILD_ROADMAP.md` (Phase 0).
**Claude spec → Cursor builds → Claude reviews → checkpoint.** Lowest-risk first slice:
carve the brain/surface seam and **declare** the V2 deps **without touching V1**.

## Goal (one sentence)
Establish the brain/surface boundary in the repo + adopt the V2 stack on paper, so
Phase 1 (Pipecat voice skeleton) has a clean seam to build into — **while the V1 app
still runs and its gate stays green.**

## Non-goals (explicit — keep Phase 0 tiny)
- **No Pipecat pipeline code.** No VAD/STT/TTS wiring. That's Phase 1.
- **No heavy install.** Do NOT `pip install` pipecat/torch in this slice; only declare it.
- **No PixiJS install.** Only record the decision; install lands in Phase 5.
- **No change to soul behavior or V1 entrypoints** (`backend/app/main.py`, `frontend/`,
  any `backend/app/{memory,behavior,providers,files,reflection}` logic).

## Task 1 — Brain package skeleton (`backend/realtime/`)
New package = the future Pipecat "brain" voice loop. It **reuses the soul, never forks it.**
- `backend/realtime/__init__.py`.
- `backend/realtime/companion_brain.py`: a documented skeleton that *imports* the soul
  seam and exposes ONE class `CompanionBrain` with stub methods Phase 1 will fill —
  signatures only, each `raise NotImplementedError("V2 Phase 1")`, but the imports must
  resolve so the seam is proven:
  - imports: `build_provider_context` (`backend.app.memory.context_builder`),
    `evaluate_behavior` (the behavior engine entry in `backend.app.behavior.engine`),
    the provider router (`backend.app.providers.router.get_provider_router`),
    `record_turn_memories` (`backend.app.memory.write_policy`),
    `load_persona_system_prompt` (`backend.app.memory.persona`).
  - methods (stubs, typed): `decide(user_text) -> behavior decision`,
    `respond(user_text) -> (reply_text, avatar_state, signals)`,
    `remember(user_text, signals) -> None`. Docstrings point to the Phase 1 spec.
  - **Confirm exact soul entry-point names by reading the modules first** (e.g. the
    behavior engine's public function may not be literally `evaluate_behavior` — use
    whatever `/chat/complete` in `main.py` already calls). Mirror `main.py`'s usage.
- `backend/realtime/README.md`: 8–12 lines — brain = this + the soul (Python); surface =
  `frontend/` (PixiJS room + audio I/O); they meet over a WebSocket (Phase 1+). Link
  `docs/ARCHITECTURE_V2.md`.

## Task 2 — Declare V2 deps (do not install)
- `backend/requirements-realtime.txt` (NEW, separate from `requirements.txt` so the V1
  install + `npm run check` are untouched): pin `pipecat-ai` (latest stable) with a
  header comment: "V2 realtime brain deps — installed in Phase 1, not by the V1 gate."
- Do not add anything to `backend/requirements.txt` / `requirements-dev.txt`.

## Task 3 — Record reuse (`docs/OPEN_SOURCE_REUSE.md`)
Add rows (decision recorded; install timing noted):
- Pipecat (`pipecat-ai`) — BSD-2, Level 4 (base voice). Declared Phase 0, installed Phase 1.
- PixiJS — MIT, Level 3 (pixel room renderer). Recorded Phase 0, installed Phase 5.
- Silero VAD via `@ricky0123/vad-web` — MIT, Level 2. Phase 1.
- Capacitor — MIT, Level 2 (iPhone surface wrapper). Phase 9.

## Task 4 — Document the layout
Add a short **"Repo layout (V2)"** section to `docs/ARCHITECTURE_V2.md`:
- `backend/app/` = soul (kept): memory / behavior / providers / files / reflection + V1 HTTP API.
- `backend/realtime/` = brain voice loop (Pipecat, Phase 1+), reuses the soul.
- `frontend/` = surface (V1 CSS avatar now; PixiJS room replaces it, Phase 5).
- Brain ↔ surface meet over WebSocket (Phase 1+). V1 app stays runnable throughout.

## Task 5 — Prove the seam (`backend/tests/test_realtime_skeleton.py`)
- `import backend.realtime` and `from backend.realtime.companion_brain import CompanionBrain`
  succeed (the soul imports resolve).
- Instantiating + calling a stub raises `NotImplementedError` (documents Phase 1 boundary).
- This test runs inside the existing V1 gate **without** pipecat installed (the skeleton
  must NOT import pipecat — only the soul).

## Done criteria
1. `PYTHON_BIN=.venv/bin/python npm run check` + `npm run build:frontend` green — V1
   untouched; new skeleton test passes without pipecat installed.
2. `backend/realtime/` exists, imports the soul, declares (not installs) pipecat.
3. Reuse ledger + ARCHITECTURE_V2 layout updated.
4. Diff confined to: `backend/realtime/**`, `backend/requirements-realtime.txt`,
   `backend/tests/test_realtime_skeleton.py`, `docs/OPEN_SOURCE_REUSE.md`,
   `docs/ARCHITECTURE_V2.md`, `docs/TODO.md`, `docs/SESSION_LOG.md`.

## Boundaries
- V1 keeps running; brain/surface principle from `ARCHITECTURE_V2.md` holds.
- Skeleton imports the soul only — **no pipecat import**, no heavy install, no soul edits.
- Cloud brains stay cloud; no secrets in code.
