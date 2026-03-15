# OpenClaw Version Adapter

## 概述

监控 OpenClaw 版本更新，自动检测 API 变化，在版本升级前测试关键功能，提供迁移脚本。

## 背景

OpenClaw 2026.2.13 版本后，`isolated` + `agentTurn` 模式下子 Agent 无法调用工具，导致所有定时任务失效。此 Skill 旨在防止类似问题再次发生。

## 核心功能

### 1. 版本监控
- 检测 OpenClaw 版本更新
- 记录版本变更历史
- 发送版本更新通知

### 2. API 兼容性检测
- 测试关键 API 端点
- 验证工具调用模式
- 检查定时任务执行

### 3. 迁移脚本生成
- 自动生成迁移脚本
- 提供回滚方案
- 记录迁移日志

## 使用方法

### 检查当前版本
```bash
python3 scripts/check_version.py
```

### 测试兼容性
```bash
python3 scripts/test_compatibility.py
```

### 生成迁移脚本
```bash
python3 scripts/generate_migration.py --from <old_version> --to <new_version>
```

## 定时任务

建议配置每日版本检查：
- 时间：每天 08:00
- 操作：检查版本更新，如有更新则测试兼容性并发送通知

## 风险等级

- **Critical**: 直接影响系统核心功能
- **High**: 影响部分功能
- **Medium**: 影响用户体验

## 相关文档

- [OpenClaw 官方文档](https://docs.openclaw.ai)
- [版本更新日志](https://github.com/openclaw/openclaw/releases)