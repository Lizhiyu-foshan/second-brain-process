---
name: auto-fix
description: 自动修复工具。根据健康检查报告自动执行修复操作，包括清理旧会话文件、处理队列积压、释放磁盘空间、自动压缩会话上下文等。支持模拟模式预览修复内容，执行后生成修复报告。使用场景：(1) 定期自动修复系统问题，(2) 手动触发一键修复，(3) 与健康检查联动实现闭环，(4) 自动压缩过大的会话文件。
---

# Auto Fix

自动修复工具，让系统问题自动恢复。

## 包含工具

### 1. auto_fix.py - 综合修复工具

根据健康检查报告自动执行修复。

### 2. auto_compact.py - 自动会话压缩

**核心功能**：自动检测并压缩过大的会话文件，无需人工干预。

## 背景问题

### 综合修复
健康检查发现的问题需要手动修复：
- 队列积压 → 需要手动执行队列清理
- 磁盘空间不足 → 需要手动清理文件

### 会话压缩
会话文件会不断增长，导致：
- 上下文过长，AI 响应变慢
- 内存占用增加
- 需要手动执行 `/compact`

**Auto Fix 自动处理这些问题**。

## 核心功能

### auto_fix.py

#### 1. 自动读取健康报告

读取 `pipeline-health-monitor` 生成的健康报告。

#### 2. 支持的修复操作

| 问题类型 | 修复操作 | 实现方式 |
|----------|----------|----------|
| 队列积压 | 处理队列 | 执行 process_queue.py |
| 磁盘空间不足 | 清理临时文件 | 删除 /tmp/*.tmp 和旧日志 |

### auto_compact.py

#### 自动压缩策略

| 阈值 | 大小 | 动作 |
|------|------|------|
| 警告 | 10MB | 记录日志，不处理 |
| 自动压缩 | 20MB | 自动清理旧会话 |
| 紧急 | 50MB | 立即强制压缩 |

#### 压缩规则

1. **保留活跃会话**（当前正在使用的）
2. **保留最近24小时**的会话
3. **删除过期会话**文件
4. **避免频繁压缩**（至少间隔1小时）

## 使用方法

### auto_fix.py

```bash
# 执行自动修复
python3 ~/.openclaw/skills/auto-fix/scripts/auto_fix.py

# 模拟模式
python3 ~/.openclaw/skills/auto-fix/scripts/auto_fix.py --dry-run
```

### auto_compact.py

```bash
# 检查是否需要压缩
python3 ~/.openclaw/skills/auto-fix/scripts/auto_compact.py --check

# 手动触发压缩
python3 ~/.openclaw/skills/auto-fix/scripts/auto_compact.py --force

# 模拟模式
python3 ~/.openclaw/skills/auto-fix/scripts/auto_compact.py --dry-run
```

### 定时自动运行

建议设置为定时任务：

```bash
# 每30分钟检查一次会话大小
*/30 * * * * python3 ~/.openclaw/skills/auto-fix/scripts/auto_compact.py --silent

# 每天凌晨3点执行综合修复
0 3 * * * python3 ~/.openclaw/skills/auto-fix/scripts/auto_fix.py --silent
```

## 输出示例

### 自动压缩触发

```
==================================================
自动会话压缩 - 2026-03-12 11:45
==================================================

📊 当前状态:
   会话文件数: 27
   最大文件: 25.3MB
   压缩阈值: 20MB

🔍 检查: 会话文件过大 (25.3MB > 20MB)

🔧 执行压缩...
   ✅ 已清理 5 个旧会话文件，释放 15.2MB

==================================================
检查完成
==================================================

✅ 通知已发送
```

### 未达阈值

```
==================================================
自动会话压缩 - 2026-03-12 12:00
==================================================

📊 当前状态:
   会话文件数: 22
   最大文件: 8.5MB
   压缩阈值: 20MB

🔍 检查: 会话文件正常 (8.5MB)

⏭️  跳过压缩

==================================================
检查完成
==================================================
```

## 相关文件

- 脚本位置：`scripts/auto_fix.py`, `scripts/auto_compact.py`
- 修复报告：`/root/.openclaw/workspace/.learnings/auto_fix_report.json`
- 压缩状态：`/root/.openclaw/workspace/.learnings/auto_compact_state.json`
- 健康报告：`/root/.openclaw/workspace/.learnings/health_check_report.json`

## 更新日志

- **2026-03-12**: 初始版本，支持综合修复和自动会话压缩
