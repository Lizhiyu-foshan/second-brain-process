#!/usr/bin/env python3
"""
清晨 5:00 对话整理脚本（无 AI）
从 OpenClaw 会话历史读取昨天对话，保存到 Obsidian Vault
"""

import json
import os
import sys
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 配置
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
CONVERSATIONS_DIR = VAULT_DIR / "02-Conversations"
SESSIONS_FILE = Path("/root/.openclaw/agents/main/sessions/sessions.json")

def get_24h_timestamp_range():
    """获取往前24小时的时间戳范围（毫秒）
    
    每天凌晨5:00执行，整理从昨天凌晨5:00到今天凌晨5:00的24小时对话
    北京时间5:00 = UTC 21:00（前一天）
    """
    now_utc = datetime.now(timezone.utc)
    
    # 今天凌晨5:00北京时间 = 昨天21:00 UTC
    end_time = now_utc  # 当前执行时间（约5:00 UTC）
    start_time = end_time - timedelta(days=1)  # 24小时前
    
    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)
    
    # 返回日期字符串（使用开始时间的日期作为文件名）
    beijing_tz = timezone(timedelta(hours=8))
    start_beijing = start_time.astimezone(beijing_tz)
    
    return start_ts, end_ts, start_beijing.strftime("%Y-%m-%d")

def load_sessions():
    """加载会话历史"""
    if not SESSIONS_FILE.exists():
        print(f"[ERROR] 会话文件不存在: {SESSIONS_FILE}")
        return {}
    
    try:
        with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] 读取会话文件失败: {e}")
        return {}

def load_session_messages(session_key, session_data, start_ts, end_ts):
    """从 jsonl 文件加载会话消息"""
    messages = []
    
    # 从 session_data 获取真正的 sessionId（文件名）
    session_id = session_data.get("sessionId", "")
    if not session_id:
        # 兼容旧逻辑：从 session_key 提取
        parts = session_key.split(':')
        if len(parts) >= 3:
            session_id = parts[2]
    
    if not session_id:
        return messages
    
    # 构建 jsonl 文件路径
    jsonl_path = Path(f"/root/.openclaw/agents/main/sessions/{session_id}.jsonl")
    
    if not jsonl_path.exists():
        return messages
    
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    msg = json.loads(line)
                    
                    # 只处理消息类型
                    if msg.get("type") != "message":
                        continue
                    
                    # 解析 ISO 8601 时间戳
                    ts_str = msg.get("timestamp", "")
                    if not ts_str:
                        continue
                    
                    # 转换为毫秒时间戳
                    try:
                        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        msg_ts = int(dt.timestamp() * 1000)
                    except:
                        continue
                    
                    # 检查时间戳是否在范围内
                    if start_ts <= msg_ts <= end_ts:
                        message_data = msg.get("message", {})
                        role = message_data.get("role", "unknown")
                        
                        # 获取内容
                        content_parts = message_data.get("content", [])
                        if isinstance(content_parts, list) and len(content_parts) > 0:
                            content = content_parts[0].get("text", "")
                        else:
                            content = str(content_parts)
                        
                        # 跳过系统消息和心跳
                        if role == "system" or "HEARTBEAT_OK" in content:
                            continue
                        
                        messages.append({
                            "timestamp": msg_ts,
                            "role": role,
                            "content": content,
                            "session": session_key
                        })
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    continue
    except Exception as e:
        print(f"[WARN] 读取会话文件失败 {jsonl_path}: {e}")
    
    return messages

def extract_last_24h_messages(sessions, start_ts, end_ts):
    """提取过去24小时的消息"""
    messages = []
    
    for session_key, session_data in sessions.items():
        # 只处理主会话
        if not session_key.startswith("agent:main:main"):
            continue
        
        # 从 jsonl 文件读取消息
        session_messages = load_session_messages(session_key, session_data, start_ts, end_ts)
        messages.extend(session_messages)
    
    # 按时间排序
    messages.sort(key=lambda x: x["timestamp"])
    return messages

def format_message(msg):
    """格式化单条消息"""
    ts = datetime.fromtimestamp(msg["timestamp"] / 1000).strftime("%H:%M:%S")
    role = msg["role"]
    content = msg["content"]
    
    # 截断过长的内容
    if len(content) > 2000:
        content = content[:2000] + "\n... [内容过长，已截断]"
    
    if role == "user":
        return f"**[{ts}] 用户**\n{content}\n\n---\n\n"
    elif role == "assistant":
        return f"**[{ts}] AI**\n{content}\n\n---\n\n"
    else:
        return f"**[{ts}] {role}**\n{content}\n\n---\n\n"

def save_conversations(messages, date_str):
    """保存对话到 Obsidian Vault"""
    if not messages:
        print(f"[WARN] 昨天（{date_str}）没有对话记录")
        return False, 0
    
    # 确保目录存在
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    output_file = CONVERSATIONS_DIR / f"{date_str}_conversations.md"
    
    # 构建文件内容
    content_lines = [
        f"---",
        f"date: {date_str}",
        f"type: 聊天记录",
        f"tags: [对话, 自动归档]",
        f"message_count: {len(messages)}",
        f"---",
        f"",
        f"# {date_str} 对话记录",
        f"",
        f"## 统计",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 消息数量：{len(messages)} 条",
        f"- 状态：待 AI 深度分析",
        f"",
        f"---",
        f"",
        f"## 原始对话",
        f"",
    ]
    
    # 添加所有消息
    for msg in messages:
        content_lines.append(format_message(msg))
    
    # 写入文件
    content = "\n".join(content_lines)
    output_file.write_text(content, encoding='utf-8')
    
    print(f"[SUCCESS] 对话已保存: {output_file}")
    print(f"[INFO] 消息数量: {len(messages)} 条")
    print(f"[INFO] 文件大小: {len(content)} 字符")
    
    return True, len(messages)

def process_raw_dialog():
    """主函数：处理原始对话"""
    print(f"[{datetime.now()}] === 开始执行原始对话整理 ===")
    
    # 1. 获取昨天的时间范围
    start_ts, end_ts, date_str = get_24h_timestamp_range()
    print(f"[INFO] 处理时间: 过去24小时 (文件名: {date_str})")
    print(f"[INFO] 时间范围: {start_ts} - {end_ts}")
    
    # 2. 加载会话
    sessions = load_sessions()
    if not sessions:
        print("[ERROR] 无法加载会话数据")
        return False
    
    print(f"[INFO] 加载会话数: {len(sessions)}")
    
    # 3. 提取过去24小时的消息
    messages = extract_last_24h_messages(sessions, start_ts, end_ts)
    print(f"[INFO] 提取消息数: {len(messages)}")
    
    # 4. 保存对话
    success, count = save_conversations(messages, date_str)
    
    if success:
        print(f"[{datetime.now()}] === 原始对话整理完成 ===")
        print(f"[RESULT] 成功保存 {count} 条消息到 {CONVERSATIONS_DIR}")
        return True
    else:
        print(f"[{datetime.now()}] === 原始对话整理完成（无数据） ===")
        return True  # 无数据不算失败

if __name__ == "__main__":
    try:
        success = process_raw_dialog()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[CRITICAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
