#!/bin/bash
# 自我进化流水线 - 架构师阶段
# 每天 4:00 和 20:00 执行

LOG_FILE="/tmp/evolution_pipeline_architect.log"
PLAN_DIR="/root/.openclaw/workspace/shared/pipeline"
DATE_STR=$(date +%Y%m%d)

echo "=== 架构师阶段启动 $(date) ===" >> "$LOG_FILE"

# 调用 OpenClaw API 启动架构师分析
# 由于无法直接使用 agentTurn，改为生成待处理标记
cat > "$PLAN_DIR/pending_architect_$DATE_STR.flag" << EOF
{
  "stage": "architect",
  "timestamp": "$(date -Iseconds)",
  "status": "pending",
  "message": "需要执行架构师阶段：分析.learnings/目录，生成plan_$DATE_STR.json"
}
EOF

echo "已创建待处理标记: pending_architect_$DATE_STR.flag" >> "$LOG_FILE"
echo "请手动执行架构师阶段，或等待人工触发" >> "$LOG_FILE"

# 可选：发送通知
curl -s -X POST "http://localhost:8080/api/notify" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"[Evolution Pipeline] 架构师阶段待执行，请检查 pending_architect_$DATE_STR.flag\"}" 2>/dev/null || true
