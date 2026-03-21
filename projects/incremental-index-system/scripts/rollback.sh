#!/bin/bash
# 增量索引系统回滚脚本
# Rollback script for Incremental Message Index System

set -e

echo "=========================================="
echo "Incremental Index System Rollback"
echo "=========================================="
echo ""

TARGET_DIR="/root/.openclaw/workspace/second-brain-processor"

echo "[1/4] Stopping current process..."
# 检查是否有正在运行的任务
pkill -f "process_incremental.py" 2>/dev/null || true
echo "  ✓ Processes stopped"

echo ""
echo "[2/4] Restoring original files..."

# 恢复原始脚本
if [ -f "$TARGET_DIR/process_raw.py.backup" ]; then
    cp "$TARGET_DIR/process_raw.py.backup" "$TARGET_DIR/process_raw.py"
    echo "  ✓ Restored process_raw.py"
else
    echo "  ⚠ Backup not found, manual restoration required"
fi

echo ""
echo "[3/4] Updating cron job..."
# 恢复定时任务配置
# 这里需要根据实际情况修改
echo "  ⚠ Please manually update cron job to use process_raw.py"
echo "     Run: openclaw cron list"
echo "     Then: openclaw cron update <job-id> --payload '...process_raw.py...'"

echo ""
echo "[4/4] Verifying rollback..."
if [ -f "$TARGET_DIR/process_raw.py" ]; then
    python3 -m py_compile "$TARGET_DIR/process_raw.py" && echo "  ✓ Original script is valid"
else
    echo "  ✗ Original script not found!"
    exit 1
fi

echo ""
echo "=========================================="
echo "Rollback Complete!"
echo "=========================================="
echo ""
echo "Note: Index files in .data/ are preserved."
echo "      They can be safely removed if needed."
echo ""
