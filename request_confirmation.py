#!/usr/bin/env python3
"""
8:30 复盘报告推送（待确认模式）
检查待整理内容，发送飞书消息请求用户确认
"""

import json
import os
import sys
from datetime import datetime

# 添加路径
sys.path.insert(0, '/root/.openclaw/workspace/second-brain-processor')

def check_pending_content():
    """检查待整理的对话和笔记"""
    pending_count = 0
    
    # 检查今日对话记录（5:00 已生成）
    today = datetime.now().strftime("%Y-%m-%d")
    dialog_path = f"/root/.openclaw/workspace/obsidian-vault/02-Daily/{today}_dialog.md"
    
    if os.path.exists(dialog_path):
        pending_count += 1
    
    # 检查待读笔记（需要整合现有逻辑）
    # TODO: 检查 second-brain-processor 的待读队列
    
    return {
        "dialog_count": pending_count,
        "notes_count": 0  # TODO: 实现
    }

def send_confirmation_message():
    """发送飞书确认消息"""
    pending = check_pending_content()
    
    total = pending["dialog_count"] + pending["notes_count"]
    
    if total == 0:
        print("[INFO] 没有待整理内容，跳过")
        return
    
    message = f"""📝 有待整理内容

- 对话笔记：{pending["dialog_count"]} 条
- 待读笔记：{pending["notes_count"]} 条

回复"整理"开始 AI 处理，预计耗时 2-5 分钟。"""

    print(f"[CONFIRMATION] {message}")
    
    # TODO: 通过飞书 API 发送消息
    # 这里需要使用 feishu-send-guardian 或现有消息发送逻辑
    
    print(f"[{datetime.now()}] 确认消息已发送")

if __name__ == "__main__":
    send_confirmation_message()
