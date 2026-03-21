#!/usr/bin/env python3
"""
定时任务发送链路验证器
按照 AGENTS.md 规则7：主动发送任务必须验证发送链路
"""

import subprocess
import sys
from datetime import datetime

def verify_send_link():
    """验证飞书发送链路是否正常"""
    
    print(f"[{datetime.now()}] 开始验证发送链路...")
    
    # 测试消息
    test_msg = "🔗 发送链路测试 - 验证飞书通道正常"
    
    try:
        # 尝试发送测试消息
        cmd = [
            "openclaw", "message", "send",
            "--channel", "feishu",
            "--target", "ou_363105a68ee112f714ed44e12c802051",
            "--message", test_msg
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            print(f"[{datetime.now()}] ✅ 发送链路正常")
            return True
        else:
            error = result.stderr[:300] if result.stderr else "未知错误"
            print(f"[{datetime.now()}] ❌ 发送链路异常: {error}")
            
            # 记录到错误日志
            with open("/root/.openclaw/workspace/.learnings/CRON_FAILURES.md", "a") as f:
                f.write(f"\n## [{datetime.now().isoformat()}] 发送链路中断\n")
                f.write(f"**任务**: 飞书发送链路验证\n")
                f.write(f"**错误**: {error}\n")
                f.write(f"**建议**: 检查 openclaw 飞书插件配置\n\n")
            
            return False
            
    except Exception as e:
        print(f"[{datetime.now()}] ❌ 验证过程出错: {e}")
        return False

def main():
    if "--dry-run" in sys.argv:
        print("[DRY-RUN] 模拟验证模式")
        return True
    
    success = verify_send_link()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
