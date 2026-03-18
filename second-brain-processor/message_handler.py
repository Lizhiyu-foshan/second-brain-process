#!/usr/bin/env python3
"""
消息处理器
响应飞书消息中的关键词（如"整理"）
"""

import sys
import os
import subprocess
from datetime import datetime

# 添加路径
sys.path.insert(0, '/root/.openclaw/workspace/second-brain-processor')

def handle_confirm_message(message_text: str, sender_id: str = None):
    """处理确认消息"""
    
    # 检查是否包含确认关键词
    confirm_keywords = ["整理", "开始整理", "AI 处理", "开始"]
    
    if not any(keyword in message_text for keyword in confirm_keywords):
        print(f"[INFO] 非确认消息：{message_text}")
        return False
    
    print(f"[{datetime.now()}] === 检测到用户确认 ===")
    print(f"消息内容：{message_text}")
    print(f"发送者：{sender_id or 'unknown'}")
    
    # 执行 AI 整理
    script_path = "/root/.openclaw/workspace/second-brain-processor/handle_user_confirm.py"
    
    if not os.path.exists(script_path):
        print(f"[ERROR] 脚本不存在：{script_path}")
        return False
    
    # 执行脚本
    result = subprocess.run(
        f"python3 {script_path}",
        shell=True,
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print(f"[STDERR] {result.stderr}")
    
    if result.returncode == 0:
        print(f"[{datetime.now()}] ✅ AI 整理完成")
        # TODO: 发送完成通知到飞书
        return True
    else:
        print(f"[{datetime.now()}] ❌ AI 整理失败")
        # TODO: 发送失败通知到飞书
        return False

if __name__ == "__main__":
    # 从命令行参数获取消息内容
    if len(sys.argv) < 2:
        print("用法：python3 message_handler.py <消息内容> [发送者 ID]")
        sys.exit(1)
    
    message_text = sys.argv[1]
    sender_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = handle_confirm_message(message_text, sender_id)
    sys.exit(0 if success else 1)
