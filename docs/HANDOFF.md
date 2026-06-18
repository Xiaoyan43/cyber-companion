# HANDOFF — 上下文交接（2026-06-19，第二十六轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**provider 选型（第二轮）进行中。**
正在测试 OpenRouter 上的多个模型。当前默认：`google/gemini-2.5-flash-lite`（via OpenRouter）。
TTS 已切换为 Fish Audio（文字聊天路径）。

## 本轮已完成（2026-06-19，第二十六轮）

| 文件 | 改动内容 |
|---|---|
| `backend/app/tts/fish_audio.py` | 新建 FishAudioTTSProvider：HTTP streaming，s2-pro，opus，emotion bracket 前置，prosody.speed 映射 |
| `backend/app/tts/registry.py` | 加 fish_audio 分支 |
| `config/tts.example.json` | 加 fish_audio 模板条目 |
| `backend/tests/test_tts.py` | +8 个单测（registry/status/config/stream/emotion/speed/auth） |

**验证**：473 pytest passed（+8），tsc 零错误，实机文字聊天有音频输出 ✅

## 本轮已完成（2026-06-19，第二十五轮）

> 本轮所有改动**尚未 commit**，均为 working tree 修改。

| 文件 | 改动内容 |
|---|---|
| `config/persona.example.json` | 格式纪律：删"动作放（）"→改为"禁止用括号写动作或内心描述"；加"说话方式：口语，自然，不废话，不做客服，不解释自己" |
| `config/persona.json`（gitignored） | 同上 + 加"感受就是感受，直接说。不分析，不加引号，不解释，不用技术词汇替代情感" |
| `backend/app/tts/text_cleanup.py` | `_strip_stage_directions` 大幅简化：删中文括号 strip / `_QUOTED_SPAN_PATTERN` / 占位符机制 / `[...]` fallback strip；现在只 strip 半角 `(...)` |
| `backend/app/main.py` | `/tts/stream` 加 `user_message` 参数：有时用作 `context_texts`（对话上下文），无时回退 `tts_emotion_directive()` |
| `backend/realtime/doubao_streaming_tts_service.py` | Pipecat TTS：去掉 `extract_voice_instruction`，`[#指令]` 现在内联留在合成文本里传给 doubao |
| `frontend/src/api/tts.ts` | `buildTtsStreamUrl` 加 `userMessage` → `user_message` 查询参数 |
| `frontend/src/voice/useTextToSpeech.ts` | `SpeakReplyInput` + `playSpeechChunk` 加 `userMessage`，贯穿到 URL 构建 |
| `frontend/src/App.tsx` | `submitToBackend` 里 `speakReply` 传 `userMessage: userText`；`speakReplyRef` 类型加 `userMessage?` |
| `backend/tests/test_tts.py` | 更新测试匹配新 strip 行为（`（...）` 不再被 strip；`[#...]` 不再被 strip） |

**验证**：`npm run check`（tsc 零错误）+ 465 pytest passed。

## 本轮诊断结论（provider 选型同步观察）

| 现象 | 根因 | 处理 |
|---|---|---|
| TTS 长句"像两个人念" | Doubao 内部分段，情绪不跨段传递；`context_texts` 只影响首段 | TTS 能力天花板，非代码 bug；Fish Audio（P5-B）是长期解法 |
| `（动作描述）` 过多 | 格式纪律"动作放（）"→ LLM 过度执行；去掉指令还不够，需加明确禁令 | 已加"禁止用括号写动作或内心描述" |
| 客服感 | 缺"说话方式"约束，Gemini 默认礼貌风格 | 已加"口语，自然，不废话，不做客服，不解释自己" |
| 解构情感（"想念"加引号、用"数据权重"替代情绪） | 伴侣 persona 无自由表达约束，模型默认 honest-AI 行为 | 已加"感受就是感受，直接说" |
| `context_texts` 用法偏差 | 官方文档：对话 TTS 应传用户上一句话；我们传的是情绪短语 | 已改：文字聊天 TTS 传用户消息 |
| `[#指令]` 通道 | 官方文档：`[#...]` 留在合成文本里；我们之前抽取到 `context_texts` | 已改：Pipecat 路径不再抽取，内联传给 doubao |

## 临时测试文件（重要！）

`config/persona.json`（gitignored，本地存在）= 临时「伴侣人设」测试文件：
- persona_prompt：「你是 Boxi，Chris 的伴侣…」+ 无括号禁令 + 说话方式 + 感受直说
- `disable_existential_block: true`（屏蔽存在论注入，给纯模型能力测试用）
- **测完需删除**：`rm config/persona.json` → 自动恢复存在论人设（`persona.example.json`）
- **不要 commit** 这个文件

## 当前 providers.json 状态（本地，gitignored）

- `default_provider: openrouter`
- model: `google/gemini-2.5-flash-lite`
- `OPENROUTER_API_KEY` 已写入 `.env`

## 当前未完成（产品侧）

- **⚠️ 两轮改动均未 commit**：建议合并为两个 commit：
  1. `feat(tts+persona): ban brackets, user-message context_texts, inline [#指令]`（第二十五轮 8 个文件）
  2. `feat(tts): add FishAudioTTSProvider, switch text-chat TTS to Fish Audio`（第二十六轮 4 个文件）
- **provider 选型（进行中）**：
  - 当前测 `google/gemini-2.5-flash-lite` via OpenRouter（临时伴侣人设）
  - 测完后：① 决定最终默认 provider；② 删 `config/persona.json` 恢复存在论人设；③ 更新 HANDOFF
  - 下一个候选模型由用户自带
- **~~TTS → Fish Audio（P5-B）文字聊天路径~~** ✅ 已完成（第二十六轮）。Pipecat 路径（P1）仍用 Doubao，待单独任务处理。
- **P1（RTC character_manifest 同步）**：`persona.example.json` 的 `rtc_character_manifest` 和 `persona.py` 的 `_DEFAULT_RTC_CHARACTER_MANIFEST` 还是旧毒舌框架，未对齐新人设。
- **信笺 UI · P2**：精细化 mood 映射 + Voice 模式信笺呈现。**阻塞：** 需用户答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个问题。
- **Pipecat 路径 user_message → context_texts**：文字聊天路径已改；Pipecat 路径（`doubao_streaming_tts_service.py`）需把 STT 用户话语线程进 `run_tts()`，未做。
- **R11（搁置）**：纯 E2E 长期记忆偶发失忆。下次发现失忆当场验证，不主动排查。
- **world brain 后续**：天气 API（需 key）/ 未来事件表。

## 已知 bug / 风险

- **TTS 长句断裂（TTS 能力天花板）**：Doubao 单向 HTTP API 对超长文本内部分段，情绪不跨段传递。Fish Audio 是候选替换（P5-B）。
- **`[#指令]` 内联效果待验证**：将 `[#...]` 从 `context_texts` 改为内联文本是基于官方文档推断，实际 doubao API 是否对内联 `[#...]` 有更好响应，需实测。
- **`（动作描述）` 可能仍偶发**：加了禁令，但某些模型对否定指令遵守度不稳定，需观察。
- **cost 模块不认 openrouter 模型**：`estimate_cost()` 对未知模型返回 $0.0，不影响功能。
- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——不要继续开发它。

## 新增 provider 接入说明（下一轮必读）

**OpenRouter 接入架构**：
- `backend/app/providers/openrouter.py`：继承 VeniceProvider，`name = "openrouter"`，override `_extra_payload_params()` 注入 `{"provider": {"allow_fallbacks": False}}`
- `config/providers.json`（本地）：`default_provider: openrouter`，model 字段写完整 OpenRouter 模型路径
- 换模型：只改 `providers.json` 的 `model` 字段 + `.env` 的 `OPENROUTER_API_KEY`，不需改代码

## TTS 管道说明（本轮变更后）

| 路径 | `[#指令]` | `context_texts` |
|---|---|---|
| 文字聊天 `/tts/stream` | LLM 不生成（文字模式无此指令） | 用户上一句话（有时）；回退 `tts_emotion_directive()`（无时） |
| Pipecat `doubao_streaming_tts_service` | 内联留在合成文本里 | 仅 `section_id`（用户 STT 话语暂未接入） |

## 下一步只需读取（按任务，只读这些）

- **永远先读**：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若做 **commit 两轮改动**：`git diff --stat` 确认文件，分两次 commit
- 若做 **provider 选型收尾**：读 `config/providers.json`（本地）、`.env`；删 `config/persona.json` 后验证存在论人设恢复
- 若做 **Pipecat TTS → Fish Audio（P1）**：读 `backend/realtime/doubao_streaming_tts_service.py` + `backend/realtime/companion_brain.py`；pip install pipecat-ai[fish]
- 若做 **P1（RTC manifest 同步）**：读 `config/persona.example.json`（`rtc_character_manifest` 字段）+ `backend/app/memory/persona.py`（`_DEFAULT_RTC_CHARACTER_MANIFEST`）

## 下一步不要读取（省上下文）

- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务

**先 commit 本轮改动**（8 个文件，`npm run check` 已过），然后继续 provider 选型测试。
测完 Gemini 后决定最终 provider → 删 `config/persona.json` → 恢复存在论人设验证 → 更新 HANDOFF。
