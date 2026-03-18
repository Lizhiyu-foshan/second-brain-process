#!/usr/bin/env python3
"""
执行前检查脚本 - morning_task_pre_check.py
验证凌晨5:00任务的前置条件
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
SESSION_DIR = Path("/root/.openclaw/agents/main/sessions")
OUTPUT_DIR = WORKSPACE / "obsidian-vault" / "02-Conversations"

def check_api_key() -> tuple:
    """检查API Key"""
    api_key = os.environ.get('KIMI_API_KEY')
    if not api_key:
        return False, "KIMI_API_KEY 未设置"
    if len(api_key) < 10:
        return False, "KIMI_API_KEY 格式异常"
    return True, f"API Key有效 (前8位: {api_key[:8]}...)"

def check_directories() -> tuple:
    """检查目录"""
    checks = [
        (WORKSPACE, "工作空间", os.R_OK),
        (SESSION_DIR, "Session目录", os.R_OK),
        (OUTPUT_DIR, "输出目录", os.W_OK),
    ]
    
    for path, name, perm in checks:
        if not path.exists():
            return False, f"{name}不存在: {path}"
        if not os.access(path, perm):
            return False, f"{name}权限不足: {path}"
    
    return True, "所有目录检查通过"

def check_git_status() -> tuple:
    """检查Git状态"""
    try:
        result = subprocess.run(
            ['git', '-C', str(WORKSPACE), 'status', '--porcelain'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return False, f"Git状态检查失败: {result.stderr}"
        
        # 检查是否有未提交的更改（警告级别）
        if result.stdout.strip():
            return True, f"Git检查通过（有未提交更改: {len(result.stdout.strip().split(chr(10)))} 个文件）"
        return True, "Git检查通过（工作区干净）"
    except Exception as e:
        return False, f"Git检查异常: {e}"

def check_disk_space() -> tuple:
    """检查磁盘空间"""
    try:
        result = subprocess.run(
            ['df', '-h', '/'],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            usage = lines[1].split()[4].rstrip('%')
            if int(usage) > 90:
                return False, f"磁盘使用率过高: {usage}%"
            return True, f"磁盘空间充足: {usage}%"
    except Exception as e:
        return False, f"磁盘检查异常: {e}"

def check_memory() -> tuple:
    """检查内存"""
    try:
        result = subprocess.run(
            ['free', '-m'],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            available = int(lines[1].split()[6])
            if available < 500:
                return False, f"可用内存不足: {available}MB"
            return True, f"内存充足: {available}MB"
    except Exception as e:
        return False, f"内存检查异常: {e}"

def check_network() -> tuple:
    """检查网络连接"""
    try:
        result = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
             'https://api.moonshot.cn'],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout.strip() == '200':
            return True, "API服务器可访问"
        return False, f"API服务器返回: {result.stdout.strip()}"
    except Exception as e:
        return False, f"网络检查异常: {e}"

def check_running_instances() -> tuple:
    """检查是否有其他实例在运行"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'run_morning_process'],
            capture_output=True, text=True, timeout=5
        )
        pids = [p for p in result.stdout.strip().split('\n') if p]
        # 排除自己
        current_pid = str(os.getpid())
        other_pids = [p for p in pids if p != current_pid]
        
        if other_pids:
            return False, f"发现其他运行实例: {other_pids}"
        return True, "无其他运行实例"
    except Exception as e:
        return False, f"进程检查异常: {e}"

def run_all_checks() -> dict:
    """运行所有检查"""
    checks = [
        ("API Key", check_api_key),
        ("目录权限", check_directories),
        ("Git状态", check_git_status),
        ("磁盘空间", check_disk_space),
        ("内存检查", check_memory),
        ("网络连接", check_network),
        ("实例冲突", check_running_instances),
    ]
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "passed": [],
        "failed": [],
    }
    
    print("=" * 50)
    print("凌晨5:00任务 - 执行前检查")
    print("=" * 50)
    
    for name, check_func in checks:
        success, message = check_func()
        status = "✅" if success else "❌"
        print(f"{status} {name}: {message}")
        
        if success:
            results["passed"].append({"name": name, "message": message})
        else:
            results["failed"].append({"name": name, "message": message})
    
    print("=" * 50)
    print(f"检查完成: {len(results['passed'])} 通过, {len(results['failed'])} 失败")
    
    return results

if __name__ == "__main__":
    results = run_all_checks()
    sys.exit(0 if len(results['failed']) == 0 else 1)
