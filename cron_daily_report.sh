#!/bin/bash
# 每日复盘报告推送脚本
# 由 Cron 直接调用执行

set -e

cd /root/.openclaw/workspace/second-brain-processor

# 生成报告并获取内容
REPORT_CONTENT=$(python3 -c "
import sys
sys.path.insert(0, '.')
from feishu_send import generate_daily_report
result = generate_daily_report()
print(result['content'])
" 2>/dev/null || echo "📊 每日复盘报告（$(date +%Y-%m-%d)）

昨日暂无新数据处理。

💡 今日建议
• 发送链接给我，自动添加到待处理队列
• 回复'队列'查看待处理列表")

# 发送报告
python3 send_feishu.py "$REPORT_CONTENT" daily_report

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 每日复盘报告已发送"
