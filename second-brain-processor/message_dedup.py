#!/usr/bin/env python3
"""
消息去重系统 - Message Deduplication System

防止消息重复发送的核心机制：
1. 生成消息内容指纹
2. 检查指纹是否已存在
3. 保存新指纹到持久化存储

使用场景：
- 定时任务发送前检查
- 任何可能重复触发的消息发送

Author: Kimi Claw
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# 存储路径
WORKSPACE = Path("/root/.openclaw/workspace")
FINGERPRINT_FILE = WORKSPACE / ".learnings" / "message_fingerprints.json"

# 去重窗口（小时）
DEDUP_WINDOW_HOURS = 24


def _load_fingerprints() -> dict:
    """加载已存在的指纹记录"""
    if FINGERPRINT_FILE.exists():
        try:
            with open(FINGERPRINT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_fingerprints(fingerprints: dict):
    """保存指纹记录"""
    try:
        FINGERPRINT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(FINGERPRINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(fingerprints, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] 保存指纹失败: {e}")


def _generate_fingerprint(content: str) -> str:
    """生成消息内容指纹"""
    # 标准化内容：去除空白、转小写
    normalized = content.strip().lower()
    # 生成MD5指纹
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


def _cleanup_old_fingerprints(fingerprints: dict) -> dict:
    """清理过期的指纹记录"""
    cutoff = (datetime.now() - timedelta(hours=DEDUP_WINDOW_HOURS)).isoformat()
    return {k: v for k, v in fingerprints.items() if v.get('timestamp', '') > cutoff}


def is_message_sent(content: str) -> bool:
    """
    检查消息是否已经发送过（24小时内）
    
    Returns:
        True - 消息已发送过（应跳过）
        False - 消息未发送过（可以发送）
    """
    fingerprints = _load_fingerprints()
    fingerprint = _generate_fingerprint(content)
    
    if fingerprint in fingerprints:
        # 检查是否在去重窗口内
        timestamp = fingerprints[fingerprint].get('timestamp', '')
        cutoff = (datetime.now() - timedelta(hours=DEDUP_WINDOW_HOURS)).isoformat()
        if timestamp > cutoff:
            return True
    
    return False


def record_message_sent(content: str, message_id: Optional[str] = None):
    """
    记录消息已发送
    
    必须在消息发送成功后立即调用！
    """
    fingerprints = _load_fingerprints()
    
    # 清理过期记录
    fingerprints = _cleanup_old_fingerprints(fingerprints)
    
    # 添加新指纹
    fingerprint = _generate_fingerprint(content)
    fingerprints[fingerprint] = {
        'timestamp': datetime.now().isoformat(),
        'message_id': message_id,
        'preview': content[:100]  # 保存前100字符用于调试
    }
    
    _save_fingerprints(fingerprints)


def get_fingerprint_stats() -> dict:
    """获取指纹统计信息"""
    fingerprints = _load_fingerprints()
    return {
        'total': len(fingerprints),
        'window_hours': DEDUP_WINDOW_HOURS,
        'file_path': str(FINGERPRINT_FILE)
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        stats = get_fingerprint_stats()
        print(f"消息指纹统计：")
        print(f"  总记录数: {stats['total']}")
        print(f"  去重窗口: {stats['window_hours']}小时")
        print(f"  存储文件: {stats['file_path']}")
    else:
        print("消息去重系统已加载")
        print(f"使用方式：")
        print(f"  from message_dedup import is_message_sent, record_message_sent")
        print(f"  ")
        print(f"  # 发送前检查")
        print(f"  if is_message_sent(content):")
        print(f"      print('消息已发送过，跳过')")
        print(f"      return")
        print(f"  ")
        print(f"  # 发送消息...")
        print(f"  ")
        print(f"  # 发送成功后记录")
        print(f"  record_message_sent(content)")
