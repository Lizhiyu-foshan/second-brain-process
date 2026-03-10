#!/bin/bash
#
# 每日复盘报告 - 真正执行封装脚本
# 杜绝模拟执行
#

set -e

SCRIPT_DIR="/root/.openclaw/workspace/second-brain-processor"
LOG_FILE="/tmp/daily_report_$(date +%Y%m%d_%H%M%S).log"

echo "========================================" | tee -a "$LOG_FILE"
echo "每日复盘报告 - $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

cd "$SCRIPT_DIR"

# 执行真正的复盘报告脚本
if python3 real_daily_report.py 2>&1 | tee -a "$LOG_FILE"; then
    echo "✅ 复盘报告执行成功" | tee -a "$LOG_FILE"
else
    echo "❌ 复盘报告执行失败" | tee -a "$LOG_FILE"
    # 发送告警
    echo "每日复盘报告执行失败，请检查日志: $LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "完成 - $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 保留最近7天的日志
find /tmp -name "daily_report_*.log" -mtime +7 -delete 2>/dev/null || true

exit 0
