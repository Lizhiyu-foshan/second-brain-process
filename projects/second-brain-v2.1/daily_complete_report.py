#!/usr/bin/env python3
"""
daily_complete_report.py - v2.1
8:30定时任务 - 复盘报告+整理提示
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
INBOX_DIR = VAULT_DIR / "00-Inbox"


def generate_daily_report():
    """生成每日复盘报告"""
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")
    
    # 统计信息
    inbox_files = list(INBOX_DIR.glob("*_raw.md")) if INBOX_DIR.exists() else []
    
    report = f"""📊 每日复盘报告 ({date_str})

【收集统计】
• Inbox原始记录: {len(inbox_files)} 天

【整理提示】
📋 今日对话已收集到 00-Inbox/{date_str}_raw.md

如需AI深度整理，请回复"整理"
整理内容包括：
• 识别主题讨论精华（哲学/社会学/系统论/技术冲击等）
• 生成结构化摘要（一句话摘要+核心要点+关联思考）
• 分类推送到对应目录（01-Discussions/ 02-Conversations/）

⏰ 15分钟内回复有效，超时将保留在Inbox等待下次处理
"""
    return report


def add_pending_organize():
    """设置待处理队列"""
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")
    raw_file = f"00-Inbox/{date_str}_raw.md"
    
    # 这里会调用queue_response_handler.add_pending
    # 简化版本直接返回提示
    return {
        "type": "daily_conversation_organize",
        "raw_file": raw_file,
        "timeout_minutes": 15
    }


if __name__ == "__main__":
    print(generate_daily_report())
    pending = add_pending_organize()
    print(f"\n[队列设置] {pending}")
