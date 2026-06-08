# Phase: Streaming Replies (LLM stream → live text → sentence TTS)

Author: Claude (plan + specs + review). Implementation: Cursor, slice by slice.
Goal: kill the "wait for the whole reply, then it appears" delay. Text should
start typing out in ~0.5 s, and audio should start near the first sentence.

## Why / current state

Measured: a real DeepSeek turn is ~1.9 s and the text only appears after the
whole reply is generated; TTS (now streaming) starts right after. The remaining
delay is the non-streaming LLM. Context is already lean (~180 tokens), so
trimming context is NOT the lever — streaming is.

## Hard rules (do not regress)

- Keep `/chat/complete` working unchanged as the fallback. Streaming is additive.
- Preserve the full turn flow: behavior eval + mood update + budget gate +
  context build happen BEFORE streaming; persist_chat_turn + M2 auto-write +
  summary update happen AFTER the stream completes on the accumulated text.
- Preserve the avatar/TTS race fix (epoch guard, deferIdleFallback,
  speakReply→bool, onSpeakingStart/End). This is the #1 review gate.
- Preserve Option A (strip stage-direction parentheticals) before TTS.
- Preserve selective-speech policy + `allow_cloud_*` gating.
- Plain-text assumption: the persona is not prompted for JSON today, so stream
  raw text deltas. (If structured output is ever turned on, streaming + the
  structured parser must be reconciled — out of scope here; note it.)

## Slice S1 — Backend: streaming provider + `POST /chat/stream` (text only)

- Provider interface: add `complete_stream(request)` that yields text deltas.
  - DeepSeek adapter: call with `stream=true` and
    `stream_options={"include_usage": true}`; yield each content delta; capture
    final usage from the last chunk. Reuse the persistent httpx client.
  - Mock/other: yield the full reply as one (or a few) deltas so the endpoint
    works for every provider.
  - Usage/cost: prefer DeepSeek's reported usage; else estimate from the
    accumulated text. Persisted cost must stay accurate (budget brake depends
    on it). Suggested shape: generator yields `("delta", str)` items and a final
    `("usage", TokenUsage)`.
- Router: add `complete_stream`.
- Endpoint `POST /chat/stream` → `StreamingResponse(media_type="text/event-stream")`:
  1. Same pre-work as `/chat/complete` (extract input, evaluate_behavior, budget
     gate, build context).
  2. If `should_call_llm` and gate allows: stream deltas as SSE
     `data: {"type":"delta","text":"…"}` lines while accumulating the full text;
     on end, parse structured response, persist the turn, run M2 + summary, then
     emit `data: {"type":"done","meta":{provider,model,decision,avatar_state,
     should_call_llm,usage,cost}}`.
  3. If local decision or budget-blocked: emit the local line as one `delta`
     then `done` (no real LLM stream).
  4. On mid-stream error: emit `data: {"type":"error","message":"…"}` and stop;
     the turn should not be half-persisted.
- Tests: with the mock provider, assert the SSE sequence (deltas then done), that
  the turn is persisted once, that M2/summary still run, and that a budget block
  yields a local `done` with `should_call_llm=false`, cost 0.
- Acceptance: `curl -N /chat/stream` shows deltas then a `done` with correct
  meta; DB shows exactly one persisted turn.

## Slice S2 — Frontend: consume `/chat/stream`, render text live (audio still after)

- `api/chat`: add a streaming call (fetch + ReadableStream, parse SSE lines),
  invoking `onDelta(text)` and `onDone(meta)` / `onError`.
- `App.tsx`: on submit, use streaming when available (fall back to
  `/chat/complete` on error/unsupported). Append an empty Boxi bubble and grow
  its text as deltas arrive (typing effect). Avatar: `thinking` until the first
  delta, `talking` while streaming. On `done`: set the message meta + `lastTurn`.
- TTS in S2 stays as today: when the stream finishes, call `speakReply` once with
  the full accumulated text. (Incremental TEXT now; audio still after the full
  reply — that's fine for this slice.)
- Preserve the race machinery exactly (epoch/deferIdleFallback/onSpeakingEnd).
- Acceptance: text types out live (~0.5 s to first chars); audio still plays via
  the existing path; overlap/race regression tests still pass.

> After S1+S2 you already get the big perceived win (instant text). S3 is the
> last step to make audio start early too — do it only once S1+S2 are solid.

## Slice S3 — Frontend: sentence-chunked TTS queue (audio starts ~first sentence)

- As deltas arrive, accumulate into a buffer; when a sentence boundary is hit
  (。！？!?…\n or a max-length cap), cut a chunk, run Option A stripping, and
  enqueue it to a TTS playback queue.
- Play the queue **sequentially** via the existing `/tts/stream` (one sentence at
  a time, in order, no overlap). Fire `onSpeakingStart` on the first audio,
  `onSpeakingEnd` when the queue drains and the stream is done.
- Apply the selective-speech policy sensibly (e.g., decide once per reply, or
  skip tiny fragments). Mute/stop must abort the queue and any in-flight stream.
- This is the race-critical slice: keep the epoch guard so a newer turn cancels
  the old queue; never let a finishing old sentence drag the avatar to idle while
  a new turn is active.
- Acceptance: audio begins roughly one sentence in; sentences play in order; a
  second turn mid-playback cancels cleanly (no stuck `thinking`, no overlap);
  existing TTS smoke still passes.

## Ownership

- Claude: this plan, the S1 provider/route spec, and review of every slice
  (turn-flow preservation, budget brake, race fix, fallback).
- Cursor: implement S1→S2→S3, tests, docs (ARCHITECTURE streaming note,
  SESSION_LOG). Checkpoint per slice. Do NOT start a slice before the previous
  one is reviewed/green.
- User: try each slice in the browser; confirm text-speed and audio-start feel.

## Out of scope

- Structured (JSON) persona output + streaming reconciliation.
- Changing memory/behavior/provider semantics beyond adding the stream path.
