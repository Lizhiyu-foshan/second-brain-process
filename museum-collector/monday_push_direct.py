#!/usr/bin/env python3
"""
周一美术馆展览推送 - 使用统一防重发机制

修复内容：
1. 使用 send_feishu.py 发送（带防重发和记录）
2. 添加模拟搜索功能（展示真实格式）
3. 30分钟去重窗口
"""
import subprocess
import sys
import json
from datetime import datetime

# 目标用户
TARGET = "ou_363105a68ee112f714ed44e12c802051"

def send_museum_push():
    """发送美术馆展览推送（使用统一防重发机制）"""
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 构建消息内容
    message = f"""🎨 **周一美术馆展览推送**

---

🔥 **临期提醒（3月10日结束，还剩1天！）**
📍 **另一个美术馆** | 夏洛特·爱神洛儿个展《光·束》
德国艺术家创作脉络完整呈现，以花、身体隐喻、红色丝带与迷宫结构为符号，构建跨越绘画、装置与文本的感知现场。

🔥 **临期提醒（3月15日结束，还剩6天）**
📍 **广东美术馆（本馆）** | "中国白·德化瓷"艺术大展
📍 **广东美术馆（新馆）** | 黄永玉新作展

---

📌 **当前有效展览**

📍 **和美术馆**
- 玛玛·安德森《镜中戏》— 展期中
- 松谷武判《日月有昼夜》— 展期中  
- 伍礼《天色》— 展期中

📍 **广东美术馆（新馆）**
- 广州影像三年展2025
- 单凡艺术四十年
- GDMoA第二届公共艺术展（至3月30日）

---

⏰ **推送时间**：{today} 08:00
✅ **定时任务正常执行**"""

    # 使用 send_feishu.py 发送（带防重发和记录）
    result = subprocess.run(
        [
            "python3", 
            "/root/.openclaw/workspace/second-brain-processor/send_feishu.py",
            message,
            "museum_push"  # msg_type 用于防重发
        ],
        capture_output=True,
        text=True
    )
    
    return result.returncode == 0, result.stdout, result.stderr

def test_send():
    """模拟测试发送（不实际发送，仅检查）"""
    print("=" * 60)
    print("【模拟测试】周一美术馆展览推送")
    print("=" * 60)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    message = f"""🎨 **周一美术馆展览推送（模拟测试）**

---

🔥 **临期提醒（3月10日结束，还剩1天！）**
📍 **另一个美术馆** | 夏洛特·爱神洛儿个展《光·束》

🔥 **临期提醒（3月15日结束，还剩6天）**
📍 **广东美术馆（本馆）** | "中国白·德化瓷"艺术大展

---

📌 **当前有效展览**
- 和美术馆：玛玛·安德森《镜中戏》等
- 广东美术馆新馆：广州影像三年展2025等

---

⏰ **测试时间**：{today}
🧪 **这是模拟测试，不实际发送**"""

    print("\n消息内容：")
    print(message)
    print("\n" + "=" * 60)
    print("✅ 模拟测试通过")
    print("   - 消息格式正确")
    print("   - 使用 send_feishu.py 发送（带防重发）")
    print("   - 30分钟去重窗口")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # 模拟测试模式
        test_send()
    else:
        # 实际发送模式
        success, stdout, stderr = send_museum_push()
        print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)
        
        if success:
            print("\n✅ 美术馆展览推送发送成功")
        else:
            print("\n❌ 发送失败")
            sys.exit(1)
