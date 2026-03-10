# AI驱动的代码改进系统

使用阿里云GLM5模型生成代码改进方案，结合基于规则的快速回退机制。

## 架构

```
┌─────────────────────────────────────────────┐
│           每日复盘流程 (5:00 AM)             │
├─────────────────────────────────────────────┤
│  1. 发现错误                                 │
│     ↓                                        │
│  2. 基于规则快速生成改进（5秒内）            │
│     ↓                                        │
│  3. 实施改进（保证快速响应）                 │
│     ↓                                        │
│  4. 后台启动GLM5生成（异步，不阻塞）         │
│     ↓                                        │
│  5. 下次运行时对比/合并GLM5结果              │
└─────────────────────────────────────────────┘
```

## 文件说明

| 文件 | 作用 |
|------|------|
| `system_evolution_ai.py` | 主程序，快速生成+后台启动GLM5 |
| `ai_async_generator.py` | GLM5异步生成器（长超时） |
| `check_ai_status.py` | 查看GLM5生成状态 |
| `trigger_ai_generator.sh` | 手动触发GLM5生成 |

## 使用方式

### 1. 查看GLM5生成状态

```bash
cd /root/.openclaw/workspace/second-brain-processor
python3 check_ai_status.py
```

### 2. 手动触发GLM5生成

```bash
cd /root/.openclaw/workspace/second-brain-processor
./trigger_ai_generator.sh
```

### 3. 查看后台任务日志

```bash
# 查看自动触发的日志
tail -f /tmp/ai_generator_*.log

# 查看手动触发的日志
tail -f /tmp/ai_generator_manual_*.log
```

### 4. 查看AI生成结果

结果保存在：`.learnings/AI_RESULTS.json`

```bash
cat /root/.openclaw/workspace/.learnings/AI_RESULTS.json
```

## GLM5响应时间

- 简单问题：约6秒
- 代码改进生成：30秒-5分钟（取决于复杂度）
- 设置超时：5分钟

## 配置

环境变量配置文件：`.env`

```bash
ALICLOUD_API_KEY=sk-sp-68f6997fc9924babb9f6b50c03a5a529
ALICLOUD_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
ALICLOUD_MODEL=glm-5
```

## 定时任务

已集成到 `run_morning_process.sh`，每天5:00自动：
1. 执行基于规则的改进（快速）
2. 后台启动GLM5生成（异步）

## 注意事项

1. GLM5生成较慢，采用异步方式不阻塞主流程
2. 基于规则的改进保证系统快速响应
3. GLM5结果可用于对比和优化
4. 如果GLM5失败，基于规则的改进已确保系统可用
