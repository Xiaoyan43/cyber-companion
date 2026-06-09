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

- macOS with microphone + speaker. **Use headphones** for Phase 2 testing (echo not fixed yet).
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

Run:

```bash
python -m backend.realtime.run_voice
```

**Working looks like:** speak Chinese → Doubao ASR transcribes → **Companion Brain**
(behavior + compact memory context + persona) streams DeepSeek → signal-strip → Doubao
灿灿 TTS speaks back (PCM 24 kHz). Boxi may stay silent or refuse (behavior engine).
**Interrupt** by talking while Boxi is speaking; Silero VAD should cut TTS and re-listen.
On laptop + external speaker, interruption is best-effort (half-duplex); use headphones.

Stack: Pipecat **1.3.0**, VAD = **SileroVADProcessor**, STT = **DoubaoFlashSTTService** or
**DoubaoStreamingSTTService** (`CYBER_COMPANION_VOICE_STT=doubao_stream`), LLM slot =
**CompanionBrainProcessor** (soul mirror of `/chat/complete`), TTS = **DoubaoTTSService**.
Fallbacks: `CYBER_COMPANION_VOICE_STT=whisper`, `CYBER_COMPANION_VOICE_TTS=mac_say`.
