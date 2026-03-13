#!/usr/bin/env python3
"""
美术馆展览推送触发器
由定时任务调用，通知主会话执行实际搜索
"""
import subprocess
import sys
from datetime import datetime

def main():
    """发送触发消息到主会话"""
    message = "【定时任务触发】执行美术馆展览推送"
    
    try:
        result = subprocess.run(
            ['openclaw', 'message', 'send',
             '--target', 'ou_363105a68ee112f714ed44e12c802051',
             '--message', message],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"[{datetime.now()}] 触发消息已发送")
            return 0
        else:
            print(f"[{datetime.now()}] 触发失败: {result.stderr}")
            return 1
    except Exception as e:
        print(f"[{datetime.now()}] 异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
