#!/bin/bash
# 凌晨 5:00 系统整理任务 - 包装脚本
# 用于确保任务真正执行并记录日志

set -e

LOG_FILE="/tmp/morning_process_execution.log"
ERROR_FILE="/tmp/morning_process_execution.error"
WORKSPACE="/root/.openclaw/workspace"

echo "=== 凌晨 5:00 系统整理任务 ===" > "$LOG_FILE"
echo "启动时间：$(date -Iseconds)" >> "$LOG_FILE"
echo "状态：STARTED" >> "$LOG_FILE"

# 清除旧错误日志
rm -f "$ERROR_FILE"

# 执行 Python 脚本
cd "$WORKSPACE/second-brain-processor"
if python3 run_morning_process_progress.py >> "$LOG_FILE" 2>&1; then
    echo "状态：SUCCESS" >> "$LOG_FILE"
    echo "完成时间：$(date -Iseconds)" >> "$LOG_FILE"
    echo "✅ 任务执行成功"
    exit 0
else
    EXIT_CODE=$?
    echo "状态：FAILED" >> "$LOG_FILE"
    echo "失败时间：$(date -Iseconds)" >> "$LOG_FILE"
    echo "退出码：$EXIT_CODE" >> "$LOG_FILE"
    echo "❌ 任务执行失败，退出码：$EXIT_CODE"
    
    # 复制错误到最后
    tail -50 "$LOG_FILE" > "$ERROR_FILE"
    exit $EXIT_CODE
fi
