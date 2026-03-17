#!/usr/bin/env python3
"""
验证凌晨5:00可靠任务执行情况
由Linux Cron在7:30调用，不依赖OpenClaw
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

def verify_morning_task():
    """验证任务执行情况"""
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    
    checks = []
    all_passed = True
    
    # 检查1: 日志文件存在且时间正确
    log_file = Path("/tmp/morning_reliable.log")
    if log_file.exists():
        content = log_file.read_text()
        if "SUCCESS" in content and today in content:
            checks.append(("✅", "日志文件", "存在且标记成功"))
        else:
            checks.append(("⚠️", "日志文件", "存在但状态异常"))
            all_passed = False
    else:
        checks.append(("❌", "日志文件", "不存在"))
        all_passed = False
    
    # 检查2: 队列文件存在
    queue_file = Path("/tmp/ai_analysis_queue.json")
    if queue_file.exists():
        try:
            queue = json.loads(queue_file.read_text())
            if queue.get('status') == 'files_created':
                checks.append(("✅", "队列文件", f"已创建 {queue.get('files_created', 0)} 个文件"))
            else:
                checks.append(("⚠️", "队列文件", "状态异常"))
                all_passed = False
        except:
            checks.append(("⚠️", "队列文件", "格式错误"))
            all_passed = False
    else:
        checks.append(("⚠️", "队列文件", "不存在（可能无新对话）"))
    
    # 检查3: 标记文件时间
    marker = Path("/root/.openclaw/workspace/.learnings/last_morning_task.txt")
    if marker.exists():
        marker_time = marker.read_text().strip()
        if today in marker_time:
            checks.append(("✅", "标记文件", "今日已更新"))
        else:
            checks.append(("⚠️", "标记文件", f"不是今日 ({marker_time})"))
            all_passed = False
    else:
        checks.append(("❌", "标记文件", "不存在"))
        all_passed = False
    
    # 检查4: 生成的对话文件
    conv_dir = Path("/root/.openclaw/workspace/obsidian-vault/02-Conversations")
    if conv_dir.exists():
        today_files = list(conv_dir.glob(f"{yesterday}_*.md"))
        if today_files:
            checks.append(("✅", "对话文件", f"找到 {len(today_files)} 个文件"))
        else:
            checks.append(("⚠️", "对话文件", f"未找到 {yesterday} 的文件"))
    else:
        checks.append(("⚠️", "对话目录", "不存在"))
    
    # 输出报告
    print(f"=== 凌晨5:00任务验证 [{datetime.now().strftime('%Y-%m-%d %H:%M')}] ===")
    print()
    for status, name, detail in checks:
        print(f"{status} {name}: {detail}")
    
    print()
    if all_passed:
        print("✅ 所有检查通过，任务执行正常")
        return 0
    else:
        print("⚠️ 部分检查未通过，可能需要关注")
        return 1

if __name__ == "__main__":
    sys.exit(verify_morning_task())
