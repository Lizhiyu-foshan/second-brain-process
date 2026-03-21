#!/usr/bin/env python3
"""
Feishu 消息接收去重器 - 命令行接口版本

用法:
  python3 feishu_receive_dedup_cli.py --check "消息内容" "发送者 ID"
  python3 feishu_receive_dedup_cli.py --record "消息内容" "发送者 ID"
"""

import sys
import os

# 导入主模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feishu_receive_dedup import is_message_received, record_message_received

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print(f"  {sys.argv[0]} --check \"消息内容\" \"发送者 ID\"")
        print(f"  {sys.argv[0]} --record \"消息内容\" \"发送者 ID\"")
        sys.exit(1)
    
    if sys.argv[1] == "--check" and len(sys.argv) >= 4:
        # 检查消息是否重复
        # 输出：DUPLICATE（重复）或 NEW（新消息）
        content = sys.argv[2]
        sender = sys.argv[3]
        result = is_message_received(content, sender)
        print('DUPLICATE' if result else 'NEW')
        sys.exit(0)
    
    elif sys.argv[1] == "--record" and len(sys.argv) >= 4:
        # 记录消息
        content = sys.argv[2]
        sender = sys.argv[3]
        record_message_received(content, sender)
        print(f"已记录：{sender}: {content[:50]}...")
        sys.exit(0)
    
    else:
        print("用法:")
        print(f"  {sys.argv[0]} --check \"消息内容\" \"发送者 ID\"")
        print(f"  {sys.argv[0]} --record \"消息内容\" \"发送者 ID\"")
        sys.exit(1)
