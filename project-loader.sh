#!/bin/bash
# Kimi Claw 项目智能加载器
# 根据用户选择自动加载项目上下文

WELCOME_SCRIPT="/root/.openclaw/workspace/welcome-screen.sh"

# 显示欢迎界面
bash "$WELCOME_SCRIPT"

# 读取用户选择
echo ""
read -p "请输入选项 [1-9/n/l]: " choice
echo ""

# 处理选择
case "$choice" in
    [1-9])
        PROJECT_FILE="/tmp/kimi-project-$choice.txt"
        if [ -f "$PROJECT_FILE" ]; then
            PROJECT_PATH=$(cat "$PROJECT_FILE")
            PROJECT_NAME=$(basename "$PROJECT_PATH")
            
            echo "✅ 已选择项目: $PROJECT_NAME"
            echo ""
            
            # 显示项目日志
            if [ -f "$PROJECT_PATH/PROJECT_LOG.md" ]; then
                echo "📖 项目历史："
                echo "────────────────────────────────────────────────────────────"
                head -30 "$PROJECT_PATH/PROJECT_LOG.md"
                echo "────────────────────────────────────────────────────────────"
                echo ""
            fi
            
            # 显示 Git 状态
            if [ -d "$PROJECT_PATH/.git" ]; then
                cd "$PROJECT_PATH"
                echo "📊 Git 状态："
                git log --oneline -3 2>/dev/null | sed 's/^/   /'
                echo ""
            fi
            
            # 询问操作
            echo "🤔 请选择操作："
            echo ""
            echo "  [1] 继续开发（加载项目环境）"
            echo "  [2] 运行测试"
            echo "  [3] 查看代码结构"
            echo "  [4] 优化代码"
            echo "  [5] 推送到 GitHub"
            echo "  [n] 不操作，返回"
            echo ""
            read -p "请输入选项 [1-5/n]: " action
            echo ""
            
            case "$action" in
                1)
                    echo "🚀 加载项目环境..."
                    echo ""
                    echo "请告诉 Kimi Claw："
                    echo "────────────────────────────────────────────────────────────"
                    echo ""
                    echo "继续开发项目: $PROJECT_PATH"
                    echo ""
                    echo "请："
                    echo "1. 读取 PROJECT_LOG.md 了解上下文"
                    echo "2. 检查当前代码状态"
                    echo "3. 列出待完成的任务"
                    echo "4. 等待我指示下一步操作"
                    echo ""
                    echo "────────────────────────────────────────────────────────────"
                    ;;
                2)
                    echo "🧪 准备运行测试..."
                    echo ""
                    echo "请告诉 Kimi Claw："
                    echo "────────────────────────────────────────────────────────────"
                    echo ""
                    echo "在项目 $PROJECT_PATH 中运行测试"
                    echo ""
                    echo "请："
                    echo "1. 检查是否有测试文件"
                    echo "2. 运行所有测试"
                    echo "3. 报告测试结果"
                    echo ""
                    echo "────────────────────────────────────────────────────────────"
                    ;;
                3)
                    echo "📂 查看代码结构..."
                    echo ""
                    echo "请告诉 Kimi Claw："
                    echo "────────────────────────────────────────────────────────────"
                    echo ""
                    echo "显示项目 $PROJECT_NAME 的代码结构"
                    echo ""
                    echo "请："
                    echo "1. 使用 tree 或 find 显示项目结构"
                    echo "2. 列出主要文件和目录"
                    echo "3. 显示关键代码文件的内容摘要"
                    echo ""
                    echo "────────────────────────────────────────────────────────────"
                    ;;
                4)
                    echo "🔧 优化代码..."
                    echo ""
                    echo "请告诉 Kimi Claw："
                    echo "────────────────────────────────────────────────────────────"
                    echo ""
                    echo "优化项目: $PROJECT_PATH"
                    echo ""
                    echo "请："
                    echo "1. 读取 PROJECT_LOG.md 的待优化项"
                    echo "2. 检查代码质量"
                    echo "3. 列出可优化的地方"
                    echo "4. 等待我确认后再执行优化"
                    echo ""
                    echo "────────────────────────────────────────────────────────────"
                    ;;
                5)
                    echo "📤 推送到 GitHub..."
                    echo ""
                    echo "请告诉 Kimi Claw："
                    echo "────────────────────────────────────────────────────────────"
                    echo ""
                    echo "将项目 $PROJECT_NAME 推送到 GitHub"
                    echo ""
                    echo "请："
                    echo "1. 检查 Git 配置"
                    echo "2. 添加远程仓库（如果需要）"
                    echo "3. 推送代码"
                    echo "4. 提供仓库链接"
                    echo ""
                    echo "────────────────────────────────────────────────────────────"
                    ;;
                *)
                    echo "返回主菜单..."
                    bash "$0"
                    ;;
            esac
        else
            echo "❌ 无效的项目编号"
        fi
        ;;
    n|N)
        echo "🆕 开始新的对话"
        echo ""
        echo "💡 提示：你可以随时通过以下方式访问项目："
        echo "   • 项目目录: /root/.openclaw/workspace/projects/"
        echo "   • 恢复脚本: /root/.openclaw/workspace/restore-project.sh"
        ;;
    l|L)
        echo "📂 所有项目列表："
        echo ""
        ls -la /root/.openclaw/workspace/projects/
        echo ""
        read -p "按回车键返回..."
        bash "$0"
        ;;
    *)
        echo "❌ 无效选项"
        ;;
esac
