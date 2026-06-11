# RTC Demo Setup — Stage 2a / 2b (official `rtc-aigc-demo`)

Validate **voice-Boxi over Volcengine RTC** before we wire RTC into our own frontend.
This runbook uses the official demo **adjacent to this repo** — we do **not** vendor it here.

| Stage | Goal | Brain |
|---|---|---|
| **2a** | Prove RTC + account creds work | Doubao **OutputMode 0** (pure S2S) |
| **2b** | Route speech through our soul | **OutputMode 1** + custom LLM = Stage-1 `soul_llm_server` |

Official references:

- Demo repo: [volcengine/rtc-aigc-demo](https://github.com/volcengine/rtc-aigc-demo) (BSD-3-Clause)
- `StartVoiceChat` API: [docs/6348/2123348](https://www.volcengine.com/docs/6348/2123348) (field names)
- Quick-start console (copy JSON): [快速跑通 Demo](https://console.volcengine.com/rtc/aigc/run?s=g) → **接入 API**
- End-to-end S2S guide: [docs/6348/1902994](https://www.volcengine.com/docs/6348/1902994)
- Custom LLM: [docs/6348/1581714](https://www.volcengine.com/docs/6348/1581714)

---

## 0. Prerequisites

1. **This repo** — `.venv` installed, `DEEPSEEK_API_KEY` set (real soul in 2b; mock OK for tunnel smoke).
2. **Node 18+** and **yarn** (demo Server) + **npm** (demo web client).
3. **Volcengine console access** — RTC AIGC app, IAM AK/SK, 端到端实时语音大模型 App ID + Access Token.
4. **Stage 2b only:** `cloudflared` or `ngrok` on PATH (see `scripts/soul_tunnel.sh`).

Copy env names from `.env.example` into this repo's `.env` (never commit values).

---

## 1. Credentials map

Fill `.env` in **this repo**. Paste the same values into the demo's `Server/scenes/*.json`.

| Our `.env` | Demo JSON path | Console source |
|---|---|---|
| `VOLC_RTC_APP_ID` | `RTCConfig.AppId`, `VoiceChat.AppId` | [RTC AIGC 应用列表](https://console.volcengine.com/rtc/aigc/listRTC) |
| `VOLC_RTC_APP_KEY` | `RTCConfig.AppKey` | same (AppKey — server-side only, demo strips it from API responses) |
| `VOLC_ACCESS_KEY` | `AccountConfig.accessKeyId` | [IAM 密钥管理](https://console.volcengine.com/iam/keymanage/) (`AKLT…`) |
| `VOLC_SECRET_KEY` | `AccountConfig.secretKey` | same |
| `DOUBAO_RT_APP_ID` | `VoiceChat.Config.S2SConfig.ProviderParams.app.appid` | 豆包语音 → **端到端实时语音大模型** → App ID |
| `DOUBAO_RT_ACCESS_TOKEN` | `…ProviderParams.app.token` | same → Access Token |
| `DOUBAO_RT_SPEAKER` | inside `…dialog` / TTS speaker fields (console JSON) | optional; default in our Pipecat path: `zh_male_yunzhou_jupiter_bigtts` |
| `DOUBAO_RT_MODEL` | `…dialog.extra.model` or model version field in console JSON | e.g. `1.2.1.1` (O2.0) |
| `SOUL_LLM_API_KEY` | `VoiceChat.Config.LLMConfig.APIKey` | you choose; **required** when cloud calls the soul via tunnel |
| `DEEPSEEK_API_KEY` | — | soul brain (2b); not sent to Volcengine |

**Tip:** After [快速跑通 Demo](https://console.volcengine.com/rtc/aigc/run?s=g) succeeds once, click **接入 API** and paste the generated `VoiceChat` block into a scene JSON — then replace secrets with env vars locally. Field names in the pasted JSON match [6348/2123348](https://www.volcengine.com/docs/6348/2123348).

---

## 2. Clone & run the demo (adjacent, not in this repo)

```bash
# sibling directory — NOT inside 赛博伴侣/
cd "$(dirname "$PWD")"
git clone https://github.com/volcengine/rtc-aigc-demo.git
cd rtc-aigc-demo
```

### 2.1 Demo Node proxy (signs StartVoiceChat)

```bash
cd Server
yarn
yarn dev    # listens http://localhost:3001
```

### 2.2 Demo web client (RTC Web SDK)

In a **second terminal**:

```bash
cd rtc-aigc-demo
npm install
npm run dev   # CRA dev server, default http://localhost:3000
```

The web app proxies OpenAPI calls to `http://localhost:3001` (`src/config/index.ts` → `AIGC_PROXY_HOST`).

**Browser:** Chrome/Edge, allow mic. Use **HTTPS or localhost** (WebRTC requirement).

### 2.3 Scene JSON

Create or edit `Server/scenes/Boxi.json` (copy structure from `Server/scenes/Custom.json`).
Restart `yarn dev` after JSON changes — the Server reads `Server/scenes/*.json` at startup.

Top-level shape (demo convention):

```json
{
  "SceneConfig": { "icon": "…", "name": "Boxi RTC" },
  "AccountConfig": { "accessKeyId": "…", "secretKey": "…" },
  "RTCConfig": { "AppId": "…", "AppKey": "…", "RoomId": "", "UserId": "", "Token": "" },
  "VoiceChat": { "AppId": "…", "RoomId": "…", "TaskId": "…", "AgentConfig": { … }, "Config": { … } }
}
```

Empty `RoomId` / `UserId` / `Token` → demo Server auto-generates them.

---

## 3. Stage 2a — OutputMode 0 (pure S2S, no soul yet)

**Done when:** sub-second RTC voice + barge-in on **your** account; no custom LLM.

### 3.1 Configure `VoiceChat.Config`

Use the console **端到端实时语音大模型** preset. The important block is **`S2SConfig`** (see [6348/1902994](https://www.volcengine.com/docs/6348/1902994)):

| Field (under `VoiceChat.Config.S2SConfig`) | 2a value | Notes |
|---|---|---|
| `OutputMode` | **`0`** | pure end-to-end; Doubao brain |
| `Provider` | `volcano` | fixed for Volcengine S2S |
| `ProviderParams.app.appid` | `DOUBAO_RT_APP_ID` | |
| `ProviderParams.app.token` | `DOUBAO_RT_ACCESS_TOKEN` | |
| `ProviderParams.dialog.system_role` | Boxi persona text | copy from `config/persona.example.json` tone or our `load_persona_system_prompt()` output |
| `ProviderParams.dialog.bot_name` | e.g. `Boxi` | |
| `ProviderParams.dialog.speaking_style` | short style hint | e.g. 毒舌、口语、一两句 |

Example skeleton (fill from console paste — **docs win over this snippet**):

```json
"Config": {
  "S2SConfig": {
    "OutputMode": 0,
    "Provider": "volcano",
    "ProviderParams": {
      "app": { "appid": "<DOUBAO_RT_APP_ID>", "token": "<DOUBAO_RT_ACCESS_TOKEN>" },
      "dialog": {
        "bot_name": "Boxi",
        "speaking_style": "毒舌但不恶毒，口语化，每次一两句",
        "system_role": "<Boxi persona — from console or persona.example.json>"
      }
    }
  },
  "InterruptMode": 0
}
```

`AgentConfig` (same level as `Config`, inside `VoiceChat`):

- `WelcomeMessage` — first spoken line
- `TargetUserId` — leave empty; demo fills at runtime
- `UserId` — bot participant id (demo may auto-fill)

You do **not** need `LLMConfig.Mode: CustomLLM` in 2a.

### 3.2 Manual test

1. Open `http://localhost:3000`, pick the **Boxi** scene.
2. Join room → allow mic → speak Chinese.
3. Expect: fast reply, interruptible (barge-in). Note rough **user_stop → first_audio** latency.

### 2a troubleshooting

| Symptom | Check |
|---|---|
| `NoPermissionForApp` | RTC AppId matches token; IAM AK/SK correct; AIGC product enabled |
| `AccountConfig.accessKeyId 不能为空` | Scene JSON AccountConfig filled; Server restarted |
| No audio / stuck connecting | Browser mic permission; try headphones; check RTC AppKey |
| Wrong persona | `system_role` / `bot_name` under `S2SConfig.ProviderParams.dialog` |

---

## 4. Stage 2b — OutputMode 1 + soul as custom LLM

**Done when:** RTC voice uses **our** `/v1/chat/completions` (persona + memory across turns).

Cloud AIGC must reach your **local** soul → use a tunnel.

### 4.1 Start soul endpoint + tunnel (this repo)

Terminal A — from repo root:

```bash
# .env must include SOUL_LLM_API_KEY (cloud cannot use localhost-only auth)
bash scripts/soul_tunnel.sh
```

The script:

1. Starts `python -m backend.realtime.soul_llm_server` on `SOUL_LLM_HOST:SOUL_LLM_PORT` (default `127.0.0.1:8100`).
2. Starts `cloudflared` (default) or `ngrok` (`SOUL_TUNNEL_PROVIDER=ngrok`).
3. Prints **`SOUL_LLM_PUBLIC_URL`** — paste into demo JSON.

Local smoke (no tunnel):

```bash
curl -s http://127.0.0.1:8100/health
curl -N http://127.0.0.1:8100/v1/chat/completions \
  -H "Authorization: Bearer $SOUL_LLM_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"boxi-soul","stream":true,"messages":[{"role":"user","content":"你好"}]}'
```

### 4.2 Switch demo to OutputMode 1 + CustomLLM

Edit `VoiceChat.Config` in your scene JSON. Keep **`S2SConfig`** for fast ASR/TTS orchestration; add **`LLMConfig`** for the external brain ([6348/1581714](https://www.volcengine.com/docs/6348/1581714), [6348/2123348 CustomLLM](https://www.volcengine.com/docs/6348/2123348)):

| Field | 2b value | Maps to |
|---|---|---|
| `S2SConfig.OutputMode` | **`1`** | hybrid — Doubao ASR/TTS + external LLM |
| `S2SConfig.ProviderParams.app.*` | same as 2a | realtime model auth |
| `S2SConfig.ProviderParams.dialog.system_role` | optional / minimal | orchestration layer persona; **full soul is in our endpoint** |
| `LLMConfig.Mode` | **`CustomLLM`** | third-party OpenAI-compatible |
| `LLMConfig.Url` | **`https://<tunnel-host>/v1/chat/completions`** | from `soul_tunnel.sh` output — include path |
| `LLMConfig.APIKey` | `SOUL_LLM_API_KEY` | sent as `Authorization: Bearer …` by Volcengine cloud |
| `LLMConfig.ModelName` | **`boxi-soul`** | optional; our server accepts `model` in POST body |

Example fragment:

```json
"Config": {
  "S2SConfig": {
    "OutputMode": 1,
    "Provider": "volcano",
    "ProviderParams": {
      "app": { "appid": "<DOUBAO_RT_APP_ID>", "token": "<DOUBAO_RT_ACCESS_TOKEN>" },
      "dialog": { "bot_name": "Boxi", "speaking_style": "口语、简短" }
    }
  },
  "LLMConfig": {
    "Mode": "CustomLLM",
    "Url": "https://xxxx.trycloudflare.com/v1/chat/completions",
    "APIKey": "<SOUL_LLM_API_KEY>",
    "ModelName": "boxi-soul"
  },
  "InterruptMode": 0
}
```

Restart demo Server after edits. **Keep `soul_tunnel.sh` running** for the whole session.

### 4.3 Manual test (memory + persona)

1. Tunnel + soul server up; demo Server + web client up.
2. Say something identity-related: *「我叫小明，记住」* → Boxi 毒舌回复.
3. New turn: *「我叫什么」* → should recall (soul `remember()` off-path).
4. Compare latency vs 2a pure mode and vs local `CYBER_COMPANION_VOICE_MODE=realtime` baseline (~Session 32 table in `docs/SESSION_LOG.md`).

### 4b troubleshooting

| Symptom | Check |
|---|---|
| LLM timeout / generic error | Tunnel still alive; `SOUL_LLM_API_KEY` matches JSON; Url ends with `/v1/chat/completions` |
| 401 from soul | `Authorization: Bearer` matches `.env`; restart soul after key change |
| Empty / silent reply | behavior `silent` decision; check soul logs; try non-empty user utterance |
| Persona OK but no memory | soul server running same `CYBER_COMPANION_DATA_DIR`; only **latest user message** is sent — memory is internal to soul |
| CORS errors in browser | **Ignore** — browser talks to demo Server; only **Volcengine cloud** calls the soul (server-to-server) |

---

## 5. OutputMode 0 → 1 checklist

```
[ ] 2a pure voice works (OutputMode 0, no tunnel)
[ ] soul_llm_server answers curl locally with SOUL_LLM_API_KEY
[ ] soul_tunnel.sh prints public URL; health reachable through tunnel
[ ] VoiceChat.Config.S2SConfig.OutputMode = 1
[ ] VoiceChat.Config.LLMConfig.Mode = CustomLLM + Url + APIKey
[ ] Cross-turn memory verified in 2b
[ ] Latency noted (RTC hybrid vs pure vs pipeline)
```

---

## 6. What stays in this repo

| Artifact | Purpose |
|---|---|
| `backend/app/rtc/` | In-repo `/rtc/prepare`, `/rtc/agent/start`, `/rtc/stop` (Stage 2c) |
| `frontend/src/rtc/` + `RtcVoicePanel` | Browser RTC + subtitles in companion panel |
| `backend/realtime/soul_llm_server.py` | Stage-1 OpenAI-compatible soul |
| `scripts/soul_tunnel.sh` | soul + tunnel helper (Stage 2b) |
| `.env` | all secrets (from `.env.example` names) |
| `docs/RTC_DEMO_SETUP.md` | external demo runbook (reference + debugging) |

Do **not** commit `rtc-aigc-demo/`, tunnel URLs, or credential values.
