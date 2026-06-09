# Spec — V2 Phase 2b: Doubao streaming WebSocket ASR

Source: `docs/ARCHITECTURE_V2.md` + `docs/REBUILD_ROADMAP.md` (Phase 2 streaming STT).
**Claude spec → Cursor builds → Claude reviews → checkpoint.** Reuse-first.

## Why
Phase 2 shipped the **flash one-shot STT** (`DoubaoFlashSTTService`, `SegmentedSTTService`):
the whole clip is sent *after* you stop talking → ~1.5–2.5 s post-release wait = the latency
the user feels. **Streaming ASR transcribes while you speak**, so the final transcript is
ready almost the instant you stop. This is the latency fix.

## Goal
A `DoubaoStreamingSTTService` (continuous Pipecat **`STTService`**, not segmented) that opens
Doubao's **streaming ASR WebSocket**, feeds mic PCM as it arrives, and emits
`InterimTranscriptionFrame` (partial) + `TranscriptionFrame` (final) — noticeably lower
perceived latency than flash.

## Ground rule on protocol accuracy (read first)
The Doubao/Volcengine **BigASR streaming** protocol is a **binary WebSocket** framing
(4-byte header: protocol version / message type / flags / serialization / compression, then
a gzip-JSON config message, then audio-only messages; responses carry partial+final results).
**Do NOT hand-roll it from memory or from anything written in this spec.** Implement against:
- the **official Volcengine 流式语音识别 (BigASR / `sauc`) docs** (same 6561 doc series as the
  flash adapter, which cites `https://www.volcengine.com/docs/6561/1631584`), and
- **Volcengine's official streaming-ASR Python sample / SDK** if one exists — **reuse it**
  (wrap or adapt) rather than reinventing the framing. Record what you used in
  `docs/OPEN_SOURCE_REUSE.md`.
If the live protocol disagrees with anything here, the **docs win**.

## What we already know (proven this session)
- Auth is the simple new-console style: header **`X-Api-Key`** = env **`DOUBAO_API_KEY`**
  (the same key that returned `code:0` audio in the Phase-2 TTS probe authenticates the
  account's speech services).
- Flash uses `X-Api-Resource-Id: volc.bigasr.auc_turbo`. **Streaming uses a *different*
  resource id** (a `volc.bigasr.sauc.*` value — confirm exact id from the docs); expose it
  via env **`DOUBAO_ASR_RESOURCE_ID`** (override) with a sensible streaming default.
- Audio in: **PCM 16 kHz mono** (the pipeline's `INPUT_SAMPLE_RATE`). Enable punctuation +
  ITN like the flash adapter (`enable_punc`, `enable_itn`).
- The existing flash adapter `backend/app/stt/doubao.py` is the reference for auth headers,
  resource-id resolution, language normalization, and error/“no speech” handling — reuse its
  *shapes*; the streaming transport is the new part.

## Tasks
1. **Dependency:** add an async WebSocket client to `backend/requirements-realtime.txt`
   (`websockets` preferred — mature, asyncio-native; or Volcengine's SDK if it cleanly does
   streaming ASR). Keys stay env-only.
2. **`backend/realtime/doubao_streaming_stt_service.py`** — subclass Pipecat **`STTService`**
   (the continuous one that consumes audio frames; **not** `SegmentedSTTService`):
   - On start: open the WS, send the config/start message (audio params, model, resource id,
     punc/itn), per the docs.
   - On each audio frame: forward PCM bytes (chunked per the protocol).
   - On responses: push `InterimTranscriptionFrame` for partials and `TranscriptionFrame` for
     finals (mirror `DoubaoFlashSTTService`'s frame fields + language tagging).
   - On stop / interruption: send end-of-stream, drain the final result, close the WS cleanly.
   - Robustness: reconnect/teardown on WS error; surface fatal errors as `ErrorFrame`; treat
     silence/no-result like the flash service (no crash, no empty frame).
3. **Wire the toggle** in `run_voice.py`: add `doubao_stream` to `CYBER_COMPANION_VOICE_STT`
   (alongside existing `doubao` flash + `whisper`). **Keep flash as the fallback.** Pick the
   default: ship `doubao_stream` as default **only after** it’s validated; otherwise leave
   flash default and note it. Keep the OpenBLAS thread-serialization fix in place.
4. **Tests** (`backend/tests/test_realtime_voice.py` or a new file): `importorskip` so the V1
   gate stays green without pipecat/websockets. Unit-test what's testable without the network —
   e.g. the binary frame builder/parser (construct a config frame, parse a canned response
   into interim/final), and the toggle selection. Don't require a live WS in the gate.

## Done criteria (manual — audio loop)
1. `PYTHON_BIN=.venv/bin/python npm run check` + `npm run build:frontend` green; V1 untouched;
   realtime tests `importorskip`.
2. `CYBER_COMPANION_VOICE_STT=doubao_stream python -m backend.realtime.run_voice` (Doubao env +
   headphones): **interim transcripts appear while speaking**, final lands ~immediately at
   end-of-speech, and end-to-end latency is **clearly lower than flash**.
3. Session log: streaming resource id + protocol source (doc/SDK) used, any SDK reused, and a
   **before/after latency note** (flash vs streaming).
4. Diff confined to: `backend/realtime/**`, `backend/requirements-realtime.txt`,
   `docs/SESSION_LOG.md`, `docs/TODO.md`, `docs/OPEN_SOURCE_REUSE.md`. **No `backend/app/**`
   or `frontend/**`** — the V1 flash adapter `backend/app/stt/doubao.py` stays untouched.

## Boundaries
- Reuse Volcengine's documented protocol / official sample; don't reinvent the framing.
- Verify every protocol/resource-id detail against the live Doubao docs — this spec's
  protocol notes are orientation, not gospel.
- Keep the flash STT path working as a fallback toggle (don't delete it this slice).
- Keys via env only; no V1 changes; soul wiring is still Phase 3.
- If the WS protocol can't be made reliable in this slice, **report the specific blocker**
  (auth? framing? resource id? partial-result parsing?) rather than thrashing — we iterate.
