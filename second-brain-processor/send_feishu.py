#!/usr/bin/env python3
"""
统一飞书消息发送入口

所有飞书消息必须通过此脚本发送，确保全局防重发

用法:
  python3 send_feishu.py "消息内容" [msg_type]

示例:
  python3 send_feishu.py "每日报告内容" daily_report
  python3 send_feishu.py "待处理链接提醒" pending_links
"""

import sys
import os

# 添加路径
WORKSPACE = "/root/.openclaw/workspace"
sys.path.insert(0, f"{WORKSPACE}/second-brain-processor")

from feishu_guardian import send_feishu_safe

# 默认目标用户
DEFAULT_TARGET = "ou_363105a68ee112f714ed44e12c802051"


def main():
    if len(sys.argv) < 2:
        print("用法: python3 send_feishu.py '消息内容' [msg_type]")
        print("  msg_type: daily_report, pending_links, morning_process, test")
        sys.exit(1)
    
    content = sys.argv[1]
    msg_type = sys.argv[2] if len(sys.argv) > 2 else "default"
    target = DEFAULT_TARGET
    
    print(f"[INFO] 发送消息 (类型: {msg_type})")
    print(f"[INFO] 内容预览: {content[:50]}...")
    
    result = send_feishu_safe(content, target=target, msg_type=msg_type, max_retries=1)
    
    if result["success"]:
        print(f"[SUCCESS] 消息已发送")
        print(f"[INFO] 指纹: {result.get('fingerprint', 'N/A')}")
    else:
        print(f"[FAILED] {result['message']}")
    
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
