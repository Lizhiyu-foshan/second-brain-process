#!/bin/bash
#
# 艺术史漫游课程推送 - 系统级cron版本
# 每周五20:00推送艺术史课程内容

WORKSPACE="/root/.openclaw/workspace"
TARGET="ou_363105a68ee112f714ed44e12c802051"
TODAY=$(date +"%Y-%m-%d")

# 读取当前进度
PROGRESS_FILE="${WORKSPACE}/art_curriculum/progress.json"
if [ -f "$PROGRESS_FILE" ]; then
    CURRENT_WEEK=$(python3 -c "import json; print(json.load(open('$PROGRESS_FILE'))['current_week'])")
else
    CURRENT_WEEK=1
fi

# 构建艺术史课程内容（简化版，实际应从课程库读取）
MESSAGE="🎨 **艺术史漫游 - 第${CURRENT_WEEK}期**

📅 ${TODAY} | 每周艺术主题

📖 **本周主题：中世纪艺术（12世纪）**

🏛️ **西方部分**
- 哥特式建筑的兴起
- 彩色玻璃窗的宗教叙事
- 罗马式与哥特式的对比

🏛️ **东方部分**
- 南宋院体画的成熟
- 禅宗绘画的留白美学
- 丝绸之路的艺术交融

🔗 **连接点**
- 宗教在建筑与绘画中的表达差异
- 12世纪东西方对"神圣空间"的不同理解

📍 **大湾区观展指引**
- 和美术馆：可关注当代艺术家对中世纪的重新诠释

---
⏰ **推送时间**：${TODAY} 20:00
📚 **下一期**：文艺复兴早期（13-14世纪）"

# 使用 send_feishu.py 发送（带防重发）
cd ${WORKSPACE}/second-brain-processor
python3 send_feishu.py "${MESSAGE}" "art_history"

# 更新进度到下一期
python3 -c "
import json
with open('$PROGRESS_FILE', 'r') as f:
    data = json.load(f)
data['current_week'] = ${CURRENT_WEEK} + 1
data['last_pushed'] = '${TODAY}'
with open('$PROGRESS_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"

echo "[$(date)] 艺术史漫游推送执行完成 - 第${CURRENT_WEEK}期" >> /tmp/art_history.log
