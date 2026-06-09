# backend/realtime — V2 brain (voice loop)

The **brain** is this package plus the existing Python **soul** in `backend/app/`
(memory, behavior, providers, persona). Phase 1+ adds a Pipecat pipeline here;
Phase 0 only declares the seam.

The **surface** is `frontend/` — V1 CSS avatar today; a PixiJS room replaces it in
Phase 5. Audio I/O and rendering live on the surface.

Brain and surface meet over a **WebSocket** (Phase 1+). The V1 HTTP app in
`backend/app/main.py` stays runnable throughout the rebuild.

See `docs/ARCHITECTURE_V2.md` for the full target architecture.

## Run the voice skeleton (Phase 1–2)

Prerequisites:

- macOS with microphone + speaker. **Half-duplex is on by default** — external speakers
  work without echo self-interrupt. Set `CYBER_COMPANION_VOICE_HALF_DUPLEX=off` + **headphones**
  if you want barge-in (full-duplex).
- `brew install portaudio` (PyAudio / local mic I/O).
- `.venv` with V1 deps already installed (`backend/requirements-dev.txt`).
- `DEEPSEEK_API_KEY` in the environment or `.env`.
- For default Doubao voice I/O: `DOUBAO_API_KEY`, `DOUBAO_TTS_API_KEY`, `DOUBAO_TTS_VOICE_TYPE`
  (see `.env.example`).

Install realtime deps (separate from the V1 gate — **do not** add to `requirements.txt`):

```bash
pip install -r backend/requirements-realtime.txt
```

Env vars:

| Variable | Default | Purpose |
|---|---|---|
| `DEEPSEEK_API_KEY` | (required) | DeepSeek API key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI-compatible base URL |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Chat model |
| `CYBER_COMPANION_VOICE_STT` | `doubao` | `doubao` (cloud flash ASR) or `whisper` (local) |
| `CYBER_COMPANION_VOICE_TTS` | `doubao` | `doubao` (灿灿 PCM 24 kHz) or `mac_say` (macOS placeholder) |
| `DOUBAO_API_KEY` | — | Doubao ASR (flash) API key |
| `DOUBAO_ASR_RESOURCE_ID` | `volc.bigasr.auc_turbo` | ASR resource override |
| `DOUBAO_TTS_API_KEY` | — | Doubao TTS API key |
| `DOUBAO_TTS_VOICE_TYPE` | — | e.g. `zh_female_cancan_uranus_bigtts` |
| `CYBER_COMPANION_SAY_VOICE` | `Tingting` | macOS `say` voice when `CYBER_COMPANION_VOICE_TTS=mac_say` |
| `CYBER_COMPANION_VOICE_LOG_LEVEL` | `INFO` | `DEBUG` for per-turn latency lines |
| `CYBER_COMPANION_VOICE_VAD_STOP_SECS` | `0.4` | Silero VAD stop delay (turn-finalize) |
| `CYBER_COMPANION_VOICE_ASR_END_WINDOW_MS` | `300` | Doubao streaming `end_window_size` |
| `CYBER_COMPANION_VOICE_MAX_TOKENS` | `200` | Spoken reply cap (+ signals trailer room) |
| `CYBER_COMPANION_VOICE_HALF_DUPLEX` | `on` | Mute mic/STT while Boxi speaks (laptop speakers). `off` = barge-in + headphones |
| `CYBER_COMPANION_VOICE_MODE` | `pipeline` | `pipeline` (STT→brain→TTS) or `realtime` (Doubao Dialog S2S) |
| `CYBER_COMPANION_VOICE_OUTPUT_MODE` | `0` | `0` = pure end-to-end (Doubao brain); `1` = hybrid (not yet) |
| `DOUBAO_RT_APP_ID` | — | Dialog S2S App ID (realtime mode only) |
| `DOUBAO_RT_ACCESS_TOKEN` | — | Dialog S2S Access Token (realtime mode only) |
| `DOUBAO_RT_SPEAKER` | `zh_male_yunzhou_jupiter_bigtts` | S2S TTS speaker override |
| `DOUBAO_RT_MODEL` | `1.2.1.1` | Dialog model version (O2.0) |
| `DOUBAO_RT_AUDIO_FORMAT` | `pcm_s16le` | TTS output format — **must** be 16-bit for Pipecat (not float `pcm`) |

Run:

```bash
python -m backend.realtime.run_voice
```

**Working looks like:** speak Chinese → Doubao ASR transcribes → **Companion Brain**
(behavior + compact memory context + persona) streams DeepSeek → signal-strip → Doubao
灿灿 TTS speaks back (PCM 24 kHz). Boxi may stay silent or refuse (behavior engine).
**Interrupt** by talking while Boxi is speaking when `CYBER_COMPANION_VOICE_HALF_DUPLEX=off`
(headphones recommended). With half-duplex **on** (default), Boxi finishes its reply before
listening again — no self-interrupt on laptop speakers.

Stack: Pipecat **1.3.0**, VAD = **SileroVADProcessor**, STT = **DoubaoFlashSTTService** or
**DoubaoStreamingSTTService** (`CYBER_COMPANION_VOICE_STT=doubao_stream`), LLM slot =
**CompanionBrainProcessor** (soul mirror of `/chat/complete`), TTS = **DoubaoTTSService**.
Fallbacks: `CYBER_COMPANION_VOICE_STT=whisper`, `CYBER_COMPANION_VOICE_TTS=mac_say`.

**Realtime mode** (`CYBER_COMPANION_VOICE_MODE=realtime`, OutputMode 0):

```bash
CYBER_COMPANION_VOICE_MODE=realtime python -m backend.realtime.run_voice
```

Doubao Dialog WebSocket fuses ASR+LLM+TTS — cloud VAD + barge-in, Boxi persona via
`system_role` / `bot_name` / `speaking_style`. Per-turn latency logged at INFO
(`user_end→first_audio`, `first_asr→first_audio`). Headphones recommended.

## Soul LLM server (RTC Stage 1 — OutputMode 1 custom LLM)

OpenAI-compatible shim around **CompanionBrain** for Volcengine AIGC-RTC hybrid mode.
Separate from the V1 HTTP app (`backend/app/main.py`).

```bash
CYBER_COMPANION_PROVIDER_MODE=mock python -m backend.realtime.soul_llm_server
```

| Variable | Default | Purpose |
|---|---|---|
| `SOUL_LLM_HOST` | `127.0.0.1` | Bind address |
| `SOUL_LLM_PORT` | `8100` | Bind port |
| `SOUL_LLM_API_KEY` | — | Bearer token for `/v1/chat/completions`. If unset, **localhost only** |
| `SOUL_LLM_LOG_LEVEL` | `info` | Uvicorn log level |

Smoke (mock provider, stream):

```bash
curl -N http://127.0.0.1:8100/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"boxi-soul","stream":true,"messages":[{"role":"user","content":"你好"}]}'
```

With `SOUL_LLM_API_KEY` set, add `-H "Authorization: Bearer $SOUL_LLM_API_KEY"`.
Only the **latest user message** is passed to the soul; inbound history is ignored.
Spoken deltas strip `<<<BOXI_SIGNALS>>>`; memory writes run off-path via `remember()`.

**RTC Stage 2 (browser demo):** see `docs/RTC_DEMO_SETUP.md` + `scripts/soul_tunnel.sh`.
