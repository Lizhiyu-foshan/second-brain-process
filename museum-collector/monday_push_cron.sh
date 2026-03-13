#!/bin/bash
#
# 周一美术馆展览推送 - 系统级cron版本（真正搜索）
# 调用 Python 脚本使用 Kimi K2.5 搜索真实展览信息

python3 /root/.openclaw/workspace/museum-collector/museum_push_with_search.py --mode monday >> /tmp/museum_push.log 2>&1
