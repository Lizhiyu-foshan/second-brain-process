#!/usr/bin/env python3
"""
资源守护模块 - 系统级防护
由动态上下文压缩守护调用，每小时检查一次
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SESSIONS_DIR = Path("/root/.openclaw/agents/main/sessions")
THRESHOLDS = {
    "warning": {"files": 200, "size_mb": 50},
    "critical": {"files": 400, "size_mb": 100}
}

def check_resources():
    """检查资源使用情况"""
    if not SESSIONS_DIR.exists():
        return {"status": "ok", "message": "目录不存在"}
    
    try:
        # 统计文件
        files = list(SESSIONS_DIR.glob("*.jsonl"))
        file_count = len(files)
        
        # 计算总大小
        total_size = sum(f.stat().st_size for f in files if f.exists())
        size_mb = total_size / (1024 * 1024)
        
        # 判断状态
        if file_count > THRESHOLDS["critical"]["files"] or size_mb > THRESHOLDS["critical"]["size_mb"]:
            status = "critical"
        elif file_count > THRESHOLDS["warning"]["files"] or size_mb > THRESHOLDS["warning"]["size_mb"]:
            status = "warning"
        else:
            status = "ok"
        
        return {
            "status": status,
            "file_count": file_count,
            "size_mb": round(size_mb, 1),
            "message": f"{file_count}个文件, {size_mb:.1f}MB"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

def take_action(result: dict):
    """根据状态采取行动"""
    status = result["status"]
    
    if status == "critical":
        print(f"🚨 [CRITICAL] 会话目录危险: {result['message']}")
        print("   触发紧急清理...")
        
        # 直接调用紧急清理
        cleanup_script = Path(__file__).parent.parent / "cleanup_v2.sh"
        try:
            subprocess.run(
                ["bash", str(cleanup_script)],
                timeout=60,
                check=True
            )
            print("   ✅ 紧急清理已执行")
        except Exception as e:
            print(f"   ❌ 紧急清理失败: {e}")
        
        return True  # 需要通知
        
    elif status == "warning":
        print(f"⚠️ [WARNING] 会话目录增长: {result['message']}")
        print("   下次定时清理时应该会处理")
        return False  # 不紧急，不需要通知
        
    else:
        print(f"✅ 会话目录正常: {result['message']}")
        return False

if __name__ == "__main__":
    result = check_resources()
    need_notify = take_action(result)
    
    # 只有critical状态才返回非0，触发告警
    sys.exit(2 if result["status"] == "critical" else 0)
