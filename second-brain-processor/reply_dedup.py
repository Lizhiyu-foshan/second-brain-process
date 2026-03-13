#!/usr/bin/env python3
"""
对话级去重检查 - 防止重复回复

由于系统入口无法修改，在对话处理层面增加二次去重。
- 记录已处理的用户输入指纹
- 检测到重复输入时返回 NO_REPLY
- 独立于系统级去重，作为兜底机制
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/second-brain-processor')
from feishu_receive_dedup import check_and_record_message, generate_message_fingerprint

WORKSPACE = Path("/root/.openclaw/workspace")
REPLIED_FILE = WORKSPACE / ".learnings" / "replied_messages.json"

def check_and_record_reply(content: str, sender: str = "") -> bool:
    """
    检查并记录已回复的消息
    
    Returns:
        True: 新消息（应该回复）
        False: 已回复过（返回 NO_REPLY）
    """
    # 使用接收去重系统记录
    is_new = check_and_record_message(content, sender)
    return is_new


def is_duplicate_in_session(content: str, sender: str = "", window_minutes: int = 30) -> bool:
    """
    检查在会话窗口内是否已回复
    
    Args:
        content: 用户输入内容
        sender: 发送者ID  
        window_minutes: 检查窗口（默认30分钟）
    
    Returns:
        True: 是重复消息（不应回复）
        False: 是新消息（应该回复）
    """
    try:
        if not REPLIED_FILE.exists():
            return False
        
        with open(REPLIED_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        fingerprint = generate_message_fingerprint(content, sender)
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        
        for record in data.get("replied", []):
            if record.get("fingerprint") == fingerprint:
                record_time = datetime.fromisoformat(record.get("time", "2000-01-01"))
                if record_time > cutoff:
                    return True
        
        return False
    except Exception:
        return False


def record_reply(content: str, sender: str = ""):
    """记录已回复的消息"""
    try:
        data = {"replied": []}
        if REPLIED_FILE.exists():
            with open(REPLIED_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        fingerprint = generate_message_fingerprint(content, sender)
        data["replied"].append({
            "fingerprint": fingerprint,
            "time": datetime.now().isoformat(),
            "content_preview": content[:50]
        })
        
        # 只保留最近100条
        if len(data["replied"]) > 100:
            data["replied"] = data["replied"][-100:]
        
        REPLIED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REPLIED_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] 记录回复失败: {e}")


if __name__ == "__main__":
    # 测试
    test_msg = "测试重复回复检查"
    sender = "test_user"
    
    print("测试1: 首次消息")
    result1 = check_and_record_reply(test_msg, sender)
    print(f"  是否新消息: {result1}")  # 应为 True
    
    print("测试2: 重复消息")
    result2 = check_and_record_reply(test_msg, sender)
    print(f"  是否新消息: {result2}")  # 应为 False
    
    print("测试3: 不同内容")
    result3 = check_and_record_reply("不同内容", sender)
    print(f"  是否新消息: {result3}")  # 应为 True
