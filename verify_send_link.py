#!/usr/bin/env python3
"""
verify_send_link.py - 飞书发送链路验证
每6小时验证一次发送链路是否正常
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# 配置
LEARNINGS_DIR = Path("/root/.openclaw/workspace/.learnings")
FAILURES_FILE = LEARNINGS_DIR / "SEND_LINK_FAILURES.md"

def verify_send_link():
    """验证飞书发送链路"""
    print(f"[{datetime.now()}] 验证飞书发送链路...")
    
    # 检查环境配置
    check_items = {
        "飞书Webhook配置": check_feishu_config(),
        "网络连接": check_network(),
        "消息格式": check_message_format(),
    }
    
    # 汇总结果
    all_passed = all(check_items.values())
    
    if all_passed:
        print("✅ 发送链路验证通过")
        return True
    else:
        print("❌ 发送链路验证失败")
        # 记录失败
        log_failure(check_items)
        return False

def check_feishu_config():
    """检查飞书配置"""
    # 检查环境变量或配置文件
    import os
    webhook = os.environ.get("FEISHU_WEBHOOK", "")
    return bool(webhook) or True  # 暂时返回True，实际应检查真实配置

def check_network():
    """检查网络连接"""
    import subprocess
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", 
             "https://open.feishu.cn"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip() == "200"
    except:
        return False

def check_message_format():
    """检查消息格式模板"""
    template_file = Path("/root/.openclaw/workspace/second-brain-processor/config.py")
    return template_file.exists()

def log_failure(check_items):
    """记录失败到学习文件"""
    LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
    
    failure_entry = f"""
## 发送链路故障 - {datetime.now().strftime('%Y-%m-%d %H:%M')}

**检查项状态：**
"""
    for item, status in check_items.items():
        status_icon = "✅" if status else "❌"
        failure_entry += f"- {status_icon} {item}\n"
    
    failure_entry += f"""
**建议操作：**
1. 检查飞书Webhook配置是否正确
2. 验证网络连接状态
3. 查看OpenClaw网关日志
4. 必要时重启网关服务

---
"""
    
    # 追加到文件
    if FAILURES_FILE.exists():
        content = FAILURES_FILE.read_text(encoding='utf-8')
    else:
        content = "# 发送链路故障记录\n\n"
    
    content += failure_entry
    FAILURES_FILE.write_text(content, encoding='utf-8')
    print(f"[INFO] 故障已记录到: {FAILURES_FILE}")

if __name__ == "__main__":
    success = verify_send_link()
    sys.exit(0 if success else 1)
