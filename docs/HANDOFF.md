# HANDOFF — 上下文交接（2026-06-25，第六十三轮）

> 本文件每次「瘦身交接」/「工作流交接」时整体覆盖更新。新 session 先读这一份，不要回放旧 SESSION_LOG。

## 当前项目目标
赛博伴侣 / Boxi：一个「被困盒子里的存在」——有人格、记忆、情绪、会主动找你的 AI 陪伴。
最终形态 = Direction C「一个有世界的存在」（深度 > 延迟；soul 写每个字）。仓库 **public**（MIT）。

## 当前阶段目标
**语音 Pipecat 路径的表达质量打磨。** 本轮把 task 3「标签器音效标签滥用」做完并真机验证 PASS，
已 commit `70d5c7a`。**下一步**：task 3 的下一层（`[crying loudly]` 等其它 A 类标签）暂无新症状，
建议先观察真机使用稳定性，再决定是否启动新一轮表达质量任务或转向其它 TASK_QUEUE 候选。

## 本轮已完成（2026-06-25，第六十三轮，commit `70d5c7a`，真机验证 PASS）

### ✅ commit `70d5c7a` · task 3 标签器音效标签语义闭门
- `/architect` 确认 scope：唯一改动点是 `backend/app/tts/expression_tagger.py` 的
  `TAGGER_INSTRUCTION_TEMPLATE` 字符串，不碰代码护栏（`_normalize_*`、`_preserves_original_wording`）——
  情绪恰当性是 LLM 的职责，代码只管格式/位置合法性，这条架构边界本轮没有越界。
- **规则4 改写**：把 A/B 类区分的标准从"会不会发出声音"纠正为"会不会插入一段**独立可分离的非语言
  声音事件**"（用户指出 `[soft tone]` 也改变了声音，原措辞不准确）；新增第三条子规则——A 类标签只能
  在文字明确写到该动作**真实发生**时使用，不能当成惆怅/心软/伤感/温柔等情绪基调的代用记号，情绪基调
  改用 B 类语气标签；给了正反例（`[sighing]` vs `[nostalgic]`）。
- **音效词表补 description 锚点**：每个 A 类标签后面加了官方语义描述（如
  `[sighing]=叹气（宽慰或沮丧时的呼气声，不是惆怅/温柔的代用记号）`），给 LLM 判断"是否真实发生"
  提供硬锚点，而不是只靠标签名望文生义。
- **没做的事（讨论后排除）**：用户问能不能把 Fish 官方中/英/日 phoneme 发音文档整段喂给标签器
  prompt——**排除**，理由：①发音文档教 LLM 插 `<|phoneme_start|>` 改写原文，会撞
  `_preserves_original_wording` 硬护栏，整句被判"改字"降级；②官方情绪控制文档本身有反例（如推荐
  `[sad][sighing]` 组合、要求音效后补说话内容），喂进去等于反向强化本轮要消灭的 bug；③流式路径按句
  调 tagger，文档量越大单句调用 token 成本越高；④`docs/FISH_AUDIO_REFERENCE.md`（第三十轮）已经是
  官方文档蒸馏+纠错后的项目版真理，prompt 词表已经来自那里，整包塞回去等于丢掉那次蒸馏。

### 真机验证（用户单轮多场景测试，session 内完整日志已核对）
- **统计**：~20 句标签器调用里，A 类（音效/生理）标签只出现 2 次——`[sighing]` 1 次（伤感故事收尾句，
  语义边界本身就模糊）、`[crying loudly]` 1 次（"影子碎成满地月光"的比喻句，边界案例）。
- **对比基线**：HANDOFF 旧记录"一轮内伤感故事+表白场景 `[sighing]` 出现 6+ 次"——本轮同类场景
  （伤感故事+表白+撒娇）只剩 1 次，**量级下降明显**。
- **正向分流证据**：原本可能被贴 `[sighing]` 的惆怅/温柔位置，这轮正确改用了 B 类标签——
  `[soft tone]`（7次）、`[whispering]`（4次）、`[teasing tone]`、`[annoyed tone]` 等，证明规则4
  新增的语义闭门子规则确实在生效，不是巧合。
- **未根除的灰色地带**：剩下的 1 次 `[sighing]` + 1 次 `[crying loudly]` 都卡在语义本身模糊的位置
  （讲完悲伤故事后的叹气 / 比喻性的"碎成月光"），这是 LLM 语义判断的固有边界，prompt 收紧能压低
  频率但不可能也不该压到 0（真实叹气场景本该用 `[sighing]`）。N=2 样本量太小，不值得为这两个边界
  案例继续抠 prompt 措辞，边际收益已经很低——**结论：净正向，判定为可 commit、可结案**。
- **副产物（确认无回归）**：本轮真机日志里 task 2 的 P1 守卫（`[break]`/`[long-break]` 冗余/密度）
  触发了 4 次，全部行为正确（剥贴标点冗余、剥超额密度、保留合法孤立的单个 break），证明上一轮已
  commit 的代码守卫和这轮 prompt 改动叠加正常工作，无冲突。首音延迟 2.2s–3.4s，在正常范围，prompt
  变长没有引入明显延迟回归。

### 测试
- `pytest backend/tests/test_expression_tagger.py backend/tests/test_expression_tagger_guards.py`：
  59 passed（21 task2 守卫 + 38 既有），两轮编辑后都跑过，无测试断言具体 prompt 文案、无需改测试。
- **本轮没跑全量 `npm run check`**——只改了一个 prompt 字符串常量，未涉及其它模块，建议下次顺手跑一次
  全量门禁确认整体状态，不阻塞本轮结案。

## 已修改文件（本轮）
- **已 commit `70d5c7a`**：`backend/app/tts/expression_tagger.py`（+12/-5：`TAGGER_INSTRUCTION_TEMPLATE`
  规则4改写 + 音效词表补 description 锚点，详见上方「本轮已完成」）。无新增/改动测试文件。
- **待提交（本次交接 commit）**：`docs/HANDOFF.md`（本文件）+ `docs/TASK_QUEUE.md`。
- **未提交（工作区保留）**：`run_voice.py` 仅历史遗留的 `_LatencySpikeLogger`（用户要求保留、commit 时照惯例排除；
  本轮代码改动**不在** `run_voice.py`）。

## 当前未完成

### 🟢 task 3 · 标签器音效标签滥用——**已结案**（commit `70d5c7a`，真机验证 PASS）
- 剩余 2 个边界案例（`[sighing]` 1次、`[crying loudly]` 1次）属于 LLM 语义判断固有灰色地带，N 太小
  不值得继续抠 prompt，**不建议重开**。除非未来真机再次观察到**高频**（非个例）复发，否则不要回来动
  `TAGGER_INSTRUCTION_TEMPLATE` 这块规则4。

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
- **task 3 · `[sighing]`/`[crying loudly]` 边界案例残留**：已结案（见上），N=2 低频灰色地带，非阻塞。
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
- 没有明确下一步主线——task 3 已结案，建议先观察真机使用稳定性（无需立刻读代码），或与用户讨论
  TASK_QUEUE 里下一个候选（task 4 自回声/AEC epic 仍标记暂缓；P12/P9-P2-C/P9-D 等沿用未完成项）。

## 下一步不要读取（省上下文）
- ❌ `docs/SESSION_LOG.md`（历史日志，不维护）
- ❌ `reference/`（Pipecat/Fish 文档线已结）
- ❌ `experiments/`（废弃 spike，故意不提交）
- ❌ 不要重开破音 / P13 normal / 省略号 / 自回声主修 / 截断 / task 2 P0+P1 / task 3（均已结案 / 已 commit）
- ❌ 全仓库扫描

## 推荐下一个最小任务
- **无紧急主线**：建议下一 session 先跟用户确认是否有新真机症状，没有的话从 TASK_QUEUE 沿用未完成项
  （P12 Hume prosody 立项 / P9-P2-C 真联网素材源 / task 2 剩余 P2/P3，均已降级非紧急）里选一个，或
  跑一次全量 `npm run check` 补本轮没跑的门禁。

---

> 建议执行 `/clear` 或新开 session。下一 session 只需读取 `docs/HANDOFF.md`、`docs/TASK_QUEUE.md`、
> `docs/ARCHITECTURE_SNAPSHOT.md`。
