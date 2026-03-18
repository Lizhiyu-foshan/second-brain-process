#!/usr/bin/env python3
"""
进化日志健康检查集成

在每天 4:30 的健康检查中调用，检查进化日志状态
"""

import json
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
SCANNER_PATH = WORKSPACE / "scripts" / "evolution_scanner.py"

def check_evolution():
    """执行进化日志检查"""
    print("🔍 执行进化日志检查...")
    
    try:
        result = subprocess.run(
            ['python3', str(SCANNER_PATH), '--check'],
            capture_output=True, text=True, timeout=60
        )
        
        # 解析 JSON 输出（找到最后一个 JSON 对象）
        lines = result.stdout.strip().split('\n')
        data = None
        for line in reversed(lines):
            line = line.strip()
            if line and line.startswith('{'):
                try:
                    data = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        
        if data is None:
            print("⚠️ 无法解析进化日志检查结果")
            return {"healthy": False, "message": "解析失败"}
        
        stats = data.get("stats", data)  # 兼容直接返回 stats 的情况
        warnings = data.get("warnings", [])
        has_warnings = data.get("has_warnings", len(warnings) > 0)
        
        # 生成健康状态
        if has_warnings:
            return {
                "healthy": False,
                "message": f"发现 {len(warnings)} 个告警",
                "warnings": warnings,
                "stats": {
                    "errors": stats.get("errors", 0),
                    "learnings": stats.get("learnings", 0),
                    "improvements": stats.get("improvements", 0),
                    "commits": stats.get("commits", 0)
                }
            }
        else:
            return {
                "healthy": True,
                "message": f"进化正常 (错误:{stats.get('errors',0)} 学习:{stats.get('learnings',0)} 改进:{stats.get('improvements',0)})",
                "stats": {
                    "errors": stats.get("errors", 0),
                    "learnings": stats.get("learnings", 0),
                    "improvements": stats.get("improvements", 0),
                    "commits": stats.get("commits", 0)
                }
            }
            
    except subprocess.TimeoutExpired:
        return {"healthy": False, "message": "进化日志检查超时"}
    except Exception as e:
        import traceback
        return {"healthy": False, "message": f"检查异常: {e}", "traceback": traceback.format_exc()}

if __name__ == "__main__":
    result = check_evolution()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 如果有告警，退出码为 1
    if not result.get("healthy", True):
        sys.exit(1)
