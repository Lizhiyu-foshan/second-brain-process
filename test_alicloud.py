#!/usr/bin/env python3
"""
阿里百炼API调用测试
"""

import subprocess
import json

# 使用openclaw调用阿里百炼模型
result = subprocess.run(
    [
        "openclaw", "sessions", "spawn",
        "--task", "分析这段对话的核心主题：用户讨论了Harness Engineering概念，认为模型不是关键，Harness才是。请输出JSON格式，包含主题名称和核心观点。",
        "--agentId", "main",
        "--model", "alicloud/qwen3.5-plus",
        "--timeoutSeconds", "60"
    ],
    capture_output=True,
    text=True,
    timeout=70
)

print(f"返回码: {result.returncode}")
print(f"stdout:\n{result.stdout[:2000]}")
print(f"stderr:\n{result.stderr[:500]}")
