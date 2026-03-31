#!/usr/bin/env python3
"""
手动处理特定日期的对话记录 - v2.0
优化内容：
- 过滤空消息和系统消息
- 过滤工具调用和心跳消息
- 支持消息内容清洗
- 更好的错误处理
"""

import json
import sys
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 添加lib目录到路径
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from message_index import IndexManager

# 配置
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
CONVERSATIONS_DIR = VAULT_DIR / "02-Conversations"
SESSIONS_DIR = Path("/root/.openclaw/agents/main/sessions/")

# 需要过滤的消息模式
SKIP_PATTERNS = [
    r"^\s*$",  # 纯空白
    r"^HEARTBEAT_OK\s*$",  # 心跳确认
    r"^Read HEARTBEAT\.md",  # 心跳指令
    r"^\[object Object\]",  # 对象序列化错误
    r"^\[\s*\]$",  # 空数组
    r"^\{\s*\}$",  # 空对象
    r"^<.*>.*</.*>$",  # XML/HTML 标签
]

SKIP_ROLES = ["system", "tool"]
SKIP_TYPES = ["tool_call", "tool_result", "function_call"]


def should_skip_message(msg: dict, content: str) -> bool:
    """
    判断是否应该跳过这条消息
    
    跳过条件：
    1. 角色是 system 或 tool
    2. 内容为空或纯空白
    3. 匹配跳过模式
    4. 是工具调用相关的消息
    """
    # 检查角色
    role = msg.get("role", "").lower()
    if role in SKIP_ROLES:
        return True
    
    # 检查消息类型
    msg_type = msg.get("type", "").lower()
    if msg_type in SKIP_TYPES:
        return True
    
    # 检查是否有 tool_calls（工具调用）
    if "tool_calls" in msg and msg["tool_calls"]:
        return True
    
    # 清理内容
    if not content:
        return True
    
    content = content.strip()
    if not content:
        return True
    
    # 检查跳过模式
    for pattern in SKIP_PATTERNS:
        if re.match(pattern, content, re.IGNORECASE):
            return True
    
    return False


def extract_content(msg: dict) -> str:
    """
    从消息中提取内容，处理多种格式
    """
    content = ""
    
    # 尝试不同的字段路径
    if "content" in msg:
        content_data = msg["content"]
        
        if isinstance(content_data, str):
            content = content_data
        elif isinstance(content_data, list) and len(content_data) > 0:
            # 处理 [{"type": "text", "text": "..."}] 格式
            if isinstance(content_data[0], dict):
                content = content_data[0].get("text", "")
                # 合并多个 content parts
                if not content:
                    parts = [p.get("text", "") for p in content_data if isinstance(p, dict)]
                    content = "\n".join(filter(None, parts))
            else:
                content = str(content_data[0])
        else:
            content = str(content_data)
    
    # 如果上述方法失败，尝试 message.content 路径
    if not content and "message" in msg:
        message_data = msg["message"]
        if isinstance(message_data, dict):
            msg_content = message_data.get("content", "")
            if isinstance(msg_content, list) and len(msg_content) > 0:
                if isinstance(msg_content[0], dict):
                    content = msg_content[0].get("text", "")
                else:
                    content = str(msg_content[0])
            elif isinstance(msg_content, str):
                content = msg_content
    
    return content.strip()


def process_date_range(start_date: str, end_date: str):
    """处理指定日期范围的对话"""
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    
    print(f"📅 处理日期范围: {start_date} 到 {end_date}")
    print(f"⏱️  时间戳范围: {start_ts} 到 {end_ts}")
    print()
    
    # 收集消息
    messages_by_date = {}
    total_scanned = 0
    total_skipped = 0
    
    for jsonl_file in SESSIONS_DIR.glob("*.jsonl"):
        if "deleted" in jsonl_file.name:
            continue
        
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    total_scanned += 1
                    
                    try:
                        msg = json.loads(line.strip())
                        
                        # 跳过非消息类型
                        if msg.get("type") != "message":
                            total_skipped += 1
                            continue
                        
                        ts_str = msg.get("timestamp", "")
                        if not ts_str:
                            total_skipped += 1
                            continue
                        
                        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        msg_ts = int(dt.timestamp() * 1000)
                        
                        # 检查是否在目标范围内
                        if not (start_ts <= msg_ts < end_ts):
                            continue
                        
                        # 提取内容
                        content = extract_content(msg)
                        
                        # 跳过无效消息
                        if should_skip_message(msg, content):
                            total_skipped += 1
                            continue
                        
                        # 确定角色
                        role = msg.get("role", "")
                        if not role and "message" in msg:
                            role = msg["message"].get("role", "")
                        
                        role = "user" if role == "user" else "assistant"
                        
                        date_str = dt.strftime("%Y-%m-%d")
                        if date_str not in messages_by_date:
                            messages_by_date[date_str] = []
                        
                        messages_by_date[date_str].append({
                            "timestamp": msg_ts,
                            "role": role,
                            "content": content,
                            "time_str": dt.strftime("%H:%M")
                        })
                        
                    except json.JSONDecodeError:
                        total_skipped += 1
                        continue
                    except Exception:
                        total_skipped += 1
                        continue
                        
        except Exception as e:
            print(f"⚠️  Error reading {jsonl_file}: {e}")
    
    print(f"📊 扫描统计: 共扫描 {total_scanned} 条记录, 跳过 {total_skipped} 条")
    print()
    
    # 排序并生成文件
    total_written = 0
    for date_str in sorted(messages_by_date.keys()):
        messages = messages_by_date[date_str]
        messages.sort(key=lambda x: x["timestamp"])
        
        # 生成markdown
        output_file = CONVERSATIONS_DIR / f"{date_str}_对话记录.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {date_str} 对话记录\n\n")
            f.write(f"**生成时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
            f.write(f"**有效消息**: {len(messages)} 条\n\n")
            f.write("---\n\n")
            
            for msg in messages:
                role_emoji = "👤" if msg["role"] == "user" else "🤖"
                f.write(f"### {msg['time_str']} {role_emoji} {msg['role'].upper()}\n\n")
                f.write(f"{msg['content']}\n\n")
            
            f.write("---\n\n")
            f.write(f"**共 {len(messages)} 条有效消息**\n")
        
        total_written += len(messages)
        print(f"✅ 已生成: {output_file.name} ({len(messages)} 条消息)")
    
    print()
    print(f"🎉 完成! 共处理 {len(messages_by_date)} 个日期, {total_written} 条有效消息")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="手动处理特定日期的对话记录")
    parser.add_argument("--start", "-s", default="2026-03-28", help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", "-e", default="2026-03-29", help="结束日期 (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    process_date_range(args.start, args.end)
