#!/bin/bash
# Kimi Claw 项目快速恢复脚本
# 如果对话丢失，运行此脚本恢复上下文

echo "=========================================="
echo "🔄 Kimi Claw 项目恢复"
echo "=========================================="
echo ""

# 检查项目目录
PROJECT_DIR="/root/.openclaw/workspace/projects/ecommerce-mvp"

if [ -d "$PROJECT_DIR" ]; then
    echo "✅ 项目目录存在: $PROJECT_DIR"
    cd "$PROJECT_DIR"
    
    # 显示项目信息
    if [ -f "PROJECT_LOG.md" ]; then
        echo ""
        echo "📋 项目日志:"
        head -20 PROJECT_LOG.md
    fi
    
    # 显示 Git 状态
    echo ""
    echo "📊 Git 状态:"
    git log --oneline -3 2>/dev/null || echo "Git 未初始化"
    
    echo ""
    echo "✅ 恢复完成！"
    echo ""
    echo "继续开发命令:"
    echo "  cd $PROJECT_DIR"
    echo "  python main.py"
else
    echo "❌ 项目目录不存在"
    echo "可能原因:"
    echo "  1. 系统已重置"
    echo "  2. 项目被移动"
    echo ""
    echo "解决方案:"
    echo "  1. 从 Git 远程仓库克隆"
    echo "  2. 从本地备份恢复"
fi

echo ""
echo "=========================================="
