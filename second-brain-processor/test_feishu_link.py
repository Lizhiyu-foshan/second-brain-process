#!/usr/bin/env python3
"""
飞书链路端对端测试脚本
验证重启后飞书插件配置是否正常
"""

import subprocess
import sys
from datetime import datetime

def test_feishu_link():
    """执行端对端测试"""
    
    test_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"[{test_time}] 开始飞书链路端对端测试...")
    print("="*60)
    
    # 构建测试消息
    test_msg = f"""🧪 飞书链路端对端测试

⏰ 测试时间：{test_time}
🎯 测试目标：验证重启后飞书插件配置
✅ 测试内容：
  1. openclaw 命令调用正常
  2. 飞书插件配置无警告
  3. 消息成功送达用户

如果收到此消息，说明发送链路已恢复正常。
"""
    
    try:
        cmd = [
            "openclaw", "message", "send",
            "--channel", "feishu",
            "--target", "ou_363105a68ee112f714ed44e12c802051",
            "--message", test_msg
        ]
        
        print(f"执行命令: {' '.join(cmd[:6])}...")
        print("-"*60)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"返回码: {result.returncode}")
        
        if result.stdout:
            print(f"标准输出:\n{result.stdout}")
        
        if result.stderr:
            print(f"标准错误:\n{result.stderr[:500]}")
        
        if result.returncode == 0:
            print("="*60)
            print(f"[{datetime.now()}] ✅ 测试成功！飞书链路已恢复正常")
            print("消息已成功发送至飞书")
            return True
        else:
            print("="*60)
            print(f"[{datetime.now()}] ❌ 测试失败")
            print(f"错误: {result.stderr[:300]}")
            
            # 记录失败
            with open("/root/.openclaw/workspace/.learnings/SEND_LINK_FAILURES.md", "a") as f:
                f.write(f"\n## [{datetime.now().isoformat()}] 端对端测试失败\n")
                f.write(f"**任务**: 飞书链路测试-17:30\n")
                f.write(f"**错误**: {result.stderr[:300]}\n\n")
            
            return False
            
    except subprocess.TimeoutExpired:
        print("="*60)
        print(f"[{datetime.now()}] ❌ 测试超时（30秒）")
        return False
    except Exception as e:
        print("="*60)
        print(f"[{datetime.now()}] ❌ 测试异常: {e}")
        return False

def main():
    success = test_feishu_link()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
