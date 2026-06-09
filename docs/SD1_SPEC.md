# SD-1 Implementation Spec — Piggyback signal contract

Phase **SD-1** of `docs/SOUL_DEEPENING_SPEC.md`. **Owner: `[Claude→Cursor]`.**
Claude wrote this spec → Cursor implements → Claude reviews the diff → checkpoint.

## Goal (one sentence)

Make the assistant reply able to carry a **signals trailer** (emotion appraisal /
relationship deltas / memory candidates) that is **parsed but never leaks** to the
user-facing text or TTS — on both `/chat/complete` and `/chat/stream`.

## Scope — what SD-1 does and does NOT do

**Does:**
1. Define the sentinel + extend the parser to split it out and expose `signals`.
2. Strip the trailer from the **streaming** delta path so live text + TTS never see it.
3. Add a compact persona **output-protocol** instruction so the model emits it.
4. Tests for: no-sentinel, sentinel+valid-JSON, sentinel+malformed-JSON, streaming
   strip (incl. sentinel split across chunks), and the existing legacy JSON form.

**Does NOT (later phases — do not touch in SD-1):**
- Do **not** apply `appraisal`/`relationship` to mood/relationship state — that is
  SD-2. Parse and ignore them for now.
- Do **not** write `signals.memory[]` to the DB — that is SD-3. Parse and ignore.
- `avatar_state` and `decision` keep being honored **exactly as today** (the two
  parse sites at `main.py:633` and `:905` already read `parsed.avatar_state` /
  `parsed.decision`). No behavior change there.
- No schema change. No new config knob (the `llm_memory_extraction` knob arrives
  with SD-3; SD-1's persona instruction is always on).

## The contract (recap from SOUL_DEEPENING_SPEC §3)

Model emits natural reply, then on a new line the sentinel, then one single-line JSON:
```
<natural reply text — this is `content`>
<<<BOXI_SIGNALS>>>
{"avatar_state":"worried","decision":"reply","appraisal":{...},"relationship":{...},"memory":[...]}
```
- `SIGNALS_SENTINEL = "<<<BOXI_SIGNALS>>>"`.
- `content` = text **before** the sentinel, trimmed.
- All trailer fields optional. Chat must never break on a missing/garbled trailer.

---

## Task 1 — Parser (`backend/app/behavior/parser.py`)

Extend `StructuredAssistantResponse`:
```python
@dataclass(frozen=True)
class StructuredAssistantResponse:
    content: str
    avatar_state: str | None = None
    decision: str | None = None
    signals: dict | None = None        # NEW — appraisal/relationship/memory; unused in SD-1
```

Add the constant and rewrite `parse_structured_assistant_response` with this
precedence (first match wins):

1. **Sentinel form (new, primary).** If `SIGNALS_SENTINEL` is in the text:
   - `content` = text before the sentinel, `.strip()`.
   - Take the text after the sentinel; `json.loads` the first `{...}` block in it.
   - On success: `avatar_state`/`decision` read from that JSON if present; `signals`
     = the whole parsed dict (so SD-2/SD-3 can read `signals["appraisal"]` etc.).
   - On `JSONDecodeError`/no JSON: `content` = pre-sentinel text, everything else
     `None`. **Never** return the sentinel or raw JSON inside `content`.
2. **Legacy whole-string JSON (keep — back-compat).** Existing branch: if the whole
   stripped string is a JSON object with a `content` key, parse as today. (Keeps
   `test_structured_parser_reads_json_payload` green.)
3. **Legacy embedded-JSON block (keep).** Existing `JSON_BLOCK_PATTERN` branch.
4. **Fallback.** `content` = stripped raw text, all else `None` (today's default).

Notes:
- Reuse the existing `json` import. Add `SIGNALS_SENTINEL` as a module constant.
- The sentinel check must come **before** the legacy JSON branches so a reply that
  happens to start with `{` is not misparsed when a trailer is present.

---

## Task 2 — Streaming strip (`backend/app/main.py`, `/chat/stream`)

Today (around `main.py:878`):
```python
if chunk_kind == "delta":
    accumulated_parts.append(chunk_value)
    yield _sse_data({"type": "delta", "text": chunk_value})   # leaks the trailer
```
The trailer must not reach the client. Use a **sentinel-aware filter** that holds
back a tail (in case the sentinel is forming across chunk boundaries) and stops
emitting once the sentinel appears — while `accumulated_parts` still gets everything
for the final parse.

Add a small helper (new function in `main.py`, or `behavior/parser.py` — put it next
to the sentinel constant):
```python
class SignalStreamFilter:
    """Emits reply text up to SIGNALS_SENTINEL; swallows the trailer. The caller
    still accumulates the full raw text separately for the final parse."""
    def __init__(self) -> None:
        self._buf = ""          # not-yet-emittable tail
        self._done = False      # sentinel seen -> emit nothing more

    def feed(self, chunk: str) -> str:
        if self._done:
            return ""
        self._buf += chunk
        idx = self._buf.find(SIGNALS_SENTINEL)
        if idx != -1:
            out = self._buf[:idx]
            self._buf = ""
            self._done = True
            return out
        # hold back the last (len(sentinel)-1) chars: they might begin the sentinel
        keep = len(SIGNALS_SENTINEL) - 1
        if len(self._buf) > keep:
            out = self._buf[:-keep]
            self._buf = self._buf[-keep:]
            return out
        return ""

    def flush(self) -> str:
        # stream ended with no sentinel -> the held-back tail was real content
        if self._done:
            return ""
        out = self._buf
        self._buf = ""
        return out
```

Wire it into the delta loop:
```python
signal_filter = SignalStreamFilter()
...
if chunk_kind == "delta":
    accumulated_parts.append(chunk_value)          # full raw text, unchanged
    visible = signal_filter.feed(chunk_value)
    if visible:
        yield _sse_data({"type": "delta", "text": visible})
elif chunk_kind == "usage":
    stream_usage = chunk_value
...
# after the for-loop, before _finalize_streamed_turn:
tail = signal_filter.flush()
if tail:
    yield _sse_data({"type": "delta", "text": tail})
```
`accumulated_text = "".join(accumulated_parts)` and the final
`parse_structured_assistant_response(accumulated_text)` are **unchanged** — they parse
the full raw text and `parsed.content` equals the visible stream. `_finalize_streamed_turn`
already sets `final_content = parsed.content`, so the persisted/returned content is
clean.

> Local `/chat/complete` path needs no streaming change — `main.py:633-646` already
> rebuilds `result` with `content=parsed.content`, which (with the new parser) is the
> pre-sentinel text. Just confirm it still strips correctly with a trailer present.

---

## Task 3 — Persona output protocol (`backend/app/memory/persona.py`)

Append a short protocol block to the returned system prompt (both the persona-file
path and the hardcoded fallback string). Keep it compact — it is sent every turn.

Suggested text (tune wording, keep it this short):
```
Output protocol: First write your natural reply in Boxi's voice — that is all the
user sees. Then on a NEW line write exactly <<<BOXI_SIGNALS>>> followed by ONE
single-line JSON object with optional keys: avatar_state (one of: idle, happy, sad,
angry, sleepy, thinking, talking, worried, annoyed, silent), decision, appraisal
{valence,-1..1; arousal,0..1; goal_relevance,0..1; note}, relationship
{trust,closeness,tension as small deltas -0.1..0.1}, memory [{type, content,
importance 0..1, confidence 0..1, tags[]}]. Never put <<<BOXI_SIGNALS>>> anywhere
except before that JSON. If you have nothing to add, omit the trailer entirely.
```
Do not change persona name/tone/boundaries/catchphrases. This is an **append**.

---

## Task 4 — Tests (`backend/tests/test_behavior.py`)

Add cases (keep the existing `test_structured_parser_reads_json_payload`):

| Test | Input | Expect |
|---|---|---|
| `test_parser_no_sentinel_plain_text` | `"行吧，先做一步。"` | `content == "行吧，先做一步。"`, `signals is None`, `avatar_state is None` |
| `test_parser_sentinel_valid_json` | `"先做一步。\n<<<BOXI_SIGNALS>>>\n{\"avatar_state\":\"thinking\",\"decision\":\"reply\",\"relationship\":{\"trust\":0.04}}"` | `content == "先做一步。"`, `avatar_state == "thinking"`, `decision == "reply"`, `signals["relationship"]["trust"] == 0.04` |
| `test_parser_sentinel_malformed_json` | `"先做一步。\n<<<BOXI_SIGNALS>>>\n{not valid json"` | `content == "先做一步。"`, `signals is None`; **sentinel/JSON absent from `content`** |
| `test_parser_legacy_json_still_works` | (existing test, unchanged) | still green |

Stream-filter cases (unit-test `SignalStreamFilter` directly — no HTTP needed):

| Test | Feeds | Expect concatenated `feed`+`flush` output |
|---|---|---|
| `test_stream_filter_no_sentinel` | `["行吧","，先","做一步。"]` | `"行吧，先做一步。"` |
| `test_stream_filter_strips_trailer` | `["先做一步。","\n<<<BOXI","_SIGNALS>>>\n{...}"]` | `"先做一步。\n"`-ish (everything before sentinel; **no `<<<` and no JSON**) |
| `test_stream_filter_sentinel_split_across_chunks` | feed the sentinel one char per chunk after some text | output contains the text, **never** any prefix of the sentinel |

(For the split-across-chunks case the key assertion is: the emitted output never
contains `<<<BOXI_SIGNALS>>>` nor any partial like `<<<BOXI`.)

---

## Done criteria (how Claude will review)

1. `PYTHON_BIN=.venv/bin/python npm run check` green (all backend tests + tsc).
2. New parser + stream-filter tests present and passing; legacy parser test still green.
3. Manual smoke (reviewer): run the app, send a message, confirm in the live stream +
   the spoken TTS that **no `<<<BOXI_SIGNALS>>>` or JSON** ever appears, while the
   avatar still animates from `avatar_state`.
4. Trailer-absent replies behave exactly as before SD-1 (no regressions).
5. Diff is confined to: `behavior/parser.py`, `memory/persona.py`, `main.py`
   (stream loop only), `backend/tests/test_behavior.py`. No schema/config/memory
   changes.

## Boundaries (SD-1)

- No memory schema change; no `docs/MEMORY_DESIGN.md` edit needed this phase.
- Don't consume `appraisal`/`relationship`/`memory` yet (SD-2/SD-3).
- Don't send full history; don't touch budget/provider/file-gateway.
- Keep Boxi's voice unchanged — the protocol block is appended, persona core intact.
