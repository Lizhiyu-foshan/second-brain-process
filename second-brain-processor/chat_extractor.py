#!/usr/bin/env python3
"""
OpenClaw 会话历史提取器
从 OpenClaw 的会话历史文件（.jsonl）中提取今天的聊天记录
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

# 会话存储目录
SESSIONS_DIR = Path("/root/.openclaw/agents/main/sessions")
MEMORY_DIR = Path("/root/.openclaw/workspace/memory")

# 主会话标识符
MAIN_SESSION_KEYS = ["agent:main:main", "agent:main:feishu"]

def extract_chat_from_jsonl(file_path: Path) -> list:
    """
    从 JSONL 文件中提取用户和助手的对话
    
    返回：[(timestamp, role, content), ...]
    """
    chats = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                # 只提取消息类型的记录
                if record.get('type') != 'message':
                    continue
                
                message = record.get('message', {})
                role = message.get('role')
                
                # 只提取用户和助手的消息
                if role not in ['user', 'assistant']:
                    continue
                
                # 提取时间戳
                timestamp = record.get('timestamp', '')
                
                # 提取内容
                content_parts = message.get('content', [])
                content = extract_content_text(content_parts)
                
                if content and not is_heartbeat(content):
                    chats.append({
                        'timestamp': timestamp,
                        'role': role,
                        'content': content
                    })
                    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        
    return chats

def extract_content_text(content_parts: list) -> str:
    """从内容部分提取文本"""
    texts = []
    
    for part in content_parts:
        if isinstance(part, dict):
            if part.get('type') == 'text':
                texts.append(part.get('text', ''))
            elif part.get('type') == 'toolCall':
                # 记录工具调用但不显示详细参数
                tool_name = part.get('name', 'unknown')
                texts.append(f"[使用工具: {tool_name}]")
            elif part.get('type') == 'toolResult':
                # 工具结果摘要
                texts.append("[工具执行完成]")
    
    return '\n'.join(texts)

def is_heartbeat(content: str) -> bool:
    """判断是否是心跳消息"""
    heartbeat_patterns = [
        'HEARTBEAT_OK',
        'Read HEARTBEAT.md',
        'If nothing needs attention',
        'Current time:',
    ]
    
    for pattern in heartbeat_patterns:
        if pattern in content:
            return True
    
    return False

def get_today_chats() -> dict:
    """
    获取今天的所有聊天记录
    
    返回：{
        'has_chats': bool,
        'title': str,
        'content': str,
        'session_count': int,
        'message_count': int
    }
    """
    today = datetime.now().strftime('%Y-%m-%d')
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    all_chats = []
    session_files = []
    
    # 查找今天的会话文件
    if SESSIONS_DIR.exists():
        for jsonl_file in SESSIONS_DIR.glob('*.jsonl'):
            # 跳过锁文件和已删除的会话
            if '.lock' in jsonl_file.name or '.deleted' in jsonl_file.name:
                continue
                
            # 检查文件修改时间
            try:
                mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
                if mtime >= today_start:
                    chats = extract_chat_from_jsonl(jsonl_file)
                    if chats:
                        all_chats.extend(chats)
                        session_files.append(jsonl_file.name)
            except Exception as e:
                print(f"Error checking {jsonl_file}: {e}")
    
    if not all_chats:
        return {
            'has_chats': False,
            'title': '',
            'content': '',
            'session_count': 0,
            'message_count': 0
        }
    
    # 按时间排序
    all_chats.sort(key=lambda x: x['timestamp'])
    
    # 生成内容
    content_lines = []
    for chat in all_chats:
        role_label = "用户" if chat['role'] == 'user' else "AI"
        content_lines.append(f"\n## {role_label} ({chat['timestamp']})\n")
        content_lines.append(chat['content'])
    
    content = '\n'.join(content_lines)
    
    # 提取标题（从第一条用户消息）
    title = f"{today} 会话记录"
    for chat in all_chats:
        if chat['role'] == 'user':
            first_line = chat['content'].split('\n')[0][:50]
            if first_line and not is_heartbeat(chat['content']):
                title = f"{today} {first_line}"
                break
    
    return {
        'has_chats': True,
        'title': title,
        'content': content,
        'session_count': len(session_files),
        'message_count': len(all_chats)
    }

def save_chat_to_memory(chat_data: dict) -> Path:
    """
    将聊天记录保存到 memory/ 目录
    
    返回：保存的文件路径
    """
    if not chat_data['has_chats']:
        return None
    
    today = datetime.now().strftime('%Y-%m-%d')
    memory_file = MEMORY_DIR / f"{today}.md"
    
    # 确保目录存在
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成 frontmatter
    markdown = f"""---
date: {today}
type: 聊天记录
tags: [对话, 自动归档]
---

# {chat_data['title']}

## 统计
- 会话数：{chat_data['session_count']}
- 消息数：{chat_data['message_count']}
- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

---

{chat_data['content']}

---

*自动归档于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
    
    with open(memory_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    return memory_file

if __name__ == "__main__":
    # 测试
    result = get_today_chats()
    
    if result['has_chats']:
        print(f"找到 {result['message_count']} 条消息，来自 {result['session_count']} 个会话")
        print(f"标题: {result['title']}")
        
        # 保存到 memory/
        saved_path = save_chat_to_memory(result)
        if saved_path:
            print(f"已保存到: {saved_path}")
    else:
        print("今天没有聊天记录")
