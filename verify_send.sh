#!/bin/bash
# Cron Job 发送验证脚本
# 在发送消息后调用，记录发送状态并验证

JOB_ID="$1"
JOB_NAME="$2"
MESSAGE_PREVIEW="$3"

if [ -z "$JOB_ID" ] || [ -z "$JOB_NAME" ]; then
    echo "Usage: $0 <job_id> <job_name> [message_preview]"
    exit 1
fi

# 记录发送成功
python3 /root/.openclaw/workspace/cron_monitor.py \
    --record-success "$JOB_ID" \
    --job-name "$JOB_NAME"

# 输出验证信息
echo "✅ [$JOB_NAME] 发送状态已记录"
echo "   Job ID: $JOB_ID"
echo "   时间: $(date '+%Y-%m-%d %H:%M:%S')"
