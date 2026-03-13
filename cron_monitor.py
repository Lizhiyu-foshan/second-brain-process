#!/usr/bin/env python3
"""
Cron Job 发送状态监控器
用于验证消息是否成功送达飞书
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 状态文件
STATE_FILE = Path("/root/.openclaw/workspace/cron-monitor-state.json")
LOG_FILE = Path("/root/.openclaw/workspace/cron-monitor.log")

def load_state():
    """加载监控状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        "jobs": {},
        "lastCheck": None,
        "alerts": []
    }

def save_state(state):
    """保存监控状态"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def log_event(message):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry)
    print(log_entry.strip())

def check_job_status(job_id, job_name, expected_send_time):
    """
    检查特定 job 的发送状态
    
    返回: {
        "status": "ok" | "pending" | "failed" | "unknown",
        "details": str,
        "needs_alert": bool
    }
    """
    state = load_state()
    job_state = state["jobs"].get(job_id, {})
    
    # 检查是否在预期时间后收到确认
    last_success = job_state.get("lastSuccess")
    last_attempt = job_state.get("lastAttempt")
    
    if last_success:
        last_success_dt = datetime.fromisoformat(last_success)
        if last_success_dt >= expected_send_time:
            return {
                "status": "ok",
                "details": f"上次成功: {last_success}",
                "needs_alert": False
            }
    
    # 检查是否已尝试但可能失败
    if last_attempt:
        last_attempt_dt = datetime.fromisoformat(last_attempt)
        if last_attempt_dt >= expected_send_time:
            # 已尝试但无成功记录，可能失败
            return {
                "status": "failed",
                "details": f"已尝试但未确认成功: {last_attempt}",
                "needs_alert": True
            }
    
    # 尚未尝试
    return {
        "status": "pending",
        "details": f"等待执行，预期时间: {expected_send_time}",
        "needs_alert": False
    }

def record_attempt(job_id, job_name):
    """记录发送尝试"""
    state = load_state()
    if job_id not in state["jobs"]:
        state["jobs"][job_id] = {}
    
    state["jobs"][job_id]["lastAttempt"] = datetime.now().isoformat()
    state["jobs"][job_id]["name"] = job_name
    save_state(state)
    log_event(f"[{job_name}] 记录发送尝试")

def record_success(job_id, job_name, message_preview=""):
    """记录发送成功"""
    state = load_state()
    if job_id not in state["jobs"]:
        state["jobs"][job_id] = {}
    
    state["jobs"][job_id]["lastSuccess"] = datetime.now().isoformat()
    state["jobs"][job_id]["name"] = job_name
    state["jobs"][job_id]["lastPreview"] = message_preview[:100]
    save_state(state)
    log_event(f"[{job_name}] 记录发送成功")

def generate_daily_report():
    """生成每日监控报告"""
    state = load_state()
    
    report_lines = [
        "📊 Cron Job 发送状态监控报告",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]
    
    jobs_config = [
        ("35ff007b-d995-4650-a90f-f3c973a386ca", "每日复盘报告", "08:30"),
        ("53918d8d-df68-49cc-bdf4-1fa6ca1c39ed", "每日待确认列表", "23:30"),
        ("d9031bf8-d243-4426-bdd2-94337f7f0f89", "每周美术馆推送(周一)", "周一 08:00"),
        ("f49caaa6-7b68-4d12-9a71-4549c01e9c14", "每周美术馆推送(周五)", "周五 20:00"),
    ]
    
    for job_id, name, schedule in jobs_config:
        job_state = state["jobs"].get(job_id, {})
        last_success = job_state.get("lastSuccess", "从未")
        last_attempt = job_state.get("lastAttempt", "从未")
        
        report_lines.extend([
            f"📌 {name}",
            f"   计划: {schedule}",
            f"   上次尝试: {last_attempt}",
            f"   上次成功: {last_success}",
            ""
        ])
    
    return "\n".join(report_lines)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Cron Job 监控器')
    parser.add_argument('--record-attempt', type=str, help='记录发送尝试 (job_id)')
    parser.add_argument('--record-success', type=str, help='记录发送成功 (job_id)')
    parser.add_argument('--job-name', type=str, help='Job 名称')
    parser.add_argument('--report', action='store_true', help='生成监控报告')
    
    args = parser.parse_args()
    
    if args.record_attempt and args.job_name:
        record_attempt(args.record_attempt, args.job_name)
    elif args.record_success and args.job_name:
        record_success(args.record_success, args.job_name)
    elif args.report:
        print(generate_daily_report())
    else:
        parser.print_help()
