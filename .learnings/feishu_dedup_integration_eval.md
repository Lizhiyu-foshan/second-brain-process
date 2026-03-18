# Feishu 消息去重集成评估报告

**会议 ID**: FEISHU-DEDUP-20260316
**时间**: 2026-03-16 19:54
**背景**: 用户报告 Feishu 重复回复问题，已有去重脚本但未集成到 OpenClaw 插件

---

## 问题背景

### 现象
用户在 Feishu 收到重复回复（同一条消息，AI 回复了 2-3 次）

### 初步分析
1. **去重脚本已存在**: `/root/.openclaw/workspace/second-brain-processor/feishu_receive_dedup.py`
2. **脚本逻辑已修复**: 先检查后记录（2026-03-16 修复）
3. **但脚本未被集成**: 只在 workspace 脚本中被调用，未进入 OpenClaw 消息处理流程

### 关键发现
**Feishu 插件已有去重机制**！
- 位置：`/root/.openclaw/extensions/feishu/src/dedup.ts`
- 函数：`tryRecordMessage(messageId, scope)`
- 逻辑：基于 Feishu message_id 进行内存去重
- 窗口：30 分钟 TTL，最多 1000 条记录
- 作用域：按 accountId 隔离

---

## 当前问题分析

### 为什么有去重机制还会重复？

#### 可能原因 1：去重窗口不够长
- **当前**: 30 分钟 TTL
- **问题**: Feishu 重试可能超过 30 分钟？（不太可能）

#### 可能原因 2：消息 ID 不一致
- Feishu 重试时是否使用相同的 message_id？
- 如果重试生成新 ID，去重会失效

#### 可能原因 3：去重只在插件层，AI 处理层没有兜底
- 插件去重 → AI 处理 → 回复
- 如果 AI 处理超时，Feishu 重试，但插件已认为处理成功
- 下次重试时，message_id 相同，去重拦截 ✓

#### 可能原因 4：多实例/多账号作用域问题
- 如果有多个 Feishu 账号，scope 隔离可能导致重复

#### 可能原因 5：内存重启丢失
- 去重记录存在内存 Map 中
- OpenClaw 重启后，去重记录清空
- 如果 Feishu 在重启后重试旧消息，会重复处理

---

## 评估结论

### ✅ 现有去重机制是足够的（理论上）

Feishu 插件的 `tryRecordMessage` 已经基于 message_id 进行去重：
- **优点**: 精确去重（Feishu message_id 是唯一的）
- **窗口**: 30 分钟（覆盖绝大多数重试场景）
- **性能**: 内存 Map，O(1) 查询

### ⚠️ 但可能存在的问题

1. **重启丢失**: 内存去重在 OpenClaw 重启后失效
2. **窗口限制**: 30 分钟可能不够长（极端重试场景）
3. **日志不足**: 没有详细日志，难以排查问题

### 📋 建议方案

#### 方案 A：增强现有去重（推荐）
**修改**: `/root/.openclaw/extensions/feishu/src/dedup.ts`
- 增加 TTL 到 12 小时
- 增加日志输出（记录去重命中）
- 可选：持久化到文件（重启不丢失）

**风险**: 低（只修改插件内部逻辑）
**收益**: 高（解决根本问题）

#### 方案 B：增加 AI 处理层兜底
**位置**: 在 AI 回复前检查（reply-dispatcher 层）
- 记录已回复的消息指纹
- 检测到重复请求时返回 NO_REPLY

**风险**: 中（增加复杂度）
**收益**: 中（兜底保护）

#### 方案 C：无需修改（先观察）
- 现有去重机制理论上是足够的
- 先增加日志，观察重复发生的具体场景
- 根据日志再决定是否需要增强

**风险**: 低
**收益**: 低（只是拖延问题）

---

## 最终建议

### 立即执行：增加日志（方案 A 的子集）
修改 `dedup.ts`，增加详细日志：
```typescript
if (processedMessageIds.has(dedupKey)) {
  console.log(`[DEDUP] 拦截重复消息：${messageId} (scope=${scope})`);
  return false;
}
```

### 观察期：1 周
- 记录所有去重命中的日志
- 分析重复回复发生的具体场景
- 确认是否是重启导致去重失效

### 后续优化（根据观察结果）
如果日志显示：
- **30 分钟内重复** → 现有逻辑 bug，需要排查
- **30 分钟后重复** → 延长 TTL 到 12 小时
- **重启后重复** → 增加持久化存储

---

## 风险提醒

**修改插件的风险**:
- 需要重新编译/重启 OpenClaw
- 可能影响所有 Feishu 消息处理
- 需要充分测试

**不修改的风险**:
- 用户继续收到重复回复
- 影响使用体验

**折中方案**:
- 只增加日志，不修改核心逻辑
- 观察 1 周后再决定

---

## 附录：关键代码位置

### Feishu 插件去重
- 文件：`/root/.openclaw/extensions/feishu/src/dedup.ts`
- 函数：`tryRecordMessage(messageId, scope)`
- 调用位置：`bot.ts:1282-1286`

### Workspace 去重脚本
- 文件：`/root/.openclaw/workspace/second-brain-processor/feishu_receive_dedup.py`
- 函数：`check_and_record_message(content, sender)`
- 调用位置：`reply_dedup.py` (仅在 workspace 脚本中使用)

---

**记录时间**: 2026-03-16 19:54
**记录者**: Multi-Agent Pipeline Evaluation
