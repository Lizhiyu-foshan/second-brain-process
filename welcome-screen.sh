#!/bin/bash
# Kimi Claw 开屏项目选择器
# 每次启动时显示最近3天内的项目

PROJECTS_DIR="/root/.openclaw/workspace/projects"
DAYS_TO_SHOW=3

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           🦊 Kimi Claw - 欢迎回来！                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 获取当前时间戳
NOW=$(date +%s)
DAYS_AGO=$((NOW - DAYS_TO_SHOW * 24 * 3600))

# 检查项目目录
if [ ! -d "$PROJECTS_DIR" ]; then
    echo "📂 项目目录为空，开始新的对话吧！"
    exit 0
fi

# 查找最近的项目
echo "📋 最近 $DAYS_TO_SHOW 天内的项目："
echo ""

cd "$PROJECTS_DIR"
PROJECT_COUNT=0

for project in */; do
    if [ -d "$project" ]; then
        PROJECT_NAME=${project%/}
        PROJECT_PATH="$PROJECTS_DIR/$PROJECT_NAME"
        
        # 获取最后修改时间
        LAST_MODIFIED=$(stat -c %Y "$PROJECT_PATH" 2>/dev/null || stat -f %m "$PROJECT_PATH" 2>/dev/null)
        
        # 检查是否在3天内
        if [ "$LAST_MODIFIED" -gt "$DAYS_AGO" ]; then
            PROJECT_COUNT=$((PROJECT_COUNT + 1))
            MODIFIED_DATE=$(date -d "@$LAST_MODIFIED" '+%m月%d日 %H:%M' 2>/dev/null || date -r "$LAST_MODIFIED" '+%m月%d日 %H:%M')
            
            # 读取项目描述（从 PROJECT_LOG.md）
            DESCRIPTION=""
            if [ -f "$PROJECT_PATH/PROJECT_LOG.md" ]; then
                DESCRIPTION=$(head -5 "$PROJECT_PATH/PROJECT_LOG.md" | grep -E "^#|^项目名称" | head -1 | sed 's/# //' | sed 's/项目名称: //')
            fi
            
            # 显示项目信息
            echo "  [$PROJECT_COUNT] 📁 $PROJECT_NAME"
            echo "      📝 ${DESCRIPTION:-暂无描述}"
            echo "      🕐 最后修改: $MODIFIED_DATE"
            echo "      📍 位置: $PROJECT_PATH"
            echo ""
            
            # 保存项目路径到临时文件（供后续使用）
            echo "$PROJECT_PATH" > "/tmp/kimi-project-$PROJECT_COUNT.txt"
        fi
    fi
done

if [ $PROJECT_COUNT -eq 0 ]; then
    echo "📂 最近 $DAYS_TO_SHOW 天内没有项目活动"
    echo ""
    echo "💡 提示："
    echo "   • 所有项目保存在: $PROJECTS_DIR"
    echo "   • 开始新的对话来创建项目"
else
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "🤔 请选择操作："
    echo ""
    echo "  [1-$PROJECT_COUNT]  选择项目继续开发"
    echo "  [n]                 开始新的对话"
    echo "  [l]                 列出所有项目（不限时间）"
    echo ""
    echo "════════════════════════════════════════════════════════════"
fi
