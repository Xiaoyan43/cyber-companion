# HANDOFF — 上下文交接（2026-06-27，第七十三轮 · 语音并行轨稳定化 checkpoint）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## ⚠️ 给新 session 的最小上手指引

1. 先读本文件 + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`，**不要全仓库扫描**。
2. **当前分支 = `codex/voice-stabilization-20260627`，voice implementation checkpoint = `dd026ee`**。已从 `codex/soul-runtime` 的 `f1298d3` 分离；工作树仍有故意不提交残留：
   - `backend/realtime/run_voice.py`（`_LatencySpikeLogger`，P8-C 探针）——**不要 commit**。
   - untracked：`experiments/tagger_ab.py`（已本地改过，见下）、`experiments/tagger_listen_haiku.py`、
     `voice_compare.py`、`data/tagger_eval/`、`.mcp.json` 等实验/数据。
3. 生效配置（`config/providers.json` 与 `.env` gitignored；`config/tts.json` 已进 voice checkpoint）：
   - `config/providers.json`：tagger 跑 `anthropic/claude-haiku-4.5`（provider 条目已正名为 `"tagger"`）。
   - `config/tts.json`：`fish_audio.model = s2.1-pro`，音色嘉岚 `fbe02f8306fc4d3d915e9871722a39d5`。
   - `.env`：`CYBER_COMPANION_VOICE_FISH_NORMALIZE=false`（第六十九轮 A/B 胜出项）。
4. `normalize=false` 已进入 Pipecat 真实多轮链路，用户听感「还可以」；发平/句间呼吸的最终优化延后与音色和其他参数一起评估，不继续单点追节奏标签。
5. 本轮发现单字尾音自回声：Boxi「先睡，乖。」→ ASR「乖。」→ Boxi 再回复。已做窄修复：仅在停止播放后 2s 内拦截与尾字完全一致的单字。真机已生成单字回复「一」，本次未被 ASR 回收且未自触发；直接拦截命中待自然复现时观察。
6. 第七十三轮稳定化后已重新跑通：后端全量 **745 passed**、invariant **366 passed**、前端 `tsc --noEmit` 通过、`git diff --check` 通过。
7. Codex 已配置 Fish 官方 agent tooling（全局，不在仓库 commit 内）：Fish Docs MCP + `fish-audio-api`/`fish-audio-sdk` skills。新会话可能需要重启后才热加载。
8. 标签器/翻译共用的 OpenRouter provider 已从误导性的 `"gemini"` 正名为 `"tagger"`；实际模型仍是 Haiku。新环境变量为 `OPENROUTER_TAGGER_API_KEY`，但注册层会自动兼容旧 `OPENROUTER_GEMINI_API_KEY`，本机无需立即迁移。
9. B 类位置的真正杠杆是移除 tagger prompt 的动态 mood 注入：已写完的正文是唯一情绪来源。neutral-mood A/B 两轮 10/10 不再提前染色，`position_v5` **已由用户听感验收通过，决定保留**。
10. **语音微调与 dirty 分轨均已结案**，下一会话不要继续追加 tagger/Fish 规则。下一步进入产品体验整合；日常使用中被动观察单字自回声即可。

---

## 第六十七轮已完成（2026-06-26，**已 commit `08bf0ec` + `0d51acb`**）

### ✅ 代码：Rule 3 重写 + 跨句去重护栏

**方向一 · Rule 3 重写（Haiku-friendly 明确判断协议）**
- `TAGGER_INSTRUCTION_TEMPLATE` Rule 3：从「软倾向不加」→「默认不加；仅条件 A（情绪切换）或 B（开头突出）才加」。
- 两条 `禁止` 针对 Haiku 常见违规：按句机械分配 / 循环轮换不同标签制造多样感。
- 测试：`"逐句重新判断"` → `"每句话默认不加标签"`。

**方向二 · `suppress_repeated_leading_tags`**
- 新函数 + `_SOUND_EFFECT_TAG_INNERS` / `_DEDUP_EXEMPT_TAG_INNERS`（`expression_tagger.py`）。
- 连续两句句首非 exempt 标签完全相同 → 删后一句（延续基调，非新切换）；无标签句重置基线。
- 接入 `apply_expression_tags`（全文路径）+ `main.py` `_tag_reply_by_sentence`（逐句 join 后）。
- +10 单测（`test_expression_tagger_guards.py`），tagger 相关 **69 pytest 全绿**。

**已修改文件（`08bf0ec`）**
- `backend/app/tts/expression_tagger.py`
- `backend/app/main.py`
- `backend/tests/test_expression_tagger.py`
- `backend/tests/test_expression_tagger_guards.py`

### ✅ 量化验证（同轮 Cursor session，`experiments/tagger_ab.py` N=3）

脚本走**生产逐句路径** + join 后 `suppress_repeated_leading_tags`（本地 untracked 版已改好，未 commit）。

| 模型 | 场景 | 改前基线 | 改后（含护栏） |
|------|------|----------|----------------|
| **Haiku** | long_story | ~1.00 | **0.67** |
| **Haiku** | short_chat | ~1.00 | **0.56** |
| Gemini | long_story | 0.43 | **0.43**（无回归） |
| Gemini | short_chat | 0.11–0.33 | **0.33–0.44** |

**结论**：Haiku 密度从「几乎句句贴」降到「约 2/3 句有标签」，主目标达成；Gemini 未退化。

**同轮 `tagger_eval.py`（全文路径，4 fixture，Haiku）**

| Fixture | 标签 | tagged_sent | 评价 |
|---------|------|-------------|------|
| 01 揶揄+想念 | `[sarcastic]` + `[nostalgic]` | 2/4 | 转折处分贴，好 |
| 02 冷淡失落 | `[lonely]` 仅句首 | 1/4 | opening_only，略平 |
| 03 得意挖苦 | `[smug]` 仅句首 | 1/3 | opening_only，可接受 |
| 04 揶揄→心软 | `[soft tone]` 在「不过」前 | 1/4 | 转折点句中插入，好 |

### ✅ Fish 文档对照 + 密度/位置/语义分析（同轮讨论，无新代码）

对照 [Fish Emotion Control](https://docs.fish.audio/developer-guide/core-features/emotions) +
`docs/FISH_AUDIO_REFERENCE.md` §3–4，结论摘要：

**密度**
- Fish：「space out emotional changes」「短文本别滥用」「一句最多一种情绪（不是每句都必须有标签）」。
- **不是过少**：长故事 0.67、短对话 0.25–0.56，已从过密回到合理区间。
- **长叙事略密于 Fish 理想（~0.35–0.50）**，但可接受；短对话偏克制，符合官方「短文本别滥用」。

**位置准确度（中等偏上）**
- **做得好**：情绪转折点句中插入（04 `[soft tone]`、01 后半 `[nostalgic]`）；break 冗余/悬空标签有代码护栏。
- **仍偏弱**：B 类常偷懒贴句首（整句染色，精度不如句中贴）；`opening_only`（02/03 仅开头一标）。
- **未做**：task 2 的 P2（词中插 `那[sighing]股`）/ P3（无意义句首堆叠）守卫。

**语义对齐 & A/B 类标签用法**
- **Haiku（当前生产）**：B 类情绪跟情节走（`[nostalgic]`/`[sad]`/`[relieved]`），A 类滥用少（task 3 prompt 仍有效）。
- **Gemini**：密度优，但 A 类语义错（`[sighing]`/`[panting]` 贴拟声「扑通」）、生造标签（`[heartbeat]`、`[wistful]`）、脏标签（`[beklagende]`）。
- **架构边界不变**：代码只强制格式/明显非法位置；**情绪恰当性 & A/B 类选对**靠 LLM，`_preserves_original_wording` 会在改字插标时整句放弃标签。

**架构决策（仍有效）**：禁止用代码硬删 `[sighing]` 等语义判断——见 TASK_QUEUE task 3 结案记录。

### ✅ 运维：前后端已重启供真机检测

- 后端：`http://127.0.0.1:8000`（`bash scripts/dev_backend.sh`）
- 前端：`http://127.0.0.1:5173`（`npm run dev --workspace frontend`）
- 用户开新 session 前若服务已停，重新 `npm run dev:backend` + `npm run dev:frontend`。

---

## 第六十八轮补充（2026-06-26，**未 commit，仅更新 HANDOFF + Codex 全局配置**）

### ✅ 用户真机听感结论已记录

- 当前标签密度/稳定性：**较为稳定**，不再是第六十七轮前那种「几乎句句贴」的主问题。
- 主要听感问题：**稍微发平**，重点像是**语句之间停顿不足、没有顿挫感**。
- 方向判断：下一步不应全局加密度，也不应回退到句句贴；主线应切到 Fish TTS 的**节奏/韵律控制**。

### ✅ Fish 文档复核后的新调优线索

只读 `docs/FISH_AUDIO_REFERENCE.md`、`docs/PIPECAT_REFERENCE.md`、`docs/PIPECAT_AUDIT.md` 与当前 Fish/Pipecat 装配，结论：

1. **节奏标签疑似需要 A/B**
   Fish S2-Pro 文档里的节奏类标签是 `[pause]` / `[short pause]` / `[long pause]`，但当前标签器 prompt 和守卫用的是 `[break]` / `[long-break]`。历史上 `[break]` 似乎有过效果，不能直接断言是 bug；但这正贴合「句间没顿挫」症状，应优先固定文本 A/B。
2. **Pipecat 语音路径没有显式传 Fish 表达参数**
   `backend/realtime/run_voice.py` 当前只传 `voice` / `model` / `latency=balanced`。Pipecat `FishAudioTTSService.Settings` 支持 `normalize`、`temperature`、`top_p`、`prosody_speed`、`prosody_volume`，但语音路径未显式设置。
3. **文字路径和语音路径配置不一致**
   `backend/app/tts/fish_audio.py` 已传 `temperature/top_p`，并设置 `prosody.normalize_loudness=false`；Pipecat 语音路径仍走默认 `normalize=True`，可能压平 whisper/shouting 等动态。
4. **`latency=normal` 仍不要碰**
   项目已真机确认 normal 在 Pipecat 多轮会失声，且首字节约 3.5s；继续锁 `balanced` 是当前正确取舍。

### ✅ Codex 侧 Fish 官方 agent tooling 已配置

根据 Fish 官方博客 `llms.txt + MCP + Agent Skills`：

- 已在 `/Users/xiaoiwawang/.codex/config.toml` 追加全局 MCP：
  - `[mcp_servers.fish_audio]`
  - `url = "https://docs.fish.audio/mcp"`
  - 备份：`/Users/xiaoiwawang/.codex/config.toml.bak-fish-audio-mcp`
- 已安装 Codex 全局 skills：
  - `/Users/xiaoiwawang/.agents/skills/fish-audio-api`
  - `/Users/xiaoiwawang/.agents/skills/fish-audio-sdk`
- 当前会话可能不会热加载；新 Codex 会话应可发现。以后 Fish API/SDK 代码生成优先用 skill，开放式/最新文档问题优先查 MCP。

---

## 第六十九轮补充（2026-06-27，**未 commit，Fish 节奏/参数 A/B**）

### ✅ 固定文本节奏标签 A/B 已做，结论：不要迁移词表

新增 `experiments/fish_rhythm_ab.py`，真实 Fish HTTP 生成固定文本 A/B：

- 输出目录：`data/fish_rhythm_ab/s21-pro-free/`
- 比较：无标签 / `[break]` / `[long-break]` / `[pause]` / `[short pause]` / `[long pause]`
- 用户听感：**区别不是很大**
- 决策：**暂不把生产 prompt/guard 从 `[break]` 系迁移到 `[pause]` 系**；节奏标签词表不是当前主矛盾。

### ✅ Fish 参数 A/B 已做，结论：只关 normalize

同一脚本生成 `pause` 固定文本参数 A/B：

- `pipecat_default_norm_true`（近似 Pipecat 默认 `normalize=True`）
- `normalize_false`
- `normalize_false_speed_094`
- `normalize_false_speed_094_temp_08`

用户听感：

- **`normalize=false` 最正常**
- 其他三组句间呼吸略别扭

已改：

- `.env` 增加 `CYBER_COMPANION_VOICE_FISH_NORMALIZE=false`
- `backend/realtime/run_voice.py` 已支持可选 Fish Settings：`normalize` / `temperature` / `top_p` / `prosody_speed` / `prosody_volume`
- `.env.example` 标注当前推荐：只关 normalize；降速/升温仅作为后续实验项
- 测试：`pytest backend/tests/test_voice_config.py backend/tests/test_fish_audio_pipecat_tts.py` → 11 passed

下一步：**跑 Pipecat 真机语音链路验证 `normalize=false` 是否也改善真实对话**。不要同时开 `prosody_speed=0.94` 或 `temperature=0.8`。

### ✅ 模型版本 A/B 样本已生成（S2.1 Pro paid vs free vs S2.0/S2-Pro）

用户多轮真机怀疑问题可能来自 `s2.1-pro-free`。按 Fish 文档/API 语义确认：

- S2.1 Pro paid：`model` header 用 `s2.1-pro`
- S2.1 Pro Free：`s2.1-pro-free`
- 上一代 S2 / S2.0：`s2-pro`

新增 `experiments/fish_model_ab.py`，只做离线 HTTP `/v1/tts` 样本，不改生产配置。

生成参数：

- voice：嘉岚 `fbe02f8306fc4d3d915e9871722a39d5`
- models：`s2.1-pro` vs `s2.1-pro-free` vs `s2-pro`
- fixtures：5 条不同情绪（teasing / soft / angry / excited / lonely）
- `format=mp3`
- `latency=balanced`（贴近当前 Pipecat 真实链路）
- `temperature=0.7`
- `top_p=0.7`
- `prosody.normalize_loudness=false`

输出：

- `data/fish_model_ab/s2.1-pro/*.mp3`
- `data/fish_model_ab/s2.1-pro-free/*.mp3`
- `data/fish_model_ab/s2-pro/*.mp3`
- `data/fish_model_ab/manifest.json`

下一步：用户人工横向听同名文件（如三组 `01_teasing.mp3`），判断 paid S2.1 Pro 是否明显优于 Free，或 `s2-pro` 是否更自然。

用户听后三组结论：**`s2.1-pro-free` 明显过于粗糙，当前 `s2.1-pro` 最好**。已把本地 `config/tts.json`
切到 `s2.1-pro`；Pipecat 构造验证为 `model=s2.1-pro`、`latency=balanced`、`normalize=False`。

### ✅ Paid S2.1 Pro 上已重做停顿/normalize 样本

因为前一轮 `[break]`/`[pause]` 和 `normalize=false/true` 判断基于 `s2.1-pro-free`，用户要求在 paid
`s2.1-pro` 上重测。已用同一固定文本、同一嘉岚音色、同一参数生成：

- `data/fish_rhythm_ab/s21-pro/rhythm_norm_false/*.mp3`
- `data/fish_rhythm_ab/s21-pro/rhythm_norm_true/*.mp3`

每组 6 条：`none` / `break` / `long_break` / `short_pause` / `pause` / `long_pause`。

用户听感结论：

- 停顿/顿挫：各标签**没什么区别**，不要因为这轮去大改节奏词表。
- `normalize=false`：比 `true` **稍微好一点**，当前 `.env` 保留 `CYBER_COMPANION_VOICE_FISH_NORMALIZE=false`。
- 奇怪现象：两组里 `long_pause` 的**音质**都更好一些，但这不像是“停顿/顿挫”改善，更可能是 Fish 生成随机性、
  分段/采样路径变化，或 `[long pause]` 对整句韵律的副作用。**不要直接把所有停顿迁移成 `[long pause]`**；
  若要利用它，需再做多次重复样本确认稳定性。

### ✅ B 类标签位置 prompt 精修已做

用户决定不再围绕停顿标签打转，转向 B 类标签位置精修。已修改
`backend/app/tts/expression_tagger.py` 的 `TAGGER_INSTRUCTION_TEMPLATE`：

- 强化语气/情绪/音调类标签不要偷懒全放句首。
- 优先贴在情绪真正开始的位置，尤其是转折词或情绪起点前：如「不过」「但是」「其实」「只是」「偏偏」
  「突然」「后来」「那一刻」。
- 只有整句从第一个字开始就是同一种明确情绪时，才句首贴。
- 新增正反例：
  - `我嘴上嫌你烦，[soft tone]不过还是给你留了灯。`
  - `我今天去了那家店，[sad]后来才发现你不在。`

边界：这次**没有**新增代码语义 guard。B 类标签位置属于语义判断，仍交给 tagger LLM；代码只做格式/明显非法位置护栏。

测试：`pytest backend/tests/test_expression_tagger.py backend/tests/test_expression_tagger_guards.py backend/tests/test_main_tag_reply_by_sentence.py`
→ 76 passed。

### ✅ B 类位置精修听感样本已生成

新增 `experiments/tagger_position_listen.py`，用真实 tagger（当前 `"gemini"` provider 实际 Haiku）+
paid `s2.1-pro` + 嘉岚 + `latency=balanced` + `normalize_loudness=false` 生成 5 条位置专项样本：

- 输出：`data/tagger_position_listen/s2.1-pro/*.mp3`
- manifest：`data/tagger_position_listen/s2.1-pro/manifest.json`

样本专门设计成「前文中性 → 当前句中途转情绪」，用来听 B 类标签是否贴在转折/情绪起点：

- `01_tease_to_soft`：成功贴到 `[soft tone]不过`
- `03_dry_to_sarcastic`：成功贴到 `[disdainful]其实`
- `02_neutral_to_sad`：仍偏句首 `[sad]我本来只是想随便看看...`，没贴到「后来」
- `04_calm_to_worried`：过早贴 `[worried]水也喝一口`，且第二句又贴 worried
- `05_story_to_nostalgic`：opening-only / 重复 `[nostalgic]`

初步观察：prompt 精修有作用，但 Haiku 仍不稳定；下一步以用户听感为准。若仍不满意，可能要继续 prompt 收紧
「不要提前染中性铺垫」，或改 tagger 策略，而不是继续调 TTS。

### ⚠️ 已撤销：`[sad]` / `[worried]` high-risk guard

曾短暂尝试把 `[sad]` / `[worried]` 强制替换成 `[low voice]` / `[soft tone]`，但用户复听后判断：

- 02 / 04 的主要问题是**位置**，不是 `[sad]` / `[worried]` 标签本身。
- 不需要替换 `[sad]` / `[worried]`。
- 也不要在 prompt 里保留“谨慎使用”提醒。

因此已撤销：

- `_normalize_high_risk_tone_tags()` 删除。
- `[sad]` / `[worried]` 保留在基础情绪词表。
- prompt 不再提示它们是 high-risk。
- 相关测试断言已恢复。

保留结论：下一步继续处理 B 类标签**位置**，不要用代码硬替换情绪标签。

---

## 第七十轮补充（2026-06-27，**未 commit，Pipecat 真机 + 单字自回声修复**）

### ✅ `normalize=false` 真实链路已验证

- 启动日志确认：`Fish TTS explicit settings: {'normalize': False}`。
- 真机多轮完成 STT → soul → 逐句 tagger → Fish TTS；一轮 `user-stopped→first-audio = 2.576s`。
- 用户听感：「还可以」；发平和句间呼吸暂不继续单点调参，最后与换音色/其他设置统一评估。
- 继续保留 `s2.1-pro + latency=balanced + normalize=false`；不开 `prosody_speed=0.94` / `temperature=0.8`，不迁移 `[pause]` 词表。

### ✅ 单字尾音自回声已做窄修复

真机时 Boxi 上轮末句是「先睡，乖。」，播放尾音被 ASR 识别成新的用户 final「乖。」，
触发 Boxi 再回复「嗯，这就乖了。」。根因是现有 `is_self_echo` 故意保留单字用户回复，
`min_chars=2` 让单字尾音漏过。

修复：

- 保留通用匹配器 `min_chars=2`，不全局吞掉「嗯」/「好」这类真实单字接话。
- `SelfEchoGate` 新增 2s 窄窗口：只有用户 final 正好等于 Boxi 尾字时才拦截，且不做模糊单字匹配。
- +3 回归测试：1.5s 内「乖」被拦截；2.1s 后「乖」保留；窗口内无关「好」保留。
- 测试：21 passed。真机又运行三轮，Boxi 实际生成单字回复「一」；本次扬声器尾音没有被 ASR 回收，因此未直接命中 `self-echo suppressed`，但也未自触发下一轮。随后真实用户输入正常通过。

---

## 第七十一轮补充（2026-06-27，**未 commit，标签器 provider 正名**）

### ✅ `gemini` 别名已改为模型无关的 `tagger`

- `DEFAULT_TAGGER_PROVIDER` 和共用翻译 provider 的默认名统一为 `"tagger"`。
- `config/providers.example.json` 及本机 `config/providers.json` 已改用 `"tagger"`；本机模型仍是 `anthropic/claude-haiku-4.5`。
- 新环境变量名为 `OPENROUTER_TAGGER_API_KEY`。注册层优先用新名，新名缺失时自动回退到旧 `OPENROUTER_GEMINI_API_KEY`；旧 `"gemini"` provider key 也保留为配置兼容别名。
- 本机按 dev backend 的 `.env` 加载方式验证：`tagger` 可解析且旧密钥兼容生效，未打印密钥。
- 测试：相关切片 67 + 54 passed；后端全量 744 passed；前端 `tsc --noEmit` 通过；`git diff --check` 通过。

---

## 第七十二轮补充（2026-06-27，**未 commit，B 类位置 prompt + 真实样本**）

### ✅ 根因坐实：动态 mood 注入在二次创作情绪

- `position_v2` 坐实旧问题：04 提前把中性「水也喝一口」染成 worried，05 在景物铺垫和「那一刻」重复 nostalgic。
- 继续叠具体示例的 `position_v3/v4` 不稳定：Haiku 会模仿示例吞掉前缀，或仍然被 mood 拉回句首。因此撤掉过拟合的长示例，不再继续叠 prompt。
- A/B：同样 5 个 fixture，只把 mood 设为 neutral，两轮共 10/10 条都没有提前染中性铺垫，情绪点稳定落在正文证据附近。
- 生产改动：移除 `TAGGER_INSTRUCTION_TEMPLATE` 的动态 `mood_block`。`mood` 参数暂保留在函数契约中保持调用兼容，但不再进 prompt；已写完的 Boxi 正文是 tagger 的唯一情绪来源。
- 实验脚本新增 `--label` 可重复选项，可只重生成单个 fixture，避免重复付费调其他样本。
- 最终 `position_v5` 五条全部正确：01 `[soft tone]不过`；02 在「那里安静得有点过分」前；03 `[sarcastic]其实`；04 在「我有点担心」前；05 `[nostalgic]那一刻`。
- 样本：`data/tagger_position_listen/s2.1-pro/position_v5/`，当前 Haiku tagger + paid `s2.1-pro` + `normalize_loudness=false`。
- 测试：相关 92 passed；后端全量 745 passed；`git diff --check` 通过。

### ✅ 用户听感验收通过

2026-06-27，用户听完 `position_v5` 并明确决定保留。B 类位置精修正式结案；不再重开动态 mood 注入、high-risk 替换或节奏词表迁移。

---

## 当前项目目标

赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标

**Fish/TTS/tagger 微调与工程稳定化均已结案。语音改动已在独立分支形成四个可审查实现 checkpoint，下一步转入产品体验。**
文字路径逐句化（P0+P1）已在 `111c70c` 落地并真机验证。

---

## 已知 bug / 风险

- **~~Haiku 密度过高~~ → 已大幅改善**：`tagger_ab` N=3 证实 long_story 1.00→0.67；用户真机反馈当前较稳定。
- **当前听感偏平**：主要像语句之间停顿/顿挫不足，不是标签数量不足。
- **节奏标签词表 A/B 差异不大**：当前 prompt/guard 仍保留 `[break]` / `[long-break]`，不要仅凭文档迁移到 `[pause]` 系。
- **Pipecat Fish 参数已暴露，A/B 胜出项是 `normalize=false`**：本地 `.env` 已设置；降速/升温听感别扭，先不要启用。
- **~~标签器 provider 命名债~~ → 已完成**：默认 key 已改为 `"tagger"`，并保留旧 key/env 兼容。
- **位置精度**：B 类句首粗放、opening_only；A 类一旦出现容错极低——真机重点听。
- **Gemini A 类语义错**：若回退 Gemini 换密度，会重新引入音效标签误用。
- **改字护栏副作用**：Haiku 试图给「扑通」插 `[扑通]` 类标签时被拒绝 → 该句无标签（正确降级，但丢表达）。
- Fish 账号 Free 套餐锁住克隆/Voice Design（不阻塞）。
- **自回声残余**：本轮已补单字干净尾音；ASR 增字/误听成非干净后缀仍是内容匹配器的固有边界，真治仍是未来 WebRTC/AEC。
- 沿用：P12、P9-P2-C、P9-D、日语音色未接后端、Fish WS 空闲断连。

---

## 当前未完成

### 🟡 单字自回声后续观察

代码和确定性回归已完成；真机生成单字回复时未重现回声，暂不为了制造回声继续消耗云调用。

推荐最小顺序：

1. 下次日常真机对话若再出现尾字回收，确认日志出现 `self-echo suppressed`，并且没有新的 `Boxi decision=reply`。
2. 若仍自触发，记录 ASR final 文字和相对 `BotStopped` 时间；不盲目继续放宽单字匹配。

### ✅ 位置精修（用户听感 PASS，结案）

- Prompt 保留抽象证据规则：中性铺垫不贴标签，后文情绪不得倒灌。
- 动态 mood 不再注入 tagger；正文是唯一情绪来源。
- `position_v5` 已由用户听感验收并决定保留。
- 代码守卫（未做）：P2 词中插、P3 无意义句首堆叠（task 2 遗留，真机未复现故降级过）。

### 🟢 Fish 音色克隆/设计（等用户升级 Plus）

详见 memory `fish-voice-creation-plan`。当前维持嘉岚。

### 沿用未完成项

task 4 非干净后缀自回声/AEC、P12、P9-P2-C、P9-D、日语音色切换。

---

## 历史背景（第六十五轮 `111c70c`，摘要）

- P0/P1：文字路径标签器逐句化 + 并发，单句失败不再整段作废。
- 模型 A/B：Haiku 情绪准 / Gemini 密度优；MiniMax-M3 出局。
- task 3（第六十三轮 `70d5c7a`）：A/B 类音效 vs 语气 prompt 修正，`[sighing]` 滥用从 6+/轮 降到 ~1–2/20 句。
- 嘉岚音色无问题；长叙事听感差根因是密度过高（本轮已量化改善）。
- Fish 克隆/Voice Design 需 Plus，用户暂不升级。

---

## 下一步只需读取（按任务挑）

- **永远先读**：本文件 + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- **节奏/韵律 A/B**：`docs/FISH_AUDIO_REFERENCE.md` §2/4/7/9 + `docs/PIPECAT_REFERENCE.md` §4/8 +
  `docs/PIPECAT_AUDIT.md` B 项 + `backend/realtime/run_voice.py` + `backend/app/tts/fish_audio.py` +
  `backend/app/tts/expression_tagger.py`（节奏词表/guard）。
- **checkpoint 状态**：`docs/SOUL_RUNTIME_STATUS.md` + `git status`；确认只剩 `_LatencySpikeLogger` 与明确排除的本地实验/数据。

## 下一步不要读取

- ❌ `docs/SESSION_LOG.md`
- ❌ `reference/`（Pipecat/Fish 文档线已结；Fish 查 `docs/FISH_AUDIO_REFERENCE.md` 或 MCP）
- ❌ `experiments/` 废弃 spike（**除外**：`tagger_ab.py`、`tagger_listen_haiku.py`、`voice_compare.py`）
- ❌ 不要重开：P0/P1 逐句化、嘉岚音色问题、MiniMax-M3、Fish 会员门槛、第六十七轮密度代码（已 commit）
- ❌ 全仓库扫描

## 推荐下一个最小任务

1. 转入产品体验：优先低 GPU、asset-based 视觉存在感与端到端日常使用，不再继续微调 TTS。
2. 日常真机若再次出现尾字回收，只记录 ASR final 与 `BotStopped` 相对时间；不要主动制造回声或扩大匹配。
3. `_LatencySpikeLogger`、音频数据、实验脚本与 agent/MCP 工具配置继续保持本地未提交。

---

> **给新 session**：`/clear` 后只读 `docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
> 用户真机听感结论已记录：`normalize=false` 真实链路「还可以」；`position_v5` 已验收保留。下一步进入产品体验，单字尾音自回声仅随日常使用观察。
