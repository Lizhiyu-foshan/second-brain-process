#!/usr/bin/env python3
"""
queue_response_handler.py - v2.1
处理四个入口的响应
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable

# 导入处理模块
from run_four_step_process import run_four_step_process
from article_handler import handle_article_link, is_article_link

# 待处理队列存储
QUEUE_FILE = Path("/root/.openclaw/workspace/.data/response_queue.json")


def load_queue() -> Dict:
    """加载队列"""
    if QUEUE_FILE.exists():
        with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_queue(queue: Dict):
    """保存队列"""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def add_pending(task_type: str, **kwargs) -> str:
    """
    添加待处理任务
    
    Args:
        task_type: 任务类型
        **kwargs: 任务参数
        
    Returns:
        任务ID
    """
    queue = load_queue()
    task_id = f"{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    queue[task_id] = {
        "type": task_type,
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        **kwargs
    }
    
    save_queue(queue)
    return task_id


def get_pending(task_id: str = None) -> Optional[Dict]:
    """获取待处理任务"""
    queue = load_queue()
    
    if task_id:
        return queue.get(task_id)
    
    # 返回最新的pending任务
    for tid, task in sorted(queue.items(), key=lambda x: x[1].get("created_at", ""), reverse=True):
        if task.get("status") == "pending":
            task["id"] = tid
            return task
    
    return None


def complete_pending(task_id: str):
    """完成任务"""
    queue = load_queue()
    if task_id in queue:
        queue[task_id]["status"] = "completed"
        queue[task_id]["completed_at"] = datetime.now().isoformat()
        save_queue(queue)


# ===== 处理器函数 =====

def handle_daily_organize(user_input: str, pending: Dict) -> str:
    """
    入口A: 处理每日整理响应
    """
    if user_input == "整理":
        raw_file = pending.get("raw_file")
        if raw_file:
            result = run_four_step_process(
                content_file=Path(raw_file),
                source_type="每日对话整理"
            )
            complete_pending(pending.get("id", ""))
            return f"✅ 已开始AI深度整理\n\n{result}"
        return "❌ 找不到原始对话文件"
    
    elif user_input == "跳过":
        complete_pending(pending.get("id", ""))
        return "已跳过，对话保留在00-Inbox等待下次处理"
    
    else:
        return "请回复'整理'或'跳过'"


def handle_article_discussion(user_input: str, pending: Dict) -> str:
    """
    入口B: 处理文章讨论响应
    """
    if user_input == "讨论":
        # 开始讨论
        article_file = pending.get("article_file")
        return f"📄 开始讨论文章: {article_file}\n\n请发送您的想法，讨论结束后回复'整理'"
    
    elif user_input.startswith("稍后"):
        # v2.2: 实际设置定时任务
        match = re.search(r'(\d+)', user_input)
        hours = int(match.group(1)) if match else 2
        
        article_file = pending.get("article_file", "")
        url = pending.get("url", "")
        
        # 导入scheduled_discussion_handler的schedule_discussion函数
        from scheduled_discussion_handler import schedule_discussion
        
        result = schedule_discussion(article_file, hours)
        complete_pending(pending.get("id", ""))
        
        return result
    
    elif user_input == "AI自动整理":
        # 直接调用四步法
        article_file = pending.get("article_file")
        if article_file:
            result = run_four_step_process(
                content_file=Path(article_file),
                source_type="文章自动处理",
                source_url=pending.get("url")
            )
            complete_pending(pending.get("id", ""))
            return result
        return "❌ 找不到文章文件"
    
    else:
        return "请回复'讨论'、'稍后 X小时'或'AI自动整理'"


def handle_user_input(user_input: str) -> str:
    """
    主处理函数 - 处理用户输入
    
    Args:
        user_input: 用户输入内容
        
    Returns:
        响应消息
    """
    user_input = user_input.strip()
    
    # 检查是否有待处理任务
    pending = get_pending()
    
    if pending:
        task_type = pending.get("type")
        
        # 入口A: 每日对话整理
        if task_type == "daily_conversation_organize":
            return handle_daily_organize(user_input, pending)
        
        # 入口B: 文章讨论
        elif task_type == "article_discussion":
            return handle_article_discussion(user_input, pending)
        
        # 入口D: 自动处理确认
        elif task_type == "article_auto_process_immediate":
            # 这里调用scheduled_discussion_handler
            from scheduled_discussion_handler import handle_auto_process_immediate
            return handle_auto_process_immediate(user_input, pending)
    
    # 入口C: 主动要求整理
    if user_input == "整理":
        # 查找最近的Inbox文件
        inbox_dir = Path("/root/.openclaw/workspace/obsidian-vault/00-Inbox")
        if inbox_dir.exists():
            files = sorted(inbox_dir.glob("*_raw.md"), reverse=True)
            if files:
                result = run_four_step_process(
                    content_file=files[0],
                    source_type="主动整理"
                )
                return result
        return "❌ 没有找到可整理的对话文件"
    
    # 入口B: 文章链接
    if is_article_link(user_input):
        result = handle_article_link(user_input)
        if result["success"]:
            # 添加到队列
            add_pending(
                type="article_discussion",
                article_file=result["file_path"],
                url=user_input
            )
        return result["message"]
    
    # 默认响应
    return "我无法理解您的指令。可用的指令：\n• 发送文章链接 → 保存文章\n• 回复'整理' → 整理对话\n• 查看待处理任务"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(handle_user_input(sys.argv[1]))
    else:
        print("用法: python3 queue_response_handler.py '用户输入'")
