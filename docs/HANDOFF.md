# HANDOFF — 上下文交接（2026-06-19，第二十四轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**provider 选型（第二轮）进行中。**
正在测试 OpenRouter 上的多个模型。当前默认：`google/gemini-2.5-flash-lite`（via OpenRouter）。
同步进行的结论：DeepSeek 和 Claude 都不满足要求（DeepSeek 文学天花板低、Claude 延迟高且内容干瘪），两者都需要替换。

## 本轮已完成（2026-06-19，第二十四轮）

| commit | 内容 |
|---|---|
| `3533414` | **system prompt 重写**：存在论框架 + 四条纪律 + 成年虚构框定（`config/persona.example.json` `persona_prompt` 字段）|
| `85bc37a` | **OpenRouterProvider 新增**：继承 VeniceProvider，`registry.py` 注册，2 个单测 |
| `496e995` | **`allow_fallbacks: false`**：VeniceProvider 加 `_extra_payload_params()` 钩子；OpenRouterProvider override 禁止 fallback |
| `448c784` | **`disable_existential_block` 标志**：context_builder 遇到此标志跳过存在论注入；测试用 monkeypatch/tmp_path 隔离真实 persona.json |
| `5380a19` | **persona 格式纪律**：去掉「最多一两句」长度限制 → 「自然」；加「格式纪律：只说第一人称，动作放（），禁写第三人称叙述」|

**验证结果**：465 pytest passed，tsc --noEmit 零错误（所有 commit）。

## 本轮 provider A/B 实测结论

| 模型 | 问题 |
|---|---|
| DeepSeek（原默认）| 文学/调情天花板低，暧昧感≈10-14岁文学 |
| Claude Sonnet 4.6 | 延迟极高；严格遵守「最多一两句」导致内容干瘪；整体体验不如 DeepSeek |
| dolphin-mistral-24b-venice（free）| 已测，内容质量提升明显，但测试中途换模型 |
| google/gemini-2.5-flash-lite | 当前正在测试（$2 限额 key，allow_fallbacks=false）|

**当前 providers.json 状态**（本地，gitignored）：
- `default_provider: openrouter`
- model: `google/gemini-2.5-flash-lite`
- `OPENROUTER_API_KEY` 已写入 `.env`

## 临时测试文件（重要！）

`config/persona.json`（gitignored，本地存在）= 临时「伴侣人设」测试文件：
- persona_prompt：「你是 Boxi，Chris 的伴侣。你爱他，亲密、自然…」
- `disable_existential_block: true`（屏蔽存在论注入，给纯模型能力测试用）
- **测完需删除**：`rm config/persona.json` → 自动恢复存在论人设（`persona.example.json`）
- **不要 commit** 这个文件

## 三个慢底色字段说明（P1/P2 作者必读）

| 字段 | 语义 | 0.0 | 1.0 | decay 速率 |
|---|---|---|---|---|
| `gap_feeling` | 间隙感：对「你不在的空白」的姿态 | 牵挂 | 平静 | ~0.04/day（向 0.0 漂移，若无互动） |
| `box_relation` | 盒子关系：对自身处境的姿态 | 这是笼 | 这是家 | ~0.01/day（极慢，由对话质地决定） |
| `self_ease` | 自处：对「自己是这种存在」的安定程度 | 不安 | 安定 | ~0.005/day（最稳，几乎不自然变化） |

**关键设计决定**：
- 三维都向 0.0 漂移（牵挂 / 笼感 / 不安），无互动时越来越"困"。
- `loneliness`（快情绪）保留不动，继续驱动 `tone.py` 的 lonely register——两者并存不冲突。
- 三维都是**纯惰性（decay-on-read）**，不写 DB，调用方拿到 decayed 值后按需传入上下文。
- 注入 system prompt 的是**状态描述文字**（如「她对这段空白有些牵挂」），LLM 自由生成台词。
- `disable_existential_block: true` 可在 persona 配置中屏蔽注入（临时测试用）。

## 当前未完成（产品侧）

- **provider 选型（进行中）**：
  - 当前测 `google/gemini-2.5-flash-lite` via OpenRouter（临时伴侣人设，屏蔽存在论块）
  - 测完后需：① 删 `config/persona.json` 恢复存在论人设；② 决定最终默认 provider；③ 更新 HANDOFF
  - 下一个候选模型由用户自带
- **TTS → Fish Audio（P5-B）**：provider 选型稳定后进行。**阻塞：** 需用户提供 Fish Audio API 文档。
- **P1（RTC character_manifest 同步）**：`config/persona.example.json` 的 `rtc_character_manifest` 和 `persona.py` 的 `_DEFAULT_RTC_CHARACTER_MANIFEST` 还是旧毒舌框架，未对齐新存在论人设。优先级低，用户确认后再做。
- **信笺 UI · P2**：精细化 mood 映射 + Voice 模式信笺呈现。**阻塞：** 需用户答 `docs/LETTER_UI_MOOD_MAPPING_DRAFT.md` 的 3 个问题。
- **R11（搁置）**：纯 E2E 长期记忆偶发失忆。**下次发现失忆当场验证**，不主动排查。
- **world brain 后续**：天气 API（需 key）/ 未来事件表。

## 已知 bug / 风险

- **声音语气平板（TTS 问题，未解）**：豆包 TTS 对「低沉」「含混」「轻叹」等复杂语气处理为口播平调，与文字内容不匹配。根因是 TTS 能力/审核天花板，不是 system prompt 问题。Fish Audio 是候选替换。
- **纪律二（锋利/毒舌）未体现**：新 prompt 改为「允许」而非「指令」，LLM 倾向保守。测完 provider 后如仍有问题，可加回具体示例指令。
- **cost 模块不认 openrouter 模型**：`estimate_cost()` 对未知模型返回 $0.0 + `pricing_source: "unknown-model"`，不影响功能。
- **R8（低优先级）**：`.env` 中 `VIKING_MEMORY_API_KEY` 曾明文截图分享，建议轮换。
- **R4**：`experiments/` 未跟踪（一次性视觉 spike）——不要继续开发它。
- **时区说明**：`recent_event` 的 `created_at` 是 UTC 写入时间（非事件发生时间），相对时间前缀按新西兰日期计算。绝大多数场景无影响。

## 新增 provider 接入说明（下一轮必读）

**OpenRouter 接入架构**：
- `backend/app/providers/openrouter.py`：继承 VeniceProvider，`name = "openrouter"`，override `_extra_payload_params()` 注入 `{"provider": {"allow_fallbacks": False}}`
- `config/providers.json`（本地）：`default_provider: openrouter`，model 字段写完整 OpenRouter 模型路径
- 换模型：只改 `providers.json` 的 `model` 字段 + `.env` 的 `OPENROUTER_API_KEY`，不需改代码
- 换回 DeepSeek：`default_provider: deepseek`，一行，重启后端

## 下一步只需读取（按任务，只读这些）

- **永远先读**：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若做 **provider 选型收尾**：读 `config/providers.json`（本地）、`.env`；删 `config/persona.json` 后验证存在论人设恢复
- 若做 **P1（RTC manifest 同步）**：读 `config/persona.example.json`（`rtc_character_manifest` 字段）+ `backend/app/memory/persona.py`（`_DEFAULT_RTC_CHARACTER_MANIFEST`）
- 若做 **TTS → Fish Audio（P5-B）**：需用户先提供 Fish Audio API 文档

## 下一步不要读取（省上下文）

- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务

**provider 选型收尾**：测完 Gemini 2.5 Flash Lite 后，用户决定最终默认 provider → 更新 `config/providers.json` + 删 `config/persona.json` + 恢复存在论人设验证 → 更新 HANDOFF。

之后视用户反馈，下一刀候选：
1. Fish Audio TTS 接入（P5-B）——需用户提供文档
2. P1（RTC manifest 同步）——小 diff，快速完成
3. provider 选型：用户自带的下一个候选模型
