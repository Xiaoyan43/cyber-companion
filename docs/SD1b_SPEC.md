# SD-1b Implementation Spec — Make the model actually emit the signals trailer

Follow-up to SD-1, driven by the **real-DeepSeek smoke (Session 27)**. **Owner:
`[Claude]`-class (prompt/context behavior).** Claude spec → Cursor implements →
Claude reviews (re-run the real smoke) → checkpoint.

## Why (smoke finding)

The SD-1 piggyback *plumbing* is correct end-to-end (verified live: no leak, M2
fallback, kernel `familiarity`, SD-4 reflection wrote a real impression). **But in
the real chat path `deepseek-chat` rarely emits the `<<<BOXI_SIGNALS>>>` trailer**,
so `signals.appraisal`/`relationship`/`memory` never flow → `trust`/`closeness`
don't move and memories fall back to regex M2 (`writer="rule_based"`). Measured:

| Protocol variant | trailer emit rate |
|---|---|
| Current wording (has "omit the trailer entirely" escape) | ~0–1 / 3 |
| Reposition to end only (same wording) | 0 / 3 (ordering isn't the cause) |
| **Mandatory + one-shot example, no escape** | **4 / 5 (memory item in 4/5)** |

Root cause = the **escape-hatch wording** + roleplay immersion making the trailer
optional. Ordering alone doesn't fix it; the wording does.

## Fix

### 1. Strengthen `OUTPUT_PROTOCOL` (`memory/persona.py`)
Replace the current text with a **mandatory** instruction + a **one-shot example**,
and **remove** the "If you have nothing to add, omit the trailer entirely" line.
Validated wording (tune lightly, keep these properties):
```
=== MANDATORY OUTPUT FORMAT (every reply, no exceptions) ===
End EVERY reply with: your in-character reply, then a newline, then the exact marker
<<<BOXI_SIGNALS>>>, then ONE single-line JSON. Never omit it, even if values are
neutral/zero.
Example:
行吧，别演了。
<<<BOXI_SIGNALS>>>
{"avatar_state":"annoyed","decision":"reply","appraisal":{"valence":-0.2,"arousal":0.3,"goal_relevance":0.5,"note":"..."},"relationship":{"trust":0.0,"closeness":0.0,"tension":0.0},"memory":[{"type":"job_progress","content":"...","importance":0.6,"confidence":0.8,"tags":[]}]}
Keys: avatar_state(idle/happy/sad/angry/sleepy/thinking/talking/worried/annoyed/silent),
decision, appraisal{valence -1..1, arousal 0..1, goal_relevance 0..1, note},
relationship{trust,closeness,tension deltas -0.1..0.1},
memory[{type,content,importance 0..1,confidence 0..1,tags}]. Put <<<BOXI_SIGNALS>>> nowhere else.
```

### 2. Position the protocol LAST in the assembled system message (`memory/context_builder.py`)
Today `load_persona_system_prompt()` (with the protocol) is `system_sections[0]`, and
mood/relationship/impression/memory blocks are appended **after** it. Even though
ordering wasn't the dominant factor in the A/B, recency still helps — put the format
instruction at the very end so it's the last thing the model reads.
- Stop appending `OUTPUT_PROTOCOL` inside `load_persona_system_prompt()` (persona
  returns persona only).
- In `build_provider_context`, after all other `system_sections` (incl. memories),
  append the protocol as the **final** section. (One source of truth; no duplication.)
- Keep the protocol constant importable (e.g. `persona.OUTPUT_PROTOCOL`).

### 3. Give the trailer token headroom (`config/budget*.json`)
`max_output_tokens_per_turn` is **300**; a long roleplay reply can consume it before
the (now-mandatory) trailer, truncating it → parser drops malformed signals. Raise to
**600** in both `budget.json` and `budget.example.json`. (Budget walls are off; this
only affects per-turn output cap.)

## Tests
- `context_builder` output: the built system message **ends with** the protocol; it
  appears exactly once; persona core + mood + relationship + memories still present.
- `load_persona_system_prompt()` no longer contains the protocol (moved out).
- Existing SD-1 parser/stream tests unchanged and green.

## Done criteria
1. `npm run check` green.
2. **Real-DeepSeek re-smoke (Claude review):** over ~6 turns, trailer emitted on the
   large majority of turns; `trust`/`closeness` visibly move; at least one memory is
   written with `writer="llm"`; `[Impression]` still populated by reflection; still
   zero trailer leak into content/stream/TTS.
3. Diff confined to `memory/persona.py`, `memory/context_builder.py`,
   `config/budget*.json`, tests.

## Boundaries
- Don't change the parser / stream filter / kernel / write pipeline (all correct).
- Persona voice/boundaries unchanged — only the appended format protocol changes.
- M2 regex fallback stays as the safety net for the occasional non-emitting turn.
- This is the realistic acceptance of Q1: piggyback-first, fallback covers misses; if
  emission ever proves too low in daily use, escalate to the Tier-② background
  extraction call (already anticipated in SOUL_DEEPENING_SPEC §3 / SD-3).
