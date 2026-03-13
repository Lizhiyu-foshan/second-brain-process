#!/usr/bin/env python3
"""
轻量级 Cron 监控 - 聚焦关键时间窗口
只在任务执行后的1小时内进行密集监控
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
VAULT_DIR = WORKSPACE / "obsidian-vault"
LOG_FILE = WORKSPACE / "cron-monitor" / "check.log"

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def get_job_last_run(job_id: str) -> dict:
    """获取任务最后一次运行状态"""
    try:
        result = subprocess.run(
            ["openclaw", "cron", "runs", job_id, "--limit", "1"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            entries = data.get("entries", [])
            if entries:
                return entries[0]
    except Exception as e:
        log(f"获取任务状态失败: {e}")
    return None

def should_check_now(schedule_hour: int, schedule_minute: int) -> bool:
    """检查当前是否在任务执行后的1小时窗口内"""
    now = datetime.now()
    scheduled_today = now.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)
    
    # 如果计划时间还没到，检查昨天的
    if scheduled_today > now:
        scheduled_today -= timedelta(days=1)
    
    time_diff = (now - scheduled_today).total_seconds() / 60  # 分钟
    return 0 <= time_diff <= 60  # 1小时内

def send_report_manually() -> bool:
    """手动补发复盘报告"""
    try:
        result = subprocess.run(
            ["python3", str(WORKSPACE / "second-brain-processor/daily_report.py")],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            log(f"报告生成失败: {result.stderr}")
            return False
        
        report = result.stdout.strip()
        if not report:
            log("报告为空，跳过发送")
            return True
        
        # 发送到飞书
        send_result = subprocess.run(
            ["openclaw", "message", "send",
             "--target", "ou_363105a68ee112f714ed44e12c802051",
             "--message", report],
            capture_output=True, text=True, timeout=30
        )
        
        if send_result.returncode == 0:
            log("报告补发成功")
            return True
        else:
            log(f"发送失败: {send_result.stderr}")
            return False
            
    except Exception as e:
        log(f"补发异常: {e}")
        return False

def send_alert(title: str, message: str):
    """发送告警"""
    try:
        full_msg = f"⚠️ {title}\n\n{message}\n\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(
            ["openclaw", "message", "send",
             "--target", "ou_363105a68ee112f714ed44e12c802051",
             "--message", full_msg],
            capture_output=True, text=True, timeout=30
        )
    except Exception as e:
        log(f"发送告警失败: {e}")

def check_daily_report_job():
    """检查每日复盘报告任务（8:30）"""
    if not should_check_now(8, 30):
        return  # 不在监控窗口
    
    log("检查每日复盘报告任务...")
    last_run = get_job_last_run("35ff007b-d995-4650-a90f-f3c973a386ca")
    
    if not last_run:
        log("无运行记录")
        return
    
    status = last_run.get("status")
    run_at_ms = last_run.get("runAtMs", 0)
    run_time = datetime.fromtimestamp(run_at_ms / 1000)
    
    # 检查是否是今天的运行
    today_830 = datetime.now().replace(hour=8, minute=30, second=0, microsecond=0)
    if run_time < today_830:
        log(f"最后一次运行是 {run_time.strftime('%Y-%m-%d %H:%M')}，今天尚未执行")
        return
    
    if status == "error":
        error_msg = last_run.get("error", "未知错误")
        log(f"任务失败: {error_msg}")
        
        # 自动补发
        log("尝试自动补发...")
        if send_report_manually():
            send_alert("复盘报告已自动补发", f"原任务失败原因: {error_msg}\n已自动补发今日报告。")
        else:
            send_alert("复盘报告补发失败", f"原任务失败: {error_msg}\n自动补发也失败，请手动处理。")
            
    elif status == "ok":
        log(f"任务正常完成，耗时 {last_run.get('durationMs', 0)/1000:.1f}s")

def main():
    log("="*40)
    log("开始监控检查")
    
    # 只检查每日复盘报告（8:30任务）
    check_daily_report_job()
    
    log("检查完成")

if __name__ == "__main__":
    main()
