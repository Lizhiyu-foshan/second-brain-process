#!/usr/bin/env python3
"""
OpenClaw Compatibility Tester
测试关键 API 和功能的兼容性
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 测试配置
TEST_RESULTS_FILE = Path("/root/.openclaw/workspace/.compatibility_tests.json")

# 关键功能测试清单
CRITICAL_TESTS = [
    {
        "name": "gateway_status",
        "description": "Gateway 状态检查",
        "command": ["openclaw", "gateway", "status"],
        "timeout": 10,
        "expected_returncode": 0
    },
    {
        "name": "session_list",
        "description": "会话列表查询",
        "command": ["openclaw", "sessions", "list", "--limit", "5"],
        "timeout": 15,
        "expected_returncode": 0
    },
    {
        "name": "cron_list",
        "description": "定时任务列表",
        "command": ["openclaw", "cron", "list"],
        "timeout": 10,
        "expected_returncode": 0
    }
]

# Agent 模式测试（检测 isolated + agentTurn 问题）
AGENT_MODE_TESTS = [
    {
        "name": "isolated_agent_test",
        "description": "测试 isolated session 中的 agentTurn 模式",
        "note": "此测试需要在实际 isolated session 中执行",
        "simulated": True,
        "expected_behavior": "工具调用应该成功执行"
    }
]


def run_command_test(test):
    """运行命令测试"""
    print(f"\n测试: {test['name']}")
    print(f"描述: {test['description']}")
    print(f"命令: {' '.join(test['command'])}")
    
    result = {
        "name": test["name"],
        "description": test["description"],
        "timestamp": datetime.now().isoformat(),
        "status": "unknown"
    }
    
    try:
        proc = subprocess.run(
            test["command"],
            capture_output=True,
            text=True,
            timeout=test.get("timeout", 30)
        )
        
        result["returncode"] = proc.returncode
        result["stdout"] = proc.stdout[:500]  # 截断输出
        result["stderr"] = proc.stderr[:500]
        
        if proc.returncode == test.get("expected_returncode", 0):
            result["status"] = "passed"
            print("✅ PASSED")
        else:
            result["status"] = "failed"
            print(f"❌ FAILED (returncode: {proc.returncode})")
            if proc.stderr:
                print(f"Error: {proc.stderr[:200]}")
    
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        print(f"⏱️ TIMEOUT ({test.get('timeout', 30)}s)")
    
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"💥 ERROR: {e}")
    
    return result


def check_known_issues():
    """检查已知问题"""
    issues = []
    
    # 检查 isolated + agentTurn 问题
    # 这是 OpenClaw 2026.2.13 版本的已知问题
    print("\n=== 检查已知问题 ===")
    
    # 检查定时任务配置
    try:
        result = subprocess.run(
            ["openclaw", "cron", "list", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            cron_jobs = json.loads(result.stdout)
            isolated_jobs = [j for j in cron_jobs if j.get("sessionTarget") == "isolated"]
            
            if isolated_jobs:
                issues.append({
                    "type": "isolated_agentTurn_risk",
                    "severity": "warning",
                    "message": f"发现 {len(isolated_jobs)} 个使用 isolated session 的定时任务，存在工具调用失败风险",
                    "affected_jobs": [j.get("id") for j in isolated_jobs]
                })
                print(f"⚠️ Warning: {len(isolated_jobs)} isolated jobs found")
    
    except Exception as e:
        print(f"Could not check cron jobs: {e}")
    
    return issues


def run_compatibility_tests():
    """运行所有兼容性测试"""
    print("=== OpenClaw Compatibility Tests ===")
    print(f"Time: {datetime.now().isoformat()}")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": [],
        "issues": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "timeout": 0,
            "error": 0
        }
    }
    
    # 运行关键功能测试
    print("\n=== 关键功能测试 ===")
    for test in CRITICAL_TESTS:
        result = run_command_test(test)
        results["tests"].append(result)
        results["summary"]["total"] += 1
        results["summary"][result["status"]] += 1
    
    # 检查已知问题
    results["issues"] = check_known_issues()
    
    # 保存结果
    with open(TEST_RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    # 输出摘要
    print("\n=== 测试摘要 ===")
    print(f"Total: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Timeout: {results['summary']['timeout']}")
    print(f"Error: {results['summary']['error']}")
    
    if results["issues"]:
        print(f"\n⚠️ 发现 {len(results['issues'])} 个潜在问题")
        for issue in results["issues"]:
            print(f"  - [{issue['severity']}] {issue['message']}")
    
    # 返回状态
    all_passed = results["summary"]["passed"] == results["summary"]["total"]
    no_critical_issues = not any(i["severity"] == "critical" for i in results["issues"])
    
    return all_passed and no_critical_issues


if __name__ == "__main__":
    success = run_compatibility_tests()
    sys.exit(0 if success else 1)