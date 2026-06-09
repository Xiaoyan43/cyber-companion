# Spec — V2 Phase 1: Pipecat voice skeleton (hardest unknown first)

Source: `docs/ARCHITECTURE_V2.md` + `docs/REBUILD_ROADMAP.md` (Phase 1).
**Claude spec → Cursor builds → Claude reviews → checkpoint.** Reuse-first: adopt
Pipecat for the real-time plumbing; **placeholder STT/TTS is fine** — the deliverable is
the *loop + interruption*, not voice quality.

## Goal (one sentence)
Stand up a minimal Pipecat pipeline — **mic → VAD → STT → DeepSeek → TTS → speaker** — on
the dev laptop, where you can **speak, hear DeepSeek reply in voice, and interrupt it**.
Half-duplex (Boxi pauses listening while speaking) is acceptable this phase.

## Ground rule on API accuracy (read first)
**Do NOT trust any Pipecat class/function name written in this spec verbatim.** Pipecat's
API changes across versions. Scaffold from **Pipecat's own official quickstart / foundational
example for the installed version (`pipecat-ai==1.3.0`, see `backend/requirements-realtime.txt`)**
and adapt it. The spec gives the *architecture + decisions + done-criteria*; the exact API is
whatever the installed Pipecat's docs/examples use. If 1.3.0 is awkward, pin the nearest
stable Pipecat that has a clean local-audio quickstart and update `requirements-realtime.txt`
(note the change in the session log).

## Decisions (the reuse-first choices)
- **Entrypoint:** new `backend/realtime/run_voice.py` — a standalone script/process. **Does
  NOT touch V1** (`backend/app`, `frontend`). Run it directly; it is not part of the V1 gate.
- **Install:** install the realtime deps now (Phase 1 is when we install) from
  `requirements-realtime.txt` into `.venv`, plus the Pipecat *extras* for the chosen
  transport/VAD/STT/TTS/LLM (per Pipecat 1.3.0 docs). macOS local audio likely needs
  PortAudio (`brew install portaudio`) for `pyaudio`/`sounddevice` — document any system dep.
- **Transport:** Pipecat **local audio** transport (laptop mic + speaker).
- **VAD:** Pipecat built-in **Silero VAD** — endpointing + barge-in trigger. This is what
  makes interruption work; it is the core of the phase.
- **LLM:** **DeepSeek**, via Pipecat's OpenAI-compatible LLM service
  (`base_url=https://api.deepseek.com`, `model=deepseek-chat`, key from env
  `DEEPSEEK_API_KEY` — never hardcoded). System prompt: a short Boxi line is fine; **full
  soul/behavior-engine wiring is Phase 3, not now.**
- **STT/TTS:** *fastest working option*, placeholder OK.
  - STT recommendation: **local Whisper** Pipecat service (no new key). Chinese accuracy
    isn't the Phase-1 bar; the Doubao **streaming** STT/TTS port is **Phase 2**.
  - TTS recommendation: whatever Pipecat TTS runs with a key you already have, else a
    minimal/local TTS placeholder so output is audible. Do **not** block Phase 1 on TTS
    quality or on acquiring a new paid key — if needed, ship an audible placeholder and
    note it.
- **Turn-taking:** half-duplex (VAD pauses input while TTS plays). Full-duplex barge-in on
  external speakers is explicitly a later/hardware win — do not chase it here.

## Tasks
1. `backend/realtime/run_voice.py`: build the Pipecat pipeline (transport → VAD → STT → LLM
   (DeepSeek) → TTS → transport out), wire interruption per Pipecat's interruption example,
   `async` main runner. Config (model, base_url, device, service keys) read from env /
   existing `config/` where natural; no secrets in code.
2. Make interruption real: speaking while Boxi talks must cut its TTS and re-listen (Silero
   VAD barge-in). This is the acceptance core.
3. `backend/realtime/README.md`: append a **"Run the voice skeleton"** section — install
   command (incl. extras + PortAudio), env vars, `python -m backend.realtime.run_voice`,
   and what "working" looks like (speak → DeepSeek voice reply → interrupt stops it).
4. **Don't regress V1:** `pipecat-ai` stays out of `backend/requirements.txt`; the V1 gate
   (`npm run check`) must not import pipecat. If you add a tiny import-smoke test, guard it
   so it is **skipped when pipecat/audio aren't available** (`pytest.importorskip`) — the V1
   gate must stay green on machines without pipecat installed.

## Done criteria (manual — this is an audio loop)
1. `PYTHON_BIN=.venv/bin/python npm run check` + `npm run build:frontend` still green
   (V1 untouched; any realtime test is import-skipped without pipecat).
2. Running `python -m backend.realtime.run_voice` on the laptop: user speaks → DeepSeek
   replies **in voice** → user can **interrupt** mid-reply and Boxi stops + listens.
3. Record in the session log: the exact STT/TTS chosen, the Pipecat version, any system deps
   (PortAudio), and an honest note on interruption reliability on laptop speakers.
4. Diff confined to: `backend/realtime/**`, `backend/requirements-realtime.txt` (version/extras
   only), `docs/SESSION_LOG.md`, `docs/TODO.md`, `docs/OPEN_SOURCE_REUSE.md` (if a service lib
   is added). No `backend/app/**` or `frontend/**` changes.

## Boundaries
- Brain/surface split holds: this is brain-side, standalone, no V1 coupling.
- Soul (behavior engine / memory / persona injection) is **Phase 3** — Phase 1 is raw
  DeepSeek in the LLM slot just to prove the loop.
- Keys via env only; cloud only for DeepSeek (+ any chosen cloud STT/TTS).
- If a service can't be wired fast, **fall back to a placeholder and report the blocker** —
  do not thrash. This is the hardest phase; a proven interruptible loop > a perfect voice.
