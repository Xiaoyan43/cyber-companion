# V2 RTC Pure E2E + Viking 长期记忆 — 实施规格

纯 E2E（`OutputMode 0`）保持豆包云端大脑与低延迟；长期记忆走火山 **Viking 记忆库** +
`StartVoiceChat.Config.MemoryConfig`。本地 SQLite 记忆与 Viking **暂不合并**（Phase C 可选）。

官方参考：

- [Viking 产品简介](https://www.volcengine.com/docs/84313/1860732?lang=zh)
- [打通 RTC + Viking 长期记忆](https://www.volcengine.com/docs/84313/1928352)
- [接入记忆库（长期记忆）](https://www.volcengine.com/docs/6348/1899860)
- [StartVoiceChat API](https://www.volcengine.com/docs/6348/2123348?lang=zh)
- [AddSession](https://www.volcengine.com/docs/84313/1783353)

---

## 跨会话怎么接（新 Cursor 窗口）

每个 Cursor chat 结束时，维护者会在 `docs/SESSION_LOG.md` 写 **「下次接着做」**，
并在本 spec 勾选对应 Slice。新窗口说 **`推进`** 时按顺序读：

1. `docs/TODO.md` → 找 **V2 RTC Viking Memory** 小节
2. `docs/SESSION_LOG.md` → 最新一条
3. **本文件** → 第一个未勾选的 Slice

**不要**在一次 session 里跨多个 Slice，除非用户明确要求。

| Slice | 内容 | Done when |
|-------|------|-----------|
| **VM-1** | 稳定 `user_id` + `MemoryConfig` 注入 `StartVoiceChat` | 单测绿；`agent/start` body 含 `MemoryConfig`（env 已配时） |
| **VM-2** | 控制台：记忆库 + `VoiceChatRoleForRTC` 跨服务授权 | 用户实机：跨天 RTC 能提到昨天的事 |
| **VM-3** | 通话结束 → 字幕 → Viking `AddSession` 代理 | `POST /rtc/memory/session` 单测；leave 后记忆库有新事件 |
| **VM-4** | 进房前 SQLite 摘要注入 `system_role`（可选） | 文字聊天写入的事实能在纯 E2E 语音里被提到 |
| **VM-5** | 左栏 UI：Viking 记忆状态徽章 + 文档 | `GET /rtc/status` 暴露 `viking_memory_enabled` |

当前进度：**VM-1～5 + VM-4 已完成**（Viking 跨会话 PASS）。文字聊天仍走 SQLite，挂断后写入 Viking。

---

## 架构

```text
纯 E2E RTC 通话
  StartVoiceChat
    S2SConfig.OutputMode = 0
    MemoryConfig → Viking 检索（每轮，云端）
    dialog.system_role → Boxi 人设（短）

通话结束（VM-3）
  字幕 transcript → AddSession → Viking 抽取事件/画像

文字聊天
  仍走 SQLite；进房前 VM-4 把摘要/要点注入 system_role（不自动写 Viking）
```

### 短期记忆（会话内）

同一次 `StartVoiceChat` 任务内，豆包云端维护多轮上下文；`StopVoiceChat` 即清空。
**不**使用 `LLMConfig.UserPrompts`（那是 OutputMode 1 / Ark 路径）。

---

## 环境变量（VM-1）

| 变量 | 必填 | 说明 |
|------|------|------|
| `VOLC_RTC_DEFAULT_USER_ID` | 建议 | Viking `filter.user_id`；默认 `boxi_user` |
| `VIKING_MEMORY_COLLECTION` | 启用长期记忆时 | 控制台记忆库名称 |
| `VIKING_MEMORY_LIMIT` | 否 | 检索条数，默认 `3` |
| `VIKING_MEMORY_TRANSITION_WORDS` | 否 | 注入前缀，默认空 |
| `VIKING_MEMORY_ASSISTANT_ID` | 否 | 画像按 assistant 隔离时填写 |
| `VIKING_MEMORY_TYPES` | 否 | 逗号分隔 `memory_type` 过滤 |

未设置 `VIKING_MEMORY_COLLECTION` 时 **不**发送 `MemoryConfig`（行为与现在一致）。

---

## VM-2 控制台清单（用户手动）

1. [Viking 记忆库](https://www.volcengine.com/docs/84313/1827400?lang=zh) 创建 collection，配置事件/画像规则。
2. RTC 控制台为 `VoiceChatRoleForRTC` 授权访问 VikingDB（见 [1928352](https://www.volcengine.com/docs/84313/1928352) 步骤 2）。
3. `.env` 填入 `VIKING_MEMORY_COLLECTION=你的库名`。
4. 重启 backend；两次 RTC 通话验证跨会话召回。

---

## 边界

- 不改 SQLite schema、不改 `CompanionBrain` 契约。
- VM-3 的 Viking API 密钥只放服务端 `.env`，不下发浏览器。
- Soul 混合（OutputMode 1）仍走 `soul_llm_server` 本地记忆，与本 spec 并行、不互斥。
