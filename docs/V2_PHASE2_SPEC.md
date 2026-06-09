# Spec — V2 Phase 2: Doubao streaming STT/TTS as Pipecat services

Source: `docs/ARCHITECTURE_V2.md` + `docs/REBUILD_ROADMAP.md` (Phase 2).
**Claude spec → Cursor builds → Claude reviews → checkpoint.** Reuse-first.

## Why (the user's pain)
Phase 1 used **local Whisper STT** (CPU → fans) + macOS `say` TTS, and one-shot STT (slow).
Phase 2 moves voice I/O to **Doubao cloud streaming** → the laptop goes thin (fans quiet)
and the post-release latency drops. Two *separable* wins:
- **Fans/CPU** ← stop doing STT locally (any cloud STT fixes this, even one-shot).
- **Latency** ← *streaming* STT (send audio while speaking, no full-clip wait).

## Goal
Swap `run_voice.py`'s STT+TTS to **Doubao** Pipecat services: fast, accurate Chinese voice
in/out through the existing Pipecat pipeline (keep Silero VAD + DeepSeek LLM).

## Out of scope (explicit)
- **Echo / self-interruption is NOT fixed here.** That's the next slice (half-duplex). For
  Phase-2 testing, **use headphones** so Boxi doesn't cut itself off.
- Soul/behavior-engine wiring is **Phase 3**.
- **No V1 changes.** The V1 HTTP Doubao adapters (`backend/app/{stt,tts}/doubao.py`) and
  routes stay exactly as-is; Phase 2 adds Pipecat wrappers under `backend/realtime/`.

## Task 0 — Reuse-first check (do this first, record the answer)
Check whether the installed Pipecat (`pipecat-ai==1.3.0`) already ships a **Volcengine /
Doubao / ByteDance** STT and/or TTS service (`python -c "import pipecat.services..."` /
browse the installed package). If it does → **use it directly** with our keys; do not
port. Only build custom services for whatever Pipecat lacks. Note the finding in the
session log.

## Task 1 — Doubao streaming TTS Pipecat service (the easy win, do first)
We already have streaming TTS: `backend/app/tts/doubao.py` →
`DoubaoTTSProvider.synthesize_stream(SynthesisRequest(text=...)) -> Iterator[bytes]`
(V3 unidirectional HTTP, base64 audio chunks already decoded).
- New `backend/realtime/doubao_tts_service.py`: a Pipecat **TTSService** subclass whose
  `run_tts(text)` drives `synthesize_stream(...)` and yields Pipecat audio frames
  (`TTSAudioRawFrame` or the installed version's equivalent) as chunks arrive.
- **Set output to raw PCM at 24000 Hz** (`DoubaoTTSProvider(audio_format="pcm")`) so Pipecat
  gets PCM frames with no decode step; declare the sample rate to Pipecat. (The adapter
  supports `format`/`sample_rate` already; `pcm` is in `FORMAT_TO_MIME`.)
- The adapter's stream is sync (httpx). Run it without blocking the event loop (thread /
  `run_in_executor` / async wrapper) so audio frames flow as they arrive.
- Env: `DOUBAO_TTS_API_KEY`, `DOUBAO_TTS_VOICE_TYPE` (`zh_female_cancan_uranus_bigtts`);
  resource `seed-tts-2.0` resolves automatically via `resolve_resource_id`. Keys env-only.

## Task 2 — Doubao streaming STT Pipecat service (the hard, high-value part)
The V1 `backend/app/stt/doubao.py` is **one-shot flash** (HTTP, whole-clip) — reuse its
auth shape + language normalization, but the **streaming** path is new:
- New `backend/realtime/doubao_stt_service.py`: a Pipecat **STTService** subclass that opens
  Doubao's **streaming ASR WebSocket**, streams the pipeline's mic PCM frames as they arrive,
  and emits `InterimTranscriptionFrame` / `TranscriptionFrame` (installed-version names) as
  partial/final results return. VAD end-of-utterance finalizes the turn.
- **Verify the streaming protocol against Doubao docs** (Volcengine BigASR streaming /
  `sauc`): WebSocket URL, binary framing, the `X-Api-Resource-Id` for *streaming* (differs
  from flash's `volc.bigasr.auc_turbo` — confirm, likely a `volc.bigasr.sauc.*` id),
  `X-Api-Key`/`X-Api-App-Key` headers, PCM rate (16 kHz mono). Env: `DOUBAO_API_KEY`,
  `DOUBAO_ASR_RESOURCE_ID` (allow override).
- **Staged fallback (anti-thrash):** if the WebSocket streaming ASR can't be wired cleanly
  in this slice, ship **Task 1 (Doubao streaming TTS) + a cloud one-shot STT** (reuse the
  existing flash `DoubaoASRProvider` behind a minimal Pipecat STT shim) so the **fans/CPU
  win lands now**, and split streaming ASR into a follow-up **Phase 2b**. Report the blocker;
  do not burn the slice fighting the WS protocol.

## Task 3 — Wire `run_voice.py`
- Replace `WhisperSTTService` → Doubao STT service; `MacSayTTSService` → Doubao TTS service.
- Keep `LocalAudioTransport`, `SileroVADAnalyzer`, `OpenAILLMService(DeepSeek)`.
- Leave `mac_say_tts.py` in place as a no-key fallback (selectable via an env flag, e.g.
  `CYBER_COMPANION_VOICE_TTS=mac_say|doubao`, default `doubao`); same optional flag for STT
  (`whisper|doubao`) so testing can fall back without a code edit.
- `faster-whisper` may stay declared in `requirements-realtime.txt` (no longer the default).

## Done criteria
1. `PYTHON_BIN=.venv/bin/python npm run check` + `npm run build:frontend` green — V1
   untouched; realtime tests `importorskip` without pipecat installed.
2. `python -m backend.realtime.run_voice` (with Doubao env + **headphones**): speak Chinese →
   transcribed → DeepSeek → **Doubao 灿灿 voice out**, with **no local-Whisper CPU load**
   (fans quiet). If streaming ASR landed, post-release wait is gone; if the fallback shipped,
   note the remaining one-shot latency + that Phase 2b finishes streaming.
3. Session log: Task 0 finding (Pipecat Doubao support?), which STT path shipped
   (streaming vs flash-fallback), before/after latency + CPU/fan observation, the chosen
   sample rates.
4. Diff confined to: `backend/realtime/**`, `backend/requirements-realtime.txt` (deps only,
   e.g. a `websockets` client), `docs/SESSION_LOG.md`, `docs/TODO.md`,
   `docs/OPEN_SOURCE_REUSE.md` (if a new lib is added). **No `backend/app/**` or `frontend/**`.**

## Boundaries
- Reuse our existing Doubao adapter logic; don't reinvent auth/streaming we already have.
- Keys via env only; cloud = DeepSeek + Doubao.
- V1 stays runnable and green. Echo/half-duplex + soul are later slices.
- Don't trust Pipecat/Doubao API symbol names in this spec verbatim — verify against the
  installed Pipecat version and current Doubao docs.
