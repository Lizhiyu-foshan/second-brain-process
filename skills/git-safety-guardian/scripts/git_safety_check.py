#!/usr/bin/env python3
"""
Git 安全检查脚本 - git-safety-check

功能：
1. 检查当前目录是否在git仓库内
2. 验证remote URL是否正确
3. 检查当前分支
4. 检测嵌套仓库结构（防止误推送到子目录仓库）
5. 高危操作（--force）二次确认

使用方法：
    python3 git_safety_check.py [--pre-push]

退出码：
    0 - 检查通过
    1 - 检查失败，需处理
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple, List, Optional


def run_git_command(args: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """运行git命令，返回 (returncode, stdout, stderr)"""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=10
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def is_git_repository(path: Path = None) -> bool:
    """检查当前目录是否是git仓库"""
    cwd = path or Path.cwd()
    git_dir = cwd / ".git"
    
    # 检查.git目录是否存在
    if git_dir.exists():
        return True
    
    # 尝试运行git status
    code, _, _ = run_git_command(["status"], cwd=cwd)
    return code == 0


def get_current_branch(cwd: Path = None) -> Optional[str]:
    """获取当前分支名称"""
    code, stdout, _ = run_git_command(["branch", "--show-current"], cwd=cwd)
    if code == 0 and stdout:
        return stdout
    return None


def get_remote_url(cwd: Path = None) -> Optional[str]:
    """获取remote URL"""
    code, stdout, _ = run_git_command(["remote", "get-url", "origin"], cwd=cwd)
    if code == 0 and stdout:
        return stdout
    return None


def find_nested_git_repos(start_path: Path = None, max_depth: int = 3) -> List[Path]:
    """
    查找嵌套的git仓库
    返回相对于当前目录的嵌套仓库路径列表
    """
    start = start_path or Path.cwd()
    nested = []
    
    # 递归查找子目录中的.git
    for i in range(1, max_depth + 1):
        pattern = "/".join(["*"] * i) + "/.git"
        for git_dir in start.glob(pattern):
            if git_dir.is_dir():
                repo_root = git_dir.parent.relative_to(start)
                nested.append(repo_root)
    
    return nested


def check_push_safety(cwd: Path = None, is_force: bool = False) -> Tuple[bool, List[str]]:
    """
    执行完整的推送安全检查
    
    返回: (is_safe, messages)
    """
    messages = []
    is_safe = True
    cwd = cwd or Path.cwd()
    
    # 检查1: 是否是git仓库
    messages.append("🔍 检查1: Git仓库验证")
    if not is_git_repository(cwd):
        messages.append("   ❌ 当前目录不是Git仓库")
        return False, messages
    messages.append("   ✅ 当前目录是有效的Git仓库")
    
    # 检查2: 当前分支
    messages.append("\n🔍 检查2: 当前分支")
    branch = get_current_branch(cwd)
    if branch:
        messages.append(f"   ✅ 当前分支: {branch}")
        # 警告：如果在main/master分支
        if branch in ["main", "master"]:
            messages.append(f"   ⚠️  警告: 你在 {branch} 分支上，请确保操作正确")
    else:
        messages.append("   ⚠️  无法获取当前分支信息")
    
    # 检查3: Remote URL
    messages.append("\n🔍 检查3: Remote URL")
    remote = get_remote_url(cwd)
    if remote:
        messages.append(f"   ✅ Remote: {remote}")
        
        # 检查是否是obsidian-vault（特殊保护）
        if "obsidian-vault" in remote.lower():
            messages.append("   ⚠️  警告: 目标是笔记仓库(obsidian-vault)，请确认推送内容正确")
            is_safe = False
    else:
        messages.append("   ⚠️  无法获取remote URL")
    
    # 检查4: 嵌套仓库检测
    messages.append("\n🔍 检查4: 嵌套仓库检测")
    nested = find_nested_git_repos(cwd)
    if nested:
        messages.append(f"   ⚠️  发现 {len(nested)} 个嵌套仓库:")
        for n in nested[:5]:  # 最多显示5个
            messages.append(f"      - {n}")
        if len(nested) > 5:
            messages.append(f"      ... 还有 {len(nested) - 5} 个")
        messages.append("   💡 提示: 确保你在正确的目录层级执行推送")
    else:
        messages.append("   ✅ 未发现嵌套仓库")
    
    # 检查5: 高危操作警告
    if is_force:
        messages.append("\n🔍 检查5: 高危操作检测")
        messages.append("   🚨 警告: 你正在使用 --force 推送")
        messages.append("   🚨 这将覆盖远程历史，可能导致数据丢失")
        is_safe = False
    
    return is_safe, messages


def interactive_confirm(messages: List[str]) -> bool:
    """交互式确认"""
    print("\n" + "="*50)
    print("Git 安全检查报告")
    print("="*50)
    for msg in messages:
        print(msg)
    print("="*50)
    
    while True:
        choice = input("\n是否继续推送? (yes/no): ").strip().lower()
        if choice in ["yes", "y"]:
            return True
        elif choice in ["no", "n", ""]:
            return False
        print("请输入 yes 或 no")


def install_pre_push_hook(repo_path: Path = None) -> bool:
    """
    安装pre-push钩子
    """
    cwd = repo_path or Path.cwd()
    git_dir = cwd / ".git"
    
    if not git_dir.exists():
        print("❌ 当前目录不是Git仓库")
        return False
    
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    
    hook_file = hooks_dir / "pre-push"
    
    hook_content = """#!/bin/bash
# Git Safety Guardian - Pre-push Hook
# 自动在推送前执行安全检查

echo "🔒 Git Safety Guardian: 执行推送前安全检查..."

# 检查是否是强制推送
if [[ "$@" == *"--force"* ]] || [[ "$@" == *"-f"* ]]; then
    IS_FORCE="--force"
fi

# 运行安全检查
python3 ~/.openclaw/skills/git-safety-guardian/scripts/git_safety_check.py --pre-push $IS_FORCE

exit $?
"""
    
    try:
        hook_file.write_text(hook_content, encoding='utf-8')
        hook_file.chmod(0o755)  # 添加执行权限
        print(f"✅ 已安装pre-push钩子: {hook_file}")
        return True
    except Exception as e:
        print(f"❌ 安装钩子失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Git 安全检查工具')
    parser.add_argument('--pre-push', action='store_true', 
                        help='作为pre-push钩子运行（非交互模式）')
    parser.add_argument('--force', '-f', action='store_true',
                        help='标记为强制推送检查')
    parser.add_argument('--install-hook', action='store_true',
                        help='在当前仓库安装pre-push钩子')
    
    args = parser.parse_args()
    
    # 安装钩子模式
    if args.install_hook:
        success = install_pre_push_hook()
        sys.exit(0 if success else 1)
    
    # 安全检查模式
    is_safe, messages = check_push_safety(is_force=args.force)
    
    if args.pre_push:
        # 钩子模式：输出到stderr，失败时阻止推送
        for msg in messages:
            print(msg, file=sys.stderr)
        
        if not is_safe:
            print("\n❌ 安全检查未通过，推送已阻止", file=sys.stderr)
            print("   如需强制推送，请使用: git push --force", file=sys.stderr)
            sys.exit(1)
        else:
            print("\n✅ 安全检查通过，允许推送", file=sys.stderr)
            sys.exit(0)
    else:
        # 交互模式
        for msg in messages:
            print(msg)
        
        if not is_safe or args.force:
            if interactive_confirm([]):
                print("\n✅ 用户确认，继续操作")
                sys.exit(0)
            else:
                print("\n❌ 用户取消操作")
                sys.exit(1)
        else:
            print("\n✅ 安全检查通过")
            sys.exit(0)


if __name__ == "__main__":
    main()
