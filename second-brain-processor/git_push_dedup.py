#!/usr/bin/env python3
"""
Git推送回复去重机制

防止GitHub推送操作的重复回复：
- 推送成功/失败的回复在一定时间内去重
- 区分不同仓库和分支的推送
- 防止飞书重复触发导致的重复推送报告
"""

import json
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple
import threading

WORKSPACE = Path("/root/.openclaw/workspace")
LEARNINGS_DIR = WORKSPACE / ".learnings"
GIT_PUSH_RECORD_FILE = LEARNINGS_DIR / "git_push_replies.json"

# Git推送回复去重窗口 - 1小时（防止重复报告推送状态）
GIT_PUSH_DEDUP_WINDOW_MINUTES = 60

_lock = threading.Lock()


def _load_records() -> Dict:
    """加载Git推送记录"""
    if GIT_PUSH_RECORD_FILE.exists():
        try:
            with open(GIT_PUSH_RECORD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "pushes": [],  # 推送记录列表
        "last_cleanup": datetime.now().isoformat()
    }


def _save_records(data: Dict):
    """保存Git推送记录"""
    try:
        LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
        temp = GIT_PUSH_RECORD_FILE.with_suffix('.tmp')
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp.replace(GIT_PUSH_RECORD_FILE)
    except Exception as e:
        print(f"[WARN] 保存Git推送记录失败: {e}")


def _cleanup_old_records(data: Dict):
    """清理过期记录"""
    cutoff = datetime.now() - timedelta(minutes=GIT_PUSH_DEDUP_WINDOW_MINUTES)
    data["pushes"] = [
        r for r in data.get("pushes", [])
        if datetime.fromisoformat(r.get("time", "2000-01-01")) > cutoff
    ]
    data["last_cleanup"] = datetime.now().isoformat()


def is_git_push_related(content: str) -> Tuple[bool, Optional[str]]:
    """
    检查消息是否与Git推送相关
    
    Returns:
        (是否相关, 推送标识)
    """
    content_lower = content.lower()
    
    # Git推送相关关键词模式
    push_patterns = [
        r'推送到?\s*github',
        r'git\s*push',
        r'推送.*成功',
        r'推送.*失败',
        r'已?推送.*代码',
        r'github.*推送',
        r'提交到?\s*github',
        r'代码.*已?推送',
        r'同步到?\s*github',
        r'已?上传.*github',
    ]
    
    for pattern in push_patterns:
        if re.search(pattern, content_lower):
            # 提取仓库/分支信息作为标识
            repo_match = re.search(r'(?:仓库|repo|项目)[：:]?\s*(\S+)', content)
            branch_match = re.search(r'(?:分支|branch)[：:]?\s*(\S+)', content)
            
            repo = repo_match.group(1) if repo_match else "default"
            branch = branch_match.group(1) if branch_match else "main"
            
            push_id = f"{repo}:{branch}"
            return True, push_id
    
    return False, None


def generate_push_fingerprint(content: str, push_id: str) -> str:
    """生成推送指纹"""
    # 提取核心内容（去掉时间戳、随机ID等）
    core_content = re.sub(r'\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}', '', content)
    core_content = re.sub(r'om_[a-f0-9]+', '', core_content)
    core_content = re.sub(r'\s+', '', core_content)
    
    fingerprint_data = f"{push_id}:{core_content[:200]}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]


def should_reply_git_push(content: str, sender: str = "") -> Tuple[bool, str]:
    """
    检查是否应该回复Git推送相关消息
    
    Returns:
        (是否应该回复, 原因)
    """
    is_related, push_id = is_git_push_related(content)
    
    if not is_related:
        return True, "非Git推送消息"
    
    fingerprint = generate_push_fingerprint(content, push_id)
    
    with _lock:
        data = _load_records()
        
        # 检查是否已存在相同推送的回复
        cutoff = datetime.now() - timedelta(minutes=GIT_PUSH_DEDUP_WINDOW_MINUTES)
        
        for record in data.get("pushes", []):
            if record.get("fingerprint") == fingerprint:
                record_time = datetime.fromisoformat(record.get("time", "2000-01-01"))
                if record_time > cutoff:
                    elapsed = (datetime.now() - record_time).total_seconds() / 60
                    return False, f"Git推送消息已回复过（{elapsed:.0f}分钟前）"
        
        # 记录新的推送
        data["pushes"].append({
            "fingerprint": fingerprint,
            "push_id": push_id,
            "time": datetime.now().isoformat(),
            "sender": sender,
            "content_preview": content[:100]
        })
        
        # 清理旧记录
        _cleanup_old_records(data)
        
        # 保存
        _save_records(data)
        
        return True, "新的Git推送消息"


def record_git_push_reply(content: str, push_id: str = "default"):
    """
    显式记录Git推送回复（供外部调用）
    """
    fingerprint = generate_push_fingerprint(content, push_id)
    
    with _lock:
        data = _load_records()
        data["pushes"].append({
            "fingerprint": fingerprint,
            "push_id": push_id,
            "time": datetime.now().isoformat(),
            "sender": "",
            "content_preview": content[:100]
        })
        _cleanup_old_records(data)
        _save_records(data)


def get_git_push_stats() -> Dict:
    """获取Git推送去重统计"""
    data = _load_records()
    
    cutoff = datetime.now() - timedelta(minutes=GIT_PUSH_DEDUP_WINDOW_MINUTES)
    valid_records = [
        r for r in data.get("pushes", [])
        if datetime.fromisoformat(r.get("time", "2000-01-01")) > cutoff
    ]
    
    return {
        "window_minutes": GIT_PUSH_DEDUP_WINDOW_MINUTES,
        "total_pushes": len(valid_records),
        "unique_pushes": len(set(r.get("push_id") for r in valid_records)),
        "last_cleanup": data.get("last_cleanup", "从未")
    }


if __name__ == "__main__":
    # 测试
    print("=== Git推送去重测试 ===\n")
    
    test_cases = [
        ("已成功推送到GitHub仓库：my-project", "user1"),
        ("推送成功！代码已上传到GitHub", "user1"),  # 应该去重
        ("Git推送失败，请检查网络", "user2"),
        ("今天的天气怎么样？", "user3"),  # 非Git消息
        ("已成功推送到GitHub仓库：other-project", "user1"),  # 不同仓库
    ]
    
    for i, (content, sender) in enumerate(test_cases, 1):
        should_reply, reason = should_reply_git_push(content, sender)
        print(f"测试{i}: {'✓' if should_reply else '✗'} {content[:30]}...")
        print(f"       原因: {reason}\n")
    
    print("\n统计:")
    stats = get_git_push_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
