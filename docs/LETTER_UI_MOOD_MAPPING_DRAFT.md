# 信笺 UI Mood 映射草案（2026-06-16，未实施）

> 仅为草案文档，不改 `tone.py` / prototype 代码。供未来真正接入
> `experiments/letter-typography-spike-2026-06/` 时参考。**所有映射均为猜测，需用户确认。**

## 后端情绪输出（来自 `backend/app/behavior/tone.py`）

`project_tone()` 返回 `ToneProjection`：

- `felt`: `warm | sharp | worried | lonely | neutral` —— 内核真实情绪（光/core）
- `expressed_edge`: 0.0（diffuse）~ 1.0（crisp）—— 外在表现锐利度（墨/ink）
- `is_performative`: 是否"暖核+利刃"的逗弄（desync-2）
- `register`: `comfort | real_sharp | playful | warm | lonely | neutral` —— 语义分组，各端各自渲染口吻
- `register_intensity()`: 0~1，驱动该 register 的强度

## prototype 现有 4 个 mood

`calm`（稳定温和打字）/ `hesitant`（慢、犹豫、退格重写）/ `excited`（快速爆发、加粗变大）/
`fragile`（变慢、逐渐淡出）。

## 映射草案（register → mood，按 `expressed_edge`/`intensity` 再细分）

| `register` | `felt` | 建议 mood | 理由 / 不确定点 |
|---|---|---|---|
| `comfort` | `worried` 或 `sharp` | `fragile` | worried + soft edge，"变慢+淡出"贴合担心/心疼语气；`intensity` 高时可加大 fade 幅度。⚠️若 `felt=sharp`（worried 但底层在烦），是否仍用 fragile 待确认——可能需要 fragile 的"颜色"略偏冷。 |
| `real_sharp` | `sharp` | **无直接对应**——草案建议复用 `excited`，但语义不符（excited=兴奋，real_sharp=不耐烦/冲）。⚠️ 需要新 mood（如 `terse`/`clipped`：快、短句、少修饰）或接受暂时复用 excited 的"快"但调整文案基调。 |
| `playful` (`is_performative=true`) | `warm` | `excited` | 暖核+利刃的逗弄，"快速爆发+加粗"能传达"嘴上凶其实在笑"的活跃感，相对贴合。 |
| `warm` (`is_performative=false`) | `warm` | `calm` | 稳定温暖，对应 calm 的"steady, warm typing"。 |
| `lonely` | `lonely` | `hesitant` 或 新 mood | hesitant 的"慢+犹豫+重写"可隐约传达"想说又有点欲言又止"，但与 lonely 的"想找人说话"语义有偏差。⚠️ 可能需要新 mood `longing`（慢但持续、不退格，像"写了很久的信"）。 |
| `neutral` | `neutral` | `calm` | 默认兜底。 |

## 强度（`register_intensity`）映射建议

- `intensity < STRONG_THRESHOLD(0.75)`：对应 prototype 当前的"基础"版本（已有 4 个 mood 的默认参数）。
- `intensity >= 0.75`：放大该 mood 的物理参数——例如 `fragile` 的 opacity 衰减更快/更深，`excited`
  的字号/字重更夸张。**prototype 当前没有"强度"这一维度，需要新增。**

## 开放问题（需用户决定）

1. `real_sharp` 和 `lonely` 这两个 register 在 prototype 里没有自然对应的 mood——是否：
   (a) 新增 1-2 个 mood（增加 prototype 复杂度）；
   (b) 暂时复用现有 4 个 mood 中语义最接近的，接受不完全贴切；
   (c) 这两个 register 暂不接入信笺 UI（只在语音/文字侧用）。
2. `expressed_edge` / `is_performative` / `register_intensity` 是否都要映射到视觉参数，还是先只用
   `register` 这一个维度做最小接入？
3. 是否要在 prototype 里保留"calm/hesitant/excited/fragile"这套命名，还是改名以贴合 Boxi 的
   `felt`/`register` 词汇（注意：之前讨论过不要把映射表和"毒舌"人设词汇绑死，未来人设转向时这套
   命名应仍可用）。

## 下一步（未排期）

等用户确认上述开放问题后，再拆"最小接入"实施任务（大概率涉及：prototype 增加 1-2 个 mood +
读一份模拟的 `ToneProjection` JSON，仍不接真实后端）。
