#!/bin/bash
#
# 定期清理旧会话文件
# 保留最近7天的会话，清理历史文件
#

SESSION_DIR="/root/.openclaw/agents/main/sessions"
LOG_FILE="/tmp/session_cleanup_$(date +%Y%m%d).log"
RETENTION_DAYS=7

echo "$(date '+%Y-%m-%d %H:%M:%S') 开始清理会话文件..." | tee -a "$LOG_FILE"

# 检查目录是否存在
if [ ! -d "$SESSION_DIR" ]; then
    echo "会话目录不存在: $SESSION_DIR" | tee -a "$LOG_FILE"
    exit 1
fi

# 统计清理前文件数和大小
BEFORE_COUNT=$(find "$SESSION_DIR" -name "*.jsonl" -type f | wc -l)
BEFORE_SIZE=$(du -sh "$SESSION_DIR" 2>/dev/null | cut -f1)
echo "清理前: $BEFORE_COUNT 个文件, 占用 $BEFORE_SIZE" | tee -a "$LOG_FILE"

# 清理超过7天的jsonl文件
DELETED_COUNT=0
DELETED_SIZE=0

while IFS= read -r file; do
    if [ -f "$file" ]; then
        file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
        DELETED_SIZE=$((DELETED_SIZE + file_size))
        DELETED_COUNT=$((DELETED_COUNT + 1))
        rm -f "$file"
        echo "删除: $(basename "$file") ($(numfmt --to=iec $file_size 2>/dev/null || echo ${file_size}B))" | tee -a "$LOG_FILE"
    fi
done < <(find "$SESSION_DIR" -name "*.jsonl" -type f -mtime +$RETENTION_DAYS)

# 统计清理后
AFTER_COUNT=$(find "$SESSION_DIR" -name "*.jsonl" -type f | wc -l)
AFTER_SIZE=$(du -sh "$SESSION_DIR" 2>/dev/null | cut -f1)
echo "清理后: $AFTER_COUNT 个文件, 占用 $AFTER_SIZE" | tee -a "$LOG_FILE"

# 汇总
if [ $DELETED_COUNT -gt 0 ]; then
    echo "✅ 共清理 $DELETED_COUNT 个文件, 释放 $(numfmt --to=iec $DELETED_SIZE 2>/dev/null || echo ${DELETED_SIZE}B)" | tee -a "$LOG_FILE"
else
    echo "✅ 无需清理，所有文件都在保留期内" | tee -a "$LOG_FILE"
fi

# 清理30天前的日志
find /tmp -name "session_cleanup_*.log" -mtime +30 -delete 2>/dev/null || true

exit 0
