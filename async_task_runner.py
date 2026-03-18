#!/usr/bin/env python3
"""
异步任务执行器
用于在后台处理笔记，完成后发送通知
"""

import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# 添加处理器路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "second-brain-processor"))

from queue_response_handler import execute_async_task, load_state, save_state

TASK_STATE_FILE = Path("/root/.openclaw/workspace/async_tasks_state.json")

def load_task_state():
    """加载任务状态"""
    if TASK_STATE_FILE.exists():
        with open(TASK_STATE_FILE, 'r') as f:
            return json.load(f)
    return {"pending": [], "completed": [], "failed": []}

def save_task_state(state):
    """保存任务状态"""
    with open(TASK_STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def add_pending_task(task: dict, user_id: str):
    """添加待处理任务"""
    state = load_task_state()
    task_info = {
        "id": f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "task": task,
        "user_id": user_id,
        "created": datetime.now().isoformat(),
        "status": "pending"
    }
    state["pending"].append(task_info)
    save_task_state(state)
    return task_info["id"]

def run_task(task_info: dict):
    """运行单个任务"""
    task = task_info["task"]
    user_id = task_info["user_id"]
    
    print(f"[{datetime.now()}] 开始执行任务: {task_info['id']}")
    
    try:
        # 执行异步任务
        result = execute_async_task(task)
        
        # 更新任务状态
        state = load_task_state()
        task_info["status"] = "completed" if result["success"] else "failed"
        task_info["completed_at"] = datetime.now().isoformat()
        task_info["result"] = result
        
        # 移动到完成列表
        state["pending"] = [t for t in state["pending"] if t["id"] != task_info["id"]]
        if result["success"]:
            state["completed"].append(task_info)
        else:
            state["failed"].append(task_info)
        
        save_task_state(state)
        
        # 发送通知（通过 OpenClaw 的 message 工具）
        notification = result["message"]
        send_notification(user_id, notification)
        
        print(f"[{datetime.now()}] 任务完成: {task_info['id']}")
        return True
        
    except Exception as e:
        print(f"[{datetime.now()}] 任务失败: {task_info['id']}, 错误: {e}")
        
        # 更新失败状态
        state = load_task_state()
        task_info["status"] = "failed"
        task_info["error"] = str(e)
        task_info["completed_at"] = datetime.now().isoformat()
        
        state["pending"] = [t for t in state["pending"] if t["id"] != task_info["id"]]
        state["failed"].append(task_info)
        save_task_state(state)
        
        # 发送失败通知
        send_notification(user_id, f"❌ 笔记处理失败：{str(e)}\n\n请手动检查队列文件。")
        
        return False

def send_notification(user_id: str, message: str):
    """发送通知到飞书"""
    try:
        # 使用 OpenClaw 的 message 工具发送通知
        # 注意：这里假设在 OpenClaw 环境中运行
        import os
        gateway_url = os.environ.get("OPENCLAW_GATEWAY_URL", "ws://127.0.0.1:18789")
        
        # 构造通知命令
        # 实际发送会在主会话中通过 sessions_send 或 message 工具完成
        print(f"[NOTIFICATION] To {user_id}: {message[:100]}...")
        
        # 写入通知队列，供主会话读取
        notification_file = Path("/root/.openclaw/workspace/pending_notifications.json")
        notifications = []
        if notification_file.exists():
            with open(notification_file, 'r') as f:
                notifications = json.load(f)
        
        notifications.append({
            "user_id": user_id,
            "message": message,
            "created": datetime.now().isoformat()
        })
        
        with open(notification_file, 'w') as f:
            json.dump(notifications, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"发送通知失败: {e}")

def process_all_pending():
    """处理所有待处理任务"""
    state = load_task_state()
    
    if not state["pending"]:
        print("没有待处理任务")
        return
    
    print(f"发现 {len(state['pending'])} 个待处理任务")
    
    for task_info in state["pending"][:]:
        run_task(task_info)

def get_pending_notifications():
    """获取待发送的通知（供主会话调用）"""
    notification_file = Path("/root/.openclaw/workspace/pending_notifications.json")
    
    if not notification_file.exists():
        return []
    
    with open(notification_file, 'r') as f:
        notifications = json.load(f)
    
    # 清空已读取的通知
    with open(notification_file, 'w') as f:
        json.dump([], f)
    
    return notifications

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='异步任务执行器')
    parser.add_argument('--process-all', action='store_true', help='处理所有待处理任务')
    parser.add_argument('--get-notifications', action='store_true', help='获取待发送通知')
    
    args = parser.parse_args()
    
    if args.process_all:
        process_all_pending()
    elif args.get_notifications:
        notifications = get_pending_notifications()
        print(json.dumps(notifications, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
