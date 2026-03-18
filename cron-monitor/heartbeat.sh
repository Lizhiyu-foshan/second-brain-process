#!/bin/bash
# Cron 任务监控心跳 - 每 30 分钟检查一次
# 如果检测到异常，自动触发恢复流程

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/monitor_$(date +%Y%m%d).log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 监控心跳启动" >> "$LOG_FILE"

# 运行健康检查
python3 "$SCRIPT_DIR/cron_monitor.py" --now >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 监控脚本异常退出: $EXIT_CODE" >> "$LOG_FILE"
    # 发送告警
    openclaw message send --target ou_363105a68ee112f714ed44e12c802051 --message "⚠️ Cron监控脚本异常，请检查日志: $LOG_FILE"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 监控心跳完成" >> "$LOG_FILE"
