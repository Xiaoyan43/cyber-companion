# HANDOFF — 上下文交接（2026-06-25，第六十二轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**语音 Pipecat 路径的表达质量打磨。** 本轮把 task 2「标签器位置/格式守卫」拆成四个守卫并落地前两个
（P0 畸形归一化 + P1 `[break]` 冗余/密度），已 commit `b07375d`，真机两轮净正向、零误伤。
**下一步主线转向 = task 3 标签器音效标签滥用（语义判断质量）**——真机暴露 `[sighing]` 被当软情绪记号滥用，
比位置/格式守卫更高频可闻，治本在 LLM/prompt 侧。

## 本轮已完成（2026-06-25，第六十二轮，**P0+P1 已 commit `b07375d`，真机两轮净正向**）

### ✅ commit `b07375d` · task 2 标签器位置/格式守卫 P0+P1
- `/architect` 先把 task 2 拆成**四个守卫**（畸形归一化 / `[break]` 冗余密度 / 词中插 / 开头堆叠），本轮落地前两个。
- **挂载点**：两个守卫组合进新纯函数 `_normalize_tag_placement`，接在 `_strip_dangling_trailing_tags` **之后**调用，
  **整段路径 `apply_expression_tags` + 流式逐句 `apply_expression_tags_to_sentence` 双路径统一生效**（一处实现、两处接线）。
- **P0 `_normalize_malformed_tags`**：`[ sighing ]`→`[sighing]`、`[soft  tone]`→`[soft tone]`（trim 内部首尾空格 + 折叠连续空格）；
  空标签 `[]`/`[   ]`→剥除。让 Fish 一定能识别。
- **P1 `_normalize_break_tags`**：`[break]`/`[long-break]` 紧贴停顿标点（。，！？…等）即剥除（标点已提供停顿）；
  单次调用最多保留 1 个（句中滥用按序保留首个、剥除其余）。**孤立、无标点相邻的单个 break 保留**——那是合法的戏剧性
  停顿，位置交给 LLM 判断，代码不越界。
- **不变量**：守卫只增删/修复 `[tags]`、**原文一字不动** → `_preserves_original_wording` 天然成立（守卫在改字校验之后跑）。
- **观测日志**：守卫真改动时打 `🧹 placement guard: {before!r} -> {after!r}`（风格同 `🔇 self-echo`/`✂️ truncated`）。
  **打到后端终端（跑 `run_voice.py` 的窗口），不是前端**——前端字幕本就是纯文本看不到标签。

### 真机两轮结论
- **净正向**：用户确认「整体比上一轮（有 `[ sighing ]` 畸形怪声那次）有变好」。
- **零误伤**：两轮标签器贴了 8+ 种标签（`[whispering]`/`[soft tone]`/`[sad]`/`[happy]`/`[satisfied]`/`[grateful]`/
  `[calm]`/`[bored]`/`[curious]`/`[低声]` 等），**全部原样保留**，无一被守卫错删；`[whispering]` 领引号台词等放置正确。
- **守卫一次没触发**（全程零 `🧹` 行）：这两轮标签器没吐 `[ sighing ]` 畸形、也没吐 `[break]` → P0/P1 针对的是
  **低频**症状，这两轮没复现。**所以真机没直接证明守卫"治好了"什么，只证明了不误伤**；单测已证明逻辑本身正确。

### 测试
- 新建 `backend/tests/test_expression_tagger_guards.py`：21 单测（P0 6 + P1 8 + 组合 2 + wiring 2 + 其它），全绿。
- 既有 `test_expression_tagger.py` 38 全绿（含 dangling/改字守卫回归）。相关切片
  `-k "tagger or expression or realtime or voice"` **134 passed**；`py_compile` OK。
- **本轮没跑全量 `npm run check`**——建议让 Cursor 收尾跑全量门禁。

## 已修改文件（本轮）
- **已 commit `b07375d`**：`backend/app/tts/expression_tagger.py`（+84/-2：两守卫 + 组合器 + `🧹` 日志 + 两处接线）
  + `backend/tests/test_expression_tagger_guards.py`（新，21 测试）。
- **待提交（本次交接 commit）**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md`（顶部第六十二轮日志 + task 3/4）。
- **未提交（工作区保留）**：`run_voice.py` 仅历史遗留的 `_LatencySpikeLogger`（+44，用户要求保留、commit 时照惯例排除；
  本轮代码改动**不在** `run_voice.py`，故直接 stage 两文件即可，无需「临时移除 spike」处理）。

## 当前未完成

### 🔴 task 3 · 标签器音效标签滥用（下一步主线，未开工）
- **真机症状**：Gemini 把 `[sighing]`（Fish 里是触发**真实叹气声**的音效标签）当成「这句偏温柔/惆怅」的**通用软情绪
  记号**在用——一轮内伤感故事 + 表白场景出现 6+ 次，真人不会每隔一句实际叹气，**听感不自然**（用户实测确认）。
- **根因**：语义归类错误——**音效（罕见、生理动作、发真实声音）vs 语气（频繁、只影响演绎）混淆**。属 **LLM 判断**，
  不属位置/格式。**和 P0/P1 不同性质：代码守卫治不了，也不该治（情绪恰当性靠 LLM = 架构红线）。**
- **治本杠杆（全在 LLM 侧）**：① prompt 在 `TAGGER_INSTRUCTION_TEMPLATE` 第 4 条把界限划死——音效/生理类只在
  Boxi 真会做那个动作时才用、不能当软情绪记号；想表达 wistful 用 `[soft tone]` 等语气标签。② 或换标签器模型
  （memory `future-provider-swap-candidates` 已记 tagger LLM 待换）。**⚠️ 禁止用代码删 `[sighing]`**——治标不治本 +
  越界 + 用户明确不要代码硬干预密度。**先 `/architect`。**

### 🟡 task 4 · 自回声残余（归 self-echo/AEC 兜底，暂缓）
- **真机症状**：一轮 Boxi 自问自答——上句结尾「现在想让我**怎么陪你**？」音箱尾音被麦克风采回，ASR 误转成「能陪你」，
  因不是 Boxi 尾巴的干净精确/同音后缀（多了误听的「能」）或已超 4s 窗口，逃过 `self_echo_filter` → brain 当用户输入回应。
- **定性**：self-echo 内容级兜底（commit `c40efda`）的**已知残余**。真治靠 **AEC（浏览器/WebRTC 白送）**，挂未来
  「产品上 web/WebRTC」独立 epic。收紧匹配会误杀真实接话（用户也可能真说「能陪你」），是兜底固有两难。**本轮不动。**

### 🟢 task 2 剩余 · P2 词中插 / P3 开头堆叠（**已降级**）
- P2（词中插 `那[sighing]股`→剥除）、P3（开头堆叠 `[calm] [bored]`→保留首个、白名单放过 rule5 的音效+情绪配对）。
- **这两轮真机均未复现**（标签都贴在小句/标点边界，没出现词中插；堆叠只出现 `[nervous] [worried]` 句中一次 +
  `[sighing] [calm]` 句首一次但后者是 rule5 允许的音效+情绪配对）→ **优先级让位 task 3**。做时注意：P3 若做，
  需扩成「任意小句边界的堆叠上限」（不只句首），且保留 rule5 白名单。

### 沿用未完成项
- P12（Hume prosody 立项）、P9-P2-C（素材源真联网）、P9-D（投递层，暂缓）、日语音色清单未接后端按语言切换。

## 已知 bug / 风险
- **🆕 task 3 · `[sighing]` 音效标签滥用**：见上，listener-facing、每轮可闻，下一步主线。
- **🆕 task 4 · 自回声残余**：见上，归 AEC epic。
- **沿用 · Fish WebSocket 空闲断连**：轮次间隔 >15s 时 Fish 服务端主动断，随后自动重连成功、下一轮正常。功能不受影响。
- **沿用 · `s2.1-pro-free` 在省略号场景回归**：已锁 `s2-pro`，别再随手换（memory 已记）。
- **架构认知（durable，写给未来做 barge-in 的 session）**：barge-in（打断 Boxi）的拦路虎是 **AEC（回声消除），不是
  换 ASR**。现装 Pipecat 音频滤镜全是降噪（krisp/aic/rnnoise/koala），没有一个是 AEC；本地 PyAudio 路径没接参考信号。
  AEC 现实来源 = 浏览器/WebRTC（`getUserMedia echoCancellation` 白送）或耳机。**barge-in = 独立 epic，挂「产品上
  web/WebRTC」节点**；届时 half-duplex + 自回声从主力降级为残余回声兜底（task 4 同源）。
- **沿用**：破音修复的 ~200ms 首音延迟代价（commit `8d5b2fb`，已闭环勿重查）；P13 normal 失声（won't fix，锁 balanced）；
  `run_voice.py` `load_dotenv(override=True)` 改 `.env` 须重启 dev:backend；cost 模块不认 openrouter；OPEN：是否抬
  `DEFAULT_VOICE_MAX_TOKENS`（截断 fix 后变可选，默认维持 200，用户不追求超长）。

## 下一步只需读取（按任务挑）
- **永远先读**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md` + `docs/ARCHITECTURE_SNAPSHOT.md`。
- **task 3 标签器音效标签滥用（推荐）**：读 `backend/app/tts/expression_tagger.py`（`TAGGER_INSTRUCTION_TEMPLATE`
  第 4 条音效/语气精度区分）+ `docs/FISH_AUDIO_REFERENCE.md`（音效标签「触发真实声音 vs 仅影响演绎」分类）。先 `/architect`。

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/`（Pipecat/Fish 文档线已结）
- ❌ `experiments/`（废弃 spike，故意不提交）
- ❌ 不要重开破音 / P13 normal / 省略号 / 自回声主修 / 截断 / P0+P1 守卫（均已结案 / 已 commit）
- ❌ 全仓库扫描

## 推荐下一个最小任务
- **task 3 · 标签器音效标签滥用**：先 `/architect`，把「prompt 划清音效 vs 语气界限」（或评估换标签器模型）拆成最小
  可验切片，**走 LLM/prompt 侧、禁止代码删 `[sighing]`**。

---

> 建议执行 `/clear` 或新开 session。下一 session 只需读取 `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、
> `docs/ARCHITECTURE_SNAPSHOT.md`。
