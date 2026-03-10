#!/usr/bin/env python3
"""
飞书消息问题诊断工具

用于分析延迟补发问题的根源
"""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
LEARNINGS_DIR = WORKSPACE / ".learnings"

def check_cron_status():
    """检查定时任务状态"""
    print("=" * 60)
    print("📋 定时任务状态检查")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            ["openclaw", "cron", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            jobs = json.loads(result.stdout)
            print(f"\n共有 {len(jobs.get('jobs', []))} 个定时任务:")
            
            for job in jobs.get("jobs", []):
                name = job.get("name", "未知")
                enabled = "✅" if job.get("enabled") else "❌"
                last_status = job.get("state", {}).get("lastStatus", "unknown")
                last_run = job.get("state", {}).get("lastRunAtMs")
                
                if last_run:
                    last_run_time = datetime.fromtimestamp(last_run / 1000)
                    time_ago = datetime.now() - last_run_time
                    time_str = f"{time_ago.total_seconds() / 3600:.1f}小时前"
                else:
                    time_str = "从未运行"
                
                print(f"  {enabled} {name}")
                print(f"     上次状态: {last_status}, 运行时间: {time_str}")
        else:
            print(f"  ❌ 获取定时任务失败: {result.stderr}")
    except Exception as e:
        print(f"  ❌ 检查失败: {e}")


def check_send_records():
    """检查消息发送记录"""
    print("\n" + "=" * 60)
    print("📨 消息发送记录检查")
    print("=" * 60)
    
    # 检查所有可能的记录文件
    record_files = [
        LEARNINGS_DIR / "send_records.json",
        LEARNINGS_DIR / "message_state.json",
    ]
    
    for record_file in record_files:
        if record_file.exists():
            try:
                with open(record_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"\n📁 {record_file.name}:")
                
                if "records" in data:
                    records = data["records"]
                    print(f"  记录总数: {len(records)}")
                    
                    # 最近1小时的记录
                    one_hour_ago = datetime.now() - timedelta(hours=1)
                    recent = [
                        r for r in records 
                        if datetime.fromisoformat(r.get("time", "2000-01-01")) > one_hour_ago
                    ]
                    print(f"  最近1小时: {len(recent)} 条")
                    
                    # 显示最近的5条
                    if recent:
                        print("  最近记录:")
                        for r in recent[-5:]:
                            time_str = datetime.fromisoformat(r.get("time")).strftime("%H:%M:%S")
                            status = "✅" if r.get("success") else "❌"
                            preview = r.get("content_preview", "")[:40]
                            print(f"    {status} {time_str} - {preview}...")
                
                elif "sent_messages" in data:
                    messages = data["sent_messages"]
                    print(f"  已发送消息: {len(messages)}")
                    
            except Exception as e:
                print(f"  ❌ 读取失败: {e}")
        else:
            print(f"\n📁 {record_file.name}: 不存在")


def check_task_locks():
    """检查任务锁状态"""
    print("\n" + "=" * 60)
    print("🔒 任务锁状态检查")
    print("=" * 60)
    
    lock_dir = LEARNINGS_DIR / "task_locks"
    
    if lock_dir.exists():
        locks = list(lock_dir.glob("*.lock"))
        print(f"\n锁文件数量: {len(locks)}")
        
        for lock in locks:
            print(f"  - {lock.name}")
    else:
        print("\n锁目录不存在（正常，任务未运行过）")
    
    # 检查执行器状态
    state_file = LEARNINGS_DIR / "task_executor_state.json"
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            print(f"\n📊 任务执行历史:")
            for task_name, history in state.get("task_history", {}).items():
                if history:
                    last = history[-1]
                    status = last.get("status", "unknown")
                    start = last.get("start_time", "")
                    print(f"  {task_name}: {status} ({start[:19]})")
        except Exception as e:
            print(f"  ❌ 读取失败: {e}")


def check_queue_status():
    """检查队列状态"""
    print("\n" + "=" * 60)
    print("📦 队列状态检查")
    print("=" * 60)
    
    processor_dir = WORKSPACE / "second-brain-processor"
    queue_dir = processor_dir / "queue"
    processed_dir = processor_dir / "processed"
    
    if queue_dir.exists():
        queue_files = list(queue_dir.glob("*"))
        print(f"\n待处理队列: {len(queue_files)} 项")
        for f in queue_files[:5]:  # 只显示前5个
            print(f"  - {f.name}")
        if len(queue_files) > 5:
            print(f"  ... 还有 {len(queue_files) - 5} 项")
    else:
        print("\n队列目录不存在")
    
    if processed_dir.exists():
        processed_files = list(processed_dir.glob("*"))
        print(f"\n已处理: {len(processed_files)} 项")
    else:
        print("\n已处理目录不存在")


def main():
    print("\n🔍 飞书消息问题诊断")
    print("=" * 60)
    print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    check_cron_status()
    check_send_records()
    check_task_locks()
    check_queue_status()
    
    print("\n" + "=" * 60)
    print("✅ 诊断完成")
    print("=" * 60)
    
    # 建议
    print("\n💡 建议:")
    print("  1. 如果发现重复发送记录，说明去重机制可能未生效")
    print("  2. 如果定时任务状态异常，可能需要重启 Gateway")
    print("  3. 如果锁文件残留，可能导致任务无法执行")
    print("  4. 运行 feishu_guardian.py --stats 查看详细统计")


if __name__ == "__main__":
    main()
