# SD-1c Implementation Spec — Trailer reminder on the current user turn

Follow-up to SD-1b, driven by the **SD-1b re-smoke (Session 27, real DeepSeek).**
**Owner: `[Claude]`-class (context assembly).** Claude spec → Cursor implements →
Claude reviews (real re-smoke) → checkpoint.

## Why (re-smoke finding)

SD-1b strengthened `OUTPUT_PROTOCOL` (mandatory + example) and put it last in the
system message. In isolation that gave 4/5 emission — **but in the real chat path it
was still 0** (trust/closeness frozen, memories still `writer="rule_based"`).

Diagnosed live, same assembled context, controlled A/B:

| Condition | trailer emit |
|---|---|
| Full app context **with replayed assistant history** | **0 / 5** |
| Same system message, **no assistant history** | 3 / 5 |
| + trailing **system** reminder after history | 0 / 5 (ignored) |
| + reminder appended to the **current user turn** | **3 / 5** ✅ |

**Root cause:** we persist `parsed.content` (trailer stripped) and replay those
**trailer-less assistant turns** as `recent_raw` history. The model treats them as
in-context examples — "assistant replies look like this (no trailer)" — and mimics
them, overriding the system instruction. In-context examples beat the system prompt.

**Fix (validated):** append a short mandatory-trailer reminder to the **current user
message** (provider-only). The user-role + recency position is the one the model
heeds; a trailing system message does not work. Restores emission to the no-history
baseline (~3/5); M2 regex covers the misses.

## Fix — `memory/context_builder.py`

In `build_provider_context`, the final provider message is
`ChatMessage(role="user", content=provider_user_input)`. Append a concise reminder to
`provider_user_input` **for the provider only**:
```python
_TRAILER_REMINDER = (
    "\n\n（系统提醒：本轮回复必须在正文后另起一行输出 <<<BOXI_SIGNALS>>> 及其单行 JSON，"
    "不可省略。）"
)
...
provider_user_input = _truncate_user_input_for_provider(user_input, config.max_user_input_tokens)
provider_user_input_for_send = provider_user_input + _TRAILER_REMINDER
# use provider_user_input_for_send ONLY in the final ChatMessage; keep token accounting
```
Critical correctness:
- **Provider-only.** Persistence (`main.py` `persist_chat_turn`) uses the original
  `user_input`, not this augmented string — so the reminder never enters stored
  history and never accumulates across turns. Verify this stays true.
- Add the reminder's tokens to the input estimate / reserved budget so accounting
  stays honest (it's ~30 tokens).
- Keep it short; it rides every turn.
- Always append (the no-history case is also ~3/5, and consistency is simpler than
  conditioning on history presence).

## Tests — `backend/tests/test_context_builder.py`
- The final provider message (`role="user"`) **ends with** the reminder and contains
  the sentinel marker text.
- Persisted user content (assert via the existing persistence path or a focused unit)
  does **not** contain the reminder — i.e. it's provider-only. (If awkward to assert
  through the store, at minimum assert `build_provider_context` does not mutate the
  passed `user_input` and that `recent_raw` replay never carries the reminder.)
- Existing context_builder + SD-1/1b tests stay green.

## Done criteria
1. `npm run check` green.
2. **Real-DeepSeek re-smoke (Claude review):** over ~6 turns *with* accumulating
   history, the trailer is emitted on the majority of turns (≈3/5+, not 0);
   `trust`/`closeness` visibly move; ≥1 memory written `writer="llm"`; `[Impression]`
   still populated; still zero leak.
3. Diff confined to `memory/context_builder.py` + tests.

## Boundaries / notes
- Provider-only reminder; never persisted, never replayed.
- Parser / stream filter / kernel / write pipeline unchanged.
- M2 regex stays the safety net for non-emitting turns.
- **Escalation path if ≈3/5 proves too low in daily use** (don't do now): either
  (a) persist the raw assistant output (with trailer) and replay *that* as history so
  the in-context examples demonstrate the pattern, or (b) move signal extraction to a
  Tier-② background call (the Q1 fallback in SOUL_DEEPENING_SPEC §3). Both are larger;
  SD-1c is the cheap high-leverage step.
