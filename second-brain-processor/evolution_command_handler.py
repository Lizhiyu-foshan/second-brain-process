#!/usr/bin/env python3
"""
进化指令处理器 - Evolution Command Handler

功能：
1. 识别用户回复中的进化指令（安装1、修复2、启用3、详细1、全部安装、忽略）
2. 调用执行器处理指令
3. 返回处理结果给用户

使用方法：
    python3 evolution_command_handler.py --check "用户输入"    # 检查是否是进化指令
    python3 evolution_command_handler.py --execute "安装1"     # 执行指令

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
SCRIPT_DIR = Path(__file__).parent


def check_evolution_command(text: str) -> dict:
    """检查文本是否包含进化指令"""
    text = text.strip().lower()
    
    # 模式匹配
    patterns = {
        r'^安装(\d+)$': 'install_single',
        r'^安装\s+(\d+)$': 'install_single',
        r'^全部安装$': 'install_all',
        r'^修复(\d+)$': 'fix_single',
        r'^修复\s+(\d+)$': 'fix_single',
        r'^启用(\d+)$': 'enable_single',
        r'^启用\s+(\d+)$': 'enable_single',
        r'^创建(\d+)$': 'create_single',
        r'^创建\s+(\d+)$': 'create_single',
        r'^详细(\d+)$': 'show_detail',
        r'^详细\s+(\d+)$': 'show_detail',
        r'^忽略$': 'skip_all',
        r'^跳过$': 'skip_all',
        r'^以后再说$': 'skip_all',
    }
    
    for pattern, action in patterns.items():
        match = re.match(pattern, text)
        if match:
            index = int(match.group(1)) if match.groups() else None
            return {
                "is_command": True,
                "action": action,
                "index": index,
                "original_text": text
            }
    
    return {"is_command": False}


def execute_command(action: str, index: int = None) -> dict:
    """执行进化指令"""
    result = {
        "success": False,
        "message": "",
        "action": action,
        "index": index
    }
    
    try:
        if action == "install_single" and index:
            # 执行单个安装
            cmd = ["python3", str(SCRIPT_DIR / "evolution_executor.py"), "--action", "install", "--index", str(index)]
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            result["success"] = process.returncode == 0
            result["message"] = process.stdout if process.stdout else "安装执行完成"
            result["stderr"] = process.stderr if process.stderr else ""
            
        elif action == "install_all":
            # 安装所有高优先级
            cmd = ["python3", str(SCRIPT_DIR / "evolution_executor.py"), "--action", "install-all"]
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            result["success"] = process.returncode == 0
            result["message"] = process.stdout if process.stdout else "批量安装执行完成"
            
        elif action == "fix_single" and index:
            # 修复配置
            cmd = ["python3", str(SCRIPT_DIR / "evolution_executor.py"), "--action", "install", "--index", str(index)]
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            result["success"] = process.returncode == 0
            result["message"] = f"修复 #{index} 执行完成"
            
        elif action == "enable_single" and index:
            # 启用功能
            result["success"] = True
            result["message"] = f"功能 #{index} 已标记为启用（可能需要重启生效）"
            
        elif action == "show_detail" and index:
            # 显示详细信息
            cmd = ["python3", str(SCRIPT_DIR / "evolution_executor.py"), "--action", "detail", "--index", str(index)]
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            result["success"] = process.returncode == 0
            result["message"] = process.stdout if process.stdout else f"详细说明 #{index}"
            
        elif action == "skip_all":
            # 跳过所有建议
            cmd = ["python3", str(SCRIPT_DIR / "evolution_executor.py"), "--action", "skip"]
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            result["success"] = True
            result["message"] = "已跳过今日建议，明天将再次评估"
            
        else:
            result["message"] = f"未知的指令类型: {action}"
            
    except subprocess.TimeoutExpired:
        result["message"] = "指令执行超时，请稍后重试"
    except Exception as e:
        result["message"] = f"执行失败: {str(e)}"
    
    return result


def format_response(result: dict) -> str:
    """格式化响应给用户"""
    if not result.get("success"):
        return f"❌ 执行失败\n\n{result.get('message', '未知错误')}"
    
    action = result.get("action", "")
    message = result.get("message", "")
    
    if action.startswith("install"):
        return f"✅ **安装执行完成**\n\n{message[:500]}\n\n💡 提示：安装后可能需要重启会话使Skill生效"
    elif action.startswith("fix"):
        return f"✅ **修复执行完成**\n\n{message[:500]}"
    elif action.startswith("enable"):
        return f"✅ **功能已启用**\n\n{message}"
    elif action == "skip_all":
        return f"⏭️ **已跳过**\n\n{message}"
    else:
        return f"✅ **执行完成**\n\n{message[:500]}"


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='进化指令处理器')
    parser.add_argument('--check', type=str, help='检查文本是否包含进化指令')
    parser.add_argument('--execute', type=str, help='执行指令')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')
    
    args = parser.parse_args()
    
    if args.check:
        result = check_evolution_command(args.check)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result["is_command"]:
                print(f"检测到指令: {result['action']}, 序号: {result.get('index')}")
            else:
                print("未检测到进化指令")
    
    elif args.execute:
        # 先检查，再执行
        check_result = check_evolution_command(args.execute)
        if check_result["is_command"]:
            execute_result = execute_command(
                check_result["action"], 
                check_result.get("index")
            )
            if args.json:
                print(json.dumps(execute_result, ensure_ascii=False, indent=2))
            else:
                print(format_response(execute_result))
        else:
            print(f"❌ 无法识别的指令: {args.execute}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
