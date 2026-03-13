# 功能请求

记录用户提出但暂不支持的功能需求。

---

## [FR-20260305-001] 自动错误捕获机制

**Logged**: 2026-03-05T11:59:00+08:00
**Priority**: high
**Status**: implementing
**Source**: 整合 self-improving-agent 经验

### 描述
在关键操作（git push、文件处理、API 调用）失败时自动记录到 ERRORS.md，而非依赖用户反馈。

### 预期行为
1. 关键操作包装 try-catch
2. 失败时自动写入 ERRORS.md
3. 定期回顾错误模式

---

## [FR-20260305-002] 规则优先级与状态管理

**Logged**: 2026-03-05T11:59:00+08:00
**Priority**: medium
**Status**: pending
**Source**: 整合 self-improving-agent 经验

### 描述
给 AGENTS.md 的规则增加优先级和状态字段，便于筛选和回顾。

### 预期格式
```markdown
### 规则X: 名称 (YYYY-MM-DD)
**Priority**: high/medium/low
**Status**: active/deprecated/pending-review
```

---

## 格式模板

```markdown
## [FR-YYYYMMDD-XXX] 功能名称

**Logged**: ISO-8601 时间
**Priority**: high/medium/low
**Status**: pending/under-review/implementing/done/wontfix
**Source**: 来源/背景

### 描述
功能需求描述

### 预期行为
具体期望
```
