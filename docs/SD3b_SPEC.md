# SD-3b Implementation Spec — M2 fallback when M3 writes nothing + valid memory types in protocol

Follow-up to SD-3, found in the **SD-1c payoff re-smoke (Session 27, real DeepSeek).**
**Owner: `[Claude]`-class (write path + prompt).** Claude spec → Cursor → Claude
review (real re-smoke) → checkpoint.

## Why (re-smoke finding)

After SD-1c made the trailer actually fire, `trust`/`closeness` moved for real
(0.5→0.63 / 0.2→0.36) — SD-1c works. **But factual memories vanished:** the final DB
had only the reflection impression, zero `writer="llm"` *or* `writer="rule_based"`
facts (earlier smokes, with no trailer, wrote `rule_based` profile + job_progress).

Confirmed by code (no extra API calls needed):
- `store.list_memories` / `GET /memory/memories` do **not** filter expired → the
  facts were **never written**, not archived-and-hidden.
- `write_policy.record_turn_memories`: when `signals.memory` is a non-empty list it
  `return write_memories_from_signals(...)` **unconditionally** — so if every LLM item
  fails validation (type ∉ `MEMORY_TYPES`, content <4 chars, or confidence <0.6),
  M3 writes nothing **and the regex M2 fallback never runs.** The turn loses both.

So: now that the model emits `memory[]`, items that don't validate (most likely a
`type` outside our whitelist, e.g. `"personal_info"`/`"fact"`) silently drop the
turn's memory write.

## Fix

### 1. M2 fallback when M3 yields nothing (`memory/write_policy.py`)
```python
if config.llm_memory_extraction and isinstance(signals, dict):
    sig_mem = signals.get("memory")
    if isinstance(sig_mem, list) and sig_mem:
        written = write_memories_from_signals(store, sig_mem, source_message_id=..., budget=config)
        if written:
            return written
        # all LLM items rejected -> fall through to regex M2 (don't lose the turn)
return maybe_write_memories_from_turn(store, user_input=user_input, source_message_id=..., budget=config)
```
This restores the safety net: a turn never silently writes nothing just because the
LLM emitted invalid memory items.

### 2. Enumerate valid memory types in the protocol (`memory/persona.py`)
The `OUTPUT_PROTOCOL` says `memory[{type, content, ...}]` without listing the allowed
types, so the model invents ones we reject. Enumerate them so M3 acceptance goes up:
```
memory[{type, content, importance 0..1, confidence 0..1, tags}] — type MUST be one of:
stable_profile, recent_event, emotion_state, project, job_progress, reminder,
relationship_state, behavior_preference.
```
(Keep the rest of the protocol as-is; just constrain `type`.)

## Tests (`backend/tests/test_memory_write_policy.py`)
- **fallback engages:** `record_turn_memories` with `signals.memory=[{type:"bogus",...}]`
  (all invalid) writes via regex M2 instead of nothing (assert a memory from the
  user_input regex is created).
- **no double-write:** when LLM items ARE valid, M2 does **not** also run (count stays
  = M3 writes; the existing "picks M3 over regex" test still holds).
- **empty M3 + empty M2:** invalid LLM items AND a user_input with no regex hit →
  zero writes, no error.
- existing SD-3 tests stay green.

## Done criteria
1. `npm run check` green.
2. **Real-DeepSeek re-smoke (Claude review):** over ~6 turns, both signals flow
   (trust/closeness move — SD-1c) **and** at least one factual memory persists
   (`writer="llm"` if items validate, else `writer="rule_based"` via fallback);
   `/memory/memories` is non-empty with profile/job facts.
3. Diff confined to `memory/write_policy.py`, `memory/persona.py`, tests.

## Boundaries
- One write path per turn still holds — M2 only runs as a fallback when M3 wrote
  nothing (not in addition to a successful M3).
- Don't touch parser / kernel / reflection / SD-1b/1c.
- LLM memory stays data-only (validated/clamped/type-whitelisted).
