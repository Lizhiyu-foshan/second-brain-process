#!/bin/bash
# 自我进化流水线入口脚本
# 由定时任务调用

set -e

echo "=================================="
echo "自我进化流水线 - $(date)"
echo "=================================="

# 设置环境
export PYTHONPATH="/root/.openclaw/workspace:$PYTHONPATH"
export OPENCLAW_WORKSPACE="/root/.openclaw/workspace"

# 执行编排器
cd /root/.openclaw/workspace
python3 cron-jobs/self-evolution/orchestrator.py

echo "=================================="
echo "流水线结束 - $(date)"
echo "=================================="
