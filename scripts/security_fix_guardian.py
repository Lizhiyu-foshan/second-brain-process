#!/usr/bin/env python3
"""
security_fix_guardian.py - 安全修复拦截器
位置: /root/.openclaw/workspace/scripts/security_fix_guardian.py
用途: 拦截任何涉及凭据的危险操作，强制人工确认
"""

import sys
import os
import subprocess
import re
from datetime import datetime

# 危险操作模式（涉及凭据/认证）
DANGEROUS_PATTERNS = [
    # GitHub/Git 相关
    (r'GITHUB_TOKEN', 'GitHub Token 环境变量'),
    (r'git.*credentials', 'Git 凭据文件'),
    (r'\.git-credentials', 'Git 凭据存储'),
    (r'rm.*-f.*credentials', '删除凭据文件'),
    (r'echo.*>.*credentials', '覆盖凭据文件'),
    (r'>.*/\.git-credentials', '清空 Git 凭据'),
    (r'git.*push.*https://.*@github', 'HTTPS 推送（含凭据）'),
    
    # Token 相关
    (r'ghp_[a-zA-Z0-9]{36,}', 'GitHub Personal Access Token'),
    (r'github_pat_[a-zA-Z0-9]{22,}', 'GitHub Fine-grained Token'),
    (r'sk-[a-zA-Z0-9]{48,}', 'API Secret Key'),
    
    # 环境变量操作
    (r'unset.*TOKEN', '删除 Token 环境变量'),
    (r'unset.*KEY', '删除 Key 环境变量'),
    (r'export.*TOKEN=', '设置 Token 环境变量'),
    
    # SSH 相关
    (r'rm.*-f.*\.ssh/id_', '删除 SSH 密钥'),
    (r'rm.*-rf.*\.ssh', '删除整个 SSH 目录'),
]

# 熔断机制记录文件
CIRCUIT_BREAKER_FILE = "/tmp/security_fix_circuit_breaker"
MAX_FIXES_PER_HOUR = 3


def log_interception(operation, pattern):
    """记录拦截日志"""
    log_file = "/root/.openclaw/workspace/.learnings/security_fix_interceptions.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] 拦截: {operation} | 匹配: {pattern}\n")


def check_circuit_breaker():
    """检查熔断机制 - 防止连环事故"""
    try:
        if os.path.exists(CIRCUIT_BREAKER_FILE):
            with open(CIRCUIT_BREAKER_FILE, 'r') as f:
                count = int(f.read().strip() or 0)
            # 检查文件修改时间
            mtime = os.path.getmtime(CIRCUIT_BREAKER_FILE)
            if datetime.now().timestamp() - mtime < 3600:  # 1小时内
                if count >= MAX_FIXES_PER_HOUR:
                    print("🚨🚨🚨 熔断机制触发！")
                    print(f"   1小时内已执行 {count} 次安全修复")
                    print("   为防止连环事故，已暂停自动修复")
                    print("   请人工检查后再继续")
                    return False
            else:
                # 超过1小时，重置计数
                count = 0
        else:
            count = 0
        
        # 更新计数
        with open(CIRCUIT_BREAKER_FILE, 'w') as f:
            f.write(str(count + 1))
        return True
    except Exception as e:
        print(f"⚠️ 熔断机制检查失败: {e}")
        return True  # 失败时允许继续，但不安全


def is_dangerous_operation(command):
    """检查命令是否涉及凭据操作"""
    command_lower = command.lower()
    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, description, pattern
    return False, None, None


def require_user_confirmation(command, description):
    """要求用户明确确认"""
    print("\n" + "="*60)
    print("🚨🚨🚨 检测到危险操作 - 涉及凭据/认证 🚨🚨🚨")
    print("="*60)
    print(f"\n操作类型: {description}")
    print(f"完整命令: {command}")
    print("\n⚠️  根据事故教训（2026-03-18），此类操作必须:")
    print("   1. ✅ 创建备份")
    print("   2. ✅ 用户明确确认")
    print("   3. ✅ 准备回滚方案")
    print("   4. ✅ 修改后立即验证")
    print("\n❌ 禁止：未经确认直接删除/修改凭据")
    print("="*60)
    
    # 强制输入确认码
    confirm_code = "DELETE_CREDENTIAL_" + datetime.now().strftime("%H%M")
    print(f"\n请输入确认码以继续: {confirm_code}")
    user_input = input("> ")
    
    if user_input != confirm_code:
        print("\n❌ 确认码错误，操作被拒绝")
        log_interception(command, "用户拒绝确认")
        return False
    
    return True


def create_backup():
    """创建凭据备份"""
    print("\n📦 正在创建凭据备份...")
    result = subprocess.run(
        ['/root/.openclaw/workspace/scripts/credential_backup.sh'],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("✅ 备份完成")
        return True
    else:
        print(f"⚠️ 备份失败: {result.stderr}")
        response = input("备份失败，是否继续? (yes/no): ")
        return response.lower() == 'yes'


def main():
    if len(sys.argv) < 2:
        print("Usage: security_fix_guardian.py <command>")
        sys.exit(1)
    
    command = ' '.join(sys.argv[1:])
    
    # 检查是否是危险操作
    is_dangerous, description, pattern = is_dangerous_operation(command)
    
    if not is_dangerous:
        # 非危险操作，直接执行
        sys.exit(os.system(command))
    
    # 危险操作 - 进入拦截流程
    log_interception(command, description)
    
    # 检查熔断机制
    if not check_circuit_breaker():
        sys.exit(1)
    
    # 要求用户确认
    if not require_user_confirmation(command, description):
        sys.exit(1)
    
    # 创建备份
    if not create_backup():
        sys.exit(1)
    
    # 执行操作
    print(f"\n⚡ 执行: {command}")
    result = os.system(command)
    
    # 验证功能
    if result == 0:
        print("\n🔍 正在验证关键功能...")
        # 这里可以添加具体的验证逻辑
        print("✅ 操作完成，请手动验证相关功能是否正常")
    
    sys.exit(result)


if __name__ == '__main__':
    main()
