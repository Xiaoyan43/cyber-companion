# TODO

## Direction C — the being (2026-06-13: C locked; depth > latency; soul authors the words)

Final form = **"a being with a world"** (see `docs/VISUAL_SPIKE_SPEC.md` header + memory
`direction-c-soul-authored`). Soul-authored voice = **cascaded** (Phases 1–3, un-shelved);
**pure E2E retained** as fast/present mode (revisit after VikingDB schemas); hybrid = dead end.

- [ ] **Visual spike — light core + ink `[Claude spec ✓ → Cursor builds → Claude reviews]`.**
  Throwaway page: BOTH materials (semi-figurative particles / light-in-ink) × 6 states incl. the
  **two felt-vs-shown desyncs** (suppression + teasing) + thinking→speak. Shader, not fluid sim.
  Picks the material. **Spec: `docs/VISUAL_SPIKE_SPEC.md`.**
- [ ] **Felt-vs-shown split + teasing `[Claude spec ✓ → Cursor builds → updates PERSONA_AND_BEHAVIOR]`.**
  One shared tone projection → `(felt, expressed_edge, is_performative)`; add `performative_sharp`
  (positive zone: no worry/annoyance/tension + closeness high) with its OWN playful register (not
  real-annoyance); real negatives win; suppression already exists (worry beats annoyance). Makes
  desync-2 TRUE. **Spec: `docs/VISUAL_SPIKE_SPEC.md` (paired slice).**
- [ ] (post-spike, staged) Wire material ← live kernel → ambient world drift → memory traces
  (the echo world; reads existing kernel + `memories`, no new tables).
- [ ] (deep-voice) Un-shelf cascaded soul-authored voice as primary (Phases 1–3); pure E2E → fast toggle.

## Proactive initiation (PI) — 2026-06-13: the missing companion pillar

Deepening, not from-scratch — the tick loop already exists (`useBehaviorTicks` →
`POST /behavior/evaluate` → persist line). **Spec: `docs/PROACTIVE_INITIATION_SPEC.md`.**

- [x] **PI-1 — Longing model (timing) `[Claude spec ✓ → Cursor → update PERSONA_AND_BEHAVIOR + COST]`.**
  `behavior/longing.py`: longing from `last_meaningful_interaction_at × closeness` (fix the inverted
  `mood.py:74` sign), stochastic Poisson fire, availability gate (quiet hours / post-convo cooldown /
  daily cap). Replaces stale-job-only fire gate. Seedable RNG. Reuse `pearthink123/revive-companion` (MIT, Level 1). **Claude review PASS @ `ab14a7e`** — 350 tests green; see PI-1 follow-ups below.
- [x] **PI-2 — Reason + soul-authored opener `[done @ c6fe473; Claude review PASS]`.**
  Reason picker (reminder / follow-up / memory callback / check-in) → in-voice opener authored at the
  **route layer** (`proactive_opener.resolve_proactive_opener`, engine stays provider-free);
  `proactive_llm` gate + daily LLM cap (PI-4 cost hook) + triple canned fallback; 363 tests green.
  **Real-provider smoke PASS** (DeepSeek, 2026-06-14): 4 reasons → short in-voice openers
  (11–20字), no guilt/nag; check-in invoked the 盒子 persona ("别让我以为盒子里就我一个活物").
- [x] **PI-1 follow-ups (from review) `[done @ b16e2e0; Claude review PASS]`.** (a) Validation λ
  `longing_lambda_base_per_hour=0.06` + `force_proactive` dev trigger on `/behavior/evaluate`
  (skips only timing gates; **enable/backoff/daily-cap/cost stay enforced**). (b)
  `proactive_max_delta_seconds=600` Δt cap. (c) RTC voice turns confirmed `source='chat'`
  (`persist_chat_turn` line 32) — counted, no query change. 379 tests green.
- [x] **PI-3 — Delivery feels like initiation (in-app) `[done @ 16cccaf; Claude review PASS]`.** Avatar + attention cue; surfaces
  after idle without a user action. (Away-delivery = desktop/box platform follow-on.)
- [x] **PI-4 — Respect + cost brake `[done @ 52f4390; Claude review PASS]`.** ignore-backoff
  (`proactive_pending_since` blocks `awaiting_user_reply` until a user msg clears it), hours fire-gap
  (`proactive_min_fire_gap_hours`), and the USD cost brake (`evaluate_llm_budget_gate` pre-call +
  real completion threaded so cost is recorded). 372 tests green. **PI series complete (PI-1/2/3/4 + follow-ups);
remaining: settle validation λ on-device + optional UI regression test.**

## Soul Deepening (Claude spec 2026-06-09 → Cursor implements → Claude reviews)

Spec: `docs/SOUL_DEEPENING_SPEC.md`. Incremental on the working app, **no rebuild**.
Latency-smart: ① piggyback (same reply call) ② background reflection ③ local math.
Order: SD-1 → SD-2 → SD-3 → SD-4; SD-5 later. One phase = one checkpoint.

- [x] **SD-1 — Piggyback signal contract `[Claude→Cursor]`.** Extend
  `StructuredAssistantResponse` with optional `signals` + tolerant parse
  (`behavior/parser.py`); streaming sentinel-strip (`main.py`); output-protocol
  section to persona (`memory/persona.py`). Done: `signals` parsed when present,
  **never leaks** to `content`/TTS/stream deltas; absent/malformed → today's behavior.
  Tests in `test_behavior.py` (parser + `SignalStreamFilter`).
- [x] **SD-2 — Subjectivity kernel `[Claude]`.** New `relationship_state` singleton
  table (trust/closeness/familiarity/tension/last_meaningful_interaction_at); `trust`
  **moves** here (source of truth), `loneliness` **stays** in mood_state but is
  re-sourced from closeness/time-since-contact; appraisal-driven local math + decay;
  `[Relationship]`/`[Impression]` context blocks; tone factors relationship.
  **Additive table only — no `mood_state` ALTER/DROP** (no migration framework
  exists); seed singleton via `INSERT OR IGNORE`; optional one-time `trust` back-fill.
  **Update `docs/MEMORY_DESIGN.md`.**
- [x] **SD-2-UI — "Boxi 怎么看你" panel `[Cursor-ok]`.** Read-only panel showing
  relationship state (trust/closeness/familiarity/tension) + impression narrative.
  Numbers land with SD-2; impression text fills in after SD-4. Frontend-only.
- [x] **SD-3 — LLM memory extraction (M3) `[Claude]`.** Route `signals.memory[]`
  through existing dedup pipeline (`write_memories_from_signals` +
  `record_turn_memories` orchestrator); keep regex M2 as fallback; `writer="llm"`
  tag; `llm_memory_extraction` knob. Cross-type linking moved to SD-5. Spec:
  `docs/SD3_SPEC.md`.
- [x] **SD-4 — Background reflection layer `[Claude]`.** Turn-counter trigger
  (`reflection_every_n_turns`); jobs: memory consolidation/evolution, impression
  formation (`relationship_state` memory type), LLM conversation summary. Run via
  `BackgroundTasks` off the response path; single-flight; config-gated
  (`enable_reflection`); failure-isolated. Spec: `docs/SD4_SPEC.md`.
- [x] **SD-1b — Make the model actually emit the signals trailer `[Claude]`.**
  Real-DeepSeek smoke (Session 27) found the trailer is rarely emitted in the chat
  path (~0–1/3) → signals don't flow (trust/closeness frozen, memories fall to regex
  M2). Fix (validated live, raises emission to 4/5): mandatory `OUTPUT_PROTOCOL` +
  one-shot example, drop the "omit" escape (`persona.py`); position protocol LAST in
  the system message (`context_builder.py`); raise `max_output_tokens_per_turn`
  300→600 so the trailer isn't truncated. **Spec: `docs/SD1b_SPEC.md`.** Highest
  priority — without it SD-2/SD-3's live value is dormant.
- [x] **SD-1c — Trailer reminder on the current user turn `[Claude]`.** SD-1b
  re-smoke found the strengthened protocol still emits 0 in the real chat path: we
  replay trailer-stripped assistant history, so the model mimics "no trailer" and
  ignores the system instruction. Validated fix (0/5→3/5): append a short
  mandatory-trailer reminder to the **current user message** (provider-only, never
  persisted/replayed) in `context_builder.build_provider_context`. A trailing system
  message does NOT work. **Spec: `docs/SD1c_SPEC.md`.** Highest priority (pairs with
  SD-1b to actually make signals flow).
- [x] **SD-3b — M2 fallback when M3 writes nothing + valid memory types `[Claude]` (done @ Session 28).**
  Code + tests + gate landed (195 tests + tsc); **Done criterion #2 PASSED on real
  DeepSeek** (Session 28, 7-turn smoke): zero-leak ✅, signals flowed
  (trust 0.50→0.52 / closeness 0.20→0.22 / familiarity 0→0.07 / tension 0→0.17),
  **7 factual memories persisted with `writer="llm"`** (M3 validated — profile/project/
  job_progress/reminder), SD-4 impression written, reflection fired. The vanished-facts
  regression is fixed.
  SD-1c payoff smoke: signals now flow (trust 0.5→0.63, closeness 0.2→0.36 ✅) but
  factual memories vanished — `record_turn_memories` committed to M3 when `memory[]` is
  non-empty and never fell back to M2, so LLM items that fail validation (type ∉
  whitelist) dropped the turn's write. Fix: M3 empty → fall through to regex M2
  (`write_policy.py`); enumerate the 8 allowed memory types in `OUTPUT_PROTOCOL`
  (`persona.py`); `MEMORY_DESIGN.md` Auto-Write note updated. **Spec: `docs/SD3b_SPEC.md`.**
- [x] **SD-5 (optional) — Memory links + top-down retrieval `[Claude]` (done @ Session 28).**
  Additive `memory_links` table (`SCHEMA_VERSION=3`, bidirectional + idempotent +
  `ON DELETE CASCADE`); deterministic cross-type linker in reflection (after
  consolidate, no LLM); 1-hop retrieval expansion (additive, capped, expired-skipped);
  consolidation candidate set restricted to `FACTUAL_MEMORY_TYPES`. `docs/MEMORY_DESIGN.md`
  updated. 207 backend tests + tsc green (+12 `test_memory_links.py`). Spec:
  `docs/SD5_SPEC.md`.
- [x] **SD-5b — CJK-aware tokenizer for linker + retrieval `[Claude]` (done @ this commit).**
  jieba segmentation in `retrieval.tokenize` (lazy import + fallback); linker ratio
  0.34→0.25; Chinese recall + cross-type link unit tests. **Spec: `docs/SD5b_SPEC.md`.**
  **Claude re-smoke PASS (Session 28b):** Chinese 6-turn smoke now forms 2 logical
  `memory_links` (was 0 pre-jieba) — `job_progress`↔`recent_event` sharing Acme/项目.
- [x] **SD config knobs `[Cursor-ok]`.** `llm_memory_extraction` (SD-3);
  `enable_reflection`, `reflection_every_n_turns`, `llm_summary` (SD-4) in
  `BudgetConfig` + `config/budget*.json`.

## V2 Rebuild (Claude specs → Cursor builds → Claude reviews)

Source: `docs/ARCHITECTURE_V2.md` + `docs/REBUILD_ROADMAP.md`. Keep the soul; build
hardware-ready (brain/surface split). One phase = one checkpoint.

- [x] **V2 Phase 0 — Foundation `[Claude→Cursor]`.** Brain/surface seam
  (`backend/realtime/` skeleton reusing the soul) + declare Pipecat/PixiJS deps
  (no install) + reuse ledger + layout docs. V1 stays runnable. **Spec:
  `docs/V2_PHASE0_SPEC.md`.**
- [x] **V2 Phase 1 — Pipecat voice skeleton `[Claude→Cursor]`.** mic→VAD→STT→DeepSeek→TTS→speaker,
  interruptible; standalone `backend/realtime/run_voice.py`, V1 untouched; placeholder STT/TTS OK
  (Doubao streaming = Phase 2; soul = Phase 3). **Spec: `docs/V2_PHASE1_SPEC.md`.**
- [x] **V2 Phase 2 — Doubao streaming STT/TTS as Pipecat services `[Claude→Cursor]`.**
  TTS = `DoubaoTTSService` (PCM 24 kHz, `synthesize_stream`); STT = **flash fallback**
  `DoubaoFlashSTTService` (reuses `DoubaoASRProvider`) — streaming WS ASR deferred to Phase 2b.
  Env toggles `CYBER_COMPANION_VOICE_STT` / `CYBER_COMPANION_VOICE_TTS`; Whisper/mac_say kept as
  fallbacks. **Spec: `docs/V2_PHASE2_SPEC.md`.**
- [x] **V2 Phase 2b — Doubao streaming WS ASR `[Claude→Cursor]`.** `DoubaoStreamingSTTService`
  (continuous `STTService`) over the official Volcengine BigASR streaming WebSocket
  (`wss://.../api/v3/sauc/bigmodel`, resource `volc.bigasr.sauc.duration`, new-console `X-Api-Key`);
  interim+final frames; binary framing in `doubao_streaming_protocol.py` (per docs 6561/1354869 +
  public `sauc_python` demo). Toggle `CYBER_COMPANION_VOICE_STT=doubao_stream`; flash kept as
  fallback. Protocol + transcription validated live. **Spec: `docs/V2_PHASE2b_SPEC.md`.**
  Default stays flash pending live-mic acceptance (done-criteria #2) → then flip default to streaming.
- [x] **V2 Phase 3 — Companion Brain `[Claude→Cursor]`.** Fill the `CompanionBrain` stub +
  a `CompanionBrainProcessor` in the LLM slot: compact soul context (no full transcript) +
  behavior gate (reply/silent/refuse/proactive) + persona + memory write + SD-1 signal-strip;
  mirrors `/chat/complete`. Soul reused, not edited. **Spec: `docs/V2_PHASE3_SPEC.md`.**
  Manual mic recall / behavior smoke still user-owned.
- [x] **Voice latency + terseness tuning `[Claude→Cursor]`.** Session-29 metrics: LLM is fast
  (TTFB 0.3s, prefix-cached); the cost is stacked turn-finalize (VAD `stop_secs` 0.8 + Doubao
  `end_window` 800 + smart_turn) + Boxi rambling 3–4 sentences × ~1.5–2s sequential TTS (= the
  "builds up"). Fix: one-sentence voice instruction + `max_output_tokens≈200`; tighten
  turn-finalize (env-overridable). **Spec: `docs/V2_VOICE_LATENCY_SPEC.md`.**
  **Done + profiled (Session 30):** terse replies (spoken_chars ~26–55, signals intact);
  `build_provider_context` warm = **9 ms** (not the bottleneck — compact 811-tok context
  confirmed). Remaining ~1.8s `finalize→first_text` = DeepSeek-to-first-sentence (inherent
  floor). No cheap latency win left.
- [x] **V2 Half-duplex — drop the headphones `[Claude→Cursor]`.** Mute STT/VAD while Boxi
  speaks (reuse Pipecat `AlwaysUserMuteStrategy` — `STTMuteFilter` removed in 1.3.0) so speaker
  echo can't self-interrupt; toggle `CYBER_COMPANION_VOICE_HALF_DUPLEX` (default on; off =
  barge-in + headphones). Folds in jieba pre-warm. **Spec: `docs/V2_HALF_DUPLEX_SPEC.md`.**
- [ ] **V2 Phase 2c — Doubao end-to-end realtime voice (Dialog S2S) `[Claude→Cursor]`.** Fuses
  ASR+LLM+TTS in one WS → kills STT/TTS overhead, natively interruptible. Build BOTH
  `OutputMode 0` (pure, Doubao brain, sub-second; soul = persona+memory-inject+transcript
  extraction) and `OutputMode 1` (hybrid, soul/DeepSeek as orchestrated LLM, ~2s). Keep current
  pipeline as fallback toggle. Auth App ID+Access Token (env). **Spec: `docs/V2_PHASE2c_SPEC.md`.**
  - [x] Task 1 skeleton: `doubao_realtime_protocol.py` + `doubao_realtime_service.py` +
    `CYBER_COMPANION_VOICE_MODE=realtime` path in `run_voice.py`; Boxi persona via `system_role`.
  - [ ] Task 2 memory inject + transcript off-path extraction.
  - [ ] Task 3 hybrid OutputMode 1 (`LLMConfig`).
  - [ ] Task 4 toggle polish + live latency matrix (pure vs hybrid vs pipeline).
- [ ] **V2 RTC — hybrid (OutputMode 1) over Volcengine RTC AIGC `[Claude→Cursor]`.** Lower-latency
  + stable transport + emotion extension for the hybrid (soul-as-brain) path. Arch: RTC Web SDK
  client (= future iPhone surface) + `StartVoiceChat` OpenAPI binds Doubao realtime (OutputMode 1)
  + our custom LLM; **soul hosted as an OpenAI-compatible endpoint.** Reuse `volcengine/rtc-aigc-demo`.
  Creds: RTC AppId/AppKey (have) + account **AK/SK** (needed for StartVoiceChat — pending).
  - [x] **Stage 1 — soul as OpenAI-compatible `/v1/chat/completions` endpoint** (`backend/realtime/
    soul_llm_server.py`, wraps `CompanionBrain`). **Real-DeepSeek smoke PASS (Session 30):** OpenAI
    shape (stream+non-stream), zero trailer leak, **memory recall across turns** (Boxi recalled
    "Acme"). **Spec: `docs/V2_RTC_STAGE1_SPEC.md`.**
  - [ ] **Stage 2 — OutputMode-1 over RTC, validated via official demo `[Claude→Cursor]`.**
    Repo side done: `docs/RTC_DEMO_SETUP.md`, `scripts/soul_tunnel.sh`, `.env.example` RTC/IAM vars.
    **2a PASS (user):** `Boxi` scene / OutputMode 0 — RTC voice + barge-in OK on user account.
    **2b pending:** OutputMode 1 + custom-LLM = Stage-1 endpoint (via tunnel). **Spec:
    `docs/V2_RTC_STAGE2_SPEC.md`.**
  - [ ] Stage 3 — emotion-recognition extension → soul appraisal/kernel.
  - [ ] **Stage 2c — RTC in our frontend (pure E2E + soul hybrid) `[Cursor]`.**
    **v2 landed:** demo-aligned join order (`prepare` → joinRoom → mic → `agent/start`),
    binary subtitle + agent brief parsing, autoplay recovery; VoiceChat payload matches
    `Boxi.json` (short `system_role`, twopass ASR). **Pure E2E user PASS (token fix).**
  - [x] **V2 RTC Viking Memory — pure E2E + 火山长期记忆 `[Cursor]`.**
    **Spec: `docs/V2_RTC_VIKING_MEMORY_SPEC.md`**（跨 session 按 Slice VM-1…5 推进，新窗口说 `推进`）。
    - [x] **VM-1** — 稳定 `VOLC_RTC_DEFAULT_USER_ID` + `MemoryConfig` 注入 `StartVoiceChat`；
      `GET /rtc/status` → `viking_memory_enabled`。
    - [x] **VM-2** — 记忆库 `friend` + IAM 授权；跨会话召回 **用户 PASS**（昵称/城市 召回）。
      `SearchMemory` → `system_role` 注入；档案优先 + 过滤矛盾 event；`MemoryConfig` 默认 `profile_v1`。
    - [x] **VM-3** — 通话结束字幕 → `POST /rtc/memory/session` → Viking `AddSession`；leave 时自动上传。
    - [x] **VM-4** — SQLite 文字记忆注入 `system_role`（近期对话 + 计划要点 + 摘要/印象；
      间接提问如「明天干嘛」**用户 PASS**；`GET /rtc/status` → `sqlite_memory_ready`）。
    - [x] **VM-5** — 左栏 Viking 记忆状态徽章（就绪/只读/关 + 挂断写入反馈）；hover 显示 user_id。
- [ ] **V2 RTC Pure-Soul — off-path turn analyzer `[Claude spec → Cursor builds → Claude reviews]`.**
  Give pure E2E (`OutputMode 0`) the soul's emotion/relationship kernel + typed memory
  **off the audio path** — one cheap DeepSeek pass per turn turns `(user_text, bot_text)`
  into the existing signals JSON → reused `apply_signals_to_kernel` + `record_turn_memories`
  (writes **SQLite**, the source of truth). Sub-second spoken latency untouched. Replaces the
  lost `<<<BOXI_SIGNALS>>>` trailer and is *more* reliable (JSON-only, can't leak).
  **Spec: `docs/V2_RTC_PURE_SOUL_SPEC.md`** (slices PS-1…PS-6; 新窗口说 `推进`).
  - [x] **PS-1** — `reflection/turn_analyzer.py` `analyze_turn()`: local appraisal + DeepSeek
    signals pass + kernel + `persist_chat_turn` + `record_turn_memories` + reflection. Mock-provider tests.
  - [x] **PS-2** — `POST /rtc/turn` + frontend per-turn post + `BackgroundTask`; voice turns now
    feed the same SQLite soul as text. Spoken latency unchanged.
  - [x] **PS-3** — SHAPE (join-time): `rtc/state_block.py build_rtc_state_block()` → discretized
    Chinese mood/relationship stance block folded into `system_role` at `StartVoiceChat`.
    `UpdateVoiceChat` can't update config mid-session → per-call, not per-turn.
  - [x] **PS-4** — steering (join-time) via `system_role`. **⚠ device A/B: ignored — wrong channel
    (tone belongs in `speaking_style`, not `system_role`). Superseded by PS-5/PS-6.**
  - [x] **PS-5** — tone → `speaking_style` (join-time): `build_rtc_speaking_style()` = base +
    kernel modifier; **stop appending steering to `system_role`** (the PS-4 fix). `[Claude spec ✓ → Cursor]`
  - [x] **PS-6** — emotion → `UpdateVoiceChat(SetTTSContext)` (mid-session, per-turn, off-path):
    `TagParse` on at join; kernel → NL `{{additions}}` tag for the next reply; new `update_voice_chat`
    client method. **The PS-4 re-test** (does pure E2E now follow tone?) — **pending user device A/B.**
  - [ ] (later, MIT-adoptable) proactive timing via `pearthink123/revive-companion` math
    (Poisson "longing" + Bayesian user-state) — feeds the proactive part, maps onto `loneliness`.
- [x] **SC2.0 verification env `[Claude spec → Cursor builds → Claude reviews]`.** Toggle built
  (`DOUBAO_RT_SERIES`, O2.0 default). **Device A/B → SC2.0 REJECTED:** saturn/clone voices carry a
  *fixed* vocal tone (role-play built around it), so emotion can't shift mid-convo → worse than O2.0
  for a companion. Staying on O2.0; toggle left dormant. **Spec: `docs/V2_RTC_SC2_VERIFY_SPEC.md`.**
- [x] **O2.0 `persona_prompt` loader `[Cursor]`.** `load_chinese_persona_prompt` returns non-empty
  `persona_prompt` when set (Boxi 全文人设 → text chat / Soul LLM / O2.0 RTC `system_role`); falls back
  to `name+core+tone` assembly. `config/persona.example.json` ships the draft prompt.
- [ ] **O2.0 persona follow-on `[Claude draft → Cursor wires]`.** User device A/B on new Boxi voice;
  `speaking_style` 去规则化; `external_rag` (ChatRAGText 深度 lore, O2.0-only) + `dialog_id` (native
  20-round cross-session memory). ≤~4000-char `system_role`+`speaking_style` budget for memory inject.
- [ ] **VikingDB custom schemas (after SC2.0) `[Claude]`.** Soul-aligned event/profile extraction
  rules + fields + weights in the Viking 记忆库 console (per the in-depth investigation); spec to follow.
- [ ] V2 Phase 4–9 — turn-taking polish, PixiJS room, room reactivity, actions, personal files, the box.

## Current Priority

- [x] Create a checkpoint commit for the current Phase 2-10 MVP batch after user approval.
- [x] Have Claude Code do a read-only architecture/security/memory/behavior review of the current MVP batch.
- [x] Create foundational project files and cross-tool rules.
- [x] Add open-source reuse policy.
- [x] Create project scaffold.
- [x] Build local dev scripts.
- [x] Create basic frontend shell.
- [x] Create basic backend health check.

## Review Findings (Claude, 2026-06-08, @ commit 5005731)

Owner tags: `[Claude]` touches restricted layers (cost/provider/memory/behavior
contract) — do not hand to Cursor without explicit approval + doc updates.
`[Cursor-ok]` is safe for Cursor with the usual checks.

- [x] **S3 — Enforce budget caps `[Claude]` (done @ this commit).**
  `monthly_usd_limit` / `daily_llm_turn_limit` / `allow_reasoning_model` are now
  loaded in `load_budget_config` and enforced in `/chat/complete` via
  `backend/app/memory/usage_guard.py` (blocked turns answer locally, cost 0, not
  counted). Documented in `docs/COST_AND_TOKEN_BUDGET.md`; tests in
  `backend/tests/test_usage_guard.py`.
- [x] **A1+A2 — Memory-layer scan + retention `[Claude]` (done @ this commit).**
  `build_provider_context` / `summary_policy` now use SQL boundary queries
  (`count_chat_messages`, `list_recent_chat_messages`, `list_chat_messages_between`);
  `behavior_tick_retention` prunes idle lines after each persisted tick.
- [x] **B3 — Truncate user input before provider call `[Claude]` (done @ this commit).**
  `max_user_input_tokens` clamps the provider-bound user turn; behavior and
  persistence still use the full original text.
- [x] **M1 — Filter expired memories on retrieval (done @ this commit).**
  `is_expired` + context_builder recall filter; `/memory/memories` unchanged.
- [x] **M2 — Auto-write memories from conversation (rule-based MVP @ this commit).**
  `write_policy.maybe_write_memories_from_turn` runs after `/chat/complete`;
  conservative regex triggers, dedup update, `auto_memory_write` budget gate.
  LLM-based extraction remains future work.

## Backlog

### UI

- [x] Pixel character renderer.
- [x] State animation definitions.
- [x] Chat panel.
- [x] Avatar state debug controls.
- [x] Trapped-in-box idle behaviors.
- [x] Reload chat history from `/memory/messages`.
- [x] Display last-turn token/cost metadata.
- [x] Route empty submit through backend behavior decisions.
- [x] Memory links visualization in UI `[Claude]→Cursor` — read-only `GET /memory/links`
  route + "Boxi 把这些联系起来了" panel. **Spec: `docs/MEMORY_LINKS_UI_SPEC.md`**.

### Provider Layer

- [x] Define provider interface.
- [x] Add DeepSeek adapter.
- [x] Add OpenAI adapter placeholder.
- [x] Add local model adapter placeholder.
- [x] Add provider config file.
- [x] Add cost estimate metadata.

### Memory

- [x] Define SQLite schema.
- [x] Add database initialization.
- [x] Add message persistence.
- [x] Add memory CRUD.
- [x] Add mood state persistence.
- [x] Add retrieval policy.
- [x] Add summary policy.

### Behavior

- [x] Define behavior decision contract.
- [x] Implement local state variables.
- [x] Implement reply/silent/refuse/interrupt/proactive decisions.
- [x] Add persona prompt.
- [x] Add structured LLM response parser.

### Security

- [x] Add allowed folders config.
- [x] Implement path permission gateway.
- [x] Add file access log.
- [x] Add symlink escape tests.
- [x] Review Vite/esbuild dev-server audit advisory before exposing dev server beyond localhost.

### Text MVP

- [x] Connect frontend chat to backend dialogue endpoint.
- [x] Reload persisted messages on app startup.
- [x] Honor backend `avatar_state` during reply animation.
- [x] Surface basic token/cost metadata in UI.
- [x] Route empty submit through backend behavior instead of frontend-only timing.

### Voice

- [x] Design push-to-talk STT interface.
- [x] Add STT adapter placeholder.
- [x] Add push-to-talk UI and local audio capture flow.
- [x] Add mock STT provider and `/stt/transcribe` route.
- [x] Gate cloud STT behind budget/config flags.
- [x] Add TTS adapter placeholder.
- [x] Define selective speech policy.
- [x] Voice V1: local TTS via macOS `say` (`MacSayTTSProvider`, `config/tts.json`).
- [x] Voice V2: local STT via faster-whisper (`FasterWhisperProvider`, base model, PyAV decode).
- [x] Cloud TTS: 火山/豆包 adapter (`DoubaoTTSProvider`, cloud-gated by `allow_cloud_tts`).
- [x] Voice output: strip stage-direction parentheticals from spoken text (Option A, `textForSpeech`) `[Cursor]`.
- [ ] Latency: reuse 豆包 adapter HTTP connection (persistent httpx client + keep-alive) `[Cursor]`.
- [ ] Latency: streaming TTS backend — 豆包 streaming synth + GET `/tts/stream` (MP3 chunks) `[Claude spec → Cursor]`.
- [ ] Latency: streaming TTS frontend — progressive `<audio>` playback; MUST preserve avatar/TTS race fix `[Cursor]`.
- [ ] Voice cost tracking + per-day/month brake for cloud TTS/STT (parallels S3; not yet covered) `[Claude]`.

### Documentation

- [ ] Update docs after each milestone.
- [x] Add developer setup once scaffold exists.
- [x] Add manual verification checklist.
- [x] Evaluate open-source candidates before building major modules from scratch.

### Maintenance

- [x] Review FastAPI TestClient/httpx2 deprecation warning.
- [x] Fix stale `test_stt_status_route` `[Cursor]` (顺手修). It asserts
  `allow_cloud_stt is False` but Session-26 `config/budget.json` committed it as
  `true` (walls off) → 1 red in `npm run check`. Proper fix: isolate the test's own
  `budget.json` in a tmp `CYBER_COMPANION_CONFIG_DIR` so it's deterministic,
  rather than flipping the assertion to match the mutable live config.
