#!/usr/bin/env python3
"""
OpenClaw Version Checker
检查当前 OpenClaw 版本并检测更新
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 配置
VERSION_CACHE_FILE = Path("/root/.openclaw/workspace/.version_cache.json")
NOTIFICATION_FILE = Path("/root/.openclaw/workspace/.version_notifications.json")


def get_current_version():
    """获取当前 OpenClaw 版本"""
    try:
        result = subprocess.run(
            ["openclaw", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # 解析版本号，格式可能是 "openclaw version X.Y.Z"
            version_str = result.stdout.strip()
            for part in version_str.split():
                if part.count('.') == 2:  # 简单判断版本号格式
                    return part
            return version_str
    except Exception as e:
        print(f"Error getting version: {e}")
    return "unknown"


def get_latest_version():
    """获取最新版本（从 GitHub releases）"""
    try:
        result = subprocess.run(
            ["curl", "-s", "https://api.github.com/repos/openclaw/openclaw/releases/latest"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("tag_name", "unknown").lstrip("v")
    except Exception as e:
        print(f"Error checking latest version: {e}")
    return None


def load_version_cache():
    """加载版本缓存"""
    if VERSION_CACHE_FILE.exists():
        with open(VERSION_CACHE_FILE, "r") as f:
            return json.load(f)
    return {"last_check": None, "current_version": None, "latest_version": None}


def save_version_cache(cache):
    """保存版本缓存"""
    cache["last_check"] = datetime.now().isoformat()
    with open(VERSION_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def send_notification(message, level="info"):
    """发送通知（写入通知文件，等待主会话处理）"""
    notifications = []
    if NOTIFICATION_FILE.exists():
        with open(NOTIFICATION_FILE, "r") as f:
            notifications = json.load(f)
    
    notifications.append({
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message
    })
    
    with open(NOTIFICATION_FILE, "w") as f:
        json.dump(notifications, f, indent=2)
    
    print(f"[{level.upper()}] {message}")


def check_version_update():
    """检查版本更新"""
    print("=== OpenClaw Version Check ===")
    print(f"Time: {datetime.now().isoformat()}")
    
    # 获取版本
    current = get_current_version()
    print(f"Current version: {current}")
    
    latest = get_latest_version()
    if latest:
        print(f"Latest version: {latest}")
    else:
        print("Warning: Could not fetch latest version")
    
    # 加载缓存
    cache = load_version_cache()
    previous = cache.get("current_version")
    
    # 检测版本变化
    if previous and previous != current:
        send_notification(
            f"OpenClaw 版本已更新: {previous} → {current}",
            level="warning"
        )
    
    # 检测可用更新
    if latest and latest != current:
        send_notification(
            f"发现新版本: {latest} (当前: {current})",
            level="info"
        )
    
    # 更新缓存
    cache["current_version"] = current
    cache["latest_version"] = latest
    save_version_cache(cache)
    
    print("\n=== Check Complete ===")
    
    return {
        "current": current,
        "latest": latest,
        "update_available": latest and latest != current
    }


if __name__ == "__main__":
    result = check_version_update()
    sys.exit(0 if result else 1)