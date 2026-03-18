#!/usr/bin/env python3
"""
每日自动验证脚本 - daily_verification.py
每日 07:30 执行，验证凌晨5:00任务是否正常完成
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
HISTORY_FILE = WORKSPACE / ".learnings" / "morning_task_history.json"
ALERT_THRESHOLD = 2  # 连续失败2次告警

def load_history() -> list:
    """加载历史记录"""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []

def save_history(history: list):
    """保存历史记录"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history[-30:], f, indent=2)  # 保留最近30天

def calculate_success_rate(history: list, days: int = 7) -> float:
    """计算成功率"""
    recent = [h for h in history if h['date'] >= (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')]
    if not recent:
        return 0.0
    passed = sum(1 for h in recent if h['passed'])
    return passed / len(recent) * 100

def send_daily_report(history: list, today_result: dict):
    """发送每日报告"""
    success_rate_7d = calculate_success_rate(history, 7)
    success_rate_30d = calculate_success_rate(history, 30)
    
    # 统计连续失败
    consecutive_failures = 0
    for h in reversed(history):
        if not h['passed']:
            consecutive_failures += 1
        else:
            break
    
    report = f"""📊 凌晨5:00任务 - 每日验证报告

📅 检查日期: {datetime.now().strftime('%Y-%m-%d')}
✅ 今日状态: {'通过' if today_result['passed'] else '失败'}

📈 成功率统计:
   • 近7天: {success_rate_7d:.1f}%
   • 近30天: {success_rate_30d:.1f}%

🔔 连续失败: {consecutive_failures} 天

{"⚠️ 告警: 连续失败超过阈值！" if consecutive_failures >= ALERT_THRESHOLD else ""}
"""
    
    try:
        subprocess.run(
            ["openclaw", "message", "send",
             "--target", "ou_363105a68ee112f714ed44e12c802051",
             "--content", report],
            capture_output=True, timeout=10
        )
    except Exception as e:
        print(f"报告发送失败: {e}")

def main():
    """主函数"""
    print("=" * 50)
    print("每日自动验证 - 凌晨5:00任务")
    print("=" * 50)
    
    # 加载历史
    history = load_history()
    
    # 运行验证
    result = subprocess.run(
        [sys.executable, str(WORKSPACE / "scripts" / "morning_task_post_verify.py")],
        capture_output=True, text=True
    )
    
    today_result = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "passed": result.returncode == 0,
        "timestamp": datetime.now().isoformat()
    }
    
    # 更新历史
    history.append(today_result)
    save_history(history)
    
    # 发送报告
    send_daily_report(history, today_result)
    
    print(f"今日验证: {'通过' if today_result['passed'] else '失败'}")
    print(f"历史记录已更新: {HISTORY_FILE}")

if __name__ == "__main__":
    main()
