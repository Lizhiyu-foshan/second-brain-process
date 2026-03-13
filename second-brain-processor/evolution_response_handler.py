#!/usr/bin/env python3
"""
进化建议响应处理器 - Evolution Response Handler

功能：
1. 监听用户回复（安装1、全部安装、忽略等）
2. 解析指令并调用evolution_executor执行
3. 反馈执行结果

使用方式：
    python3 evolution_response_handler.py --check "用户回复内容"
    
返回JSON格式：
    {"is_response": true/false, "action": "...", "message": "..."}

作者：Kimi Claw
创建时间：2026-03-10
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# 路径配置
SCRIPT_DIR = Path("/root/.openclaw/workspace/second-brain-processor")


def parse_command(text: str) -> dict:
    """解析用户指令"""
    text = text.strip().lower()
    
    # 匹配 "安装1"、"安装 1"、"安1" 等变体
    install_match = re.match(r'^(?:安装|安|install)\s*(\d+)$', text)
    if install_match:
        return {
            "is_response": True,
            "action": "install",
            "index": int(install_match.group(1)),
            "reply": f"收到指令：安装建议 #{install_match.group(1)}"
        }
    
    # 匹配 "全部安装"、"安装全部"、"all" 等
    if re.match(r'^(?:全部安装|安装全部|all|install-all)$', text):
        return {
            "is_response": True,
            "action": "install-all",
            "reply": "收到指令：安装所有高优先级建议"
        }
    
    # 匹配 "忽略"、"跳过"、"skip"、"no" 等
    if re.match(r'^(?:忽略|跳过|skip|no|n|否)$', text):
        return {
            "is_response": True,
            "action": "skip",
            "reply": "已忽略今日建议，明天将再次评估"
        }
    
    # 匹配 "详细1"、"详细 1"、"detail 1" 等
    detail_match = re.match(r'^(?:详细|detail|详|info)\s*(\d+)$', text)
    if detail_match:
        return {
            "is_response": True,
            "action": "detail",
            "index": int(detail_match.group(1)),
            "reply": f"收到指令：查看建议 #{detail_match.group(1)} 详情"
        }
    
    # 匹配 "列表"、"list"、"显示所有" 等
    if re.match(r'^(?:列表|list|显示所有|查看所有)$', text):
        return {
            "is_response": True,
            "action": "list",
            "reply": "收到指令：显示所有建议"
        }
    
    return {"is_response": False}


def execute_command(action: str, index: int = None) -> dict:
    """执行指令"""
    try:
        if action == "install":
            # 执行安装（非交互模式，需要特殊处理）
            result = subprocess.run(
                ["python3", "evolution_executor.py", "--action", "install", "--index", str(index)],
                cwd=SCRIPT_DIR,
                capture_output=True,
                text=True,
                timeout=60,
                input="y\n"  # 自动确认
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None
            }
        
        elif action == "install-all":
            result = subprocess.run(
                ["python3", "evolution_executor.py", "--action", "install-all"],
                cwd=SCRIPT_DIR,
                capture_output=True,
                text=True,
                timeout=120,
                input="y\n"  # 自动确认
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None
            }
        
        elif action == "skip":
            result = subprocess.run(
                ["python3", "evolution_executor.py", "--action", "skip"],
                cwd=SCRIPT_DIR,
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": None
            }
        
        elif action == "detail":
            result = subprocess.run(
                ["python3", "evolution_executor.py", "--action", "detail", "--index", str(index)],
                cwd=SCRIPT_DIR,
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None
            }
        
        elif action == "list":
            result = subprocess.run(
                ["python3", "evolution_executor.py", "--action", "list"],
                cwd=SCRIPT_DIR,
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None
            }
        
        else:
            return {
                "success": False,
                "output": "",
                "error": f"未知动作: {action}"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "执行超时"
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e)
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='进化建议响应处理器')
    parser.add_argument('--check', required=True, help='用户回复内容')
    parser.add_argument('--execute', action='store_true', help='是否立即执行')
    
    args = parser.parse_args()
    
    # 解析指令
    result = parse_command(args.check)
    
    if not result["is_response"]:
        # 不是进化相关指令
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)
    
    if args.execute:
        # 执行指令
        execution_result = execute_command(
            result["action"], 
            result.get("index")
        )
        
        result["executed"] = True
        result["execution_result"] = execution_result
        
        # 构建反馈消息
        if execution_result["success"]:
            result["message"] = f"✅ {result['reply']}\n\n执行成功！\n```\n{execution_result['output'][:500]}\n```"
        else:
            error_msg = execution_result.get('error', '未知错误') or execution_result.get('output', '')
            result["message"] = f"❌ {result['reply']}\n\n执行失败:\n```\n{error_msg[:500]}\n```"
    else:
        # 仅检查，不执行
        result["executed"] = False
        result["message"] = result["reply"]
    
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
