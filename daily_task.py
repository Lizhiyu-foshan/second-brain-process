#!/usr/bin/env python3
"""
Second Brain 定时任务 - 每晚 11:30
检查两类任务：
1. 待读笔记列表（为空时静默跳过）
2. 聊天记录主题归纳（自动分类，只需确认是否保留）

免打扰逻辑：如果前一天无任何交互，第二天复盘报告也跳过
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from git_sync import commit_and_sync
from chat_extractor import get_today_chats, save_chat_to_memory

QUEUE_DIR = Path("/root/.openclaw/workspace/second-brain-processor/queue")
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
MEMORY_DIR = Path("/root/.openclaw/workspace/memory")

def has_user_interaction_last_24h() -> bool:
    """检查过去24小时是否有用户交互（待读笔记或聊天记录）"""
    # 检查待读队列
    if QUEUE_DIR.exists() and list(QUEUE_DIR.glob("*.md")):
        return True
    
    # 检查聊天记录
    if MEMORY_DIR.exists():
        cutoff_time = datetime.now() - timedelta(hours=24)
        for f in MEMORY_DIR.glob("*.md"):
            try:
                file_date = datetime.fromtimestamp(f.stat().st_mtime)
                if file_date >= cutoff_time:
                    with open(f, 'r', encoding='utf-8') as file:
                        if file.read().strip():
                            return True
            except:
                continue
    
    return False

def get_queue_list():
    """获取待处理队列列表"""
    if not QUEUE_DIR.exists():
        return []
    files = sorted(QUEUE_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
    return [
        {
            "filename": f.name,
            "path": str(f),
            "title": extract_title(f),
            "author": extract_author(f),
            "source": extract_source(f),
            "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        }
        for f in files
    ]

def get_recent_chats(hours: int = 24) -> list:
    """获取最近N小时的聊天记录"""
    if not MEMORY_DIR.exists():
        return []
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    recent_chats = []
    
    # 检查过去24小时内修改的文件（不按文件名，按修改时间）
    cutoff_time = datetime.now() - timedelta(hours=24)
    
    for f in MEMORY_DIR.glob("*.md"):
        try:
            file_mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if file_mtime >= cutoff_time:
                with open(f, 'r', encoding='utf-8') as file:
                    content = file.read()
                    if content.strip():
                        recent_chats.append({
                            "file": f.name,
                            "path": str(f),
                            "date": file_mtime.strftime("%Y-%m-%d"),
                            "content": content
                        })
        except:
            continue
    
    return recent_chats

def auto_summarize_today_chats() -> dict:
    """
    自动整理今天的聊天记录
    从 OpenClaw 会话历史文件中提取今天的聊天记录
    """
    # 使用 chat_extractor 从会话历史中提取
    chat_data = get_today_chats()
    
    if not chat_data['has_chats']:
        return {"has_chats": False}
    
    # 保存到 memory/ 目录
    saved_path = save_chat_to_memory(chat_data)
    
    return {
        "has_chats": True,
        "title": chat_data['title'],
        "summary": chat_data['content'][:300] + "..." if len(chat_data['content']) > 300 else chat_data['content'],
        "content": chat_data['content'],
        "file": str(saved_path) if saved_path else None,
        "message_count": chat_data['message_count'],
        "session_count": chat_data['session_count']
    }

def classify_chats_by_topic(chats: list) -> list:
    """
    对聊天记录按主题进行分类归纳
    返回主题列表，每个主题包含标题、摘要、关联文件
    """
    if not chats:
        return []
    
    topics = []
    
    for chat in chats:
        content = chat['content']
        lines = content.split('\n')
        
        # 尝试提取第一行非空内容作为主题
        title = "未命名对话"
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and len(line) < 50:
                title = line
                break
        
        # 生成摘要（前200字）
        summary = content[:200] + "..." if len(content) > 200 else content
        
        topics.append({
            "title": title,
            "summary": summary,
            "source_file": chat['file'],
            "path": chat['path'],
            "date": chat['date'],
            "content": content
        })
    
    return topics

def generate_chat_topics_message(topics: list) -> str:
    """生成聊天记录主题归纳提示"""
    if not topics:
        return ""
    
    message_lines = [
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄",
        f"💬 聊天记录主题归纳（过去24小时）",
        "",
        f"已自动归纳 {len(topics)} 个主题：",
        ""
    ]
    
    for i, topic in enumerate(topics, 1):
        message_lines.extend([
            f"{i}. {topic['title']} ({topic['date']})",
            f"   摘要：{topic['summary'][:100]}...",
            ""
        ])
    
    message_lines.extend([
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄",
        "📋 概况说明",
        "以上是根据今天聊天记录自动归纳的主题。",
        "如需查看详情，可在 Obsidian 中打开对应日期的笔记。",
        "",
        "是否保留这些聊天记录主题？",
        "",
        "【Y】保留并处理（进入待读笔记流程）⭐ 默认",
        "【N】删除（不保留当天聊天记录）",
        "",
        "⏰ 5分钟内无回复，默认按【Y】保留处理",
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
    ])
    
    return "\n".join(message_lines)

def move_chat_to_queue(chat_file: str) -> bool:
    """
    将聊天记录从 memory/ 移动到 queue/，进入待读笔记流程
    """
    try:
        source = Path(chat_file)
        if not source.exists():
            return False
        
        # 读取内容
        with open(source, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 生成 queue 文件
        today = datetime.now().strftime("%Y-%m-%d")
        target_file = QUEUE_DIR / f"{today}_chat_summary.md"
        
        # 添加 frontmatter
        markdown = f"""---
aliases: []
tags: [聊天记录, 待整理]
keywords: []
date: {today}
source: "聊天记录"
author: "Kimi Claw"
url: ""
---

# {today} 聊天记录总结

> 来源：聊天记录 | 作者：Kimi Claw | 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 🔑 Key Takeaway

_待 AI 提炼一句话核心观点_

---

## 📋 核心要点

- 待提炼要点

---

## 💭 关联思考

- 与 [[待补充]] 的关联：...
- 待探索的问题：
  - ...

---

## 📝 原文摘录

{content}

---

## 🔗 相关链接

- 相关笔记：[[待补充]]

---

## 🏷️ 标签

#聊天记录 #待整理

---

*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
        
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        # 删除原文件（可选，或者移动到归档目录）
        # source.unlink()
        
        return True
    except Exception as e:
        print(f"移动聊天记录到队列失败: {e}")
        return False

def extract_title(file_path: Path) -> str:
    """从 Markdown 文件提取标题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'^# (.+)$', content, re.MULTILINE)
            if match:
                title = match.group(1).strip()
                title = re.sub(r'\*\*', '', title)
                return title[:60] + "..." if len(title) > 60 else title
    except:
        pass
    return file_path.stem[:50]

def extract_author(file_path: Path) -> str:
    """从 Markdown 文件提取作者"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'source: "(.+)"', content)
            if match:
                return match.group(1)
    except:
        pass
    return "未知"

def extract_source(file_path: Path) -> str:
    """从 Markdown 文件提取来源"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'source: "(.+)"', content)
            if match:
                return match.group(1)
    except:
        pass
    return "未知"

def generate_confirmation_message() -> str:
    """生成待确认列表消息"""
    queue = get_queue_list()
    
    if not queue:
        return ""
    
    # 生成会话标识符（用于识别回复）
    session_id = datetime.now().strftime("%Y%m%d%H%M")
    
    message_lines = [
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄",
        f"📌 待读笔记列表（{datetime.now().strftime('%Y-%m-%d')}）",
        f"<!-- SESSION:{session_id} -->",
        "",
        f"共 {len(queue)} 个文件待处理：",
        ""
    ]
    
    for i, item in enumerate(queue, 1):
        message_lines.extend([
            f"{i}. {item['title']}",
            f"   作者：{item['author']} | 来源：{item['source']} | 时间：{item['created']}",
            ""
        ])
    
    message_lines.extend([
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄",
        "请选择处理方式：",
        "",
        "【A - 批量处理】",
        "  1. 原文保存",
        "  2. 主体+核心观点（500-1000字）⭐ 默认",
        "  3. 精简摘要（300字以内）",
        "",
        "【B - 差异化处理】",
        "  逐条展示并确认处理方式",
        "",
        "回复格式：",
        "  A1 / A2 / A3 - 批量处理",
        "  B - 差异化处理",
        "",
        "⏰ 15分钟内无回复，默认按 A2 处理",
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
    ])
    
    return "\n".join(message_lines)

def generate_daily_summary() -> str:
    """生成每日待确认汇总（包含两类任务）
    
    处理顺序：
    1. 先自动整理今天的聊天记录（如果没有文件）
    2. 处理聊天记录（选择保留的会进入待读队列）
    3. 再处理待读笔记（包含原有的+聊天记录新增的）
    """
    # 1. 先自动整理今天的聊天记录
    chat_summary = auto_summarize_today_chats()
    
    # 2. 如果有聊天记录，生成主题归纳提示
    chat_message = ""
    if chat_summary.get('has_chats'):
        topics = [{
            "title": chat_summary['title'],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "summary": chat_summary['summary']
        }]
        chat_message = generate_chat_topics_message(topics)
    
    # 3. 再获取待读笔记列表（此时如果用户选择保留聊天记录，会已经加入队列）
    queue = get_queue_list()
    
    # 待读笔记处理提示（后展示）
    queue_message = ""
    if queue:
        queue_message = generate_confirmation_message()
    
    # 两类都为空，静默跳过
    if not queue and not chat_summary.get('has_chats'):
        return ""
    
    # 组合消息：先聊天记录，再待读笔记
    messages = []
    
    # 1. 聊天记录主题归纳（先处理）
    if chat_message:
        messages.append(chat_message)
    
    # 2. 待读笔记列表（后处理，包含聊天记录新增的）
    if queue_message:
        if messages:
            messages.append("\n" + "="*40 + "\n")
        messages.append(queue_message)
    
    return "\n".join(messages)

def parse_response(response: str) -> dict:
    """解析用户回复"""
    response = response.strip().upper()
    
    # 批量处理
    if response.startswith('A'):
        if response == 'A1' or response == 'A 1':
            return {"type": "batch", "mode": "full", "valid": True}
        elif response == 'A2' or response == 'A 2' or response == 'A':
            return {"type": "batch", "mode": "summary", "valid": True}
        elif response == 'A3' or response == 'A 3':
            return {"type": "batch", "mode": "brief", "valid": True}
        else:
            return {"type": "invalid", "message": "回复格式错误，请使用 A1/A2/A3 或 B", "valid": False}
    
    # 差异化处理 - 进入逐条模式
    elif response == 'B':
        return {"type": "individual", "valid": True}
    
    # 逐条处理模式下的单条选择（1/2/3）
    elif response in ['1', '2', '3']:
        mode_map = {
            '1': 'full',      # 原文保存
            '2': 'summary',   # 主体+核心观点
            '3': 'brief'      # 精简摘要
        }
        return {"type": "individual_item", "mode": mode_map[response], "valid": True}
    
    # 聊天记录处理：Y=保留并处理（默认），N=删除
    elif response in ['Y', 'YES', '是', '确定', '保留', '']:
        # 将聊天记录移动到 queue/，进入待读笔记流程
        chat_summary = auto_summarize_today_chats()
        if chat_summary.get('has_chats'):
            success = move_chat_to_queue(chat_summary['file'])
            if success:
                return {"type": "chat_keep", "valid": True, "action": "moved_to_queue"}
        return {"type": "chat_keep", "valid": True}
    
    elif response in ['N', 'NO', '否', '跳过', '删除']:
        return {"type": "chat_delete", "valid": True}
    
    # 无效回复
    else:
        return {"type": "invalid", "message": "回复格式错误", "valid": False}

def sync_vault() -> dict:
    """同步 Vault 到 GitHub（双向同步）"""
    return commit_and_sync(f"Vault sync: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Second Brain Daily Task')
    parser.add_argument('--sync', action='store_true', help='仅同步到 GitHub')
    parser.add_argument('--message', '-m', type=str, help='提交消息')
    parser.add_argument('--check-interaction', action='store_true', help='检查过去24小时是否有交互')
    
    args = parser.parse_args()
    
    if args.sync:
        result = sync_vault()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.check_interaction:
        # 检查是否有交互（用于复盘报告的免打扰逻辑）
        has_interaction = has_user_interaction_last_24h()
        print(json.dumps({"has_interaction": has_interaction}, ensure_ascii=False))
    else:
        # 默认：生成每日待确认汇总
        print(generate_daily_summary())
