# VE-1 Spec — cascaded 逐句情绪（context_texts 路线）`[Claude spec → Cursor builds → Claude reviews]`

给 cascaded（我们自管的云 TTS）的口语回复加上**由灵魂内核驱动的情绪**，并把"夸张"压下来。
**已定方向（用户 2026-06-14）：保持现 2.0 音色，用 `context_texts` 自然语言指令，不换音色、不用 emotion_scale。**

母文档：`docs/VOICE_EMOTION_MEMORY_PLAN.md`。依据：`reference/15.md`(TTS API)、`reference/09.md`(音色)、`reference/SYNTHESIS.md`。

## 现状（已核实）
- `backend/app/tts/doubao.py` `_build_request_payload` 的 `audio_params` **只发 `format`+`sample_rate`**，无任何情绪/语速。
- 音色由 env `ENV_VOICE_TYPE` 指定（当前灿灿 2.0，2.0 uranus 家族）。2.0 音色**可直接用 `context_texts`**（`reference/15.md`：非复刻 2.0 音色直接支持，不需 expressive，且该字段不计费）。
- `emotion`/`emotion_scale` 仅"多情感"(`*_emo_v2`)音色支持 → 本路线**不使用**。
- markdown/emoji：2.0 音色**不允许** `disable_markdown_filter=true`（`reference/15.md`）→ 必须我们在送 TTS 前清。前端 `frontend/src/voice/speechText.ts` 已有清洗逻辑（剥括号舞台提示），后端尚无。

## 关键约束
- **per-reply，不是 per-sentence**：HTTP TTS 是「整段一次合成」，`context_texts` 作用于本次 `text` 整体。真正的逐句内联标签是 RTC 流式路径（非本切片）。本切片做"每条回复一个情绪指令"。
- 仅 **doubao 云 provider** 用这些参数；mock / mac_say 忽略。
- 纯 E2E (RTC) 路径**不动**。

## 设计

### 1. 共享「register → 情绪指令」映射（tone.py 收口）
`backend/app/behavior/tone.py` 新增（**唯一真源**，RTC 与 cascaded 都读，呼应 felt-shown「一个人格」）：
```python
# register → (context_texts 短语 | None, speech_rate 增量)
def tts_emotion_directive(projection: ToneProjection) -> tuple[list[str] | None, int]:
    ...
```
映射（短语**复用** `rtc/state_block._EMOTION_TEXT_BY_REGISTER`，措辞已是克制版——压夸张的关键）：

| register | context_texts | speech_rate |
|---|---|---|
| comfort | ["语气放软、关切、稍慢"] | -10 |
| real_sharp | ["更冲、更不耐烦但别凶"] | +8 |
| playful | ["嘴上凶、其实带笑、是逗ta"] | +5 |
| warm | None | 0 |
| lonely | ["更热络一点"] | +3 |
| neutral | None | 0 |

- **重构**：把 `state_block._EMOTION_TEXT_BY_REGISTER` 移到 `tone.py` 作为单一真源；`state_block.build_rtc_emotion_tag` 改为读 `tone.py` 的映射（行为不变，RTC 钉死测试仍过）。speech_rate 仅 cascaded 用。
- **压夸张**：短语保持"别凶/稍慢"这种克制档；speech_rate 增量小（±10 内）。**不**输出"用最生气的语气"这类极端措辞。

### 2. 文本清洗 util（后端）
新增 `backend/app/tts/text_cleanup.py` `clean_text_for_tts(text) -> str`：去 markdown 标记（`**`/`*`/`#`/`` ` ``/链接）、去 emoji、去括号舞台提示（与 `speechText.ts` 对齐）。在 `doubao.py` 合成前调用。**只清送 TTS 的文本，不动落库/字幕文本。**

### 3. 下发 payload（doubao.py）
`_build_request_payload(text, creds, *, context_texts=None, speech_rate=0)`：
```python
"req_params": {
  "text": clean_text_for_tts(text),
  "speaker": creds["voice_type"],
  "audio_params": {"format": ..., "sample_rate": 24000, "speech_rate": speech_rate},
  **({"additions": {"context_texts": context_texts}} if context_texts else {}),
}
```
`speech_rate=0` 或 `context_texts=None` 时**与现状完全一致**（向后兼容）。

### 4. 把内核情绪接到 TTS 路由
`/tts/synthesize` 路由（`backend/app/main.py`）合成前：读 store 内核 → `project_tone(mood, relationship, performative_active=performative_active_from_metadata(mood.metadata))` → `tts_emotion_directive(projection)` → 传入合成。
- 不需要前端改动（路由自己从内核取，和 `state_block` join-time 取法一致）。
- 仅当 provider 是 doubao 且配置就绪时附加；否则忽略。

### 5. 音色（仅配置，归用户）
保持 env `ENV_VOICE_TYPE`；如想更"沉稳磁性"可换 `zh_male_yunzhou_uranus_bigtts`/`zh_male_xiaotian_*`（不在本切片代码内）。

## 相关文件
- `backend/app/behavior/tone.py`（+`tts_emotion_directive` + register→context_texts 真源）
- `backend/app/rtc/state_block.py`（改读 tone.py 映射，行为不变）
- `backend/app/tts/text_cleanup.py`（新）、`backend/app/tts/doubao.py`（payload）
- `backend/app/main.py`（/tts/synthesize 接内核）
- 测试：`backend/tests/test_tone.py`(directive 映射)、`test_tts.py`(payload 含 context_texts/speech_rate + 清洗 + 向后兼容 + 中性无附加)

## Done criteria
- doubao TTS payload 在非中性内核下带 kernel 派生的 `context_texts` + `speech_rate`；中性内核与现状一致。
- markdown/emoji/括号在送 TTS 前被清（落库/字幕文本不变）。
- register→context_texts 由 tone.py 单一真源提供；RTC 既有钉死字符串不变（`test_rtc_state_block` 全过）。
- 压夸张：措辞克制档 + speech_rate ±10 内；无极端情绪措辞。
- `npm run check` 绿（含新测试）。

## 边界
- per-reply，不做 per-sentence；不换音色（代码层）；纯 E2E 路径不动；2.0 音色不设 `disable_markdown_filter`；不改 memory schema / behavior 决策契约（只加 TTS 表达层）。
