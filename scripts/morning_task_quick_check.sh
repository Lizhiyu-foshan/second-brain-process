#!/bin/bash
# 凌晨5:00任务 - 快速诊断命令集
# 用法: source morning_task_quick_check.sh

echo "=== 凌晨5:00任务快速诊断 ==="
echo ""

echo "1. Cron任务状态:"
openclaw cron list | grep -E "凌晨|5:00" || echo "  未找到相关任务"
echo ""

echo "2. 最后执行时间:"
if [ -f /tmp/morning_process_execution.log ]; then
    stat /tmp/morning_process_execution.log | grep Modify
else
    echo "  无执行日志"
fi
echo ""

echo "3. 最新输出文件:"
ls -lt /root/.openclaw/workspace/obsidian-vault/02-Conversations/*.md 2>/dev/null | head -3 || echo "  无输出文件"
echo ""

echo "4. Git状态:"
git -C /root/.openclaw/workspace log -1 --oneline 2>/dev/null || echo "  Git状态异常"
echo ""

echo "5. 磁盘空间:"
df -h / | tail -1
echo ""

echo "6. 内存使用:"
free -h | grep Mem
echo ""

echo "=== 常用操作 ==="
echo "查看日志:     tail -100 /tmp/morning_process_execution.log"
echo "手动执行:     bash /root/.openclaw/workspace/second-brain-processor/run_morning_wrapper.sh"
echo "执行前检查:   python3 /root/.openclaw/workspace/scripts/morning_task_pre_check.py"
echo "执行后验证:   python3 /root/.openclaw/workspace/scripts/morning_task_post_verify.py"
echo "完整诊断:     python3 /root/.openclaw/workspace/scripts/morning_task_diagnose.py"
echo ""
