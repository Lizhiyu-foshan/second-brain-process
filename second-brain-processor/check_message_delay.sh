#!/bin/bash
# OpenClaw 消息延迟监控脚本 - 优化版
# 功能：
# 1. 免打扰时段：00:00-08:00 不检测
# 2. 无消息来往时跳过检测
# 3. 无延迟时静默，有延迟时才发送通知

LOG_FILE="/root/.openclaw/workspace/.learnings/message_delay.log"
FEISHU_USER="ou_363105a68ee112f714ed44e12c802051"
SESSION_FILE="/root/.openclaw/agents/main/sessions/sessions.json"

# 获取当前小时
HOUR=$(date +%H)

# 免打扰时段：00:00-08:00
if [ "$HOUR" -ge 0 ] && [ "$HOUR" -lt 8 ]; then
    # 夜间静默，不检测
    exit 0
fi

# 检查最近30分钟内是否有消息来往（通过会话更新时间）
if [ -f "$SESSION_FILE" ]; then
    LAST_MODIFY=$(stat -c %Y "$SESSION_FILE")
    CURRENT=$(date +%s)
    DIFF=$((CURRENT - LAST_MODIFY))
    
    # 如果30分钟内没有消息来往，跳过检测
    if [ $DIFF -gt 1800 ]; then
        # 静默退出，无消息不发通知
        exit 0
    fi
fi

# 有消息来往，开始检测延迟
HAS_ISSUE=false
ISSUE_MSG=""

# 1. 检查会话上下文压力
if [ -f "$SESSION_FILE" ]; then
    SESSION_SIZE=$(stat -c %s "$SESSION_FILE" 2>/dev/null || echo 0)
    SESSION_SIZE_MB=$((SESSION_SIZE / 1024 / 1024))
    
    if [ $SESSION_SIZE_MB -gt 15 ]; then
        HAS_ISSUE=true
        ISSUE_MSG="${ISSUE_MSG}• 会话文件过大 (${SESSION_SIZE_MB}MB)，建议执行 /compact 压缩\n"
    fi
fi

# 2. 检查最近是否有API错误（通过日志）
RECENT_ERRORS=$(tail -100 /root/.openclaw/logs/gateway.log 2>/dev/null | grep -c "error\|fail" 2>/dev/null | tail -1 || echo 0)
if [ "$RECENT_ERRORS" -gt 5 ] 2>/dev/null; then
    HAS_ISSUE=true
    ISSUE_MSG="${ISSUE_MSG}• 检测到 ${RECENT_ERRORS} 个近期错误\n"
fi

# 3. 检查消息队列积压（简单的会话更新延迟）
if [ -f "$SESSION_FILE" ]; then
    LAST_MODIFY=$(stat -c %Y "$SESSION_FILE")
    CURRENT=$(date +%s)
    DIFF=$((CURRENT - LAST_MODIFY))
    
    if [ $DIFF -gt 300 ]; then
        HAS_ISSUE=true
        ISSUE_MSG="${ISSUE_MSG}• 会话 ${DIFF} 秒未更新，可能存在处理延迟\n"
    fi
fi

# 记录日志（无论是否有问题都记录，但只发通知给当有问题时）
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 消息延迟检查完成" >> $LOG_FILE

# 只有当检测到问题时才发送通知
if [ "$HAS_ISSUE" = true ]; then
    # 发送飞书通知
    MESSAGE="⚠️ **消息延迟告警**

检测时间：$(date '+%H:%M')

发现问题：
${ISSUE_MSG}

建议操作：
• 如延迟持续，可尝试 /compact 压缩会话
• 或重启 OpenClaw 服务"
    
    # 使用 send_feishu.py 发送（带防重发）
    python3 /root/.openclaw/workspace/second-brain-processor/send_feishu.py "$MESSAGE" "system_alert" 2>/dev/null
    
    echo "⚠️ 已发送延迟告警通知" >> $LOG_FILE
else
    # 静默完成，不发送任何通知
    echo "✅ 无延迟问题，静默完成" >> $LOG_FILE
fi

echo "" >> $LOG_FILE
