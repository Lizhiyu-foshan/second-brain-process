# Action Item Closer

复盘报告行动项闭环追踪 - 让待办不再遗漏

## 功能概述

自动提取复盘报告中的行动项，创建追踪任务，监控执行状态，到期提醒，完成验证，形成'识别-分配-执行-验证'的完整闭环。

## 核心问题

- AI生成待办但缺乏自动追踪
- 用户需手动维护待办列表
- 存在遗漏风险（如今天的"补发高质量报告"任务差点被遗忘）

## 解决方案

### 1. 自动提取
- 从复盘报告中识别行动项
- 解析"回复 `安装{n}`"等指令
- 提取TODO标记的待办

### 2. 追踪管理
- 创建唯一ID
- 设置截止日期（默认1天）
- 状态跟踪（待完成/已完成/已过期）

### 3. 定时提醒
- 每天检查过期未完成的行动项
- 推送提醒到飞书
- 显示完成进度

### 4. 完成验证
- 回复 `完成{n}` 标记完成
- 记录完成时间
- 生成完成报告

## 使用方法

### 自动提取
复盘报告生成后自动提取行动项：
```python
action_tracker.py --extract /path/to/report.md
```

### 定时检查
添加到 cron 每天检查：
```bash
0 9 * * * python3 action_tracker.py --check
```

### 查看列表
```bash
python3 action_tracker.py --list
```

### 标记完成
```bash
python3 action_tracker.py --complete "行动项ID"
```

## 输出示例

```
⏰ 行动项提醒

📅 今日: 2026-03-14

📝 待完成 (2项):
1. ⏳ 进行中 安装 context-threshold-adaptive
   截止: 2026-03-14
2. 🔴 已过期 验证定时任务运行结果
   截止: 2026-03-13

✅ 已完成 (3项):
1. 安装 meeting-prep-orchestrator
2. 发送高质量复盘报告
3. 修复skill匹配逻辑

💡 操作: 回复 `完成{n}` 标记第n项完成
```

## 数据存储

- 行动项列表: `/root/.openclaw/workspace/.learnings/action_items.json`
- 运行日志: `/tmp/action_item_closer.log`

## 配置文件

```json
{
  "default_due_days": 1,
  "reminder_time": "09:00",
  "cleanup_after_days": 7
}
```

## 版本

- v1.0.0 - 基础功能：提取、追踪、提醒、完成验证

## 作者

Kimi Claw - 基于用户反馈定制开发
