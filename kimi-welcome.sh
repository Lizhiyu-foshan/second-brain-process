#!/bin/bash
# Kimi Claw 智能启动器
# 集成到 OpenClaw 的启动流程

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           🦊 Kimi Claw 智能项目助手                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查最近项目
PROJECTS_DIR="/root/.openclaw/workspace/projects"
RECENT_PROJECT=""
RECENT_TIME=0

if [ -d "$PROJECTS_DIR" ]; then
    for project in "$PROJECTS_DIR"/*/; do
        if [ -d "$project" ]; then
            MODIFIED=$(stat -c %Y "$project" 2>/dev/null || stat -f %m "$project" 2>/dev/null)
            if [ "$MODIFIED" -gt "$RECENT_TIME" ]; then
                RECENT_TIME=$MODIFIED
                RECENT_PROJECT="$project"
            fi
        fi
    done
fi

# 显示最近项目
if [ -n "$RECENT_PROJECT" ]; then
    PROJECT_NAME=$(basename "$RECENT_PROJECT")
    MODIFIED_DATE=$(date -d "@$RECENT_TIME" '+%m月%d日 %H:%M' 2>/dev/null || date -r "$RECENT_TIME" '+%m月%d日 %H:%M')
    
    echo -e "${BLUE}📂 最近项目:${NC} $PROJECT_NAME"
    echo -e "${BLUE}🕐 最后修改:${NC} $MODIFIED_DATE"
    echo ""
    
    # 读取项目描述
    if [ -f "$RECENT_PROJECT/PROJECT_LOG.md" ]; then
        echo -e "${YELLOW}📖 项目简介:${NC}"
        head -10 "$RECENT_PROJECT/PROJECT_LOG.md" | grep -E "^#|^项目名称|^创建" | head -3
        echo ""
    fi
    
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "💡 快捷指令："
    echo ""
    echo "  ${GREEN}继续开发${NC}     → 加载最近项目并继续开发"
    echo "  ${GREEN}加载 $PROJECT_NAME${NC}  → 同上"
    echo "  ${GREEN}查看项目${NC}     → 显示项目详情和文件结构"
    echo "  ${GREEN}测试项目${NC}     → 运行项目测试"
    echo "  ${GREEN}推送 GitHub${NC}  → 将项目推送到远程仓库"
    echo "  ${GREEN}新项目${NC}       → 开始新的对话"
    echo "  ${GREEN}列出所有${NC}     → 显示所有历史项目"
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo ""
    
    # 保存到环境变量（供 Kimi Claw 读取）
    echo "$RECENT_PROJECT" > /tmp/kimi-last-project.txt
    echo "$PROJECT_NAME" > /tmp/kimi-last-project-name.txt
    
else
    echo "📂 暂无项目记录"
    echo ""
    echo "💡 开始新的对话来创建你的第一个项目！"
    echo ""
fi
