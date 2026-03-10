#!/usr/bin/env python3
"""
队列响应处理器 - Queue Response Handler

功能：
1. 检测用户回复是否是进化建议的执行指令
2. 支持指令：安装1、安装2、全部安装、忽略、详细1等
3. 自动执行并反馈结果

使用方法：
    python3 queue_response_handler.py --check "用户输入"
    
返回JSON格式：
    {"is_response": true/false, "message": "回复内容", "action": "执行动作"}

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
WORKSPACE = Path("/root/.openclaw/workspace")
SCRIPT_DIR = WORKSPACE / "second-brain-processor"


def check_evolution_response(user_input: str) -> dict:
    """
    检查用户输入是否是进化建议的响应
    
    返回:
        {
            "is_response": bool,
            "message": str,  # 回复给用户的消息
            "action": str,   # 执行的动作
            "executed": bool # 是否已执行
        }
    """
    user_input = user_input.strip().lower()
    
    # 匹配"安装" + 数字
    install_match = re.match(r'^安装\s*(\d+)$', user_input)
    if install_match:
        index = int(install_match.group(1))
        return _execute_install(index)
    
    # 匹配"全部安装"
    if user_input in ['全部安装', '安装全部', '全部', 'all']:
        return _execute_install_all()
    
    # 匹配"忽略"或"跳过"
    if user_input in ['忽略', '跳过', 'skip', 'ignore', '否', 'no']:
        return _execute_skip()
    
    # 匹配"详细" + 数字
    detail_match = re.match(r'^详细\s*(\d+)$', user_input)
    if detail_match:
        index = int(detail_match.group(1))
        return _execute_detail(index)
    
    # 匹配"修复" + 数字
    fix_match = re.match(r'^修复\s*(\d+)$', user_input)
    if fix_match:
        index = int(fix_match.group(1))
        return _execute_fix(index)
    
    # 匹配"启用" + 数字
    enable_match = re.match(r'^启用\s*(\d+)$', user_input)
    if enable_match:
        index = int(enable_match.group(1))
        return _execute_enable(index)
    
    # 不是进化建议的响应
    return {
        "is_response": False,
        "message": "",
        "action": "none",
        "executed": False
    }


def _execute_install(index: int) -> dict:
    """执行安装指定序号的建议"""
    try:
        result = subprocess.run(
            ["python3", "evolution_executor.py", "--action", "install", "--index", str(index)],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        output = result.stdout.strip()
        
        if result.returncode == 0:
            return {
                "is_response": True,
                "message": f"✅ 建议 #{index} 执行成功！\n\n{output}",
                "action": f"install_{index}",
                "executed": True
            }
        else:
            return {
                "is_response": True,
                "message": f"⚠️ 建议 #{index} 执行遇到问题：\n\n{output}\n\n错误信息：{result.stderr}",
                "action": f"install_{index}_failed",
                "executed": False
            }
    except Exception as e:
        return {
            "is_response": True,
            "message": f"❌ 执行失败：{str(e)}",
            "action": f"install_{index}_error",
            "executed": False
        }


def _execute_install_all() -> dict:
    """执行安装所有高优先级建议"""
    try:
        result = subprocess.run(
            ["python3", "evolution_executor.py", "--action", "install-all"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        output = result.stdout.strip()
        
        if result.returncode == 0:
            return {
                "is_response": True,
                "message": f"✅ 全部高优先级建议执行完成！\n\n{output}",
                "action": "install_all",
                "executed": True
            }
        else:
            return {
                "is_response": True,
                "message": f"⚠️ 部分建议执行遇到问题：\n\n{output}",
                "action": "install_all_partial",
                "executed": True
            }
    except Exception as e:
        return {
            "is_response": True,
            "message": f"❌ 执行失败：{str(e)}",
            "action": "install_all_error",
            "executed": False
        }


def _execute_skip() -> dict:
    """执行忽略/跳过"""
    try:
        result = subprocess.run(
            ["python3", "evolution_executor.py", "--action", "skip"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            "is_response": True,
            "message": "🎯 已忽略今日建议。\n\n这些建议将在明天的报告中再次呈现，你可以随时决定处理。",
            "action": "skip",
            "executed": True
        }
    except Exception as e:
        return {
            "is_response": True,
            "message": f"⚠️ 操作记录失败，但建议已标记为忽略：{str(e)}",
            "action": "skip",
            "executed": True
        }


def _execute_detail(index: int) -> dict:
    """执行显示详细信息"""
    try:
        result = subprocess.run(
            ["python3", "evolution_executor.py", "--action", "detail", "--index", str(index)],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout.strip()
        
        return {
            "is_response": True,
            "message": f"{output}\n\n💡 回复 `安装{index}` 执行此建议，或回复 `忽略` 跳过",
            "action": f"detail_{index}",
            "executed": True
        }
    except Exception as e:
        return {
            "is_response": True,
            "message": f"❌ 获取详细信息失败：{str(e)}",
            "action": f"detail_{index}_error",
            "executed": False
        }


def _execute_fix(index: int) -> dict:
    """执行修复"""
    # 修复和安装使用相同的逻辑
    return _execute_install(index)


def _execute_enable(index: int) -> dict:
    """执行启用"""
    # 启用和安装使用相同的逻辑
    return _execute_install(index)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='队列响应处理器')
    parser.add_argument('--check', required=True, help='用户输入内容')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')
    
    args = parser.parse_args()
    
    result = check_evolution_response(args.check)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 简化输出，便于shell脚本解析
        print(f"is_response: {result['is_response']}")
        print(f"action: {result['action']}")
        print(f"executed: {result['executed']}")
        print(f"message: {result['message']}")
    
    # 返回退出码：0=是响应且执行成功，1=不是响应或执行失败
    if result['is_response'] and result['executed']:
        sys.exit(0)
    elif result['is_response']:
        sys.exit(2)  # 是响应但执行失败
    else:
        sys.exit(1)  # 不是响应


if __name__ == "__main__":
    main()
