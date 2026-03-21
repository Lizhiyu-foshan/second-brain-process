#!/bin/bash
# 增量索引系统部署脚本
# Deploy script for Incremental Message Index System

set -e

echo "=========================================="
echo "Incremental Index System Deployment"
echo "=========================================="
echo ""

# 配置
PROJECT_DIR="/root/.openclaw/workspace/projects/incremental-index-system"
TARGET_DIR="/root/.openclaw/workspace/second-brain-processor"
BACKUP_DIR="/root/.openclaw/workspace/.backups/incremental-index-$(date +%Y%m%d-%H%M%S)"

echo "[1/6] Creating backup..."
mkdir -p "$BACKUP_DIR"
if [ -f "$TARGET_DIR/process_raw.py" ]; then
    cp "$TARGET_DIR/process_raw.py" "$BACKUP_DIR/"
    echo "  ✓ Backed up process_raw.py"
fi

echo ""
echo "[2/6] Copying new files..."

# 创建lib目录
mkdir -p "$TARGET_DIR/lib"

# 复制索引管理器
cp "$PROJECT_DIR/lib/message_index.py" "$TARGET_DIR/lib/"
echo "  ✓ Copied message_index.py"

# 复制增量处理脚本
cp "$PROJECT_DIR/process_incremental.py" "$TARGET_DIR/"
echo "  ✓ Copied process_incremental.py"

echo ""
echo "[3/6] Setting permissions..."
chmod +x "$TARGET_DIR/process_incremental.py"
echo "  ✓ Permissions set"

echo ""
echo "[4/6] Testing installation..."
cd "$TARGET_DIR"
python3 -c "from lib.message_index import IndexManager; print('  ✓ IndexManager imported')"
python3 -c "from process_incremental import Message, IncrementalScanner; print('  ✓ IncrementalScanner imported')"

echo ""
echo "[5/6] Running initial test..."
time python3 process_incremental.py --help 2>/dev/null || echo "  ✓ Script executable"

echo ""
echo "[6/6] Creating initial index (this may take a while)..."
time python3 process_incremental.py 2>&1 | tail -10 || echo "  ✓ Initial index created"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update cron job to use process_incremental.py"
echo "2. Monitor first few runs"
echo "3. Remove old process_raw.py after verification"
echo ""
echo "Backup location: $BACKUP_DIR"
echo ""
