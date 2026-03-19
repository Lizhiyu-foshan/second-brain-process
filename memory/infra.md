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

## 备份策略

- **自动备份**: Git提交前自动创建 `.backup.YYYYMMDD-HHMMSS`
- **保留时间**: 至少1周
- **恢复命令**: `cp *.backup.YYYYMMDD-HHMMSS 原文件名`
