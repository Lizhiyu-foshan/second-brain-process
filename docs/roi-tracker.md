# ROI 追踪器使用文档

## 概述

ROI 追踪器用于追踪自动化检查任务的投资回报率，识别低价值任务并建议停用。

**核心目标**：
- 连续追踪 7 天，观察每个任务的实际价值
- 识别并停用"空跑"任务（执行但不发现问题）
- 优化自动化检查体系，减少资源浪费

## 核心指标

| 指标 | 说明 | 计算方式 |
|------|------|---------|
| **执行次数** | 任务运行了多少次 | 累计计数 |
| **发现问题数** | 真正检测出问题的次数 | 累计计数 |
| **触发改进数** | 导致实际修复/优化的次数 | 累计计数 |
| **空跑率** | 无问题执行占比 | (总执行 - 发现问题) / 总执行 |
| **价值评分** | 单位执行产生的价值 | (发现问题 + 改进数) / 总执行 |

## 价值判定规则

| 等级 | 价值评分 | 空跑率 | 建议 |
|------|---------|--------|------|
| 🟢 高价值 | > 0.1 | < 90% | 保留 |
| 🟡 中价值 | 0.01-0.1 | 90%-99% | 优化检测逻辑 |
| 🔴 低价值 | < 0.01 | > 99% | **建议停用** |

**解释**：
- 价值评分 0.1 = 每 10 次执行至少 1 次发现问题/改进
- 价值评分 0.01 = 每 100 次执行至少 1 次发现问题/改进
- 连续一周价值评分<0.01 的任务，说明几乎不产生价值

## 使用方法

### 方法 1：使用包装器（推荐）

适用于任何现有的检查脚本，无需修改原代码：

```bash
# 基本用法
python3 /root/.openclaw/workspace/scripts/roi_wrapper.py \
  --script /root/.openclaw/skills/cron-health-dashboard/scripts/cron_health_check.py \
  --task-name "定时任务健康监控"

# 静默模式（只输出错误）
python3 roi_wrapper.py --script xxx.py --task-name "任务名" --silent

# 禁用 ROI 追踪（临时）
python3 roi_wrapper.py --script xxx.py --task-name "任务名" --no-roi
```

### 方法 2：直接调用追踪 API

适用于需要在代码中集成的场景：

```python
from roi_tracker import record_task_execution

# 执行检查
found_issues = check_something()
improvements = fix_issues()

# 记录 ROI 数据
record_task_execution(
    task_name="我的检查任务",
    found_issues=found_issues,
    improvements=improvements,
    duration_ms=1234,
    details="发现 2 个警告"
)
```

### 方法 3：生成报告

```bash
# 查看当前统计
python3 roi_tracker.py stats

# 生成周报
python3 roi_tracker.py report

# 重置追踪（开始新周期）
python3 roi_tracker.py reset
```

## 集成到定时任务

### OpenClaw Cron

更新现有的 cron 任务，使用 roi_wrapper.py 包裹：

```bash
# 原配置
openclaw cron update --job-id "xxx" --command "python3 cron_health_check.py --silent"

# 新配置（带 ROI 追踪）
openclaw cron update --job-id "xxx" --command "python3 roi_wrapper.py --script cron_health_check.py --task-name '定时任务健康监控' --silent"
```

### Linux Cron

编辑 crontab：

```bash
crontab -e

# 原配置
*/10 * * * * python3 /path/to/check.py >> /tmp/check.log 2>&1

# 新配置（带 ROI 追踪）
*/10 * * * * python3 /root/.openclaw/workspace/scripts/roi_wrapper.py \
  --script /path/to/check.py \
  --task-name "检查任务名称" \
  --silent >> /tmp/check.log 2>&1
```

## 查看报告

### 实时统计

```bash
python3 /root/.openclaw/workspace/scripts/roi_tracker.py stats
```

输出示例：
```
🟢 高价值 定时任务健康监控：价值评分=0.1523, 执行=168, 问题=25
🟡 中价值 配置健康检查：价值评分=0.0476, 执行=84, 问题=4
🔴 低价值 旧会话清理：价值评分=0.0000, 执行=168, 问题=0
```

### 周报

```bash
python3 /root/.openclaw/workspace/scripts/roi_tracker.py report
```

报告保存在：`/root/.openclaw/workspace/.learnings/roi_tracker/roi_weekly_report.md`

报告内容包括：
- 总体概览（执行次数、问题数、改进数）
- 低价值任务列表（建议停用）
- 中价值任务列表（建议优化）
- 高价值任务列表（保留）
- 最近执行记录抽样

## 追踪周期

**建议追踪 7 天**，原因：
- 覆盖完整的工作日 + 周末周期
- 足够发现周期性任务的价值
- 避免单日异常的误导

**周期结束后**：
1. 查看周报，识别低价值任务
2. 停用 1-2 个最低价值的任务
3. 观察 1-2 周，确认无负面影响
4. 如无问题，继续停用其他低价值任务
5. 开始新的追踪周期

## 文件结构

```
/root/.openclaw/workspace/scripts/
├── roi_tracker.py          # 核心追踪器
├── roi_wrapper.py          # 包装器（包裹其他脚本）
└── ...

/root/.openclaw/workspace/.learnings/roi_tracker/
├── execution_records.json  # 执行记录数据
└── roi_weekly_report.md    # 周报（每周生成）
```

## 常见问题

### Q: 追踪会影响性能吗？
A: 几乎无影响。追踪逻辑非常简单，增加的开销<10ms。

### Q: 如何判断"发现问题"？
A: 包装器会自动分析脚本输出，检测关键词如"发现"、"警告"、"错误"等。也可以手动指定。

### Q: 追踪数据会永久保存吗？
A: 建议每周重置一次，保持数据新鲜。可以使用 cron 自动重置：
```bash
# 每周日 23:50 重置
50 23 * * 0 python3 roi_tracker.py reset
```

### Q: 如何确认停用任务无风险？
A: 停用后观察 1-2 周：
1. 是否有相关问题未被发现？
2. 是否有用户反馈？
3. 系统是否正常运行？

如无异常，可以安全停用。

## 最佳实践

1. **逐步停用**：不要一次性停用所有低价值任务
2. **保留日志**：停用前备份任务配置和执行记录
3. **设置观察期**：停用后观察 2 周再决定永久删除
4. **定期复盘**：每周查看报告，持续优化

## 示例：完整集成流程

### 第 1 步：安装追踪器
```bash
cd /root/.openclaw/workspace/scripts
# 已存在 roi_tracker.py 和 roi_wrapper.py
```

### 第 2 步：更新定时任务
```bash
# 更新 cron 健康检查任务
openclaw cron update --job-id "dfaa8ed7-9b0b-4f26-b7fc-2950d2267f61" \
  --command "python3 roi_wrapper.py --script /root/.openclaw/skills/cron-health-dashboard/scripts/cron_health_check.py --task-name '定时任务健康监控' --silent"
```

### 第 3 步：追踪 7 天
等待自动执行和记录。

### 第 4 步：查看报告
```bash
python3 roi_tracker.py report
```

### 第 5 步：优化任务
根据报告建议，停用低价值任务。

### 第 6 步：开始新周期
```bash
python3 roi_tracker.py reset
```

---

**创建时间**: 2026-03-16  
**作者**: Kimi Claw  
**版本**: v1.0
