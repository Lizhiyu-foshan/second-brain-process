#!/usr/bin/env python3
"""
Migration Script Generator
生成版本迁移脚本和回滚方案
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# 配置
MIGRATION_DIR = Path("/root/.openclaw/workspace/migrations")
MIGRATION_LOG = Path("/root/.openclaw/workspace/.migration_log.json")

# 已知版本迁移指南
KNOWN_MIGRATIONS = {
    "2026.2.12_to_2026.2.13": {
        "breaking_changes": [
            "isolated + agentTurn 模式下子 Agent 无法调用工具"
        ],
        "migration_steps": [
            {
                "step": 1,
                "action": "backup_cron_jobs",
                "command": "openclaw cron list --format json > /tmp/cron_backup.json",
                "description": "备份当前定时任务配置"
            },
            {
                "step": 2,
                "action": "update_session_target",
                "description": "将 isolated 改为 main，将 agentTurn 改为 systemEvent",
                "manual": True
            },
            {
                "step": 3,
                "action": "test_cron_jobs",
                "command": "openclaw cron run <job_id> --force",
                "description": "测试每个定时任务是否正常执行"
            }
        ],
        "rollback_steps": [
            {
                "step": 1,
                "action": "restore_cron_jobs",
                "command": "cat /tmp/cron_backup.json | openclaw cron apply",
                "description": "恢复之前的定时任务配置"
            }
        ]
    }
}


def generate_migration_script(from_version, to_version, output_path=None):
    """生成迁移脚本"""
    print(f"=== 生成迁移脚本 ===")
    print(f"From: {from_version}")
    print(f"To: {to_version}")
    
    migration_key = f"{from_version}_to_{to_version}"
    
    if migration_key in KNOWN_MIGRATIONS:
        migration = KNOWN_MIGRATIONS[migration_key]
    else:
        # 生成通用迁移模板
        migration = generate_generic_migration(from_version, to_version)
    
    # 生成迁移脚本
    script_lines = [
        "#!/bin/bash",
        f"# Migration Script: {from_version} → {to_version}",
        f"# Generated: {datetime.now().isoformat()}",
        "",
        "set -e  # 遇错停止",
        "",
        "echo '=== 开始迁移 ==='",
        ""
    ]
    
    for step in migration.get("migration_steps", []):
        script_lines.append(f"# Step {step['step']}: {step['action']}")
        script_lines.append(f"echo 'Step {step['step']}: {step['description']}'")
        
        if step.get("manual"):
            script_lines.append("echo '[需要手动操作]'")
            script_lines.append(f"echo '{step['description']}'")
            script_lines.append("read -p '完成后按回车继续...'")
        elif step.get("command"):
            script_lines.append(step["command"])
        
        script_lines.append("")
    
    # 添加回滚部分
    script_lines.extend([
        "echo '=== 迁移完成 ==='",
        "",
        "# 回滚脚本（如需回滚，取消下面的注释）",
        "# echo '=== 开始回滚 ==='"
    ])
    
    for step in migration.get("rollback_steps", []):
        script_lines.append(f"# {step['description']}")
        if step.get("command"):
            script_lines.append(f"# {step['command']}")
    
    script_content = "\n".join(script_lines)
    
    # 保存脚本
    if output_path:
        with open(output_path, "w") as f:
            f.write(script_content)
        print(f"\n✅ 迁移脚本已保存: {output_path}")
    else:
        print("\n=== 迁移脚本 ===")
        print(script_content)
    
    return migration


def generate_generic_migration(from_version, to_version):
    """生成通用迁移模板"""
    return {
        "migration_steps": [
            {
                "step": 1,
                "action": "backup_config",
                "command": "cp -r /root/.openclaw /root/.openclaw.backup",
                "description": "备份当前配置"
            },
            {
                "step": 2,
                "action": "check_compatibility",
                "command": f"python3 /root/.openclaw/workspace/skills/openclaw-version-adapter/scripts/test_compatibility.py",
                "description": "运行兼容性测试"
            },
            {
                "step": 3,
                "action": "update_openclaw",
                "manual": True,
                "description": "更新 OpenClaw 版本（根据官方文档）"
            },
            {
                "step": 4,
                "action": "verify_update",
                "command": "openclaw gateway status",
                "description": "验证更新成功"
            }
        ],
        "rollback_steps": [
            {
                "step": 1,
                "action": "restore_config",
                "command": "rm -rf /root/.openclaw && mv /root/.openclaw.backup /root/.openclaw",
                "description": "恢复之前的配置"
            }
        ]
    }


def log_migration(action, details):
    """记录迁移日志"""
    log = []
    if MIGRATION_LOG.exists():
        with open(MIGRATION_LOG, "r") as f:
            log = json.load(f)
    
    log.append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "details": details
    })
    
    with open(MIGRATION_LOG, "w") as f:
        json.dump(log, f, indent=2)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="生成 OpenClaw 版本迁移脚本")
    parser.add_argument("--from", dest="from_version", required=True, help="当前版本")
    parser.add_argument("--to", dest="to_version", required=True, help="目标版本")
    parser.add_argument("--output", "-o", help="输出文件路径")
    
    args = parser.parse_args()
    
    # 创建迁移目录
    MIGRATION_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成输出路径
    output_path = args.output or MIGRATION_DIR / f"migrate_{args.from_version}_to_{args.to_version}.sh"
    
    # 生成迁移脚本
    migration = generate_migration_script(args.from_version, args.to_version, output_path)
    
    # 记录日志
    log_migration("generate_migration", {
        "from": args.from_version,
        "to": args.to_version,
        "output": str(output_path)
    })
    
    # 输出破坏性变更警告
    if migration.get("breaking_changes"):
        print("\n⚠️  破坏性变更警告:")
        for change in migration["breaking_changes"]:
            print(f"  - {change}")
    
    sys.exit(0)