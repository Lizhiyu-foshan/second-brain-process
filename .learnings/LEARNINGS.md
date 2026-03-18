# 📚 系统学习与改进记录

本文件记录系统运行中的关键学习、经验总结和持续改进。

---

## 📊 量化指标看板（自动生成）

> 本区域由 `metrics_collector.py` 自动更新

### 本周核心指标 (Week {WEEK_NUMBER})

| 指标 | 数值 | 趋势 | 目标 | 状态 |
|------|------|------|------|------|
| 🔴 错误率 | {ERROR_RATE}% | {ERROR_TREND} | <5% | {ERROR_STATUS} |
| ⏱️ 平均修复时间 | {AVG_FIX_TIME}h | {FIX_TREND} | <24h | {FIX_STATUS} |
| 🚀 改进密度 | {IMPROVEMENT_COUNT}/周 | {IMPROVEMENT_TREND} | >4/周 | {IMPROVEMENT_STATUS} |
| 📏 规则稳定性 | {STABILITY_SCORE}/100 | {STABILITY_TREND} | >80 | {STABILITY_STATUS} |
| 💰 ROI | {ROI_RATIO} | {ROI_TREND} | >1.0 | {ROI_STATUS} |

### 历史趋势数据（用于图表生成）

```json
{
  "weekly_trend": {
    "weeks": ["W1", "W2", "W3", "W4"],
    "error_rates": [],
    "fix_times": [],
    "improvements": [],
    "stability_scores": []
  },
  "monthly_summary": {
    "total_errors": 0,
    "total_improvements": 0,
    "avg_roi": 0
  }
}
```

### ASCII 趋势图

```
错误率趋势（最近4周）
20%|
15%|     █
10%| █   █
 5%| █ █ █
 0%|_█_█_█_
    W1 W2 W3 W4

改进频率趋势
10|     █
 8| █   █
 6| █ █ █
 4| █ █ █ █
 2| █ █ █ █
 0|_█_█_█_█_
    W1 W2 W3 W4
```

---

## 📈 ROI 计算详情

**投入统计**:
- 代码改进投入: {CODE_IMPROVEMENTS} 次
- 配置调整投入: {CONFIG_CHANGES} 次
- 规则更新投入: {RULE_UPDATES} 次

**产出统计**:
- 错误减少: {ERROR_REDUCTION} 个
- 修复时间缩短: {FIX_TIME_REDUCTION} 小时
- 系统稳定性提升: {STABILITY_IMPROVEMENT}%

**ROI = 产出价值 / 投入成本 = {ROI_VALUE}**

> ROI > 1.0: 改进有效 | ROI < 1.0: 需要调整策略

---

## 📝 学习记录模板

### [LEARN-YYYYMMDD-XXX] 标题

**记录时间**: YYYY-MM-DD HH:MM
**优先级**: critical/high/medium/low
**状态**: active/pending/resolved
**领域**: 系统/工具/流程/协作

#### 问题描述
详细描述遇到的问题或观察到的现象。

#### 根因分析
深入分析问题产生的根本原因。

#### 解决方案
采取的解决措施，包括代码修改、配置调整等。

#### 验证结果
- [ ] 问题已解决
- [ ] 无回归问题
- [ ] 文档已更新

#### 经验总结
1. 关键学习点
2. 最佳实践
3. 避免的坑

#### 相关链接
- 相关 Issue:
- 相关 Commit:
- 相关文档:

---

## 🏆 学习记录归档

（按时间倒序排列）

### [LEARN-20260306-001] 定时任务执行失败修复

**记录时间**: 2026-03-06 09:00
**优先级**: high
**状态**: resolved
**领域**: 系统

#### 问题描述
今天 5:00 和 8:30 的定时任务都执行失败，子 Agent 报告 API 格式错误。

#### 根因分析
`agentTurn` + `isolated` session 模式下，子 Agent 调用工具时出现 schema 验证错误（`35 validation errors`）。这是 OpenClaw 的已知边界情况。

#### 解决方案
将任务从 `agentTurn` 改为 `systemEvent`，直接在主会话执行：

| 任务 | 原模式 | 新模式 |
|------|--------|--------|
| 5:00 整理 | agentTurn + isolated | systemEvent + main |
| 8:30 复盘 | agentTurn + isolated | systemEvent + main |

#### 验证结果
- [x] 问题已解决
- [x] 无回归问题
- [x] 文档已更新

#### 经验总结
1. `agentTurn` 适合需要复杂推理的任务
2. `systemEvent` 适合简单命令执行任务
3. 定时任务优先使用 `systemEvent` + `main` 模式，更稳定

---

## 🔄 改进追踪

### 本周改进
- [ ] 改进 1
- [ ] 改进 2

### 待办改进
1. [ ] 待办 1
2. [ ] 待办 2

---

*最后更新: {LAST_UPDATE} | 下次指标更新: {NEXT_UPDATE}*
