#!/usr/bin/env python3
"""
Second Brain Git 同步管理器
支持双向同步、自动重试、冲突处理
"""

import subprocess
import time
from pathlib import Path

VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")

def run_git_command(cmd: list, cwd: Path = VAULT_DIR, timeout: int = 60) -> tuple:
    """运行 git 命令，返回 (success, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return (result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (False, "", "Command timeout")
    except Exception as e:
        return (False, "", str(e))

def sync_to_github(max_retries: int = 3, retry_delay: int = 5) -> dict:
    """
    双向同步到 GitHub
    1. 先 fetch 远程更新
    2. 合并远程更改（处理 Obsidian 双向同步）
    3. 推送本地提交
    4. 失败自动重试
    """
    results = {
        "success": False,
        "steps": [],
        "retry_count": 0
    }
    
    for attempt in range(1, max_retries + 1):
        results["retry_count"] = attempt
        step_info = f"尝试 {attempt}/{max_retries}"
        
        # Step 1: Fetch 远程更新
        success, stdout, stderr = run_git_command(["git", "fetch", "origin", "main"], timeout=30)
        if not success:
            results["steps"].append({"step": "fetch", "status": "failed", "error": stderr})
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            break
        results["steps"].append({"step": "fetch", "status": "success"})
        
        # Step 2: 检查是否有远程更新需要合并
        success, stdout, stderr = run_git_command(["git", "rev-list", "--left-right", "HEAD...origin/main"])
        if success and stdout.strip():
            # 有远程更新，需要合并
            success, stdout, stderr = run_git_command(
                ["git", "merge", "-m", "Merge remote changes (auto-sync)", "origin/main"],
                timeout=30
            )
            if not success:
                # 合并失败，尝试强制使用我们的版本
                success, stdout, stderr = run_git_command(
                    ["git", "merge", "-X", "ours", "-m", "Merge with preference to local (auto-sync)", "origin/main"],
                    timeout=30
                )
                if not success:
                    results["steps"].append({"step": "merge", "status": "failed", "error": stderr})
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        continue
                    break
            results["steps"].append({"step": "merge", "status": "success", "note": "已合并远程更新"})
        else:
            results["steps"].append({"step": "merge", "status": "skipped", "note": "无需合并"})
        
        # Step 3: 推送
        success, stdout, stderr = run_git_command(["git", "push", "origin", "main"], timeout=60)
        if success:
            results["success"] = True
            results["steps"].append({"step": "push", "status": "success"})
            return results
        else:
            results["steps"].append({"step": "push", "status": "failed", "error": stderr})
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            break
    
    return results

def commit_and_sync(commit_message: str = None) -> dict:
    """
    提交本地更改并同步到 GitHub
    完整流程：add -> commit -> fetch -> merge -> push
    """
    if commit_message is None:
        from datetime import datetime
        commit_message = f"Vault update: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    results = {
        "success": False,
        "steps": []
    }
    
    # Step 1: Add
    success, stdout, stderr = run_git_command(["git", "add", "-A"])
    if not success:
        results["steps"].append({"step": "add", "status": "failed", "error": stderr})
        return results
    results["steps"].append({"step": "add", "status": "success"})
    
    # Step 2: Commit（如果没有更改会失败，这是正常的）
    success, stdout, stderr = run_git_command(["git", "commit", "-m", commit_message])
    if success:
        results["steps"].append({"step": "commit", "status": "success", "message": commit_message})
    elif "nothing to commit" in stderr.lower() or "nothing to commit" in stdout.lower():
        results["steps"].append({"step": "commit", "status": "skipped", "note": "无更改需要提交"})
    else:
        results["steps"].append({"step": "commit", "status": "failed", "error": stderr})
        return results
    
    # Step 3: Sync to GitHub
    sync_result = sync_to_github()
    results["steps"].extend(sync_result["steps"])
    results["success"] = sync_result["success"]
    results["retry_count"] = sync_result.get("retry_count", 0)
    
    # Step 4: 如果推送成功，更新 Dashboard
    if sync_result["success"]:
        try:
            from update_dashboard import update_dashboard
            dashboard_result = update_dashboard()
            results["dashboard_updated"] = dashboard_result.get("success", False)
            if not dashboard_result.get("success"):
                results["dashboard_error"] = dashboard_result.get("error")
        except Exception as e:
            results["dashboard_updated"] = False
            results["dashboard_error"] = str(e)
    
    return results

if __name__ == "__main__":
    import json
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "sync":
        # 仅同步，不提交
        result = sync_to_github()
    else:
        # 提交并同步
        msg = sys.argv[1] if len(sys.argv) > 1 else None
        result = commit_and_sync(msg)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
