#!/bin/bash
# 自我进化流水线 - 开发者阶段
# 每天 4:40 和 20:40 执行

LOG_FILE="/tmp/evolution_pipeline_developer.log"
PLAN_DIR="/root/.openclaw/workspace/shared/pipeline"
DATE_STR=$(date +%Y%m%d)

echo "=== 开发者阶段启动 $(date) ===" >> "$LOG_FILE"

# 检查是否有架构师生成的计划
PLAN_FILE="$PLAN_DIR/plan_${DATE_STR}.json"
if [ ! -f "$PLAN_FILE" ]; then
    echo "计划文件不存在: $PLAN_FILE" >> "$LOG_FILE"
    echo "等待架构师阶段完成..." >> "$LOG_FILE"
    exit 0
fi

# 创建待处理标记
cat > "$PLAN_DIR/pending_developer_$DATE_STR.flag" << EOF
{
  "stage": "developer",
  "timestamp": "$(date -Iseconds)",
  "status": "pending",
  "plan_file": "$PLAN_FILE",
  "message": "需要执行开发者阶段：根据计划开发Skills"
}
EOF

echo "已创建待处理标记: pending_developer_$DATE_STR.flag" >> "$LOG_FILE"
echo "请手动执行开发者阶段，或等待人工触发" >> "$LOG_FILE"
