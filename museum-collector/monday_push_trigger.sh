#!/bin/bash
#
# 周一美术馆展览推送 - 触发脚本
# 直接发送执行指令到主会话
#

TARGET="ou_363105a68ee112f714ed44e12c802051"

# 发送明确的执行指令
openclaw sessions send \
    --sessionKey "agent:main:main" \
    --message "【定时任务】周一展览推送 - 立即执行

你必须：
1. 调用 kimi_search 搜索'和美术馆 展览 2026'
2. 调用 kimi_search 搜索'广东美术馆 展览 2026'  
3. 调用 kimi_search 搜索'另一个美术馆 展览 2026'
4. 整理结果
5. 调用 message 工具发送给 $TARGET

注意：
- 结束日期 < 2026-03-16 的不展示
- 7天内结束的置顶标注'还剩X天'
- 必须实际调用 message 发送，不只是生成文字
- 完成后回复 NO_REPLY" \
    --timeoutSeconds 120

echo "周一展览推送指令已发送到主会话"
