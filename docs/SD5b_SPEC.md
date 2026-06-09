# SD-5b Implementation Spec — CJK-aware tokenizer for linker + retrieval

**Owner: `[Claude]`-class (touches retrieval), but DELEGATED to Cursor via this spec.**
Claude spec → Cursor implements + runs gates → Claude reviews diff → checkpoint.
Found in the Session 28 real-DeepSeek smoke: SD-5's linker formed **0 links** on
Chinese memories.

## Why

`retrieval.tokenize` is `{m.group(0) … for TOKEN_PATTERN.finditer(text)}` where
`TOKEN_PATTERN = [\w一-鿿]+`. Chinese has no spaces, so an unsegmented clause
collapses into ONE giant token (e.g. `张伟的副业项目叫acme`). Two memories then never
share a token, so:
- the SD-5 deterministic linker (token overlap) never fires on Chinese → 0 links;
- Chinese **keyword retrieval ranking** (`score_memory` token-in-content / `boosted_memory_types`)
  is also degraded.

The mechanism is correct (English unit tests pass); the tokenizer is the bug.

## Decision (made by Claude — do not re-litigate)

Use **jieba** (`jieba`, MIT license) for Chinese word segmentation. Rationale: this is a
Chinese-first companion; real words (`项目`, `简历`, `面试`, `acme`) make BOTH linking and
keyword recall work, and keep token sets small so the linker ratio stays meaningful.
Char-bigrams were considered and rejected: they explode the token count, which breaks the
linker's `overlap / min(tokens)` ratio and adds noise.

**Graceful fallback:** if `import jieba` fails at runtime, fall back to the current
whitespace/punctuation behavior (today's `tokenize`) so the app never hard-depends on it.

## Task 1 — Dependency

- Add `jieba` to `backend/requirements.txt`.
- Record it in `docs/OPEN_SOURCE_REUSE.md` (name, MIT, why: CJK segmentation for memory
  retrieval + linking).

## Task 2 — Rewrite `tokenize` (`backend/app/memory/retrieval.py`)

Replace the body of `tokenize(text) -> set[str]`. Keep the **same signature and return
type** (a `set[str]` of lowercased tokens). Behavior:

1. Lowercase the text.
2. Extract **ASCII alnum words** with `[a-z0-9_]+`; keep those with `len >= 2` (unchanged
   from today for English — existing English tests MUST stay green).
3. Extract **CJK runs** (`[一-鿿]+`); segment each run with jieba
   (`jieba.lcut(run, cut_all=False)`); keep segments with `len >= 2` chars. Drop a small
   stopword set of common 2-char particles/pronouns that add only noise, e.g.
   `{"我们","你们","这个","那个","什么","怎么","因为","所以","但是","然后","就是","已经"}`
   (keep this list short and conservative; do NOT over-prune).
4. Lazy + cached jieba: `import jieba` inside the function (or a module-level lazy init)
   guarded by `try/except ImportError` → on failure, fall back to the **old** tokenizer
   (factor today's logic into `_tokenize_fallback`). jieba's dictionary load is one-time;
   don't load it at module import.

Single CJK characters (1-char jieba segments) are dropped (len>=2 rule) — consistent with
the existing `len >= 2` filter.

## Task 3 — Re-tune the linker threshold (`backend/app/reflection/jobs.py`)

Real-word token sets are small and Chinese memories share fewer tokens than English. With
jieba, lower the ratio gate so a genuine shared noun links a cross-type pair, without
flooding:

- Keep `_LINK_MIN_OVERLAP = 2`.
- Change `_LINK_MIN_RATIO` from `0.34` → **`0.25`**.

Validate empirically with the Chinese test below; nudge only if the test shows
false-positive links on clearly-unrelated pairs.

## Task 4 — Verify the other `tokenize` consumers (no code change expected, but TEST)

`tokenize` is also used by:
- `retrieval.score_memory` / `boosted_memory_types` — keyword recall. `TYPE_KEYWORDS`
  values are real words (`简历`, `面试`, `投递`, `job`, `resume`…) → jieba yields them as
  segments, so matching IMPROVES. Add a Chinese recall assertion.
- `write_policy._is_similar_content` — dedup similarity. jieba changes which memories count
  as "similar". Re-run `test_memory_write_policy.py`; if any dedup test flips, adjust the
  test's fixtures (not the threshold) only if the new behavior is clearly correct, and call
  it out in the SESSION_LOG.

## Task 5 — Tests

- `test_memory_retrieval.py`: a Chinese query (`我今天投递了简历`) tokenizes to include
  `投递` and `简历`; a `job_progress` memory ranks above an unrelated one.
- `test_memory_links.py`: two cross-type Chinese memories sharing a real noun link;
  unrelated Chinese pair does NOT; English cases still pass.
- jieba-absent fallback: monkeypatch the import path (or the lazy init) to force the
  fallback and assert `tokenize` still returns the old whitespace tokens.
- All existing suites stay green (English retrieval/links/dedup unchanged).

## Task 6 — Docs

- `docs/MEMORY_DESIGN.md` Retrieval Policy: note tokenization is jieba-segmented for CJK
  (bigram-free), with graceful fallback; linker ratio is 0.25.
- `docs/OPEN_SOURCE_REUSE.md`: jieba entry (Task 1).

## Done criteria

1. `PYTHON_BIN=.venv/bin/python npm run check` green (+ new tests).
2. Chinese cross-type memories sharing a real noun link in unit tests; English behavior
   unchanged; dedup suite green.
3. Diff confined to `backend/app/memory/retrieval.py`, `backend/app/reflection/jobs.py`
   (threshold constant only), `backend/requirements.txt`, tests, `docs/MEMORY_DESIGN.md`,
   `docs/OPEN_SOURCE_REUSE.md`.
4. **Real-DeepSeek re-smoke is a Claude step** (needs the key) — not required for Cursor's
   checkpoint. Cursor stops at green gate; Claude re-smokes that `memory_links > 0` on a
   Chinese conversation and reviews the diff.

## Boundaries

- Deterministic only (jieba is deterministic; no LLM in tokenize/linker).
- Same `tokenize` signature/return type; English path unchanged; never hard-crash if jieba
  is missing.
- Do NOT touch the SD-5 `memory_links` table/contract, the 1-hop expansion in
  `context_builder`, or any SD-1..SD-4 behavior.
