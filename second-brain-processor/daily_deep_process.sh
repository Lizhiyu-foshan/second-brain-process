#!/bin/bash
# AI深度整理定时任务 - 每天凌晨5:00执行
# 保存到 /root/.openclaw/workspace/second-brain-processor/daily_deep_process.sh

cd /root/.openclaw/workspace/second-brain-processor

# 日志文件
LOG_FILE="/tmp/deep_process_$(date +%Y%m%d).log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始AI深度整理..." >> "$LOG_FILE"

# 执行深度整理
python3 deep_process_all.py --mode deep >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ 深度整理完成" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ 深度整理失败" >> "$LOG_FILE"
fi

# 保留最近7天日志
find /tmp -name "deep_process_*.log" -mtime +7 -delete 2>/dev/null

exit $EXIT_CODE
