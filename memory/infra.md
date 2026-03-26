# 基础设施层 (Infrastructure)

记录服务器配置、API密钥、定时任务等基础设施信息。

---

## API配置

### Kimi API
- **Base URL**: https://api.kimi.com/coding
- **模型**: k2p5
- **Context Window**: 131072 (128k)
- **Max Tokens**: 32768

### memorySearch配置
- **Provider**: openai
- **模型**: bge_m3_embed
- **状态**: ✅ 已启用

---

## 定时任务清单

| 时间 | 任务名称 | 脚本 | 状态 |
|------|---------|------|------|
| 5:00 | 清晨整理 | `process_raw.py` | ✅ 运行中 |
| 8:30 | 复盘报告 | `daily_complete_report.py` | ✅ 运行中 |
| 13:00 | 动态上下文压缩 | `dynamic_compactor.py` | ✅ 运行中 |

---

## 关键路径

| 用途 | 路径 |
|------|------|
| 工作空间 | `/root/.openclaw/workspace` |
| 记忆目录 | `/root/.openclaw/workspace/memory` |
| 日志文件 | `/root/.openclaw/logs/openclaw.log` |
| 配置文件 | `/root/.openclaw/openclaw.json` |

---

## 模型配置参考

### 成功率排名（2026-03-08）
| 排名 | 模型 | 成功率 |
|------|------|--------|
| 1 | google/gemini-3-flash-preview | 高 |
| 2 | minimax/minimax-m2.1 | 高 |
| 3 | moonshotai/kimi-k2.5 | 高 |
| 4 | anthropic/claude-sonnet-4.5 | 高 |
| 5 | google/gemini-3-pro-preview | 高 |

**注意**: MiniMax M2.5 成功率仅35.5%，避免使用

### 版本升级注意事项

**OpenClaw 2026.2.13 已知问题**:
- `agentTurn` + `isolated` session 模式下，子 Agent 工具调用会出现 `35 validation errors`
- **解决方案**: 定时任务改用 `systemEvent` + `sessionTarget: main`

- **自动备份**: Git提交前自动创建 `.backup.YYYYMMDD-HHMMSS`
- **保留时间**: 至少1周
- **恢复命令**: `cp *.backup.YYYYMMDD-HHMMSS 原文件名`
