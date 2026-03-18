#!/bin/bash
#
# 凌晨5:00系统整理任务 - 真正执行封装脚本
# 杜绝模拟执行，所有操作必须真实发生
#

set -e  # 遇到错误立即退出

SCRIPT_DIR="/root/.openclaw/workspace/second-brain-processor"
LOG_FILE="/tmp/morning_process_$(date +%Y%m%d_%H%M%S).log"

echo "========================================" | tee -a "$LOG_FILE"
echo "凌晨5:00系统整理任务 - $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 步骤1: 执行整理脚本
echo "" | tee -a "$LOG_FILE"
echo "【步骤1】执行聊天记录整理..." | tee -a "$LOG_FILE"
cd "$SCRIPT_DIR"
if python3 kimiclaw_v2.py --morning-process 2>&1 | tee -a "$LOG_FILE"; then
    echo "✅ 整理脚本执行成功" | tee -a "$LOG_FILE"
else
    echo "❌ 整理脚本执行失败，退出码: $?" | tee -a "$LOG_FILE"
    # 记录错误
    echo "## [ERR-$(date +%Y%m%d)-$(date +%H%M)] morning_process_failed

**Logged**: $(date -Iseconds)
**Priority**: high
**Status**: pending
**Area**: daily_task

### 问题
凌晨5:00整理脚本执行失败

### 日志
$(tail -20 "$LOG_FILE")

### 解决方案
待排查

---" >> /root/.openclaw/workspace/.learnings/ERRORS.md
fi

# 步骤2: 执行系统进化复盘 (AI版本)
echo "" | tee -a "$LOG_FILE"
echo "【步骤2】执行AI驱动的系统进化复盘..." | tee -a "$LOG_FILE"
cd "$SCRIPT_DIR"
if python3 system_evolution_ai.py --daily-review 2>&1 | tee -a "$LOG_FILE"; then
    echo "✅ AI驱动的系统进化复盘完成" | tee -a "$LOG_FILE"
else
    echo "⚠️ AI复盘失败，尝试回退到标准版本..." | tee -a "$LOG_FILE"
    python3 system_evolution_v2.py --daily-review 2>&1 | tee -a "$LOG_FILE" || true
fi

# 步骤3: 后台启动GLM5异步改进生成
echo "" | tee -a "$LOG_FILE"
echo "【步骤3】后台启动GLM5异步改进生成..." | tee -a "$LOG_FILE"
cd "$SCRIPT_DIR"
# 在后台运行，不阻塞主流程
nohup python3 ai_async_generator.py --process > /tmp/ai_generator_$(date +%Y%m%d).log 2>&1 &
echo "✅ GLM5异步生成已在后台启动 (PID: $!)" | tee -a "$LOG_FILE"
echo "   日志: /tmp/ai_generator_$(date +%Y%m%d).log" | tee -a "$LOG_FILE"
echo "   结果将保存到: .learnings/AI_RESULTS.json" | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "任务完成 - $(date)" | tee -a "$LOG_FILE"
echo "日志保存: $LOG_FILE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 保留最近7天的日志
find /tmp -name "morning_process_*.log" -mtime +7 -delete 2>/dev/null || true

exit 0
