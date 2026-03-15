---
name: cron-health-dashboard
description: 跨系统定时任务健康监控工具。自动监控 OpenClaw cron 任务和 Linux 系统 cron 任务的状态，检测"僵尸任务"（显示成功但无实际输出/文件未更新），异常时主动告警并提供修复建议。使用场景：(1) 定期检查定时任务健康状态，(2) 监控任务执行失败或停滞，(3) 自动化故障发现和告警。
---

# Cron Health Dashboard

跨系统定时任务健康监控工具，让"僵尸任务"无处藏身。

## 背景问题

OpenClaw 2026.2.13 版本更新后，isolated+agentTurn 模式出现失效问题：
- 定时任务显示"成功"状态
- 实际任务未执行或执行异常
- 用户直到次日 9:45 才发现问题

这种"僵尸任务"导致系统可靠性严重下降，需要一个主动监控机制。

## 核心功能

### 1. 双系统监控

| 监控对象 | 检查内容 | 检测方式 |
|---------|----------|---------|
| OpenClaw Cron | 任务列表、执行状态、错误状态 | `openclaw cron list` |
| Linux Cron | crontab 配置、系统 cron | `/var/spool/cron/` |

### 2. 僵尸任务检测

检测以下异常模式：
- **Status=error**: 任务执行报错
- **Status=idle但应执行**: 长时间未执行（超过预期间隔2倍）
- **Last为空但非首次**: 从未执行过但已创建
- **成功但无输出**: 检查日志/输出文件时间戳

### 3. 智能告警

- **无问题**: 静默完成，不打扰用户
- **有问题**: 发送详细告警，包含修复建议

### 4. 健康报告

生成结构化健康报告，包含：
- 任务执行统计
- 异常任务详情
- 修复建议
- 历史趋势

## 使用方法

### 方法1: 手动检查

```bash
# 执行健康检查
python3 ~/.openclaw/skills/cron-health-dashboard/scripts/cron_health_check.py

# 详细检查（包含日志分析）
python3 ~/.openclaw/skills/cron-health-dashboard/scripts/cron_health_check.py --verbose

# 强制发送通知（即使没有发现问题）
python3 ~/.openclaw/skills/cron-health-dashboard/scripts/cron_health_check.py --notify
```

### 方法2: 定时自动检查

建议设置为定时任务（如每2小时检查一次）：

```bash
# 添加到 crontab（静默模式，只在有问题时通知）
0 */2 * * * python3 ~/.openclaw/skills/cron-health-dashboard/scripts/cron_health_check.py --silent
```

### 方法3: 与 OpenClaw 集成

当用户提到以下关键词时触发：
- "cron 任务"
- "定时任务"
- "任务监控"
- "健康检查"
- "僵尸任务"

```
用户: 帮我检查一下定时任务是否正常
AI:   执行健康检查中...
      ✅ 所有检查通过，系统运行正常
      
用户: 发现僵尸任务了吗？
AI:   检查定时任务状态...
      ⚠️ 发现 2 个异常任务
      - 自我进化流水线-架构师 (status=error)
      - 自我进化流水线-开发者 (last执行 12小时前)
```

## 输出示例

### 健康状态

```
==================================================
Cron 健康检查 - 2026-03-15 17:00
==================================================

🔍 OpenClaw Cron 任务 (13个)
   ✅ 正常: 10 个
   ⚠️ 警告: 2 个 (error状态)
   ❌ 严重: 1 个 (长期未执行)

🔍 Linux Cron 任务 (5个)
   ✅ 正常: 5 个

==================================================
⚠️ 发现 3 个问题
==================================================

💾 报告已保存: /root/.openclaw/workspace/.learnings/cron_health_report.json
```

### 发现问题

```
⚠️ **Cron 健康检查 - 发现问题**

检测时间：17:00

**OpenClaw Cron 异常：**

❌ bc1e430c 自我进化流水线-架构师
   Status: error
   Last: 13h ago
   Next: in 3h
   
❌ bbc6b233 自我进化流水线-开发者
   Status: error
   Last: 12h ago
   Next: in 4h
   
⚠️ ab5cc2b3 GAP02-cron-health-dash...
   Status: idle
   Last: 从未执行
   建议: 检查任务配置

**修复建议：**

🔴 重启失败的定时任务
   执行：`openclaw cron restart bc1e430c bbc6b233`

🟡 检查 isolated+agentTurn 模式
   执行：`openclaw status`
```

## 报告文件

检查结果会保存到：
```
/root/.openclaw/workspace/.learnings/cron_health_report.json
```

包含以下信息：
- 检查时间戳
- OpenClaw cron 任务详情
- Linux cron 任务详情
- 发现的问题列表
- 修复建议
- 历史统计数据

## 集成到工作流

### 与 Heartbeat 集成

在 `HEARTBEAT.md` 中添加：
```markdown
### 5. Cron 健康检查
- [ ] 执行健康检查
  ```bash
  python3 ~/.openclaw/skills/cron-health-dashboard/scripts/cron_health_check.py --silent
  ```
- [ ] 检查是否有僵尸任务
```

### 与每日复盘集成

在每日复盘中自动包含健康检查结果：
```python
# 在每日报告生成时读取健康报告
with open('/root/.openclaw/workspace/.learnings/cron_health_report.json') as f:
    health = json.load(f)
    
if health['overall_status'] != 'healthy':
    report += f"\n⚠️ Cron 健康: 发现 {len(health['issues'])} 个异常任务"
```

## 故障排查

### 检查报告未生成

检查日志文件：
```bash
tail -20 /root/.openclaw/workspace/.learnings/cron_health_report.json
```

### 通知未发送

检查发送记录：
```bash
grep "cron_health" /root/.openclaw/workspace/.learnings/send_records.json
```

### 任务状态获取失败

手动测试：
```bash
# 测试 OpenClaw cron
openclaw cron list

# 测试 Linux cron
crontab -l
```

## 扩展开发

### 添加新的检查项

在 `cron_health_check.py` 的 `run_full_check` 方法中添加：

```python
checks = [
    # ... 现有检查
    ("新检查名称", self.check_new_component),
]
```

然后实现检查方法：

```python
def check_new_component(self) -> Tuple[bool, str]:
    """检查新组件"""
    try:
        # 执行检查逻辑
        if 一切正常:
            return True, "状态正常"
        else:
            return False, "发现问题描述"
    except Exception as e:
        return False, f"检查异常: {e}"
```

### 修改告警阈值

编辑 `cron_health_check.py` 中的阈值常量：

```python
# 执行间隔超时阈值（小时）
IDLE_TIMEOUT_HOURS = 2  # 超过2倍预期间隔视为异常

# 错误状态连续次数
ERROR_STREAK_THRESHOLD = 2  # 连续2次错误告警
```

## 相关文件

- 脚本位置：`scripts/cron_health_check.py`
- 报告位置：`/root/.openclaw/workspace/.learnings/cron_health_report.json`
- 发送记录：`/root/.openclaw/workspace/.learnings/send_records.json`

## 更新日志

- **2026-03-15**: 初始版本，支持 OpenClaw + Linux 双系统监控
