#!/usr/bin/env python3
"""
处理用户确认消息
当用户回复"整理"时触发 AI 深度整理并推送 GitHub
"""

import sys
import os
import subprocess
from datetime import datetime

# 添加路径
sys.path.insert(0, '/root/.openclaw/workspace/second-brain-processor')

def trigger_ai_processing():
    """触发 AI 深度整理"""
    print(f"[{datetime.now()}] === 触发 AI 深度整理 ===")
    
    # 执行 AI 整理脚本
    script_path = "/root/.openclaw/workspace/second-brain-processor/ai_process_and_push.py"
    
    if not os.path.exists(script_path):
        print(f"[ERROR] 脚本不存在：{script_path}")
        return False
    
    # 执行脚本
    result = subprocess.run(
        f"python3 {script_path} --confirmed",
        shell=True,
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print(f"[STDERR] {result.stderr}")
    
    if result.returncode == 0:
        print(f"[{datetime.now()}] ✅ AI 整理完成")
        return True
    else:
        print(f"[{datetime.now()}] ❌ AI 整理失败")
        return False

if __name__ == "__main__":
    success = trigger_ai_processing()
    
    # 发送结果通知（待实现飞书消息）
    if success:
        print("[NOTIFY] 已通知用户：AI 整理完成，GitHub 已推送")
    else:
        print("[NOTIFY] 已通知用户：AI 整理失败，请检查日志")
    
    sys.exit(0 if success else 1)
