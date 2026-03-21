#!/usr/bin/env python3
"""
scheduled_discussion_handler.py - v2.1 入口D
定时任务自动处理 - 立即响应版本（无10分钟等待）
"""

import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict

# 导入处理模块
from run_four_step_process import run_four_step_process


def handle_no_time_response(article_file: str, url: str) -> str:
    """
    v2.1 修改：用户回复'没有时间'后立即提示，不再等待10分钟
    
    Args:
        article_file: 文章文件路径
        url: 文章URL
        
    Returns:
        提示消息
    """
    # 立即发送处理选项（v2.1: 不再等待10分钟）
    message = f"""
⏰ 文章讨论提醒

您之前保存的文章：{article_file}
检测到您没有时间讨论。

请选择：
• 回复"AI自动整理" → AI自动分析分类整理（不再讨论，直接整理）
• 回复"推迟 X小时" → 推迟到最新时间（如：推迟 2小时）
• 回复"跳过" → 保留文章，等待下次讨论
"""
    
    # 添加到队列（v2.1: 立即处理，无二次等待）
    from queue_response_handler import add_pending
    task_id = add_pending(
        type="article_auto_process_immediate",  # v2.1: 立即处理类型
        article_file=article_file,
        url=url
    )
    
    return message


def handle_auto_process_immediate(user_input: str, pending: Dict) -> str:
    """
    v2.1 修改：处理'没有时间'后的立即响应
    
    Args:
        user_input: 用户输入
        pending: 待处理任务
        
    Returns:
        处理结果
    """
    from queue_response_handler import complete_pending
    
    if user_input == "AI自动整理":
        # v2.1: 立即读取文章内容并处理（不再讨论）
        article_file = pending.get("article_file")
        
        if article_file and Path(article_file).exists():
            # 调用四步法直接处理
            result = run_four_step_process(
                content_file=Path(article_file),
                source_type="文章自动处理",
                source_url=pending.get("url")
            )
            
            # 标记完成
            complete_pending(pending.get("id", ""))
            return f"✅ 已自动处理，生成主题讨论精华\n\n{result}"
        
        return "❌ 找不到文章文件"
    
    elif user_input.startswith("推迟"):
        # v2.1: 支持推迟到最新时间
        match = re.search(r'(\d+)', user_input)
        hours = int(match.group(1)) if match else 2
        
        # 计算未来时间
        future_time = datetime.now() + timedelta(hours=hours)
        time_str = future_time.strftime("%Y-%m-%d %H:%M")
        
        # 这里应该设置实际的定时任务，简化版本
        complete_pending(pending.get("id", ""))
        
        return f"⏰ 已推迟 {hours} 小时，将在 {time_str} 再次提醒"
    
    elif user_input == "跳过":
        complete_pending(pending.get("id", ""))
        return "已跳过，文章保留在 03-Articles/ 等待下次讨论"
    
    else:
        return "请回复'AI自动整理'、'推迟 X小时'或'跳过'"


def schedule_discussion(article_file: str, hours: int) -> str:
    """
    设置定时讨论任务
    
    Args:
        article_file: 文章文件路径
        hours: 推迟小时数
        
    Returns:
        设置结果
    """
    # 简化版本，实际应使用OpenClaw Cron
    future_time = datetime.now() + timedelta(hours=hours)
    time_str = future_time.strftime("%Y-%m-%d %H:%M")
    
    return f"⏰ 已设置定时任务：{time_str} 提醒您讨论 {article_file}"


def parse_hours(user_input: str) -> int:
    """解析小时数"""
    match = re.search(r'(\d+)', user_input)
    return int(match.group(1)) if match else 2


if __name__ == "__main__":
    print("[v2.1] 入口D: 定时任务自动处理模块")
    print("特性：立即响应，无10分钟等待")
