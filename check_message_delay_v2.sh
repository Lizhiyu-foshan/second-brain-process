#!/bin/bash
# OpenClaw 消息延迟监控脚本 - 增强版
# 功能：
# 1. 检测会话文件实际更新时间
# 2. 对比消息时间戳和接收时间
# 3. 发现延迟时发送告警

LOG_FILE="/root/.openclaw/workspace/.learnings/message_delay.log"
FEISHU_USER="ou_363105a68ee112f714ed44e12c802051"
SESSION_FILE="/root/.openclaw/agents/main/sessions/sessions.json"

# 获取当前时间
CURRENT_TIME=$(date +%s)
CURRENT_HOUR=$(date +%H)

# 免打扰时段：00:00-07:00
if [ "$CURRENT_HOUR" -ge 0 ] && [ "$CURRENT_HOUR" -lt 7 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 免打扰时段，跳过检测" >> $LOG_FILE
    exit 0
fi

# 检查会话文件是否存在
if [ ! -f "$SESSION_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 会话文件不存在" >> $LOG_FILE
    exit 0
fi

# 获取会话文件最后修改时间
LAST_MODIFY=$(stat -c %Y "$SESSION_FILE")
DIFF=$((CURRENT_TIME - LAST_MODIFY))

# 日志记录
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 会话文件检查: 最后更新 ${DIFF}秒前" >> $LOG_FILE

# 如果会话5分钟内更新过，说明系统正常
if [ $DIFF -lt 300 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 系统响应正常 (${DIFF}秒)" >> $LOG_FILE
    exit 0
fi

# 会话超过5分钟未更新，检查是否有消息延迟
# 通过检查最新的会话文件内容
LATEST_SESSION=$(ls -t /root/.openclaw/agents/main/sessions/*.jsonl 2>/dev/null | head -1)
if [ -n "$LATEST_SESSION" ]; then
    LAST_LINE=$(tail -1 "$LATEST_SESSION" 2>/dev/null)
    if [ -n "$LAST_LINE" ]; then
        # 提取时间戳（如果有）
        MSG_TIME=$(echo "$LAST_LINE" | grep -oP '"timestamp":"[^"]+"' | head -1 | cut -d'"' -f4)
        if [ -n "$MSG_TIME" ]; then
            # 转换ISO时间为Unix时间戳
            MSG_UNIX=$(date -d "$MSG_TIME" +%s 2>/dev/null || echo 0)
            if [ $MSG_UNIX -gt 0 ]; then
                MSG_DIFF=$((CURRENT_TIME - MSG_UNIX))
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] 最后消息时间差: ${MSG_DIFF}秒" >> $LOG_FILE
                
                # 如果消息延迟超过5分钟，发送告警
                if [ $MSG_DIFF -gt 300 ]; then
                    MESSAGE="⚠️ **消息延迟告警**

检测时间：$(date '+%H:%M')

发现延迟：
• 最后消息延迟：${MSG_DIFF}秒
• 会话文件：${DIFF}秒未更新

可能原因：
• Feishu 服务器队列积压
• 网络抖动导致 Webhook 延迟
• 这是外部服务问题，非代码问题

建议：
• 如延迟持续超过30分钟，可尝试重启 OpenClaw
• 或等待 Feishu 服务自动恢复"
                    
                    # 发送告警
                    python3 /root/.openclaw/workspace/second-brain-processor/send_feishu.py "$MESSAGE" "system_alert" 2>/dev/null
                    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️ 已发送延迟告警 (${MSG_DIFF}秒)" >> $LOG_FILE
                    exit 0
                fi
            fi
        fi
    fi
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 检查完成，无异常" >> $LOG_FILE
exit 0
