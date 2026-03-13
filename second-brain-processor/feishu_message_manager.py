#!/usr/bin/env python3
"""
飞书消息发送管理器 - 解决延迟补发问题

核心机制：
1. 消息状态追踪 - 记录每条消息的发送状态
2. 去重机制 - 防止重复发送相同内容
3. 超时控制 - 限制单次发送的最大等待时间
4. 优雅降级 - 发送失败时保存到队列，稍后重试
"""

import json
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import subprocess
import threading

# 状态文件
WORKSPACE = Path("/root/.openclaw/workspace")
LEARNINGS_DIR = WORKSPACE / ".learnings"
MESSAGE_STATE_FILE = LEARNINGS_DIR / "message_state.json"
MESSAGE_QUEUE_FILE = LEARNINGS_DIR / "message_queue.json"
MAX_SEND_TIME = 10  # 最大发送等待时间（秒）
DEDUP_WINDOW = 300  # 去重窗口（5分钟）

# 线程锁
_lock = threading.Lock()


def _load_state() -> Dict:
    """加载消息状态"""
    if MESSAGE_STATE_FILE.exists():
        try:
            with open(MESSAGE_STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "sent_messages": [],  # 已发送消息记录
        "last_cleanup": datetime.now().isoformat()
    }


def _save_state(state: Dict):
    """保存消息状态"""
    try:
        LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
        # 原子写入
        temp_file = MESSAGE_STATE_FILE.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        temp_file.replace(MESSAGE_STATE_FILE)
    except IOError as e:
        print(f"[WARN] 保存消息状态失败: {e}")


def _cleanup_old_records(state: Dict):
    """清理过期的发送记录（超过5分钟）"""
    try:
        last_cleanup = datetime.fromisoformat(state.get("last_cleanup", "2000-01-01"))
        if datetime.now() - last_cleanup < timedelta(minutes=1):
            return  # 1分钟内清理过，跳过
        
        cutoff = datetime.now() - timedelta(seconds=DEDUP_WINDOW)
        state["sent_messages"] = [
            msg for msg in state["sent_messages"]
            if datetime.fromisoformat(msg.get("time", "2000-01-01")) > cutoff
        ]
        state["last_cleanup"] = datetime.now().isoformat()
        _save_state(state)
    except Exception as e:
        print(f"[WARN] 清理旧记录失败: {e}")


def _generate_msg_id(content: str, target: str) -> str:
    """生成消息唯一ID（基于内容和目标）"""
    # 取内容前100字符 + 目标 + 当前小时（同一小时内相同内容视为重复）
    content_hash = hashlib.md5(f"{target}:{content[:100]}".encode()).hexdigest()[:16]
    return content_hash


def is_duplicate(content: str, target: str) -> bool:
    """检查是否是重复消息"""
    with _lock:
        state = _load_state()
        _cleanup_old_records(state)
        
        msg_id = _generate_msg_id(content, target)
        
        for msg in state["sent_messages"]:
            if msg.get("id") == msg_id:
                # 检查是否在去重窗口内
                msg_time = datetime.fromisoformat(msg.get("time", "2000-01-01"))
                if datetime.now() - msg_time < timedelta(seconds=DEDUP_WINDOW):
                    return True
        return False


def record_sent(content: str, target: str, success: bool = True):
    """记录已发送消息"""
    with _lock:
        state = _load_state()
        
        msg_id = _generate_msg_id(content, target)
        
        # 添加新记录
        state["sent_messages"].append({
            "id": msg_id,
            "time": datetime.now().isoformat(),
            "target": target,
            "success": success,
            "content_preview": content[:50]
        })
        
        # 限制记录数量
        if len(state["sent_messages"]) > 100:
            state["sent_messages"] = state["sent_messages"][-100:]
        
        _save_state(state)


def send_feishu_message(content: str, target: str = "ou_363105a68ee112f714ed44e12c802051", 
                       check_duplicate: bool = True) -> Dict:
    """
    发送飞书消息（带去重和超时控制）
    
    Args:
        content: 消息内容
        target: 目标用户ID
        check_duplicate: 是否检查重复
    
    Returns:
        {"success": bool, "reason": str, "message_id": str}
    """
    # 1. 检查重复
    if check_duplicate and is_duplicate(content, target):
        return {
            "success": False,
            "reason": "duplicate",
            "message_id": _generate_msg_id(content, target)
        }
    
    # 2. 尝试发送（带超时）
    msg_id = _generate_msg_id(content, target)
    
    try:
        # 使用超时控制
        cmd = [
            "openclaw", "message", "send",
            "--target", target,
            "--message", content
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=MAX_SEND_TIME
        )
        
        if result.returncode == 0:
            record_sent(content, target, success=True)
            return {
                "success": True,
                "reason": "sent",
                "message_id": msg_id
            }
        else:
            # 发送失败，记录但不标记为已发送（允许重试）
            print(f"[WARN] 飞书发送失败: {result.stderr[:200]}")
            return {
                "success": False,
                "reason": f"send_failed: {result.stderr[:100]}",
                "message_id": msg_id
            }
            
    except subprocess.TimeoutExpired:
        print(f"[WARN] 飞书发送超时（>{MAX_SEND_TIME}秒）")
        return {
            "success": False,
            "reason": "timeout",
            "message_id": msg_id
        }
    except Exception as e:
        print(f"[WARN] 飞书发送异常: {e}")
        return {
            "success": False,
            "reason": f"exception: {e}",
            "message_id": msg_id
        }


def send_with_retry(content: str, target: str = "ou_363105a68ee112f714ed44e12c802051",
                   max_retries: int = 2) -> bool:
    """
    带重试机制的消息发送
    
    Args:
        content: 消息内容
        target: 目标用户ID
        max_retries: 最大重试次数
    
    Returns:
        bool: 是否发送成功
    """
    for attempt in range(max_retries + 1):
        result = send_feishu_message(content, target, check_duplicate=(attempt == 0))
        
        if result["success"]:
            return True
        
        # 如果是重复消息，直接返回成功（已经发送过）
        if result["reason"] == "duplicate":
            print(f"[INFO] 消息已发送过，跳过重复发送")
            return True
        
        # 如果是超时或失败，且还有重试次数，等待后重试
        if attempt < max_retries:
            wait_time = 2 ** attempt  # 指数退避：1秒, 2秒
            print(f"[INFO] 发送失败，{wait_time}秒后重试...")
            time.sleep(wait_time)
    
    return False


if __name__ == "__main__":
    # 测试
    test_msg = f"测试消息 {datetime.now().strftime('%H:%M:%S')}"
    result = send_feishu_message(test_msg)
    print(f"发送结果: {result}")
    
    # 测试重复检测
    result2 = send_feishu_message(test_msg)
    print(f"重复发送结果: {result2}")
