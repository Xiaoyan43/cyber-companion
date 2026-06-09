# Spec — V2 RTC Stage 2: OutputMode-1 over RTC (validate via the official demo)

Follows RTC Stage 1 (`soul_llm_server.py`, validated live). **Claude spec → Cursor builds
config/helpers → user runs the browser/mic steps → Claude reviews → checkpoint.** Reuse-first:
**run the official `volcengine/rtc-aigc-demo` as an adjacent reference — do NOT fork it into
this repo.** Our repo stays: soul endpoint + a tunnel/run helper + docs.

## Goal
Prove **voice-Boxi over RTC using the soul** : AIGC-RTC (OutputMode 1) does fast ASR/TTS in
an RTC room; its **custom LLM = our Stage-1 `/v1/chat/completions`** (the soul). Validate
latency + that memory/persona survive, before integrating RTC into our own frontend (later).

## Credentials (all env, never committed)
RTC `VOLC_RTC_APP_ID`/`VOLC_RTC_APP_KEY`; IAM `VOLC_ACCESS_KEY` (`AKLT…`)/`VOLC_SECRET_KEY`
(signs `StartVoiceChat`); realtime model `DOUBAO_RT_APP_ID`/`DOUBAO_RT_ACCESS_TOKEN`; optional
`SOUL_LLM_API_KEY` (the bearer the AIGC server sends to our endpoint).

## Stage 2a — Prove RTC works (pure mode, demo as-is)
Goal: confirm the heavy RTC plumbing + the user's account/creds work, end-to-end, **before**
adding the soul. Cursor: write a short **`docs/RTC_DEMO_SETUP.md`** runbook:
- Clone `volcengine/rtc-aigc-demo` **outside** this repo; `cd Server && yarn && yarn dev`; web
  client per its README (RTC Web SDK, needs HTTPS/localhost).
- Fill its config (`Server/scenes/*.json` `VoiceChat` section + console "快速跑通 Demo" params)
  with the user's RTC AppId/AppKey, IAM AK/SK, and the **Doubao realtime model** (端到端实时
  语音大模型) creds, **OutputMode 0** (pure), Boxi persona via `system_role`/`bot_name`/
  `speaking_style`.
- **User manual step:** open the web client, talk → confirm sub-second RTC voice + barge-in.
Done when: RTC voice works on the user's account (pure mode). No soul yet.

## Stage 2b — Switch to OutputMode 1 + our soul
- Reconfigure the demo's `VoiceChat` → **`OutputMode 1`** with a **custom/third-party LLM**
  pointing at our Stage-1 endpoint (`/v1/chat/completions`, model `boxi-soul`, key
  `SOUL_LLM_API_KEY`). Verify the exact custom-LLM field names against docs **6348/1558163**.
- **Tunnel:** Volcengine's *cloud* AIGC server must reach our *local* soul endpoint → Cursor
  adds a helper (`scripts/soul_tunnel.sh` using cloudflared/ngrok) + docs: run
  `python -m backend.realtime.soul_llm_server`, expose it, put the public URL in the demo's
  LLM-URL config. Note in `docs/RTC_DEMO_SETUP.md`.
- **User manual step:** talk in the web client → Boxi replies in the 毒舌 persona, **remembers
  across turns** (soul is the brain), latency measured.
Done when: voice-Boxi over RTC runs through the soul; latency + memory/persona confirmed.

## Tasks for Cursor (repo-side only)
1. `docs/RTC_DEMO_SETUP.md` — the 2a/2b runbook above (clone-adjacent, configure, run, the
   OutputMode-0→1 switch, the custom-LLM URL).
2. `scripts/soul_tunnel.sh` — start the soul endpoint + a tunnel; print the public URL to paste
   into the demo. Keys from env; nothing committed.
3. `.env.example` — add the RTC/IAM/realtime var names (no values).
4. Confirm `soul_llm_server.py` works behind a tunnel (CORS/headers as the AIGC server needs;
   add only if required — verify against docs).
5. **No new repo deps for the demo itself; do not vendor the demo. No `backend/app/**` /
   `frontend/**` changes.**

## Done criteria
1. `PYTHON_BIN=.venv/bin/python npm run check` green (repo unaffected — this stage is mostly
   external demo + docs/scripts).
2. 2a: RTC pure voice works on the user's account.
3. 2b: RTC voice routes through the soul endpoint (Boxi persona + cross-turn memory); latency
   logged vs the WS S2S baseline.
4. Diff confined to `docs/**`, `scripts/**`, `.env.example`, `backend/realtime/soul_llm_server.py`
   (only if a tunnel/CORS tweak is needed).

## Boundaries
- Reuse the official demo as a reference/validation harness; don't fork it in.
- Keys env-only; the soul endpoint stays the only thing the AIGC server calls.
- Soul reused, not edited. Current Pipecat S2S + pure realtime modes stay working.
- If `StartVoiceChat` auth/signing or the custom-LLM contract fights us, report the specific
  blocker (signature? OutputMode? LLM URL reachability?) — don't thrash.
