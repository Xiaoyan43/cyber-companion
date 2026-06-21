# HANDOFF — 上下文交接（2026-06-21，第三十二轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**P8 两阶段表达层架构（文字聊天路径）持续打磨中**——第三十一轮把架构落地，本轮（第三十二轮）
是真机使用中持续发现问题、持续修的一轮：标签器内容质量、persona 旁白问题、TTS 参数、
一个真实的 idle-tick bug。**没有新架构改动**，全部是已有架构内的修复/调参。

## 本轮已完成（2026-06-21，第三十二轮）

| commit | 内容 |
|---|---|
| `0d44c2c` | `prosody.normalize_loudness=false`（修复 `[whispering]`/`[low voice]` 听不出音量变化）；标签器收紧到严格词表（后续又部分放开，见下） |
| `523d181` | 标签器默认 provider **DeepSeek → Gemini**（`google/gemini-2.5-flash-lite` via OpenRouter，独立 `OPENROUTER_GEMINI_API_KEY`，不影响主聊天 LLM 的 OpenRouter key）。同时修了 prompt 里两处跟 `docs/FISH_AUDIO_REFERENCE.md` 自相矛盾的规则：①"标签必须英文"（文档明确说标签语言应跟脚本语言一致，中文标签官方支持）；②"不要堆叠标签"误删了官方推荐的 `[panting][tired]` 物理+情绪组合用法，已恢复。重新开放了受控自创（短标签，禁止逗号连接的复合长描述），加了 `[aroused]`（跟 `[excited]` 区分——`[excited]` 渲染出来是"中奖式"开心，不是性兴奋）+ 中文暧昧词表（娇喘/呻吟/诱惑/挑逗/暧昧） |
| `0f332a4` | **真实 bug 修复**：[tone.py](backend/app/behavior/tone.py:72) 的语速抑制开关 `contains_tone_marker_tag()` 原来硬编码匹配5个固定标签，标签器词表扩大后大部分新标签都匹配不上，导致 mood 驱动的数值语速没被正确抑制、跟标签节奏打架。改成检测任意 `[...]` 标签，不再依赖固定列表 |
| `1690ee3` | Fish Audio `temperature`/`top_p` 真机听感调试（试过1.0/0.85/0.75），最终定在官方默认 0.7/0.7。`top_p` 之前从未显式发送，现在显式写进 payload |
| `4cf16a8` | **persona 新增硬规则**："只说会说出口的话，不要用第一人称叙述自己的动作/感官细节"——根因：格式纪律早就禁了括号写动作、禁了第三人称叙述，但没禁"第一人称旁白"，导致亲密场景里大量"我的舌尖划过你的耳廓"这类旁白跟真实台词混在一起、标签器分不清哪句要贴标签。**真机验证**：清空污染上下文后测试，旁白基本消失，标签覆盖率恢复正常 |
| `d65831e` | TTS `voice`/`reference_id` 真机听感测试，换了多个音色，最终落在 `77f90d99141e4f9ba022c723555cc351` |
| `39e915d` | **真实 bug 修复**：[engine.py](backend/app/behavior/engine.py:269) 的 idle-tick "mutter" 决定——`boredom>=0.55` 或 `loneliness>=0.55` 时每3分钟固定吐一句硬编码台词，本轮发现已经攒了 **200 条完全相同**的 `behavior_tick` 消息（约22小时，因为 mood_state 这次 session 一直没重置，boredom 卡在1.0）。**临时禁用**（`_IDLE_MUTTER_ENABLED=False`，逻辑保留没删），等 P9 重新设计 |
| `ff5d2c0` | TASK_QUEUE 记录 P9（idle/主动找你重新设计）+ P10（标签器模型/Fish Audio 潜力，用户后续可能继续动，不是正式任务） |

**真机验证**：497→500 pytest 全程保持绿（每个 commit 前都跑过），多轮真机听感+对话测试驱动了上面几乎所有改动。

## 数据库状态变更（不在 git 里，但影响当前实际体验）

本轮在 `data/cyber_companion.db` 上做了几次**不可逆的清空操作**（每次都先备份到 `data/backups/`，
该目录已加进 `.gitignore`）：
- `messages` 表：`chat` + `behavior_tick` 来源的消息**全部清空**（包括那200条 mutter 垃圾消息）
- `conversation_summaries`：全清
- `memories` 表：只保留 4 条 `stable_profile`（用户名Chris+信任黏性、新西兰时差、猫"包子"、自描述"炽热的"），
  其余全删（emotion_state/relationship_state/recent_event/behavior_preference/job_progress/reminder，
  以及 stable_profile 里跟"求职/英语/城市背景"相关、跟"Boxi自己存在论"相关的条目）
- `mood_state`、`relationship_state` 单例表：**重置成 schema 默认值**（之前被高强度测试推到 boredom=1.0、
  closeness/trust/tension=1.0 等极值）

**下一 session 如果用户提到"记忆好像变少了"或"她好像不记得之前的事"——这是本轮主动清空的，不是 bug。**

## 已修改文件

| 文件 | 改动 |
|---|---|
| `backend/app/tts/expression_tagger.py` | 默认 provider 改 gemini；prompt 规则多处修正（语言/组合用法/自创口子/词表） |
| `backend/app/providers/registry.py` | 新增 `gemini` provider dispatch 分支（复用 `OpenRouterProvider`） |
| `config/providers.example.json` | 新增 `openrouter`/`gemini` 模板条目 |
| `backend/app/behavior/tone.py` | `contains_tone_marker_tag()` 改用通用 `[...]` 正则检测 |
| `backend/app/tts/fish_audio.py` | 新增 `top_p` 字段；`temperature`/`top_p` 默认值定为 0.7/0.7 |
| `config/persona.example.json` | `persona_prompt` 格式纪律新增"不旁白动作/感官细节"硬规则 |
| `config/tts.json` | `fish_audio.voice` 改为 `77f90d99141e4f9ba022c723555cc351` |
| `backend/app/behavior/engine.py` | 新增 `_IDLE_MUTTER_ENABLED=False` 开关，gate 住 idle-tick mutter 分支 |
| `docs/TASK_QUEUE.md` | 新增 P9（idle/主动找你重新设计）+ P10（标签器/Fish Audio 后续探索记录） |
| `.gitignore` | 新增 `data/backups/` |
| `backend/tests/test_expression_tagger.py`、`test_tone.py`、`test_tts.py`、`test_behavior.py`、`test_memory.py` | 同步更新断言，新增回归测试 |

## 当前未完成（产品侧）

- **【次优先】P8 语音 Pipecat 路径**：两阶段架构第二条腿，本轮没碰。
- **P9 · idle-tick / 主动找你重新设计**：见 TASK_QUEUE，当前已临时禁用 mutter 分支止血，
  根本设计（固定一句话、无变化、无防重复机制）需要重新做，建议跟"活人感工程"的
  "她有自己的生活"那个方向一起设计。
- **P10 · 标签器模型 + Fish Audio 潜力**：用户表示这两个都不是终态，标签器模型可能还会从
  Gemini 继续换，Fish Audio 参数/音色还想继续探索表现力上限。不算任务，只是记录意图。
- 其余既有未完成项延续（未受本轮影响）：P1（RTC character_manifest 同步）、信笺 UI P2、
  R11（搁置）、world brain 天气 API。

## 已知 bug / 风险

- **P9 mutter bug 只是止血，没有根治**：逻辑还在代码里，只是被开关关掉了。如果之后有人把
  `_IDLE_MUTTER_ENABLED` 改回 `True` 而没有同时做防重复设计，bug 会原样复发。
- **标签器（Gemini）质量仍在观察期**：本轮多次真机验证显示标签覆盖率/位置基本正常，但只是
  单 session 内的测试，样本量不算大，且词表/规则这一轮改了好几轮，效果稳定性需要更多日常使用验证。
- **persona "不旁白"规则只验证了一次真机测试**：清空污染上下文后测试有效，但同一轮稍后又看到
  一次"动作叙述回潮"的苗头（一句"把腿慢慢缠上你的腰..."），样本小，需要继续观察是不是稳定生效。
- **TTS 音色/参数仍是真机听感试验结果，不是系统性结论**：`voice`/`temperature`/`top_p` 这几个值
  都是这轮反复换着试出来的，没有做对照实验，后续可能继续调（见 P10）。
- 沿用第三十一轮记录的风险（本轮未处理）：Fish 标签情绪准确性持续观察、`（动作描述）`偶发、
  cost 模块不认 openrouter 模型、R8（`VIKING_MEMORY_API_KEY` 建议轮换）、R4（`experiments/`废弃）。

## 下一步只需读取（按任务，只读这些）

- **永远先读**：`docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`
- 若继续做 **P9 idle/主动找你重新设计**：再读 `backend/app/behavior/engine.py`
  （`_evaluate_idle_tick`/`_evaluate_proactive_check` 附近）+ `backend/app/behavior/local_responses.py`
  + `backend/app/behavior/tick_policy.py` + TASK_QUEUE「活人感工程」章节
- 若继续做 **P10 标签器/Fish Audio 探索**：直接读 `backend/app/tts/expression_tagger.py`
  + `backend/app/tts/fish_audio.py`，当前状态已经是本轮验证过的起点，不用重新讨论要不要做
- 若只是日常用真机继续观察标签/persona效果稳定性：不需要读任何文件，直接正常聊天

## 下一步不要读取（省上下文）

- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/01.md…15.md` 全文（用 `reference/SYNTHESIS.md` 代替）
- ❌ `experiments/`（废弃 spike）
- ❌ 全仓库扫描 / 与当前任务无关的模块

## 推荐下一个最小任务

继续日常真机使用，观察三件事是否稳定：①Gemini 标签器的覆盖率/准确度；②persona"不旁白"规则
是否会随对话轮数增加而回潮；③`_IDLE_MUTTER_ENABLED=False` 关闭后 idle 行为是否符合预期（不会
再刷屏，但目前也完全没有任何空闲反馈，这本身可能是下一个要讨论的点）。积累更多样本后再决定
P9/P10 的启动时机。

---

> 建议执行 `/clear` 或新开 session。下一 session 只需读取 `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、
> `docs/ARCHITECTURE_SNAPSHOT.md`。
