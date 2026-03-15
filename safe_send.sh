#!/bin/bash
# 安全发送消息脚本 - 带去重检查
# 用法: ./safe_send.sh "消息内容" [feishu_user_id]

MESSAGE="$1"
TARGET="${2:-ou_363105a68ee112f714ed44e12c802051}"
WORKSPACE="/root/.openclaw/workspace/second-brain-processor"

# 检查参数
if [ -z "$MESSAGE" ]; then
    echo "[ERROR] 消息内容为空"
    exit 1
fi

# 使用Python检查是否已发送
cd "$WORKSPACE"
CHECK_RESULT=$(python3 -c "
import sys
sys.path.insert(0, '$WORKSPACE')
from message_dedup import is_message_sent
content = '''$MESSAGE'''
if is_message_sent(content):
    print('DUPLICATE')
else:
    print('OK')
")

if [ "$CHECK_RESULT" = "DUPLICATE" ]; then
    echo "[SKIP] 消息已发送过（24小时内），跳过"
    exit 0
fi

# 发送消息
openclaw message send --target "$TARGET" --message "$MESSAGE"
SEND_STATUS=$?

if [ $SEND_STATUS -eq 0 ]; then
    # 记录已发送
    python3 -c "
import sys
sys.path.insert(0, '$WORKSPACE')
from message_dedup import record_message_sent
content = '''$MESSAGE'''
record_message_sent(content)
print('[OK] 消息已发送并记录指纹')
"
else
    echo "[ERROR] 消息发送失败"
    exit 1
fi
