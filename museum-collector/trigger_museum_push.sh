#!/bin/bash
#
# 美术馆展览推送 - 触发脚本
# 由定时任务调用，发送指令到主会话执行实际搜索
#

TARGET="ou_363105a68ee112f714ed44e12c802051"

# 获取当前日期
TODAY=$(date +%Y年%m月%d日)
WEEKDAY=$(date +%u)

# 支持通过参数指定模式（monday/friday），默认为根据星期判断
MODE="${1:-auto}"

if [ "$MODE" = "monday" ]; then
    TITLE="🎨 周一工作日展览推送"
    SUBTITLE="本周工作日可看的展览"
elif [ "$MODE" = "friday" ]; then
    TITLE="🎨 周五周末展览推送"
    SUBTITLE="周末可看的展览"
elif [ "$WEEKDAY" -ge 5 ]; then
    TITLE="🎨 周末展览推荐"
    SUBTITLE="周末可看的展览"
else
    TITLE="🎨 本周展览推荐"  
    SUBTITLE="工作日可看的展览"
fi

MESSAGE="【定时任务触发】${TITLE}

📅 ${TODAY} | ${SUBTITLE}

请使用 kimi_search 搜索以下美术馆当前有效的展览：
1. 和美术馆 展览 2026
2. 广东美术馆 展览 2026
3. 另一个美术馆 展览 2026

过滤规则：
- ✅ 只展示结束日期 >= ${TODAY} 的展览
- ❌ 已结束的展览不展示（如毕加索与达利展 2026.2.8已结束）
- ⏰ 临近结束（7天内）的展览置顶并标注\"还剩X天，抓紧去看！\"
- 📅 无法确认结束日期的标注\"展期中\"

示例：
- ✅ 2026.1.16-2026.3.29 → 展示（还有X天）
- ✅ 2025.12.9-2026.3.15 → 展示（还剩X天，临期提醒）
- ❌ 2025.10.18-2026.2.8 → 不展示（已结束）

然后整理成飞书消息发送。"

# 发送触发消息
openclaw message send \
    --target "$TARGET" \
    --message "$MESSAGE"
