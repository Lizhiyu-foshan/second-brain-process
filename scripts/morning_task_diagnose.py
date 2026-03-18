#!/usr/bin/env python3
"""
自动诊断脚本 - morning_task_diagnose.py
快速诊断凌晨5:00任务的问题
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")

def run_command(cmd: list, timeout: int = 10) -> str:
    """执行命令并返回输出"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as e:
        return f"[ERROR] {e}"

def diagnose():
    """执行诊断"""
    print("=" * 60)
    print("凌晨5:00任务 - 自动诊断报告")
    print("=" * 60)
    
    issues = []
    
    # 1. 检查Cron任务
    print("\n[1/6] 检查Cron任务...")
    cron_output = run_command(["openclaw", "cron", "list"])
    # 查找凌晨相关的任务（可能是"凌晨5:00"或"凌晨任务"）
    has_morning_task = False
    for line in cron_output.split('\n'):
        if '凌晨' in line or ('5:00' in line and '0 5' in line):
            has_morning_task = True
            print(f"  ✅ 找到任务: {line.split()[1] if len(line.split()) > 1 else '未知'}")
            if 'ok' in line.lower():
                print("  ✅ 任务状态正常")
            elif 'idle' in line.lower():
                print("  ⏸️ 任务处于空闲状态")
            else:
                print(f"  ⚠️ 任务状态异常")
                issues.append("Cron任务状态异常")
            break
    
    if not has_morning_task:
        print("  ❌ 凌晨5:00任务不存在")
        issues.append("Cron任务不存在")
    
    # 2. 检查执行日志
    print("\n[2/6] 检查执行日志...")
    log_file = Path("/tmp/morning_process_execution.log")
    if log_file.exists():
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600
        print(f"  ✅ 日志存在，最后修改: {age_hours:.1f}小时前")
        
        content = log_file.read_text()
        if "状态：SUCCESS" in content:
            print("  ✅ 日志显示成功")
        elif "状态：FAILED" in content:
            print("  ❌ 日志显示失败")
            issues.append("任务执行失败")
        else:
            print("  ⚠️ 日志状态不明确")
    else:
        print("  ❌ 执行日志不存在")
        issues.append("执行日志不存在")
    
    # 3. 检查输出文件
    print("\n[3/6] 检查输出文件...")
    output_dir = WORKSPACE / "obsidian-vault" / "02-Conversations"
    if output_dir.exists():
        files = list(output_dir.glob(f"{datetime.now().strftime('%Y-%m-%d')}*.md"))
        if files:
            print(f"  ✅ 今日有 {len(files)} 个输出文件")
        else:
            print("  ⚠️ 今日无输出文件")
    else:
        print("  ❌ 输出目录不存在")
        issues.append("输出目录不存在")
    
    # 4. 检查Git状态
    print("\n[4/6] 检查Git状态...")
    git_output = run_command(["git", "-C", str(WORKSPACE), "status", "--porcelain"])
    if git_output:
        print(f"  ⚠️ 有未提交/推送的更改: {len(git_output.split(chr(10)))} 个文件")
    else:
        print("  ✅ Git工作区干净")
    
    # 5. 检查系统资源
    print("\n[5/6] 检查系统资源...")
    df_output = run_command(["df", "-h", "/"])
    if df_output:
        usage = df_output.split('\n')[1].split()[4].rstrip('%')
        if int(usage) > 90:
            print(f"  ⚠️ 磁盘使用率过高: {usage}%")
            issues.append(f"磁盘使用率过高: {usage}%")
        else:
            print(f"  ✅ 磁盘空间充足: {usage}%")
    
    free_output = run_command(["free", "-m"])
    if free_output:
        available = int(free_output.split('\n')[1].split()[6])
        if available < 500:
            print(f"  ⚠️ 可用内存不足: {available}MB")
            issues.append(f"内存不足: {available}MB")
        else:
            print(f"  ✅ 内存充足: {available}MB")
    
    # 6. 检查网络
    print("\n[6/6] 检查网络连接...")
    curl_output = run_command([
        "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
        "https://api.moonshot.cn"
    ], timeout=10)
    if curl_output == "200":
        print("  ✅ API服务器可访问")
    else:
        print(f"  ❌ API服务器返回: {curl_output}")
        issues.append("网络/API连接异常")
    
    # 总结
    print("\n" + "=" * 60)
    if issues:
        print(f"❌ 诊断完成，发现 {len(issues)} 个问题:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print("\n建议操作:")
        print("  1. 查看详细日志: tail -50 /tmp/morning_process_execution.log")
        print("  2. 手动执行: bash /root/.openclaw/workspace/second-brain-processor/run_morning_wrapper.sh")
        print("  3. 检查Cron配置: openclaw cron list")
    else:
        print("✅ 诊断完成，未发现问题")
    print("=" * 60)
    
    return len(issues) == 0

if __name__ == "__main__":
    success = diagnose()
    sys.exit(0 if success else 1)
