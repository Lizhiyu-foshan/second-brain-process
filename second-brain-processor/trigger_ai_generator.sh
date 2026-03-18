#!/bin/bash
#
# 手动触发GLM5异步改进生成
#

SCRIPT_DIR="/root/.openclaw/workspace/second-brain-processor"
LOG_FILE="/tmp/ai_generator_manual_$(date +%Y%m%d_%H%M%S).log"

echo "========================================"
echo "手动触发GLM5异步改进生成"
echo "时间: $(date)"
echo "========================================"
echo ""

cd "$SCRIPT_DIR"

# 检查是否已在运行
if pgrep -f "ai_async_generator.py --process" > /dev/null; then
    echo "⚠️ GLM5异步生成已在运行"
    echo "   查看状态: python3 check_ai_status.py"
    echo "   查看日志: tail -f /tmp/ai_generator_*.log"
    exit 1
fi

echo "启动GLM5异步改进生成..."
echo "日志文件: $LOG_FILE"
echo ""

python3 ai_async_generator.py --process 2>&1 | tee "$LOG_FILE"

echo ""
echo "========================================"
echo "完成时间: $(date)"
echo "查看结果: python3 check_ai_status.py"
echo "========================================"
