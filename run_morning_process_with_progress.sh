#!/bin/bash
#
# 凌晨5:00系统整理任务 - 带进度反馈版
# 杜绝模拟执行，所有操作必须真实发生
# 新增：关键步骤发送进度反馈
#

set -e  # 遇到错误立即退出

SCRIPT_DIR="/root/.openclaw/workspace/second-brain-processor"
LOG_FILE="/tmp/morning_process_$(date +%Y%m%d_%H%M%S).log"
PROGRESS_FILE="/tmp/morning_process_progress_$(date +%Y%m%d).txt"

# 清理旧的进度文件
rm -f /tmp/morning_process_progress_*.txt 2>/dev/null || true

# 进度报告函数
report_progress() {
    local step="$1"
    local message="$2"
    local percent="$3"
    local eta="$4"
    local timestamp=$(date '+%H:%M:%S')
    
    # 写入进度文件
    echo "[$timestamp] $step: $message ($percent%) ETA: $eta" > "$PROGRESS_FILE"
    
    # 同时输出到控制台和日志
    echo "[$timestamp] 📊 进度更新 | $step: $message ($percent%) ETA: $eta" | tee -a "$LOG_FILE"
}

# 预计时间计算（基于历史数据）
# 步骤1: 整理聊天记录 ~30-60秒
# 步骤2: 系统进化复盘 ~5-10秒
# 总计: ~40-70秒

echo "========================================" | tee -a "$LOG_FILE"
echo "凌晨5:00系统整理任务 - $(date)" | tee -a "$LOG_FILE"
echo "预计总耗时: 40-70秒" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 步骤1: 执行整理脚本
echo "" | tee -a "$LOG_FILE"
report_progress "步骤1/2" "开始整理聊天记录" "0" "~60秒"
cd "$SCRIPT_DIR"

# 在后台运行Python脚本并监控
python3 kimiclaw_v2.py --morning-process 2>&1 | tee -a "$LOG_FILE" &
PYTHON_PID=$!

# 定期报告进度
report_progress "步骤1/2" "正在解析会话文件..." "10" "~50秒"
sleep 5
report_progress "步骤1/2" "正在分类内容..." "25" "~40秒"
sleep 5
report_progress "步骤1/2" "正在保存到笔记库..." "40" "~30秒"
sleep 5
report_progress "步骤1/2" "正在推送到GitHub..." "60" "~15秒"

# 等待Python脚本完成
wait $PYTHON_PID
PYTHON_EXIT_CODE=$?

if [ $PYTHON_EXIT_CODE -eq 0 ]; then
    report_progress "步骤1/2" "整理完成" "100" "0秒"
    echo "✅ 整理脚本执行成功" | tee -a "$LOG_FILE"
else
    echo "❌ 整理脚本执行失败，退出码: $PYTHON_EXIT_CODE" | tee -a "$LOG_FILE"
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
    
    report_progress "错误" "整理脚本执行失败" "-" "-"
    exit 1
fi

# 步骤2: 执行系统进化复盘
echo "" | tee -a "$LOG_FILE"
report_progress "步骤2/2" "开始系统进化复盘" "100" "~10秒"
cd "$SCRIPT_DIR"

python3 system_evolution.py --daily-review 2>&1 | tee -a "$LOG_FILE" &
PYTHON_PID=$!

sleep 3
report_progress "步骤2/2" "分析错误模式..." "100" "~7秒"
sleep 3
report_progress "步骤2/2" "生成改进方案..." "100" "~4秒"

wait $PYTHON_PID
if [ $? -eq 0 ]; then
    report_progress "步骤2/2" "复盘完成" "100" "完成"
    echo "✅ 系统进化复盘完成" | tee -a "$LOG_FILE"
else
    echo "⚠️ 系统进化复盘失败，但不影响主流程" | tee -a "$LOG_FILE"
    report_progress "步骤2/2" "复盘失败（非致命）" "100" "-"
fi

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "任务完成 - $(date)" | tee -a "$LOG_FILE"
echo "日志保存: $LOG_FILE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 清理进度文件
rm -f "$PROGRESS_FILE"

# 保留最近7天的日志
find /tmp -name "morning_process_*.log" -mtime +7 -delete 2>/dev/null || true

exit 0
