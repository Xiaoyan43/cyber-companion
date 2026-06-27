# HANDOFF — 上下文交接（2026-06-27，第六十九轮 · Fish 参数 A/B 收敛）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。
>
> **范围说明**：本文件是 **voice / tagger / Fish TTS** 轨的 session 交接上下文，**不是** Shared Soul Runtime 的状态源。Soul 架构与阶段状态请读 `docs/SOUL_RUNTIME_STATUS.md`、`docs/SOUL_RUNTIME_ARCH.md` 等；**不要**从本文件推断 soul 生产状态或 RTC 阶段进度。

## ⚠️ 给新 session 的最小上手指引

1. 先读本文件 + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`，**不要全仓库扫描**。
2. **当前 git HEAD = `994fa1a`**（master；含 PR #2 Fish Pipecat settings + PR #3 B 类句中贴标 prompt）。主 dirty 工作树仍有故意不提交残留：
   - `backend/realtime/run_voice.py`（`_LatencySpikeLogger`，P8-C 探针）——**本地临时 instrumentation，不进生产 PR**；继续开发时按需保留或本地禁用。
   - untracked：`experiments/tagger_ab.py`（已本地改过，见下）、`experiments/tagger_listen_haiku.py`、
     `voice_compare.py`、`data/tagger_eval/`、`.mcp.json` 等实验/数据。
3. 生效配置（**gitignored 的本地文件**，不在 git 默认里）：
   - `config/providers.json`：tagger 跑 `anthropic/claude-haiku-4.5`（provider 条目仍叫 `"gemini"`）。
   - `config/tts.json`：**tracked repo 默认仍为 `s2.1-pro-free`** + 嘉岚 `fbe02f8306fc4d3d915e9871722a39d5`；本地 A/B 听感认为 paid `s2.1-pro` 更好，**曾仅在本地 gitignored 配置里切换做实验，是否改 repo 默认待用户确认**（单独决策，不进 voice settings PR）。
   - `.env`（可选）：本地实验可设 `CYBER_COMPANION_VOICE_FISH_NORMALIZE=false`（第六十九轮固定文本 A/B 胜出项；master 代码已支持 opt-in env，**未设则仍走 Pipecat 默认 `normalize=True`**）。
4. **主线已从「压密度」转向「Fish TTS 节奏/韵律调优」**——固定节奏标签 A/B 区别不大；Fish 参数 A/B 里只关 `normalize` 最自然。
5. 测试切片：`pytest backend/tests/test_expression_tagger_guards.py backend/tests/test_expression_tagger.py`（61 绿，PR #3 后）。
   涉及 pipecat/FastAPI 的全量 pytest 在本机可能因 numpy `_mac_os_check` 崩溃（预存环境问题）。
6. Codex 已配置 Fish 官方 agent tooling（全局，不在仓库 commit 内）：Fish Docs MCP + `fish-audio-api`/`fish-audio-sdk` skills。新会话可能需要重启后才热加载。

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

## 第六十八轮补充（2026-06-26，**仅更新 HANDOFF + Codex 全局配置**）

### ✅ 用户真机听感结论已记录

- 当前标签密度/稳定性：**较为稳定**，不再是第六十七轮前那种「几乎句句贴」的主问题。
- 主要听感问题：**稍微发平**，重点像是**语句之间停顿不足、没有顿挫感**。
- 方向判断：下一步不应全局加密度，也不应回退到句句贴；主线应切到 Fish TTS 的**节奏/韵律控制**。

### ✅ Fish 文档复核后的新调优线索

只读 `docs/FISH_AUDIO_REFERENCE.md`、`docs/PIPECAT_REFERENCE.md`、`docs/PIPECAT_AUDIT.md` 与当前 Fish/Pipecat 装配，结论：

1. **节奏标签疑似需要 A/B**  
   Fish S2-Pro 文档里的节奏类标签是 `[pause]` / `[short pause]` / `[long pause]`，但当前标签器 prompt 和守卫用的是 `[break]` / `[long-break]`。历史上 `[break]` 似乎有过效果，不能直接断言是 bug；但这正贴合「句间没顿挫」症状，应优先固定文本 A/B。
2. **Pipecat 语音路径当时未显式传 Fish 表达参数**（**已在 PR #2 解决**：optional env → `FishAudioTTSService.Settings`）。
3. **文字路径和语音路径配置不一致**  
   `backend/app/tts/fish_audio.py` 已传 `temperature/top_p`，并设置 `prosody.normalize_loudness=false`；Pipecat 语音路径在未设 env 时仍走默认 `normalize=True`，可能压平 whisper/shouting 等动态——本地可 opt-in `CYBER_COMPANION_VOICE_FISH_NORMALIZE=false` 验证。
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

## 第六十九轮补充（2026-06-27，Fish 节奏/参数 A/B + voice PR 落地）

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

- **`normalize=false` 最正常**（固定文本样本）
- 其他三组句间呼吸略别扭

**已 merge（PR #2）**：

- `voice_config.py` + `run_voice._build_tts`：optional env 注入 `normalize` / `temperature` / `top_p` / `prosody_speed` / `prosody_volume`（未设 env 则保留 Pipecat 默认）
- `.env.example`：注释推荐只关 normalize；降速/升温仅作实验项（**非注释默认值**）
- 测试：`pytest backend/tests/test_voice_config.py backend/tests/test_fish_audio_pipecat_tts.py` → 11 passed

**本地可选**：`.env` 设 `CYBER_COMPANION_VOICE_FISH_NORMALIZE=false` 做真机验证；**不要**同时开 `prosody_speed=0.94` 或 `temperature=0.8`。

下一步：**Pipecat 真机语音链路验证 `normalize=false` 是否也改善真实对话**。

### ✅ 模型版本 A/B 样本已生成（S2.1 Pro paid vs free vs S2.0/S2-Pro）

用户多轮真机怀疑问题可能来自 `s2.1-pro-free`。按 Fish 文档/API 语义确认：

- S2.1 Pro paid：`model` header 用 `s2.1-pro`
- S2.1 Pro Free：`s2.1-pro-free`
- 上一代 S2 / S2.0：`s2-pro`

新增 `experiments/fish_model_ab.py`，只做离线 HTTP `/v1/tts` 样本，不改 tracked repo 配置。

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

**本地听感结论（待用户确认是否改 repo 默认）**：

- **`s2.1-pro-free` 明显过于粗糙**；paid **`s2.1-pro` 在 A/B 中最好**。
- 实验期间曾在**本地 gitignored** `config/tts.json` 切到 `s2.1-pro` 做听感验证。
- **tracked `config/tts.json` 仍为 `s2.1-pro-free`**；是否把 master/repo 默认改为 `s2.1-pro` **尚未确认**，需单独 PR/产品决策，不要与 voice settings PR 捆绑。

### ✅ Paid S2.1 Pro 上已重做停顿/normalize 样本

因为前一轮 `[break]`/`[pause]` 和 `normalize=false/true` 判断基于 `s2.1-pro-free`，用户要求在 paid
`s2.1-pro` 上重测。已用同一固定文本、同一嘉岚音色、同一参数生成：

- `data/fish_rhythm_ab/s21-pro/rhythm_norm_false/*.mp3`
- `data/fish_rhythm_ab/s21-pro/rhythm_norm_true/*.mp3`

每组 6 条：`none` / `break` / `long_break` / `short_pause` / `pause` / `long_pause`。

用户听感结论：

- 停顿/顿挫：各标签**没什么区别**，不要因为这轮去大改节奏词表。
- `normalize=false`：比 `true` **稍微好一点**（paid `s2.1-pro` 固定文本样本）。
- 奇怪现象：两组里 `long_pause` 的**音质**都更好一些，但这不像是“停顿/顿挫”改善，更可能是 Fish 生成随机性、
  分段/采样路径变化，或 `[long pause]` 对整句韵律的副作用。**不要直接把所有停顿迁移成 `[long pause]`**；
  若要利用它，需再做多次重复样本确认稳定性。

### ✅ B 类标签位置 prompt 精修（**已 merge PR #3**）

已修改 `backend/app/tts/expression_tagger.py` 的 `TAGGER_INSTRUCTION_TEMPLATE`：

- 强化语气/情绪/音调类标签不要偷懒全放句首。
- 优先贴在情绪真正开始的位置，尤其是转折词或情绪起点前：如「不过」「但是」「其实」「只是」「偏偏」
  「突然」「后来」「那一刻」。
- 只有整句从第一个字开始就是同一种明确情绪时，才句首贴。
- 新增正反例：
  - `我嘴上嫌你烦，[soft tone]不过还是给你留了灯。`
  - `我今天去了那家店，[sad]后来才发现你不在。`

边界：这次**没有**新增代码语义 guard。B 类标签位置属于语义判断，仍交给 tagger LLM；代码只做格式/明显非法位置护栏。

测试：`pytest backend/tests/test_expression_tagger.py backend/tests/test_expression_tagger_guards.py` → 61 passed。

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

## 当前项目目标

赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标

**Fish TTS 听感调优：标签密度已基本稳定；PR #2/#3 已合入；固定节奏标签 A/B 未见明显差异；当前主线是 Pipecat 真机验证 `normalize=false`（opt-in env），其次才是位置/语义精修与 `s2.1-pro` 默认是否切换（待用户确认）。**
文字路径逐句化（P0+P1）已在 `111c70c` 落地并真机验证。

---

## 已知 bug / 风险

- **~~Haiku 密度过高~~ → 已大幅改善**：`tagger_ab` N=3 证实 long_story 1.00→0.67；用户真机反馈当前较稳定。
- **当前听感偏平**：主要像语句之间停顿/顿挫不足，不是标签数量不足。
- **节奏标签词表 A/B 差异不大**：当前 prompt/guard 仍保留 `[break]` / `[long-break]`，不要仅凭文档迁移到 `[pause]` 系。
- **Pipecat Fish 参数已暴露（PR #2）；固定文本 A/B 胜出项是 `normalize=false`**：本地 `.env` 可 opt-in；降速/升温听感别扭，先不要启用。
- **`s2.1-pro` vs `s2.1-pro-free`**：本地 A/B 听感 paid 更好，**repo 默认仍为 `s2.1-pro-free`，切换待用户确认**。
- **`_LatencySpikeLogger`**：仅主 dirty 工作树本地探针，**不进生产 PR**。
- **标签器 provider 命名债**：条目仍叫 `"gemini"`，实际跑 Haiku。独立小任务，不紧急。
- **位置精度**：B 类句首粗放、opening_only；PR #3 prompt 已收紧，Haiku 仍不稳定——真机重点听。
- **Gemini A 类语义错**：若回退 Gemini 换密度，会重新引入音效标签误用。
- **改字护栏副作用**：Haiku 试图给「扑通」插 `[扑通]` 类标签时被拒绝 → 该句无标签（正确降级，但丢表达）。
- Fish 账号 Free 套餐锁住克隆/Voice Design（不阻塞）。
- 沿用：自回声残余（AEC epic）、P12、P9-P2-C、P9-D、日语音色未接后端、Fish WS 空闲断连。

---

## 当前未完成

### 🔴 最高优先 · Pipecat 真机验证 `normalize=false`

目标：解决「稳定但发平、句间没有顿挫感」。不要先全局加标签密度。

推荐最小顺序：

1. 本地 `.env` 设 `CYBER_COMPANION_VOICE_FISH_NORMALIZE=false`，跑 `python -m backend.realtime.run_voice`，确认启动日志出现 `Fish TTS explicit settings: {'normalize': False}`。
2. 真机对话听：是否比之前少一点「发平/被压住动态」，句间呼吸是否不别扭。
3. 若 PASS：把 `normalize=false` 固化为**推荐本地配置**（仍 opt-in，不强制改 `.env.example` 默认值）；暂不改节奏词表。
4. 若仍偏平：继续 B 类标签句中位置 prompt 迭代或 tagger 策略，而不是开 `prosody_speed=0.94` / `temperature=0.8`。
5. **保留 `latency=balanced`**  
   不要为了音质切 `normal`；P13 已结案为 won't fix/不用。

### 🟡 待用户确认 · `config/tts.json` 模型默认

- 本地 A/B：`s2.1-pro` > `s2.1-pro-free`；**tracked repo 仍为 `s2.1-pro-free`**。
- 若用户确认切换：单独 PR 改 `config/tts.json`，不与 voice handoff 或 settings PR 混提。

### 🟡 位置精修（PR #3 已合入 prompt；听感验证后再定是否继续）

- 已做：B 类优先句中贴转折词前（PR #3）。
- 未做：代码守卫 P2 词中插、P3 无意义句首堆叠（task 2 遗留，真机未复现故降级过）。

### 🟡 标签器 provider 命名正名（独立小任务，不紧急）

`"gemini"` → 中性名（如 `"tagger"`），4–5 处 + env 改名。

### 🟢 Fish 音色克隆/设计（等用户升级 Plus）

详见 memory `fish-voice-creation-plan`。当前维持嘉岚。

### 沿用未完成项

task 4 自回声、P12、P9-P2-C、P9-D、日语音色切换。

---

## 历史背景（第六十五轮 `111c70c`，摘要）

- P0/P1：文字路径标签器逐句化 + 并发，单句失败不再整段作废。
- 模型 A/B：Haiku 情绪准 / Gemini 密度优；MiniMax-M3 出局。
- task 3（第六十三轮 `70d5c7a`）：A/B 类音效 vs 语气 prompt 修正，`[sighing]` 滥用从 6+/轮 降到 ~1–2/20 句。
- 嘉岚音色无问题；长叙事听感差根因是密度过高（第六十七轮已量化改善）。
- Fish 克隆/Voice Design 需 Plus，用户暂不升级。

---

## 下一步只需读取（按任务挑）

- **永远先读**：本文件 + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- **Soul 状态**（与本文件无关）：`docs/SOUL_RUNTIME_STATUS.md`、`docs/SOUL_RUNTIME_ARCH.md`。
- **节奏/韵律 A/B**：`docs/FISH_AUDIO_REFERENCE.md` §2/4/7/9 + `docs/PIPECAT_REFERENCE.md` §4/8 +
  `docs/PIPECAT_AUDIT.md` B 项 + `backend/realtime/run_voice.py` + `backend/app/tts/fish_audio.py` +
  `backend/app/tts/expression_tagger.py`（节奏词表/guard）。
- **位置精修**：`backend/app/tts/expression_tagger.py`（Rule 3/4/5）+
  `experiments/tagger_ab.py` + `backend/scripts/tagger_eval.py` + `docs/FISH_AUDIO_REFERENCE.md` §3–4。
- **provider 命名正名**：`registry.py` + `expression_tagger.py` + `.env.example`。

## 下一步不要读取

- ❌ `docs/SESSION_LOG.md`
- ❌ `reference/`（Pipecat/Fish 文档线已结；Fish 查 `docs/FISH_AUDIO_REFERENCE.md` 或 MCP）
- ❌ `experiments/` 废弃 spike（**除外**：`tagger_ab.py`、`tagger_listen_haiku.py`、`voice_compare.py`）
- ❌ 不要重开：P0/P1 逐句化、嘉岚音色问题、MiniMax-M3、Fish 会员门槛、第六十七轮密度代码（已 commit）、PR #2/#3 已合入项
- ❌ 全仓库扫描

## 推荐下一个最小任务

1. **跑 Pipecat 真机链路验证 `normalize=false`**（opt-in env，PR #2 已合入）：只听真实多轮对话是否改善发平。
2. 若 PASS：记录为当前推荐本地配置；不迁移 `[pause]` 词表。
3. 若仍不够：继续 B 类标签位置 prompt 迭代（PR #3 已合入首版），不要先加标签密度。
4. 并行待决：用户是否确认把 `config/tts.json` 默认从 `s2.1-pro-free` 切到 `s2.1-pro`（单独 PR）。
5. 备选：`experiments/tagger_ab.py` 本地改动是否保持 untracked——按惯例实验脚本不提交，但已是对生产路径的忠实镜像。

---

> **给新 session**：`/clear` 后只读 `docs/HANDOFF.md` + `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`（voice 轨）；soul 轨另读 `docs/SOUL_RUNTIME_STATUS.md`。
> 用户真机听感结论已记录：节奏标签差异不大；`normalize=false` 固定文本样本最正常；paid `s2.1-pro` 本地 A/B 更好但 repo 默认未改；下一步跑 Pipecat 真机链路验证。
