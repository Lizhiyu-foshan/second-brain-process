#!/usr/bin/env python3
"""
手动修复 3月21日对话记录
"""
import json
from pathlib import Path
from datetime import datetime, timezone

# 配置
SESSIONS_DIR = Path("/root/.openclaw/agents/main/sessions/")
CONVERSATIONS_DIR = Path("/root/.openclaw/workspace/obsidian-vault/02-Conversations")

# 3月21日的时间范围（UTC）
MARCH_21_START = int(datetime(2026, 3, 21, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
MARCH_21_END = int(datetime(2026, 3, 22, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)

def extract_messages():
    """提取3月21日的所有消息"""
    messages = []
    
    for jsonl_file in SESSIONS_DIR.glob("*.jsonl"):
        if "deleted" in jsonl_file.name:
            continue
        
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        msg = json.loads(line.strip())
                        if msg.get("type") != "message":
                            continue
                        
                        ts_str = msg.get("timestamp", "")
                        if not ts_str:
                            continue
                        
                        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        msg_ts = int(dt.timestamp() * 1000)
                        
                        # 只保留3月21日的消息
                        if msg_ts < MARCH_21_START or msg_ts >= MARCH_21_END:
                            continue
                        
                        # 解析消息内容
                        message_data = msg.get("message", {})
                        role = message_data.get("role", "unknown")
                        
                        content_parts = message_data.get("content", [])
                        if isinstance(content_parts, list) and len(content_parts) > 0:
                            content = content_parts[0].get("text", "")
                        else:
                            content = str(content_parts)
                        
                        # 跳过系统消息和心跳
                        if role == "system" or "HEARTBEAT_OK" in content or "Read HEARTBEAT.md" in content:
                            continue
                        
                        messages.append({
                            "timestamp": msg_ts,
                            "role": role,
                            "content": content,
                            "time_str": datetime.fromtimestamp(msg_ts / 1000, tz=timezone.utc).strftime("%H:%M:%S")
                        })
                    except:
                        continue
        except Exception as e:
            print(f"Error reading {jsonl_file}: {e}")
    
    # 排序
    messages.sort(key=lambda m: m["timestamp"])
    return messages

def format_message(msg):
    """格式化单条消息"""
    ts = msg["time_str"]
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

def main():
    print("提取 3月21日 消息...")
    messages = extract_messages()
    print(f"找到 {len(messages)} 条消息")
    
    if not messages:
        print("没有消息需要处理")
        return
    
    # 生成文件内容
    content_lines = [
        "---",
        "date: 2026-03-21",
        "type: 聊天记录",
        "tags: [对话, 自动归档, 增量处理]",
        f"message_count: {len(messages)}",
        "---",
        "",
        "# 2026-03-21 对话记录",
        "",
        "## 统计",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 消息数量：{len(messages)} 条",
        "- 处理模式：手动修复",
        "- 状态：待 AI 深度分析",
        "",
        "---",
        "",
        "## 原始对话",
        "",
    ]
    
    # 添加消息
    for msg in messages:
        content_lines.append(format_message(msg))
    
    # 写入文件
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = CONVERSATIONS_DIR / "2026-03-21_conversations.md"
    output_file.write_text("\n".join(content_lines), encoding='utf-8')
    
    print(f"对话记录已保存: {output_file}")
    print(f"文件大小: {output_file.stat().st_size} 字节")

if __name__ == "__main__":
    main()
