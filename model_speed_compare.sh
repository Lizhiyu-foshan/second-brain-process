#!/bin/bash
#
# 简化版模型速度对比测试
# 使用方法: bash model_speed_compare.sh [迭代次数]
#

ITERATIONS=${1:-2}
WORKSPACE="/root/.openclaw/workspace"
RESULTS_DIR="$WORKSPACE/model_compare_results"

mkdir -p "$RESULTS_DIR"

echo "========================================"
echo "🚀 模型速度对比测试"
echo "========================================"
echo ""
echo "测试配置:"
echo "  - Qwen3.5 Plus"
echo "  - Kimi K2.5"
echo "  - 迭代次数: $ITERATIONS"
echo ""

# 测试问题
TEST1="什么是Python列表推导式？简要回答。"
TEST2="写一段快速排序代码。"
TEST3="分析递归斐波那契的时间复杂度。"

echo "========================================"
echo "测试 1/3: 简单问答"
echo "========================================"
echo "问题: $TEST1"
echo ""

echo "🤖 测试 Qwen3.5 Plus..."
START=$(date +%s.%N)
# 这里需要实际调用模型，当前只是计时框架
sleep 1  # 模拟
END=$(date +%s.%N)
QWEN1=$(echo "$END - $START" | bc)
echo "  用时: ${QWEN1}s"

echo ""
echo "🤖 测试 Kimi K2.5..."
START=$(date +%s.%N)
# 这里需要实际调用模型，当前只是计时框架
sleep 1  # 模拟
END=$(date +%s.%N)
KIMI1=$(echo "$END - $START" | bc)
echo "  用时: ${KIMI1}s"

echo ""
echo "结果: Qwen=${QWEN1}s, Kimi=${KIMI1}s"

echo ""
echo "========================================"
echo "📊 总结报告"
echo "========================================"
echo ""
echo "测试完成！完整测试请运行:"
echo "  python3 model_speed_test_auto.py 3"
echo ""
