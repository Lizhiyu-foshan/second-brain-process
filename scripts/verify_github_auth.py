#!/usr/bin/env python3
"""
verify_github_auth.py - GitHub 认证验证器
位置: /root/.openclaw/workspace/scripts/verify_github_auth.py
用途: 验证 GitHub 推送功能是否正常，异常时立即告警
"""

import subprocess
import sys
import json
from pathlib import Path

VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")


def run_git_command(args, cwd=VAULT_DIR, timeout=30):
    """运行 git 命令"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)


def check_github_auth():
    """检查 GitHub 认证状态"""
    results = {
        "timestamp": subprocess.run(["date", "+%Y-%m-%d %H:%M:%S"], capture_output=True, text=True).stdout.strip(),
        "checks": {},
        "overall_status": "unknown"
    }
    
    # 检查1: 远程 URL 配置
    success, stdout, stderr = run_git_command(["remote", "-v"])
    if success and "github.com" in stdout:
        results["checks"]["remote_config"] = {"status": "ok", "url": stdout.strip().split()[1]}
    else:
        results["checks"]["remote_config"] = {"status": "error", "message": "GitHub 远程未配置"}
    
    # 检查2: 测试连接（不实际推送）
    success, stdout, stderr = run_git_command(["ls-remote", "origin", "HEAD"])
    if success:
        results["checks"]["github_connection"] = {"status": "ok"}
        results["overall_status"] = "ok"
    else:
        results["checks"]["github_connection"] = {
            "status": "error", 
            "message": stderr,
            "hint": "可能需要重新配置 GitHub 认证"
        }
        results["overall_status"] = "error"
    
    # 检查3: 待推送提交
    success, stdout, stderr = run_git_command(["rev-list", "--count", "origin/main..HEAD"])
    if success:
        count = int(stdout.strip())
        results["checks"]["pending_commits"] = {"count": count}
        if count > 0:
            results["checks"]["pending_commits"]["status"] = "warning"
            results["checks"]["pending_commits"]["message"] = f"有 {count} 个提交待推送"
    
    # 检查4: GITHUB_TOKEN 环境变量
    import os
    if os.environ.get("GITHUB_TOKEN"):
        results["checks"]["env_token"] = {"status": "ok", "length": len(os.environ.get("GITHUB_TOKEN"))}
    else:
        results["checks"]["env_token"] = {"status": "warning", "message": "GITHUB_TOKEN 未设置"}
    
    # 检查5: git 凭据存储
    cred_file = Path.home() / ".git-credentials"
    if cred_file.exists() and cred_file.stat().st_size > 0:
        results["checks"]["git_credentials"] = {"status": "ok"}
    else:
        results["checks"]["git_credentials"] = {"status": "warning", "message": "~/.git-credentials 为空或不存在"}
    
    return results


def send_alert(message):
    """发送告警通知"""
    # 这里可以集成飞书通知
    alert_file = Path("/root/.openclaw/workspace/.learnings/alerts.md")
    from datetime import datetime
    with open(alert_file, 'a') as f:
        f.write(f"\n[{datetime.now()}] 🚨 {message}\n")
    print(f"🚨 告警已记录: {message}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="验证 GitHub 认证状态")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--silent", action="store_true", help="静默模式，只在出错时输出")
    args = parser.parse_args()
    
    results = check_github_auth()
    
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif not args.silent:
        print(f"\n📊 GitHub 认证状态检查 ({results['timestamp']})")
        print("="*50)
        
        for check_name, check_result in results["checks"].items():
            status = check_result.get("status", "unknown")
            icon = {"ok": "✅", "warning": "⚠️", "error": "❌"}.get(status, "❓")
            print(f"\n{icon} {check_name}:")
            if "message" in check_result:
                print(f"   {check_result['message']}")
            if "count" in check_result:
                print(f"   数量: {check_result['count']}")
        
        print("\n" + "="*50)
        overall = results["overall_status"]
        if overall == "ok":
            print("✅ 整体状态: 正常")
        else:
            print(f"❌ 整体状态: {overall}")
            if not args.silent:
                send_alert("GitHub 认证检查失败，请检查凭据配置")
    
    # 如果状态异常，发送告警
    if results["overall_status"] == "error":
        send_alert(f"GitHub 认证异常: {results['checks'].get('github_connection', {}).get('message', '未知错误')}")
    
    sys.exit(0 if results["overall_status"] == "ok" else 1)


if __name__ == "__main__":
    main()
