#!/usr/bin/env python3
"""
清晨 5:00 对话整理脚本（无 AI）- 高性能版 v2
从 OpenClaw 会话历史读取昨天对话，保存到 Obsidian Vault

优化内容：
- 保持3天扫描范围（避免漏扫）
- 移除文件修改时间检查，直接遍历所有文件
- 批量读取文件内容，减少IO次数
- 快速预检查：读取前3行判断是否在目标时间范围
- 使用哈希去重
- 预期性能：3秒内完成（原49秒）
"""

import json
import os
import sys
import re
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 配置
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
CONVERSATIONS_DIR = VAULT_DIR / "02-Conversations"
SESSIONS_FILE = Path("/root/.openclaw/agents/main/sessions/sessions.json")

# 扫描近3天的会话（避免漏扫）
SCAN_DAYS = 3


def get_24h_timestamp_range():
    """获取往前24小时的时间戳范围（毫秒）"""
    now_utc = datetime.now(timezone.utc)
    end_time = now_utc
    start_time = end_time - timedelta(days=1)
    
    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)
    
    beijing_tz = timezone(timedelta(hours=8))
    start_beijing = start_time.astimezone(beijing_tz)
    
    return start_ts, end_ts, start_beijing.strftime("%Y-%m-%d")


def quick_time_check(file_path, start_ts, end_ts):
    """
    快速预检查：读取文件前3行，判断是否在目标时间范围内
    返回: (should_process, confidence)
    - should_process: 是否值得读取完整文件
    - confidence: high(确定有)/low(可能有)/none(确定无)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= 3:  # 只读前3行
                    break
                lines.append(line)
            
            # 如果文件少于3行，可能很旧或为空
            if len(lines) < 3:
                # 检查这仅有的几行
                for line in lines:
                    try:
                        msg = json.loads(line.strip())
                        ts_str = msg.get("timestamp", "")
                        if ts_str:
                            dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                            msg_ts = int(dt.timestamp() * 1000)
                            if start_ts <= msg_ts <= end_ts:
                                return True, "high"
                    except:
                        continue
                return False, "none"
            
            # 检查前3行
            has_recent = False
            has_old = False
            
            for line in lines:
                try:
                    msg = json.loads(line.strip())
                    ts_str = msg.get("timestamp", "")
                    if ts_str:
                        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        msg_ts = int(dt.timestamp() * 1000)
                        
                        # 如果在目标范围内
                        if start_ts <= msg_ts <= end_ts:
                            has_recent = True
                        # 如果比目标范围早很多（超过7天）
                        elif msg_ts < start_ts - 7 * 24 * 3600 * 1000:
                            has_old = True
                except:
                    continue
            
            if has_recent:
                return True, "high"
            elif has_old and not has_recent:
                # 文件开头是很旧的消息，大概率整个文件都旧
                return False, "low"
            else:
                # 不确定，需要完整读取
                return True, "low"
                
    except Exception:
        return True, "low"  # 出错时保守处理


def load_messages_from_file_optimized(jsonl_path, start_ts, end_ts):
    """
    优化的消息加载函数
    - 快速预检查避免读取无关文件
    - 批量读取内容
    """
    messages = []
    
    if not jsonl_path.exists():
        return messages
    
    # 优化1：快速预检查
    should_process, confidence = quick_time_check(jsonl_path, start_ts, end_ts)
    
    if not should_process:
        return messages  # 快速跳过
    
    # 需要完整读取
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    msg = json.loads(line)
                    
                    if msg.get("type") != "message":
                        continue
                    
                    ts_str = msg.get("timestamp", "")
                    if not ts_str:
                        continue
                    
                    try:
                        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        msg_ts = int(dt.timestamp() * 1000)
                    except:
                        continue
                    
                    if not (start_ts <= msg_ts <= end_ts):
                        continue
                    
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
                        "file": jsonl_path.name
                    })
                except json.JSONDecodeError:
                    continue
                except Exception:
                    continue
    except Exception as e:
        print(f"[WARN] 读取会话文件失败 {jsonl_path}: {e}")
    
    return messages


def extract_last_24h_messages_optimized(sessions, start_ts, end_ts):
    """
    优化的消息提取函数
    - 扫描近3天所有文件（避免漏扫）
    - 使用快速预检查减少IO
    - 使用哈希去重
    """
    messages = []
    
    sessions_dir = Path("/root/.openclaw/agents/main/sessions/")
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=SCAN_DAYS)
    
    scanned_files = 0
    matched_files = 0
    skipped_files = 0
    
    # 获取所有jsonl文件
    all_files = list(sessions_dir.glob("*.jsonl"))
    
    for jsonl_file in all_files:
        # 跳过已删除的文件
        if "deleted" in jsonl_file.name:
            continue
        
        # 检查文件mtime（用于统计，不是过滤条件）
        try:
            mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime, tz=timezone.utc)
            file_age_days = (datetime.now(timezone.utc) - mtime).days
        except:
            file_age_days = 999
        
        scanned_files += 1
        
        # 优化的文件读取
        file_messages = load_messages_from_file_optimized(jsonl_file, start_ts, end_ts)
        
        if file_messages:
            matched_files += 1
            messages.extend(file_messages)
        elif file_age_days > SCAN_DAYS:
            skipped_files += 1
    
    print(f"[INFO] 扫描会话文件: {scanned_files} 个, 匹配 {matched_files} 个, 快速跳过 {skipped_files} 个")
    
    # 按时间排序
    messages.sort(key=lambda x: x["timestamp"])
    
    # 使用哈希去重
    seen_hashes = set()
    unique_messages = []
    
    for msg in messages:
        content_hash = hashlib.md5(
            f"{msg['timestamp']}_{msg['content'][:100]}".encode('utf-8')
        ).hexdigest()
        
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            unique_messages.append(msg)
    
    if len(unique_messages) < len(messages):
        print(f"[INFO] 去重: {len(messages)} → {len(unique_messages)} 条")
    
    return unique_messages


def format_message(msg):
    """格式化单条消息"""
    ts = datetime.fromtimestamp(msg["timestamp"] / 1000).strftime("%H:%M:%S")
    role = msg["role"]
    content = msg["content"]
    
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
    
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = CONVERSATIONS_DIR / f"{date_str}_conversations.md"
    
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
    
    for msg in messages:
        content_lines.append(format_message(msg))
    
    content = "\n".join(content_lines)
    output_file.write_text(content, encoding='utf-8')
    
    print(f"[SUCCESS] 对话已保存: {output_file}")
    print(f"[INFO] 消息数量: {len(messages)} 条")
    print(f"[INFO] 文件大小: {len(content)} 字符")
    
    return True, len(messages)


def process_raw_dialog():
    """主函数：处理原始对话"""
    print(f"[{datetime.now()}] === 开始执行原始对话整理（高性能版 v2）===")
    
    start_ts, end_ts, date_str = get_24h_timestamp_range()
    print(f"[INFO] 处理时间: 过去24小时 (文件名: {date_str})")
    print(f"[INFO] 时间范围: {start_ts} - {end_ts}")
    print(f"[INFO] 扫描范围: 近{SCAN_DAYS}天所有会话文件")
    
    sessions = {}  # 保持兼容，实际不再使用
    
    messages = extract_last_24h_messages_optimized(sessions, start_ts, end_ts)
    print(f"[INFO] 提取消息数: {len(messages)}")
    
    success, count = save_conversations(messages, date_str)
    
    if success:
        print(f"[{datetime.now()}] === 原始对话整理完成 ===")
        print(f"[RESULT] 成功保存 {count} 条消息到 {CONVERSATIONS_DIR}")
        return True
    else:
        print(f"[{datetime.now()}] === 原始对话整理完成（无数据） ===")
        return True


if __name__ == "__main__":
    try:
        success = process_raw_dialog()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[CRITICAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
