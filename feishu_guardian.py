#!/usr/bin/env python3
"""
飞书消息防重发守护进程 - 彻底解决延迟补发问题

核心机制：
1. 全局消息ID追踪 - 所有消息必须经过此模块
2. 严格时间窗口 - 30分钟内完全相同的消息拒绝发送
3. 预发送检查 - 发送前再次确认是否重复
4. 执行日志 - 记录每次发送的完整上下文
"""

import json
import hashlib
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess

WORKSPACE = Path("/root/.openclaw/workspace")
LEARNINGS_DIR = WORKSPACE / ".learnings"
DUPLICATE_LOG = LEARNINGS_DIR / "duplicate_prevention_log.json"
SEND_RECORDS = LEARNINGS_DIR / "send_records.json"

# 严格去重窗口 - 8小时（覆盖完整工作日周期）
DEDUP_WINDOW_MINUTES = 480
# 发送冷却时间 - 同类型消息间隔至少10分钟
COOLDOWN_SECONDS = 600

_lock = threading.Lock()


def _generate_fingerprint(content: str, msg_type: str = "default") -> str:
    """
    生成消息指纹 - 用于去重
    基于内容前200字符 + 消息类型
    """
    normalized = content[:200].strip().lower().replace(" ", "").replace("\n", "")
    return hashlib.md5(f"{msg_type}:{normalized}".encode()).hexdigest()[:16]


def _load_records() -> Dict:
    """加载发送记录"""
    if SEND_RECORDS.exists():
        try:
            with open(SEND_RECORDS, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "records": [],
        "last_cleanup": datetime.now().isoformat()
    }


def _save_records(records: Dict):
    """保存发送记录"""
    try:
        LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
        temp = SEND_RECORDS.with_suffix('.tmp')
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        temp.replace(SEND_RECORDS)
    except Exception as e:
        print(f"[WARN] 保存记录失败: {e}")


def _cleanup_old_records(records: Dict):
    """清理过期记录（只保留最近1小时的）"""
    try:
        cutoff = datetime.now() - timedelta(minutes=DEDUP_WINDOW_MINUTES + 30)
        original_count = len(records.get("records", []))
        records["records"] = [
            r for r in records.get("records", [])
            if datetime.fromisoformat(r.get("time", "2000-01-01")) > cutoff
        ]
        records["last_cleanup"] = datetime.now().isoformat()
        
        cleaned = original_count - len(records["records"])
        if cleaned > 0:
            print(f"[INFO] 清理了 {cleaned} 条过期记录")
    except Exception as e:
        print(f"[WARN] 清理记录失败: {e}")


def check_duplicate(content: str, msg_type: str = "default") -> Tuple[bool, str]:
    """
    检查是否是重复消息
    
    Returns:
        (is_duplicate, reason)
    """
    with _lock:
        records = _load_records()
        _cleanup_old_records(records)
        
        fingerprint = _generate_fingerprint(content, msg_type)
        now = datetime.now()
        
        # 检查最近的发送记录
        for record in records.get("records", []):
            if record.get("fingerprint") == fingerprint:
                record_time = datetime.fromisoformat(record.get("time"))
                elapsed = (now - record_time).total_seconds()
                
                # 严格检查 - 30分钟内完全重复
                if elapsed < DEDUP_WINDOW_MINUTES * 60:
                    return True, f"DUPLICATE: 该消息在 {elapsed:.0f} 秒前已发送"
                
                # 检查冷却时间 - 同类型消息间隔
                if msg_type != "default" and elapsed < COOLDOWN_SECONDS:
                    return True, f"COOLDOWN: 同类型消息需要间隔 {COOLDOWN_SECONDS} 秒"
        
        return False, "OK"


def check_duplicate_by_date(msg_type: str, date_str: str) -> bool:
    """
    检查特定日期是否已经发送过某类型消息
    用于复盘报告等按日去重的场景
    """
    with _lock:
        records = _load_records()
        
        for record in records.get("records", []):
            if record.get("type") == msg_type:
                record_time = record.get("time", "")
                # 检查是否是指定日期
                if date_str in record_time:
                    return True
        
        return False


def record_send(content: str, msg_type: str = "default", target: str = "", 
                success: bool = True, error: str = ""):
    """记录发送"""
    with _lock:
        records = _load_records()
        
        records["records"].append({
            "fingerprint": _generate_fingerprint(content, msg_type),
            "time": datetime.now().isoformat(),
            "type": msg_type,
            "target": target,
            "success": success,
            "error": error,
            "content_preview": content[:100].replace("\n", " ")
        })
        
        # 限制记录数量
        if len(records["records"]) > 200:
            records["records"] = records["records"][-200:]
        
        _save_records(records)


def send_feishu_safe(content: str, target: str = "ou_363105a68ee112f714ed44e12c802051",
                     msg_type: str = "default", max_retries: int = 1) -> Dict:
    """
    安全发送飞书消息 - 严格防重复
    
    Args:
        content: 消息内容
        target: 目标用户
        msg_type: 消息类型（用于冷却控制）
        max_retries: 最大重试次数
    
    Returns:
        {"success": bool, "message": str, "fingerprint": str}
    """
    # 1. 严格预检查
    is_dup, reason = check_duplicate(content, msg_type)
    fingerprint = _generate_fingerprint(content, msg_type)
    
    if is_dup:
        print(f"[BLOCKED] {reason}")
        return {
            "success": False,
            "message": reason,
            "fingerprint": fingerprint
        }
    
    # 2. 尝试发送
    for attempt in range(max_retries + 1):
        try:
            # 再次检查（发送前最后确认）
            is_dup, _ = check_duplicate(content, msg_type)
            if is_dup:
                return {
                    "success": False,
                    "message": "RACE_CONDITION: 发送前检测到重复",
                    "fingerprint": fingerprint
                }
            
            # 执行发送
            cmd = [
                "openclaw", "message", "send",
                "--target", target,
                "--message", content
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15  # 15秒超时
            )
            
            if result.returncode == 0:
                record_send(content, msg_type, target, success=True)
                return {
                    "success": True,
                    "message": "sent",
                    "fingerprint": fingerprint
                }
            else:
                error = result.stderr[:200]
                if attempt < max_retries:
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                
                record_send(content, msg_type, target, success=False, error=error)
                return {
                    "success": False,
                    "message": f"send_failed: {error}",
                    "fingerprint": fingerprint
                }
                
        except subprocess.TimeoutExpired:
            error = "timeout"
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            
            record_send(content, msg_type, target, success=False, error=error)
            return {
                "success": False,
                "message": "timeout_after_retries",
                "fingerprint": fingerprint
            }
            
        except Exception as e:
            error = str(e)
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            
            record_send(content, msg_type, target, success=False, error=error)
            return {
                "success": False,
                "message": f"exception: {error}",
                "fingerprint": fingerprint
            }


def get_send_stats() -> Dict:
    """获取发送统计"""
    records = _load_records()
    
    total = len(records.get("records", []))
    success = sum(1 for r in records.get("records", []) if r.get("success"))
    failed = total - success
    
    # 最近30分钟的重复拦截
    cutoff = datetime.now() - timedelta(minutes=30)
    recent = [r for r in records.get("records", []) 
              if datetime.fromisoformat(r.get("time")) > cutoff]
    
    return {
        "total_records": total,
        "success": success,
        "failed": failed,
        "recent_30min": len(recent),
        "last_cleanup": records.get("last_cleanup")
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        stats = get_send_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        # 测试
        test_msg = f"测试消息 {datetime.now().strftime('%H:%M:%S')}"
        result = send_feishu_safe(test_msg, msg_type="test")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 测试重复检测
        result2 = send_feishu_safe(test_msg, msg_type="test")
        print(f"重复检测: {result2}")
