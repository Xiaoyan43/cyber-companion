# Phase: Local Voice (push-to-talk, offline-first)

Author: Claude (plan + adapter specs + review). Implementation: Cursor.
Status: planned. Greenlight required before starting.

## Goal & Scope

Make Boxi actually listen and speak, fully local/offline, on this machine
(2019 Intel MacBook Pro, quad-core i5, 16 GB, no GPU — CPU-only).

In scope:
- Real local STT (replace the mock) for push-to-talk.
- Real local TTS (replace the silent-WAV mock).
- Wire the existing push-to-talk UI to the real flow end to end.

Out of scope (separate later phases):
- Cloud voice (ElevenLabs / CosyVoice / 豆包) — supported later by adding an
  adapter + key; see "Swapping providers later".
- Voice stage 4 (always-on VAD / wake word). Push-to-talk only.
- Any change to chat, memory, behavior, provider (DeepSeek) layers.

## Architecture fit (scaffold already exists)

The STT/TTS router abstraction is already built: provider interface
(`stt/base.py`, `tts/base.py`), registry, router, config, status endpoints,
budget gates, selective-speech policy. This phase only adds **local provider
adapters** behind that interface — nothing else changes.

Key property: local providers set `cloud = False`, so the router's
`allow_cloud_stt/tts` budget gate does NOT apply (local = free, private). The
`mock` providers stay as the safe fallback.

## Hardware sizing (CPU-only)

- STT model: Whisper **base** (default) or **small**. base ≈ 1–3 s for a short
  push-to-talk clip; small ≈ 3–6 s. Do NOT use medium/large (too slow here).
- TTS: macOS `say` is instant (system voices). piper is a neural upgrade,
  still fast on CPU.

## Dependencies

- `faster-whisper` (pip, MIT) — CTranslate2 Whisper, CPU int8. Downloads the
  model on first use (base ≈ 142 MB / small ≈ 466 MB).
- `ffmpeg` (brew) — needed to decode the browser's webm/opus recording before
  transcription. `brew install ffmpeg`.
- TTS v1 uses macOS `say` (built in, no install). TTS v2 optional: `piper-tts`
  + a `zh_CN` voice model.
- Record all of these in `docs/OPEN_SOURCE_REUSE.md` when added.

## Slices

### V1 — Local TTS via macOS `say` (do first, biggest quick win)

Boxi speaks with a real system voice immediately, zero model download.

Adapter `backend/app/tts/mac_say.py` → `MacSayTTSProvider`:
- `name = "mac_say"`, `cloud = False`, `placeholder = False`.
- `synthesize(request)`: write text to a temp file or pass as a single arg,
  run `say -v <voice> -o <tmp>.wav --data-format=LEI16@22050` via
  `subprocess.run([...], shell=False)`, read the WAV bytes, return
  `SynthesisResult(provider, model=f"mac-say-{voice}", mime_type="audio/wav",
  audio_bytes=..., duration_ms=<from wav header>, mock=False)`.
- Voice configurable in `tts.json` (default a zh voice, e.g. `Tingting`).
- **Security:** never use `shell=True`; pass text as one argv element so it
  can't be interpreted as a shell command. Clean up temp files.
- If `say` is unavailable, raise a clear `TTSError` (don't crash).

Config: add `mac_say` to `tts.example.json`; enable via `config/tts.json`
(`default_provider: "mac_say"`) + `.env` `CYBER_COMPANION_TTS_MODE=` (empty).

Frontend: none needed — `useTextToSpeech` already plays the returned base64
audio and syncs the `talking` avatar state.

Acceptance: `/tts/synthesize` returns real audio; Boxi audibly speaks a reply;
avatar `talking` sync intact; mute toggle still works; existing race fix holds.

### V2 — Local STT via faster-whisper

You can talk to Boxi.

Adapter `backend/app/stt/faster_whisper.py` → `FasterWhisperProvider`:
- `name = "faster_whisper"`, `cloud = False`.
- `__init__`: `model_size` from config (default `"base"`), `device="cpu"`,
  `compute_type="int8"`. **Lazy-load the model once and cache at module level**
  (don't reload per request).
- `transcribe(request)`: decode `request.audio_bytes` (webm/opus/mp4) to 16 kHz
  mono float32 via PyAV/ffmpeg, then `model.transcribe(array,
  language=request.language or None)`; join segments → text. Return
  `TranscriptionResult(provider, model, text, mock=False, language)`.
- First call downloads the model (note the latency; allow a pre-warm).

Config: add `faster_whisper` to `stt.example.json`; enable via `config/stt.json`
(`default_provider: "faster_whisper"`, `model: "base"`) + `.env`
`CYBER_COMPANION_STT_MODE=` (empty).

Frontend: `usePushToTalk` already records + uploads; just confirm the real text
flows into the normal chat path. Surface a clear "first use is slow (model
loading)" hint.

Acceptance: hold-to-talk → release → real transcription → chat → DeepSeek reply
→ Boxi speaks (V1). Empty/garbled audio handled gracefully.

### V3 — Polish & robustness

- Model warm-up on backend startup (optional) so the first real transcription
  isn't a cold download/load.
- Thread-safety: the sync route runs in a threadpool; ensure the shared model
  instance is safe / serialized.
- Latency UX: keep the existing "Transcribing…" indicator honest.
- Optional quality upgrade: piper TTS (`piper.py` adapter, same interface) with
  a `zh_CN` voice; switch `tts.json` default to it.
- No cost tracking needed (local = free). Cloud cost tracking is deferred to
  the cloud-voice phase.

## Ownership

- **Claude:** this plan, the two adapter specs above, and review of each slice
  (audio decode correctness, no `shell=True` injection, model caching, that the
  provider interface/contract is respected, race fix preserved).
- **Cursor:** implement the adapters, config entries, frontend confirmation,
  tests, and docs (`OPEN_SOURCE_REUSE.md`, an `ARCHITECTURE.md` voice note,
  `SESSION_LOG.md`). Checkpoint per slice.
- **User:** `brew install ffmpeg`; approve `pip install faster-whisper` into
  `.venv`; grant the browser mic permission.

## Boundaries

- Do not change the STT/TTS provider interface — implement against it.
- Local adapters are `cloud = False` (not budget-gated).
- Keep `mock` working; `CYBER_COMPANION_STT_MODE/TTS_MODE=mock` must still force
  the offline mock.
- No stage-4 always-on mic. Push-to-talk only (audio leaves nothing; it's local
  anyway).
- Do not touch chat / memory / behavior / DeepSeek provider.

## Swapping providers later (not locked in)

To move TTS/STT to a cloud provider (ElevenLabs / 阿里云 CosyVoice / 豆包) later:
write one adapter against the same interface (`cloud = True`), add a
`config/*.json` entry + key in `.env`, point `default_provider` at it. Cloud
providers stay behind the `allow_cloud_*` budget gate, and that's when voice
cost tracking gets added. The rest of the system is untouched.

## Verification (each slice)

- `PYTHON_BIN=.venv/bin/python npm run check` and `npm run build:frontend` pass.
- Manual end-to-end: speak → transcript → DeepSeek reply → Boxi speaks.
- `scripts/ui_verify.mjs` still passes on mock (local voice verified manually).
