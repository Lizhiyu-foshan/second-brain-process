#!/usr/bin/env python3
"""
代码审计任务 - 精简版，审计核心组件
"""
import os
os.environ["DASHSCOPE_API_KEY"] = "sk-sp-68f6997fc9924babb9f6b50c03a5a529"
os.environ["PYTHONUNBUFFERED"] = "1"

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 重定向到文件
log_file = "/tmp/code_audit_report.md"
f = open(log_file, "w", encoding='utf-8')
sys.stdout = f
sys.stderr = f

print("# 🔒 代码安全审计报告")
print()
print("**审计项目**: 双层任务编排系统 (Layer 0/1/2)")
print("**审计角色**: Auditor (代码审计与安全专家)")
print("**使用模型**: Qwen 3.5 Plus")
print()

from layer0.ai_client import get_ai_client

def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"[读取失败: {e}]"

# 核心文件列表（最可能有问题的地方）
core_files = {
    "Layer 1 - 锁管理": "layer1/lock_manager.py",
    "Layer 1 - 任务队列": "layer1/task_queue.py",
    "Layer 1 - 角色注册": "layer1/role_registry.py",
    "Layer 0 - 基础工作器": "layer0/base.py",
    "Layer 2 - 编排器": "layer2/orchestrator.py",
    "Layer 2 - 规划器": "layer2/planner.py",
}

project_dir = "/root/.openclaw/workspace/shared/pipeline"

print("## 📁 审计文件清单")
print()
for name, path in core_files.items():
    full_path = os.path.join(project_dir, path)
    exists = "✓" if os.path.exists(full_path) else "✗"
    print(f"- {exists} {name}: `{path}`")
print()

# 收集代码
code_sections = []
for name, path in core_files.items():
    full_path = os.path.join(project_dir, path)
    if os.path.exists(full_path):
        content = read_file(full_path)
        # 截断长文件
        lines = content.split('\n')
        if len(lines) > 80:
            content = '\n'.join(lines[:80]) + f"\n# ... ({len(lines)-80} lines omitted)"
        code_sections.append(f"### {name}\n**File**: `{path}`\n```python\n{content}\n```\n")

code_package = "\n".join(code_sections)

print("---")
print()
print("🤖 正在执行代码审计...")
print()

# 调用 Auditor
client = get_ai_client()

audit_prompt = f"""作为代码审计与安全专家，请对以下Python项目代码进行安全审计。

## 审计重点
1. 文件路径操作安全性 (path traversal)
2. 异常处理和资源释放
3. 并发安全问题
4. 敏感信息硬编码
5. 不安全的反序列化

## 代码内容

{code_package}

## 输出要求
请按以下格式输出审计报告：

### 执行摘要
- 安全评分 (0-100)
- 问题统计 (Critical/High/Medium/Low)

### 详细发现
对每个问题提供：
- 严重程度
- 文件位置
- 问题描述
- 修复代码示例

### 优先修复建议"""

response = client.call(
    role="auditor",
    task_description=audit_prompt,
    model="qwen3.5-plus",
    temperature=0.3,
    max_tokens=6000
)

if response["success"]:
    print(response["content"])
    print()
    print("---")
    print("✅ 审计完成")
else:
    print(f"❌ 审计失败: {response.get('error')}")

f.close()
