---
name: pipeline-health-monitor
description: 文章剪藏处理链路健康监控工具。自动监控内容处理链路各环节（微信文章获取、AI创作、队列处理、定时任务执行）的健康状态，检测API可用性、超时、队列积压等问题，异常时主动告警并提供修复建议。使用场景：(1) 定期检查文章剪藏链路健康状态，(2) 监控队列积压和故障预警，(3) 自动化故障发现和修复建议。
---

# Pipeline Health Monitor

文章剪藏处理链路健康监控工具，让故障无处藏身。

## 背景问题

文章剪藏系统依赖多个组件协同工作：
- **微信文章获取** (kimi_fetch) - 可能被反爬或网络问题
- **AI 深度创作** (sessions_spawn) - 可能超时或失败
- **消息队列** (article_queue.json) - 可能积压
- **定时任务** (cron jobs) - 可能执行失败
- **磁盘空间** - 可能不足

当任一环节故障时，用户只能手动排查，**发现时间从分钟级延迟到小时级**。

## 核心功能

### 1. 全链路健康检查

检查以下组件的状态：

| 组件 | 检查内容 | 健康标准 |
|------|----------|----------|
| kimi_fetch | 模块可导入性 | 能正常导入 |
| sessions_spawn | 环境可用性 | 环境配置正确 |
| 消息队列 | 待处理数量 | < 10 个 |
| 定时任务 | 可获取列表 | 能获取任务列表 |
| 磁盘空间 | 使用率 | < 80% |
| 会话文件 | 文件大小 | < 10MB |

### 2. 智能告警

- **无问题**：静默完成，不打扰用户
- **有问题**：发送详细告警，包含修复建议

### 3. 自动修复建议

针对发现的问题，提供一键修复命令：

| 问题类型 | 修复建议 |
|----------|----------|
| 队列积压 | 执行队列清理脚本 |
| 会话过大 | 提示执行 `/compact` |
| 磁盘不足 | 清理旧会话文件 |
| API 异常 | 检查网络连接 |

## 使用方法

### 方法1: 手动检查

```bash
# 执行健康检查
python3 ~/.openclaw/skills/pipeline-health-monitor/scripts/health_check.py

# 完整链路探测（包含模拟文章处理）
python3 ~/.openclaw/skills/pipeline-health-monitor/scripts/health_check.py --full

# 强制发送通知（即使没有发现问题）
python3 ~/.openclaw/skills/pipeline-health-monitor/scripts/health_check.py --notify
```

### 方法2: 定时自动检查

建议设置为定时任务（如每2小时检查一次）：

```bash
# 添加到 crontab（静默模式，只在有问题时通知）
0 */2 * * * python3 ~/.openclaw/skills/pipeline-health-monitor/scripts/health_check.py --silent
```

### 方法3: 与 OpenClaw 集成

当用户提到以下关键词时触发：
- "文章没处理"
- "队列卡住"
- "检查系统"
- "健康状态"
- "故障排查"

```
用户: 帮我检查一下文章剪藏系统是否正常
AI:   执行健康检查中...
      ✅ 所有检查通过，系统运行正常
      
用户: 队列好像卡住了
AI:   检查队列状态...
      ⚠️ 队列积压 (25 个待处理)
      
      修复建议：
      🔴 执行队列清理
         执行：`cd /root/.openclaw/workspace/second-brain-processor && python3 process_queue.py`
```

## 输出示例

### 健康状态

```
==================================================
文章剪藏链路健康检查 - 2026-03-12 11:30
==================================================

🔍 检查: kimi_fetch 模块
   ✅ kimi_fetch 模块可正常导入

🔍 检查: sessions_spawn 环境
   ✅ sessions_spawn 环境正常

🔍 检查: 消息队列状态
   ✅ 队列正常 (3 个待处理)

🔍 检查: 定时任务状态
   ✅ 定时任务列表可获取

🔍 检查: 磁盘空间
   ✅ 磁盘空间充足 (45%)

🔍 检查: 会话文件大小
   ✅ 会话文件正常 (最大 2.5MB)

==================================================
✅ 所有检查通过，系统运行正常
==================================================

💾 报告已保存: /root/.openclaw/workspace/.learnings/health_check_report.json
```

### 发现问题

```
⚠️ **文章剪藏链路健康检查 - 发现问题**

检测时间：11:30

**检查结果：**

✅ kimi_fetch 模块: 模块可正常导入
✅ sessions_spawn 环境: 环境正常
⚠️ 消息队列状态: 队列积压 (35 个待处理)
✅ 定时任务状态: 定时任务列表可获取
✅ 磁盘空间: 磁盘空间充足 (62%)
⚠️ 会话文件大小: 会话文件偏大 (最大 18MB，建议 /compact)

**修复建议：**

🔴 执行队列清理
   执行：`cd /root/.openclaw/workspace/second-brain-processor && python3 process_queue.py`

🟡 压缩会话上下文
   执行：`/compact`
```

## 报告文件

检查结果会保存到：
```
/root/.openclaw/workspace/.learnings/health_check_report.json
```

包含以下信息：
- 检查时间戳
- 各组件健康状态
- 发现的问题列表
- 修复建议

## 集成到工作流

### 与 Heartbeat 集成

在 `HEARTBEAT.md` 中添加：
```markdown
### 4. 文章剪藏链路健康检查
- [ ] 执行健康检查
  ```bash
  python3 ~/.openclaw/skills/pipeline-health-monitor/scripts/health_check.py --silent
  ```
- [ ] 检查是否有告警
```

### 与每日复盘集成

在每日复盘中自动包含健康检查结果：
```python
# 在每日报告生成时读取健康报告
with open('/root/.openclaw/workspace/.learnings/health_check_report.json') as f:
    health = json.load(f)
    
if health['overall_status'] != 'healthy':
    report += f"\n⚠️ 系统健康: 发现 {len(health['issues'])} 个问题"
```

## 故障排查

### 检查报告未生成

检查日志文件：
```bash
tail -20 /root/.openclaw/workspace/.learnings/health_check_report.json
```

### 通知未发送

检查发送记录：
```bash
grep "health_check" /root/.openclaw/workspace/.learnings/send_records.json
```

### 某个组件一直检查失败

手动测试该组件：
```bash
# 测试 kimi_fetch
cd /root/.openclaw/workspace/second-brain-processor
python3 -c "from kimi_fetch import kimi_fetch; print('OK')"

# 测试队列
python3 -c "import json; q=json.load(open('article_queue.json')); print(f'队列: {len(q[\"pending\"])} 个待处理')"
```

## 扩展开发

### 添加新的检查项

在 `health_check.py` 的 `run_full_check` 方法中添加：

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

编辑 `health_check.py` 中的阈值常量：

```python
# 队列积压阈值
QUEUE_WARNING_THRESHOLD = 10   # 警告
QUEUE_CRITICAL_THRESHOLD = 50  # 严重

# 磁盘使用率阈值
DISK_WARNING_THRESHOLD = 80    # 警告
DISK_CRITICAL_THRESHOLD = 90   # 严重

# 会话文件大小阈值（MB）
SESSION_WARNING_THRESHOLD = 10   # 警告
SESSION_CRITICAL_THRESHOLD = 50  # 严重
```

## 相关文件

- 脚本位置：`scripts/health_check.py`
- 报告位置：`/root/.openclaw/workspace/.learnings/health_check_report.json`
- 发送记录：`/root/.openclaw/workspace/.learnings/send_records.json`

## 更新日志

- **2026-03-12**: 初始版本，支持6项健康检查
