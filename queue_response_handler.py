#!/usr/bin/env python3
"""
待读笔记队列回复处理器
用于处理用户对待确认列表的回复
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 队列目录
QUEUE_DIR = Path("/root/.openclaw/workspace/second-brain-processor/queue")
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
PROCESSOR_DIR = Path("/root/.openclaw/workspace/second-brain-processor")

# 状态文件（记录活跃会话）
STATE_FILE = Path("/root/.openclaw/workspace/queue_processor_state.json")

def load_state():
    """加载处理器状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"active_sessions": {}, "processed": []}

def save_state(state):
    """保存处理器状态"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_active_session():
    """获取当前活跃的待处理会话"""
    state = load_state()
    
    # 清理过期会话（15分钟）
    now = datetime.now()
    expired = []
    for session_id, session_data in state["active_sessions"].items():
        created = datetime.fromisoformat(session_data["created"])
        if now - created > timedelta(minutes=15):
            expired.append(session_id)
    
    for sid in expired:
        del state["active_sessions"][sid]
    
    if expired:
        save_state(state)
    
    # 返回最新的活跃会话
    if state["active_sessions"]:
        latest = max(state["active_sessions"].items(), 
                    key=lambda x: x[1]["created"])
        return latest[0], latest[1]
    
    return None, None

def create_session(session_id, queue_count):
    """创建新会话"""
    state = load_state()
    state["active_sessions"][session_id] = {
        "created": datetime.now().isoformat(),
        "queue_count": queue_count,
        "status": "waiting"
    }
    save_state(state)

def is_queue_response(user_input: str) -> dict:
    """
    判断用户输入是否是待读队列的响应
    
    返回: {
        "is_response": bool,
        "type": "batch" | "individual" | "invalid" | "other",
        "mode": str | None,  # full/summary/brief
        "session_id": str | None,
        "message": str  # 给用户的反馈消息
    }
    """
    user_input = user_input.strip().upper()
    
    # 获取活跃会话
    session_id, session_data = get_active_session()
    
    # 检查是否是队列相关回复
    batch_patterns = ['A1', 'A2', 'A3', 'A', 'A 1', 'A 2', 'A 3']
    individual_pattern = 'B'
    
    is_batch = any(user_input == p or user_input.startswith(p) for p in batch_patterns)
    is_individual = user_input == individual_pattern
    
    # 如果没有活跃会话
    if not session_id:
        if is_batch or is_individual:
            return {
                "is_response": True,
                "type": "invalid",
                "mode": None,
                "session_id": None,
                "message": "⏰ 待读列表已过期（超过15分钟），已自动按 A2 处理。如需特殊处理，请查看 Obsidian 中的笔记。"
            }
        else:
            # 不是队列响应，是普通对话
            return {
                "is_response": False,
                "type": "other",
                "mode": None,
                "session_id": None,
                "message": ""
            }
    
    # 有活跃会话，处理响应
    if is_batch:
        mode_map = {
            'A1': 'full', 'A 1': 'full',
            'A2': 'summary', 'A 2': 'summary', 'A': 'summary',
            'A3': 'brief', 'A 3': 'brief'
        }
        mode = mode_map.get(user_input, 'summary')
        
        return {
            "is_response": True,
            "type": "batch",
            "mode": mode,
            "session_id": session_id,
            "message": f"✅ 已选择批量处理（{'原文保存' if mode == 'full' else '主体+核心观点' if mode == 'summary' else '精简摘要'}），开始处理 {session_data['queue_count']} 个笔记..."
        }
    
    elif is_individual:
        return {
            "is_response": True,
            "type": "individual",
            "mode": None,
            "session_id": session_id,
            "message": "✅ 已选择差异化处理，逐条确认："
        }
    
    else:
        # 有活跃会话，但输入不是有效响应
        return {
            "is_response": False,
            "type": "other",
            "mode": None,
            "session_id": session_id,
            "message": ""
        }

def process_batch(mode: str) -> str:
    """批量处理队列"""
    try:
        sys.path.insert(0, str(PROCESSOR_DIR))
        from process_all import process_all
        
        result = process_all(mode=mode)
        
        if result["success"]:
            return f"\n✅ 处理完成！\n- 成功：{result['processed']} 个\n- 失败：{result['failed']} 个\n- 已同步到 Obsidian Vault"
        else:
            return f"\n⚠️ 处理完成，但有错误：{result.get('error', '未知错误')}"
    except Exception as e:
        return f"\n❌ 处理失败：{str(e)}"

def extract_session_id(message: str) -> str:
    """从消息中提取会话标识符"""
    match = re.search(r'<!-- SESSION:(\d{12}) -->', message)
    if match:
        return match.group(1)
    return None

def handle_user_input(user_input: str, context_message: str = "") -> dict:
    """
    处理用户输入的主入口
    
    返回: {
        "handled": bool,  # 是否已处理（是队列响应）
        "response": str,  # 给用户的回复
        "action": str,    # 后续动作
        "async_task": dict | None  # 异步任务信息
    }
    """
    # 首先检查是否是队列响应
    result = is_queue_response(user_input)
    
    if not result["is_response"]:
        # 不是队列响应，返回未处理状态
        return {
            "handled": False,
            "response": "",
            "action": "continue",
            "async_task": None
        }
    
    # 是队列响应，处理它
    if result["type"] == "invalid":
        return {
            "handled": True,
            "response": result["message"],
            "action": "expired",
            "async_task": None
        }
    
    elif result["type"] == "batch":
        # 异步批量处理 - 立即返回确认，后台处理
        mode = result["mode"]
        mode_name = "原文保存" if mode == "full" else "主体+核心观点" if mode == "summary" else "精简摘要"
        
        # 创建异步任务
        async_task = {
            "type": "batch_process",
            "mode": mode,
            "session_id": result["session_id"],
            "queue_count": result.get("queue_count", 1)
        }
        
        return {
            "handled": True,
            "response": f"✅ 已选择批量处理（{mode_name}）\n\n正在后台处理 {async_task['queue_count']} 个笔记，完成后会通知你。\n\n⏱️ 预计耗时 1-3 分钟",
            "action": "async_processing",
            "async_task": async_task
        }
    
    elif result["type"] == "individual":
        # 差异化处理 - 需要进一步交互
        return {
            "handled": True,
            "response": result["message"] + "\n（逐条处理功能开发中，暂请使用批量处理）",
            "action": "needs_detail",
            "async_task": None
        }
    
    return {
        "handled": False,
        "response": "",
        "action": "continue",
        "async_task": None
    }

def execute_async_task(task: dict) -> dict:
    """
    执行异步任务
    这个函数应该在后台线程或子进程中调用
    """
    if task["type"] == "batch_process":
        result = process_batch(task["mode"])
        return {
            "success": result.get("success", False),
            "processed_count": result.get("processed_count", 0),
            "success_count": result.get("success_count", 0),
            "sync_status": result.get("sync_status", ""),
            "message": format_async_result(result)
        }
    
    return {"success": False, "message": "未知任务类型"}

def format_async_result(result: dict) -> str:
    """格式化异步处理结果"""
    if result.get("success"):
        return f"""✅ 笔记处理完成！

- 处理数量：{result.get('success_count', 0)} 个
- 同步状态：已同步到 Obsidian Vault

处理结果：
{result.get('sync_status', '完成')}"""
    else:
        return f"""⚠️ 笔记处理遇到问题

{result.get('sync_status', '请检查日志了解详情')}

建议操作：
1. 检查网络连接
2. 手动同步：cd obsidian-vault && git push"""

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='队列回复处理器')
    parser.add_argument('--check', type=str, help='检查用户输入是否是队列响应')
    parser.add_argument('--create-session', type=str, help='创建新会话（传入session_id）')
    parser.add_argument('--queue-count', type=int, help='队列数量')
    
    args = parser.parse_args()
    
    if args.check:
        result = is_queue_response(args.check)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.create_session and args.queue_count:
        create_session(args.create_session, args.queue_count)
        print(f"会话 {args.create_session} 已创建，队列数量: {args.queue_count}")
    else:
        parser.print_help()
