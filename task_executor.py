#!/usr/bin/env python3
"""
定时任务执行器 - 优化版

解决延迟补发问题的核心机制：
1. 任务级锁 - 防止同一任务并发执行
2. 执行状态追踪 - 记录任务执行历史和状态
3. 超时保护 - 强制终止超时的任务
4. 智能调度 - 避免任务堆积时重复执行
"""

import fcntl
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

WORKSPACE = Path("/root/.openclaw/workspace")
LEARNINGS_DIR = WORKSPACE / ".learnings"
LOCK_DIR = LEARNINGS_DIR / "task_locks"
STATE_FILE = LEARNINGS_DIR / "task_executor_state.json"

# 默认超时时间（秒）
DEFAULT_TIMEOUT = 120


def _load_executor_state() -> Dict:
    """加载执行器状态"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "task_history": {},
        "last_cleanup": datetime.now().isoformat()
    }


def _save_executor_state(state: Dict):
    """保存执行器状态"""
    try:
        LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
        temp_file = STATE_FILE.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        temp_file.replace(STATE_FILE)
    except IOError as e:
        print(f"[WARN] 保存执行器状态失败: {e}")


def _record_task_start(task_name: str):
    """记录任务开始"""
    state = _load_executor_state()
    
    if task_name not in state["task_history"]:
        state["task_history"][task_name] = []
    
    state["task_history"][task_name].append({
        "start_time": datetime.now().isoformat(),
        "status": "running",
        "pid": os.getpid()
    })
    
    # 只保留最近20条记录
    state["task_history"][task_name] = state["task_history"][task_name][-20:]
    _save_executor_state(state)


def _record_task_end(task_name: str, success: bool, error: str = ""):
    """记录任务结束"""
    state = _load_executor_state()
    
    if task_name in state["task_history"] and state["task_history"][task_name]:
        # 更新最后一条记录
        last_record = state["task_history"][task_name][-1]
        last_record["end_time"] = datetime.now().isoformat()
        last_record["status"] = "success" if success else "failed"
        last_record["error"] = error
        last_record["duration"] = (
            datetime.now() - datetime.fromisoformat(last_record["start_time"])
        ).total_seconds()
    
    _save_executor_state(state)


def is_task_running(task_name: str, max_duration: int = 300) -> bool:
    """
    检查任务是否正在运行（防止重复执行）
    
    Args:
        task_name: 任务名称
        max_duration: 最大允许执行时间（秒），超过则认为已卡死
    
    Returns:
        bool: 是否正在运行
    """
    state = _load_executor_state()
    
    if task_name not in state["task_history"]:
        return False
    
    history = state["task_history"][task_name]
    if not history:
        return False
    
    # 检查最近的记录
    last_record = history[-1]
    if last_record.get("status") == "running":
        start_time = datetime.fromisoformat(last_record["start_time"])
        duration = (datetime.now() - start_time).total_seconds()
        
        if duration > max_duration:
            # 任务运行时间过长，认为已卡死
            print(f"[WARN] 任务 {task_name} 运行 {duration:.0f} 秒，超过限制 {max_duration} 秒，强制标记为失败")
            _record_task_end(task_name, success=False, error=f"timeout_exceeded: {duration}s")
            return False
        
        return True
    
    return False


class TaskLock:
    """任务锁上下文管理器"""
    
    def __init__(self, task_name: str, timeout: int = DEFAULT_TIMEOUT):
        self.task_name = task_name
        self.timeout = timeout
        self.lock_file = LOCK_DIR / f"{task_name}.lock"
        self.lock_fd = None
        self.acquired = False
    
    def __enter__(self):
        # 检查是否已有实例在运行
        if is_task_running(self.task_name, self.timeout):
            print(f"[INFO] 任务 {self.task_name} 正在运行中，跳过本次执行")
            sys.exit(0)
        
        # 获取文件锁
        try:
            LOCK_DIR.mkdir(parents=True, exist_ok=True)
            self.lock_fd = os.open(str(self.lock_file), os.O_RDWR | os.O_CREAT)
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # 写入进程ID
            os.write(self.lock_fd, str(os.getpid()).encode())
            os.fsync(self.lock_fd)
            
            self.acquired = True
            _record_task_start(self.task_name)
            print(f"[INFO] 任务 {self.task_name} 开始执行 (PID: {os.getpid()})")
            
        except (IOError, OSError) as e:
            print(f"[INFO] 无法获取任务锁 {self.task_name}: {e}")
            sys.exit(0)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        error = str(exc_val) if exc_val else ""
        
        if self.acquired:
            _record_task_end(self.task_name, success, error)
            
            # 释放文件锁
            try:
                if self.lock_fd is not None:
                    fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                    os.close(self.lock_fd)
                    
                    # 删除锁文件
                    try:
                        self.lock_file.unlink()
                    except:
                        pass
            except:
                pass
            
            status = "成功" if success else "失败"
            print(f"[INFO] 任务 {self.task_name} 执行{status}")


def run_command(cmd: list, timeout: int = DEFAULT_TIMEOUT) -> tuple[bool, str]:
    """
    执行命令（带超时）
    
    Returns:
        (success, output_or_error)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, f"Exit code {result.returncode}: {result.stderr}"
    
    except subprocess.TimeoutExpired:
        return False, f"Timeout after {timeout} seconds"
    except Exception as e:
        return False, f"Exception: {e}"


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="任务名称")
    parser.add_argument("--cmd", required=True, help="要执行的命令")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="超时时间（秒）")
    args = parser.parse_args()
    
    # 解析命令
    cmd_parts = args.cmd.split()
    
    with TaskLock(args.task, args.timeout):
        success, output = run_command(cmd_parts, args.timeout)
        if not success:
            print(f"[ERROR] 任务执行失败: {output}")
            sys.exit(1)
        print(output)
