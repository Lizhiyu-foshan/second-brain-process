#!/bin/bash
# 后台处理笔记的脚本
# 用法: ./background_process.sh <mode> <user_id>

MODE="$1"
USER_ID="$2"

if [ -z "$MODE" ] || [ -z "$USER_ID" ]; then
    echo "Usage: $0 <full|summary|brief> <user_id>"
    exit 1
fi

LOG_FILE="/tmp/second_brain_process_$(date +%Y%m%d%H%M%S).log"
NOTIFICATION_FILE="/root/.openclaw/workspace/pending_notifications.json"

# 执行处理
cd /root/.openclaw/workspace/second-brain-processor
python3 process_all.py "$MODE" > "$LOG_FILE" 2>&1

# 检查处理结果
if [ $? -eq 0 ]; then
    RESULT="✅ 笔记处理完成！已处理完成并同步到 Obsidian Vault。"
else
    RESULT="⚠️ 笔记处理遇到问题，请检查日志: $LOG_FILE"
fi

# 保存通知到文件，供主会话读取
NOTIFICATION=$(cat <<EOF
[{
  "user_id": "$USER_ID",
  "message": "$RESULT",
  "created": "$(date -Iseconds)"
}]
EOF
)

echo "$NOTIFICATION" > "$NOTIFICATION_FILE"

echo "处理完成，结果已保存到 $NOTIFICATION_FILE"
