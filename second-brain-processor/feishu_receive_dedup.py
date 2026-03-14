#!/usr/bin/env python3
"""
Feishu 消息接收去重器 - 防止重复回复

问题背景：
Feishu 在消息处理超时会自动重试发送，导致 OpenClaw 收到重复消息，
从而生成重复回复。

解决方案：
基于 Feishu 消息ID（或内容指纹）进行接收去重。
"""

import json
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Set
import threading

WORKSPACE = Path("/root/.openclaw/workspace")
LEARNINGS_DIR = WORKSPACE / ".learnings"
RECEIVED_MSG_FILE = LEARNINGS_DIR / "received_messages.json"

# 去重窗口 - 12小时（覆盖 Feishu 重试周期和小时边界）
DEDUP_WINDOW_SECONDS = 43200

_lock = threading.Lock()


def _load_received() -> Dict:
    """加载已接收消息记录"""
    if RECEIVED_MSG_FILE.exists():
        try:
            with open(RECEIVED_MSG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "messages": [],  # 已接收消息列表
        "last_cleanup": datetime.now().isoformat()
    }


def _save_received(data: Dict):
    """保存已接收消息记录"""
    try:
        LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
        temp = RECEIVED_MSG_FILE.with_suffix('.tmp')
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp.replace(RECEIVED_MSG_FILE)
    except Exception as e:
        print(f"[WARN] 保存接收记录失败: {e}")


def _cleanup_old(data: Dict):
    """清理过期记录"""
    try:
        cutoff = datetime.now() - timedelta(seconds=DEDUP_WINDOW_SECONDS)
        original_count = len(data.get("messages", []))
        data["messages"] = [
            m for m in data.get("messages", [])
            if datetime.fromisoformat(m.get("time", "2000-01-01")) > cutoff
        ]
        data["last_cleanup"] = datetime.now().isoformat()
        cleaned = original_count - len(data["messages"])
        if cleaned > 0:
            print(f"[INFO] 清理了 {cleaned} 条过期接收记录")
    except Exception as e:
        print(f"[WARN] 清理接收记录失败: {e}")


def generate_message_fingerprint(content: str, sender: str = "") -> str:
    """
    生成消息指纹
    
    Args:
        content: 消息内容
        sender: 发送者ID（可选）
    
    Returns:
        指纹字符串
    """
    # 归一化：小写、去除多余空格、取前200字符
    normalized = content[:200].strip().lower()
    normalized = ' '.join(normalized.split())  # 去除多余空格
    
    # 仅使用发送者和内容生成指纹（移除小时限制，避免跨小时重复）
    to_hash = f"{sender}:{normalized}"
    
    return hashlib.md5(to_hash.encode()).hexdigest()[:16]


def is_message_received(content: str, sender: str = "") -> bool:
    """
    检查消息是否已接收过
    
    Args:
        content: 消息内容
        sender: 发送者ID
    
    Returns:
        True: 已接收过（重复消息）
        False: 新消息
    """
    with _lock:
        data = _load_received()
        _cleanup_old(data)
        
        fingerprint = generate_message_fingerprint(content, sender)
        
        for msg in data.get("messages", []):
            if msg.get("fingerprint") == fingerprint:
                # 检查是否在去重窗口内
                msg_time = datetime.fromisoformat(msg.get("time", "2000-01-01"))
                if datetime.now() - msg_time < timedelta(seconds=DEDUP_WINDOW_SECONDS):
                    print(f"[DUPLICATE] 消息已接收过（{fingerprint}），跳过处理")
                    return True
        
        return False


def record_message_received(content: str, sender: str = ""):
    """
    记录已接收消息
    
    Args:
        content: 消息内容
        sender: 发送者ID
    """
    with _lock:
        data = _load_received()
        
        fingerprint = generate_message_fingerprint(content, sender)
        
        # 检查是否已存在（避免重复记录）
        for msg in data.get("messages", []):
            if msg.get("fingerprint") == fingerprint:
                return  # 已存在，不重复记录
        
        # 添加新记录
        data["messages"].append({
            "fingerprint": fingerprint,
            "time": datetime.now().isoformat(),
            "sender": sender,
            "content_preview": content[:50]
        })
        
        # 限制记录数量
        if len(data["messages"]) > 500:
            data["messages"] = data["messages"][-500:]
        
        _save_received(data)


def check_and_record_message(content: str, sender: str = "") -> bool:
    """
    检查并记录消息（原子操作）
    
    Args:
        content: 消息内容
        sender: 发送者ID
    
    Returns:
        True: 新消息（可以继续处理）
        False: 重复消息（应跳过）
    """
    if is_message_received(content, sender):
        return False
    
    record_message_received(content, sender)
    return True


# 兼容性别名
is_duplicate_message = is_message_received
mark_message_received = record_message_received


if __name__ == "__main__":
    # 测试
    test_msg = "测试消息"
    sender = "test_user"
    
    # 第一次：新消息
    result1 = check_and_record_message(test_msg, sender)
    print(f"第一次检查: {'新消息' if result1 else '重复消息'}")
    
    # 第二次：重复消息
    result2 = check_and_record_message(test_msg, sender)
    print(f"第二次检查: {'新消息' if result2 else '重复消息'}")
    
    # 不同发送者：新消息
    result3 = check_and_record_message(test_msg, "other_user")
    print(f"不同发送者: {'新消息' if result3 else '重复消息'}")
