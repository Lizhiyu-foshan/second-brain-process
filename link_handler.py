#!/usr/bin/env python3
"""
Second Brain 链接处理助手
处理用户发送的链接，提供选项，支持15分钟超时默认
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from processor import process_link, get_queue_list

QUEUE_DIR = Path("/root/.openclaw/workspace/second-brain-processor/queue")

def extract_url(text: str) -> str | None:
    """从文本中提取 URL"""
    url_pattern = r'https?://[^\s\u3000\uff0c\uff0e\uff01\uff1f\uff08\uff09\[\]"\'\n\r]+'
    match = re.search(url_pattern, text)
    return match.group(0) if match else None

def generate_options_message(url: str, title: str = None) -> str:
    """生成选项提示消息"""
    display_title = title or "未获取标题"
    display_url = url[:60] + "..." if len(url) > 60 else url
    
    return f"""📎 收到链接

{display_title}
{display_url}

请选择处理方式：

【1】存入待读列表 ⭐ 默认
【2】直接聊聊这个主题
【3】搜索其他相关讨论

⏰ 15分钟内无回复，默认按【1】处理

回复：1 / 2 / 3"""

def process_link_with_options(user_input: str, url: str = None) -> dict:
    """
    处理链接并根据用户选择执行
    支持15分钟超时默认存入待读列表
    """
    if url is None:
        url = extract_url(user_input)
    
    if not url:
        return {"success": False, "error": "未找到有效链接"}
    
    # 尝试获取标题（简化版，实际可能需要抓取网页）
    title = None
    
    # 返回选项提示
    return {
        "success": True,
        "action": "prompt_options",
        "url": url,
        "title": title,
        "message": generate_options_message(url, title),
        "timeout_seconds": 900,  # 15分钟
        "default_option": "1"    # 默认存入待读列表
    }

def save_to_queue(url: str, title: str = None, content: str = None) -> dict:
    """保存链接到待读队列"""
    # 如果提供了内容，直接保存；否则让 process_link 处理
    result = process_link(url, content)
    
    if result["success"]:
        # 检查队列中是否还有其他未处理文章
        queue = get_queue_list()
        pending_count = len(queue)
        
        result["queue_count"] = pending_count
        result["prompt_process"] = pending_count > 0
        
        if pending_count > 0:
            result["follow_up_message"] = f"""✅ 已添加到待读列表

当前队列共有 {pending_count} 篇待处理文章。

是否需要立即处理？
回复【需要】或【Y】马上处理
⏰ 15分钟内无回复，将保留在队列中稍后处理"""
    
    return result

def handle_user_choice(choice: str, url: str = None) -> dict:
    """处理用户选择"""
    choice = choice.strip().lower()
    
    if choice in ['1', '存入', '待读', '列表', '']:
        # 默认选项：存入待读列表
        if url:
            return save_to_queue(url)
        return {"success": False, "error": "缺少URL"}
    
    elif choice in ['2', '聊聊', '讨论', '主题']:
        # 直接聊聊这个主题
        return {
            "success": True,
            "action": "discuss",
            "url": url,
            "message": "好的，我们来聊聊这个主题。请告诉我你想讨论什么方面？"
        }
    
    elif choice in ['3', '搜索', '相关', '讨论']:
        # 搜索其他相关讨论
        return {
            "success": True,
            "action": "search",
            "url": url,
            "message": "正在搜索相关讨论..."
        }
    
    elif choice in ['y', 'yes', '需要', '处理', '马上']:
        # 立即处理队列
        return {
            "success": True,
            "action": "process_now",
            "message": "开始处理队列中的文章..."
        }
    
    else:
        return {"success": False, "error": "无效选项"}

def format_processed_result(result: dict) -> str:
    """格式化处理后的结果展示"""
    if not result.get('success'):
        return f"❌ 处理失败：{result.get('error', '未知错误')}"
    
    title = result.get('title', '未知标题')
    mode = result.get('mode', 'summary')
    
    if mode == 'full':
        # 全文保留模式：只显示题目、长度和开头200字
        content = result.get('content', '')
        content_length = len(content)
        preview = content[:200] + "..." if len(content) > 200 else content
        
        return f"""✅ 处理完成

📄 {title}
📊 文章长度：{content_length} 字

📝 开头预览：
{preview}

---
已保存并同步到 GitHub"""
    
    else:
        # 摘要模式：显示完整处理结果
        key_takeaway = result.get('key_takeaway', '待提炼')
        core_points = result.get('core_points', [])
        
        points_text = '\n'.join([f"• {p}" for p in core_points[:5]]) if core_points else "• 待提炼要点"
        
        return f"""✅ 处理完成

📄 {title}

🔑 Key Takeaway：
{key_takeaway}

📋 核心要点：
{points_text}

---
已保存并同步到 GitHub"""

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Second Brain 链接处理')
    parser.add_argument('input', nargs='?', help='用户输入（链接或选项）')
    parser.add_argument('--url', help='指定URL')
    parser.add_argument('--choice', help='用户选择（1/2/3/y）')
    
    args = parser.parse_args()
    
    if args.choice:
        # 处理用户选择
        result = handle_user_choice(args.choice, args.url)
    elif args.input:
        # 处理新链接
        result = process_link_with_options(args.input, args.url)
    else:
        result = {"success": False, "error": "缺少输入"}
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
