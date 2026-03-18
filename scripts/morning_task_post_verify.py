#!/usr/bin/env python3
"""
执行后验证脚本 - morning_task_post_verify.py
验证凌晨5:00任务的执行结果
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
OUTPUT_DIR = WORKSPACE / "obsidian-vault" / "02-Conversations"
LOG_FILE = Path("/tmp/morning_process_execution.log")
EXECUTION_RECORD = Path("/tmp/morning_task_execution_record.json")

def check_execution_log() -> tuple:
    """检查执行日志"""
    if not LOG_FILE.exists():
        return False, "执行日志不存在", {}
    
    content = LOG_FILE.read_text()
    
    # 检查成功状态
    if "状态：SUCCESS" not in content:
        return False, "日志中未找到成功标记", {"log_snippet": content[-500:]}
    
    # 提取执行时间
    start_time = None
    end_time = None
    for line in content.split('\n'):
        if '启动时间：' in line:
            start_time = line.split('：')[1].strip()
        if '完成时间：' in line:
            end_time = line.split('：')[1].strip()
    
    return True, "执行日志验证通过", {
        "start_time": start_time,
        "end_time": end_time,
        "log_size": len(content)
    }

def check_output_files() -> tuple:
    """检查输出文件"""
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 查找今天和昨天生成的文件
    files = []
    for date_prefix in [today, yesterday]:
        pattern = f"{date_prefix}*.md"
        files.extend(OUTPUT_DIR.glob(pattern))
    
    if not files:
        return True, "今日无输出文件（可能没有新对话）", {"files_count": 0}
    
    # 验证文件内容
    valid_files = 0
    invalid_files = []
    
    for f in files:
        try:
            content = f.read_text(encoding='utf-8')
            
            # 检查YAML frontmatter
            has_frontmatter = content.startswith('---') and 'date:' in content
            
            # 检查内容非空
            has_content = len(content) > 100
            
            # 检查无乱码（简单检查）
            has_no_garbage = '\x00' not in content
            
            if has_frontmatter and has_content and has_no_garbage:
                valid_files += 1
            else:
                invalid_files.append({
                    "file": f.name,
                    "has_frontmatter": has_frontmatter,
                    "has_content": has_content
                })
        except Exception as e:
            invalid_files.append({"file": f.name, "error": str(e)})
    
    if invalid_files:
        return False, f"发现 {len(invalid_files)} 个无效文件", {
            "total_files": len(files),
            "valid_files": valid_files,
            "invalid_files": invalid_files
        }
    
    return True, f"所有 {len(files)} 个文件验证通过", {
        "total_files": len(files),
        "valid_files": valid_files
    }

def check_git_push() -> tuple:
    """检查Git推送"""
    try:
        # 检查是否有未推送的提交
        result = subprocess.run(
            ['git', '-C', str(WORKSPACE), 'log', '@{u}..HEAD', '--oneline'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.stdout.strip():
            unpushed = len(result.stdout.strip().split('\n'))
            return False, f"有 {unpushed} 个提交未推送", {
                "unpushed_commits": unpushed
            }
        
        # 检查最后一次提交时间
        result = subprocess.run(
            ['git', '-C', str(WORKSPACE), 'log', '-1', '--format=%ci'],
            capture_output=True, text=True, timeout=10
        )
        
        last_commit_time = datetime.fromisoformat(result.stdout.strip().replace(' ', 'T').replace(' +', '+'))
        hours_since_commit = (datetime.now() - last_commit_time.replace(tzinfo=None)).total_seconds() / 3600
        
        if hours_since_commit > 25:
            return False, f"最后一次提交是 {hours_since_commit:.1f} 小时前", {
                "last_commit_time": last_commit_time.isoformat()
            }
        
        return True, f"Git推送正常，最后一次提交 {hours_since_commit:.1f} 小时前", {
            "last_commit_time": last_commit_time.isoformat()
        }
        
    except Exception as e:
        return False, f"Git检查异常: {e}", {}

def check_timestamps() -> tuple:
    """检查时间戳连续性"""
    today_5am = datetime.now().replace(hour=5, minute=0, second=0, microsecond=0)
    
    # 检查执行日志时间戳
    if LOG_FILE.exists():
        mtime = datetime.fromtimestamp(LOG_FILE.stat().st_mtime)
        if mtime < today_5am:
            return False, f"执行日志时间戳异常: {mtime}", {"log_mtime": mtime.isoformat()}
    
    # 检查输出文件时间戳
    files = list(OUTPUT_DIR.glob(f"{datetime.now().strftime('%Y-%m-%d')}*.md"))
    if files:
        latest = max(files, key=lambda p: p.stat().st_mtime)
        latest_mtime = datetime.fromtimestamp(latest.stat().st_mtime)
        
        if latest_mtime < today_5am:
            return False, f"输出文件时间戳异常: {latest_mtime}", {
                "latest_file": latest.name,
                "latest_mtime": latest_mtime.isoformat()
            }
        
        return True, f"时间戳验证通过，最新文件: {latest.name}", {
            "latest_file": latest.name,
            "latest_mtime": latest_mtime.isoformat()
        }
    
    return True, "今日无输出文件，跳过时间戳检查", {}

def run_all_verifications() -> dict:
    """运行所有验证"""
    verifications = [
        ("执行日志检查", check_execution_log),
        ("时间戳检查", check_timestamps),
        ("输出文件检查", check_output_files),
        ("Git推送检查", check_git_push),
    ]
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "verifications": {},
        "all_passed": True
    }
    
    print("=" * 60)
    print("凌晨5:00任务 - 执行后验证")
    print("=" * 60)
    
    for name, verify_func in verifications:
        success, message, details = verify_func()
        status = "✅" if success else "❌"
        print(f"{status} {name}: {message}")
        
        results["verifications"][name] = {
            "passed": success,
            "message": message,
            "details": details
        }
        
        if not success:
            results["all_passed"] = False
    
    print("=" * 60)
    
    # 保存验证记录
    with open(EXECUTION_RECORD, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"验证记录已保存: {EXECUTION_RECORD}")
    
    return results

if __name__ == "__main__":
    results = run_all_verifications()
    sys.exit(0 if results['all_passed'] else 1)
