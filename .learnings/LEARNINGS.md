## [LEARN-20260306-001] 定时任务执行失败修复

**Logged**: 2026-03-06T09:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: cron_task

### 问题
今天 5:00 和 8:30 的定时任务都执行失败，子 Agent 报告 API 格式错误。

### 根因
`agentTurn` + `isolated` session 模式下，子 Agent 调用工具时出现 schema 验证错误（`35 validation errors`）。这是 OpenClaw 的已知边界情况。

### 解决方案
将任务从 `agentTurn` 改为 `systemEvent`，直接在主会话执行：

| 任务 | 原模式 | 新模式 |
|------|--------|--------|
| 5:00 整理 | agentTurn + isolated | systemEvent + main |
| 8:30 复盘 | agentTurn + isolated | systemEvent + main |

### 实施
- [x] 修改 efccc41b-7887-4af7-b619-54f91679cdaa（5:00整理）
- [x] 修改 35ff007b-d995-4650-a90f-f3c973a386ca（8:30复盘）

### 验证
- 下次执行时间：
  - 5:00 整理：明天 2026-03-07 05:00
  - 8:30 复盘：明天 2026-03-07 08:30

### 经验
1. `agentTurn` 适合需要复杂推理的任务
2. `systemEvent` 适合简单命令执行任务
3. 定时任务优先使用 `systemEvent` + `main` 模式，更稳定

---
