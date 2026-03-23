---
date: 2026-03-23
type: AGENTS核心目录
version: 2.0
---

# AGENTS.md - 核心Harness目录

**说明**：本文档为精简版核心目录，完整规则请查看[AGENTS_DETAILS.md](AGENTS_DETAILS.md)

---

## 快速决策入口

```
开始
  ↓
消息是否重复？ ──是──→ 规则1（NO_REPLY）
  ↓ 否
涉及凭据/Token/密码？ ──是──→ 规则3
  ↓ 否
是 git push 操作？ ──是──→ 规则3
  ↓ 否
是系统监控告警？ ──是──→ 规则4
  ↓ 否
是代码/脚本修改？ ──是──→ 规则7
  ↓ 否
是定时任务配置？ ──是──→ 规则5
  ↓ 否
是模型切换？ ──是──→ 规则6
  ↓ 否
是复杂问题并行？ ──是──→ 规则8
  ↓ 否
是高风险操作？ ──是──→ 规则2
  ↓ 否
正常处理
```

---

## 核心规则索引（8条）

| 规则 | 名称 | 优先级 | 快速链接 | 健康度 |
|------|------|--------|---------|--------|
| RULE_001 | 消息接收去重检查 | high | [详情](AGENTS_DETAILS.md#规则1消息接收去重检查) | ✅ 优秀 |
| RULE_002 | 高风险操作审查 | critical | [详情](AGENTS_DETAILS.md#规则2高风险操作审查) | ✅ 优秀 |
| RULE_003 | GitHub推送与凭据处理 | critical | [详情](AGENTS_DETAILS.md#规则3github推送与凭据处理) | ✅ 关键 |
| RULE_004 | 系统问题根因分析 | high | [详情](AGENTS_DETAILS.md#规则4系统问题根因分析) | ✅ 优秀 |
| RULE_005 | 定时任务配置与监控 | critical | [详情](AGENTS_DETAILS.md#规则5定时任务配置与监控) | ✅ 优秀 |
| RULE_006 | 模型切换检查 | high | [详情](AGENTS_DETAILS.md#规则6模型切换检查) | ✅ 优秀 |
| RULE_007 | 代码部署全流程 | critical | [详情](AGENTS_DETAILS.md#规则7代码部署全流程) | ⚠️ 需优化 |
| RULE_008 | 复杂问题并行处理 | high | [详情](AGENTS_DETAILS.md#规则8复杂问题并行处理) | ✅ 优秀 |

**查看完整规则** → [AGENTS_DETAILS.md](AGENTS_DETAILS.md) (约15,000字)  
**查看规则统计** → [RULES_HEALTH_REPORT.md](RULES_HEALTH_REPORT.md)  
**查看机器索引** → [RULES_REGISTRY.json](RULES_REGISTRY.json)

---

## 今日必读（2026-03-23）

| 优先级 | 内容 |
|--------|------|
| ⚠️ 注意 | 规则7近7天触发3次误报，正在优化验证逻辑 |
| 📊 统计 | 本月规则健康度报告已生成，总体88.5分 |
| ✅ 完成 | AGENTS.md v2.0改造完成，三文件分层架构已上线 |

---

## 关键原则速查

1. **规则溯源**：每条规则背后都有具体错误案例
2. **健康度验证**：规则有效性可量化（触发/阻止/误报）
3. **熵管理**：每月自动检测僵尸规则/重复规则/复杂规则
4. **闭环改进**：错误→规则→验证→优化→固化

---

## 快速链接

- [附录A：通用执行检查清单](AGENTS_DETAILS.md#附录a通用执行检查清单)
- [附录B：多规则冲突处理](AGENTS_DETAILS.md#附录b多规则冲突处理)
- [附录C：规则关联矩阵](AGENTS_DETAILS.md#附录c规则关联矩阵)

---

*文件大小：约55行 | 最后更新：2026-03-23 | 完整版本见AGENTS_DETAILS.md*
