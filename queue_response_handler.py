#!/usr/bin/env python3
"""
待读笔记队列回复处理器 v2 - 立即响应版

功能：
1. 检测用户回复是否是待读队列的执行指令
2. 支持指令：A1(原文)、A2(摘要)、A3(精简)、AI自动整理、推迟
3. 移除10分钟超时等待，立即响应

使用方法：
    python3 queue_response_handler.py --check "用户输入"
    
返回JSON格式：
    {"is_response": true/false, "message": "回复内容", "action": "执行动作"}

作者：Kimi Claw
创建时间：2026-03-21
版本：v2（立即响应版）
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 路径配置
WORKSPACE = Path("/root/.openclaw/workspace")
SCRIPT_DIR = WORKSPACE / "second-brain-processor"
QUEUE_DIR = SCRIPT_DIR / "queue"

# 状态文件（记录待处理队列和延迟设置）
STATE_FILE = WORKSPACE / "queue_processor_state.json"

def load_state():
    """加载处理器状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"queue": [], "delayed_until": None, "auto_process": False}

def save_state(state):
    """保存处理器状态"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_queue_files():
    """获取当前队列中的文件列表"""
    if not QUEUE_DIR.exists():
        return []
    return sorted(QUEUE_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime)

def parse_user_input(user_input: str) -> dict:
    """
    解析用户输入，判断意图
    
    返回: {
        "is_response": bool,  # 是否是队列相关响应
        "action": str,        # 动作类型
        "mode": str,          # 处理模式
        "message": str        # 回复给用户的消息
    }
    """
    user_input = user_input.strip().upper()
    
    # 1. 批量处理指令 (A1, A2, A3, A)
    batch_patterns = {
        'A1': ('batch', 'full', '原文保存'),
        'A 1': ('batch', 'full', '原文保存'),
        'A2': ('batch', 'summary', '主体+核心观点'),
        'A 2': ('batch', 'summary', '主体+核心观点'),
        'A3': ('batch', 'brief', '精简摘要'),
        'A 3': ('batch', 'brief', '精简摘要'),
        'A': ('batch', 'summary', '主体+核心观点（默认）'),
    }
    
    if user_input in batch_patterns:
        action, mode, mode_name = batch_patterns[user_input]
        queue_files = get_queue_files()
        count = len(queue_files)
        
        if count == 0:
            return {
                "is_response": True,
                "action": "none",
                "mode": None,
                "message": "📭 队列为空，无需处理"
            }
        
        return {
            "is_response": True,
            "action": action,
            "mode": mode,
            "message": f"✅ 已选择批量处理（{mode_name}）\n\n正在处理 {count} 个笔记，请稍候..."
        }
    
    # 2. AI自动整理指令
    ai_patterns = ['AI', 'AI自动', 'AI自动整理', '自动整理', '整理', '处理']
    if any(user_input == p or user_input.startswith(p) for p in ai_patterns):
        queue_files = get_queue_files()
        count = len(queue_files)
        
        if count == 0:
            return {
                "is_response": True,
                "action": "none",
                "mode": None,
                "message": "📭 队列为空，无需处理"
            }
        
        # 设置自动处理标志
        state = load_state()
        state["auto_process"] = True
        state["auto_mode"] = "summary"  # 默认摘要模式
        save_state(state)
        
        return {
            "is_response": True,
            "action": "ai_auto",
            "mode": "summary",
            "message": f"🤖 AI自动整理已启动\n\n正在处理 {count} 个笔记（主体+核心观点模式）..."
        }
    
    # 3. 推迟指令
    delay_patterns = ['推迟', '延迟', '延后', '稍后', '待会', 'DELAY', 'POSTPONE', 'LATER']
    if any(user_input == p or user_input.startswith(p) for p in delay_patterns):
        # 计算新的延迟时间（默认推迟2小时）
        delay_hours = 2
        
        # 尝试提取延迟时间（如"推迟3小时"）
        match = re.search(r'(\d+)\s*小时', user_input)
        if match:
            delay_hours = int(match.group(1))
        
        new_time = datetime.now() + timedelta(hours=delay_hours)
        
        state = load_state()
        state["delayed_until"] = new_time.isoformat()
        save_state(state)
        
        return {
            "is_response": True,
            "action": "delay",
            "mode": None,
            "message": f"⏰ 已推迟处理\n\n将在 {new_time.strftime('%H:%M')} 再次提醒你。\n回复「AI自动整理」可立即开始处理。"
        }
    
    # 4. 差异化处理（逐条确认）- 暂时不支持
    if user_input == 'B':
        return {
            "is_response": True,
            "action": "individual",
            "mode": None,
            "message": "📝 逐条处理功能开发中，请使用批量处理（A1/A2/A3）或 AI自动整理"
        }
    
    # 不是队列响应
    return {
        "is_response": False,
        "action": "none",
        "mode": None,
        "message": ""
    }

def execute_batch_process(mode: str) -> dict:
    """执行批量处理"""
    try:
        result = subprocess.run(
            ["python3", "process_all.py", "--batch", mode],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        output = result.stdout.strip()
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"✅ 批量处理完成\n\n{output}",
                "output": output
            }
        else:
            return {
                "success": False,
                "message": f"⚠️ 处理遇到问题：\n\n{output}\n\n错误：{result.stderr}",
                "output": output
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "⏱️ 处理超时，但后台可能仍在运行，请稍后检查 Obsidian Vault",
            "output": ""
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ 执行失败：{str(e)}",
            "output": ""
        }

def execute_ai_auto_process() -> dict:
    """执行AI自动整理"""
    return execute_batch_process("summary")

def handle_user_input(user_input: str) -> dict:
    """
    处理用户输入的主入口
    
    返回: {
        "handled": bool,      # 是否已处理
        "response": str,      # 给用户的回复
        "action": str,        # 后续动作
        "execute": bool       # 是否立即执行
    }
    """
    result = parse_user_input(user_input)
    
    if not result["is_response"]:
        return {
            "handled": False,
            "response": "",
            "action": "continue",
            "execute": False
        }
    
    # 根据动作类型处理
    if result["action"] == "batch":
        return {
            "handled": True,
            "response": result["message"],
            "action": "batch_process",
            "execute": True,
            "mode": result["mode"]
        }
    
    elif result["action"] == "ai_auto":
        return {
            "handled": True,
            "response": result["message"],
            "action": "ai_auto_process",
            "execute": True,
            "mode": result["mode"]
        }
    
    elif result["action"] == "delay":
        return {
            "handled": True,
            "response": result["message"],
            "action": "delayed",
            "execute": False
        }
    
    elif result["action"] == "individual":
        return {
            "handled": True,
            "response": result["message"],
            "action": "individual_mode",
            "execute": False
        }
    
    elif result["action"] == "none":
        return {
            "handled": True,
            "response": result["message"],
            "action": "none",
            "execute": False
        }
    
    return {
        "handled": False,
        "response": "",
        "action": "continue",
        "execute": False
    }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='待读队列回复处理器 v2')
    parser.add_argument('--check', required=True, help='用户输入内容')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')
    parser.add_argument('--execute', action='store_true', help='立即执行处理')
    
    args = parser.parse_args()
    
    result = handle_user_input(args.check)
    
    # 如果需要执行
    if args.execute and result.get("execute"):
        if result["action"] == "batch_process":
            exec_result = execute_batch_process(result.get("mode", "summary"))
            result["execution_result"] = exec_result
            result["response"] = exec_result["message"]
        elif result["action"] == "ai_auto_process":
            exec_result = execute_ai_auto_process()
            result["execution_result"] = exec_result
            result["response"] = exec_result["message"]
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"handled: {result['handled']}")
        print(f"action: {result['action']}")
        print(f"execute: {result.get('execute', False)}")
        print(f"response: {result['response']}")
    
    # 返回退出码
    if result['handled']:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
