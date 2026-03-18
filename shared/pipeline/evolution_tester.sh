#!/bin/bash
# 自我进化流水线 - 测试员阶段
# 每天 5:30 和 21:30 执行

LOG_FILE="/tmp/evolution_pipeline_tester.log"
PLAN_DIR="/root/.openclaw/workspace/shared/pipeline"
DATE_STR=$(date +%Y%m%d)

echo "=== 测试员阶段启动 $(date) ===" >> "$LOG_FILE"

# 检查是否有开发者生成的报告
DEV_REPORT="$PLAN_DIR/dev_report_${DATE_STR}.json"
if [ ! -f "$DEV_REPORT" ]; then
    echo "开发报告不存在: $DEV_REPORT" >> "$LOG_FILE"
    echo "等待开发者阶段完成..." >> "$LOG_FILE"
    exit 0
fi

# 创建待处理标记
cat > "$PLAN_DIR/pending_tester_$DATE_STR.flag" << EOF
{
  "stage": "tester",
  "timestamp": "$(date -Iseconds)",
  "status": "pending",
  "dev_report": "$DEV_REPORT",
  "message": "需要执行测试员阶段：验证开发的Skills"
}
EOF

echo "已创建待处理标记: pending_tester_$DATE_STR.flag" >> "$LOG_FILE"
echo "请手动执行测试员阶段，或等待人工触发" >> "$LOG_FILE"
