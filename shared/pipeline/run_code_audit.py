#!/usr/bin/env python3
"""
代码审计任务 - 使用 Auditor 角色对项目进行安全审计
"""
import os
os.environ["DASHSCOPE_API_KEY"] = "sk-sp-68f6997fc9924babb9f6b50c03a5a529"

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("🔒 代码安全审计报告")
print("=" * 80)
print()

from layer0.ai_client import get_ai_client

# 收集项目代码
def collect_code_files(project_dir, extensions=['.py']):
    """收集项目中的所有Python代码文件"""
    files = []
    for ext in extensions:
        files.extend(Path(project_dir).rglob(f"*{ext}"))
    return [f for f in files if '__pycache__' not in str(f) and '.git' not in str(f)]

def read_file_content(file_path, max_lines=100):
    """读取文件内容，限制行数"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:max_lines]
            return ''.join(lines)
    except Exception as e:
        return f"[读取失败: {e}]"

# 项目目录
project_dir = "/root/.openclaw/workspace/shared/pipeline"

print(f"📁 审计项目: {project_dir}")
print()

# 收集代码文件
code_files = collect_code_files(project_dir)
print(f"📊 发现 {len(code_files)} 个代码文件")
print()

# 准备审计内容
audit_content = []
for file_path in code_files[:20]:  # 限制文件数量避免过长
    rel_path = file_path.relative_to(project_dir)
    content = read_file_content(file_path, max_lines=50)
    audit_content.append(f"## 文件: {rel_path}\n```python\n{content}\n```\n")

code_package = "\n".join(audit_content)

print("🤖 启动 Auditor 进行代码审计...")
print("   (使用 Qwen 3.5 Plus 模型)")
print()

# 调用 AI 审计
client = get_ai_client()

audit_prompt = f"""请对以下Python项目代码进行全面的安全审计和代码质量分析。

## 审计范围
- 项目类型: 双层任务编排系统 (Layer 0/1/2 架构)
- 文件数量: {len(code_files)} 个Python文件
- 关键组件: RoleRegistry, LockManager, TaskQueue, Orchestrator, Planner

## 审计要求
请重点检查以下安全问题：

1. **安全漏洞**
   - 路径遍历 (Path Traversal)
   - 命令注入 (Command Injection)
   - 不安全的反序列化
   - 敏感信息硬编码
   - 不安全的文件操作

2. **代码质量问题**
   - 异常处理是否完善
   - 资源释放（锁、文件句柄）
   - 并发安全问题
   - 输入验证

3. **架构安全**
   - 权限控制
   - 数据隔离
   - 状态一致性

## 代码内容

{code_package}

## 输出格式
请输出结构化的审计报告：

### 1. 执行摘要
- 总体安全评分 (0-100)
- 发现问题数量（按严重程度分类）
- 总体风险评估

### 2. 详细发现
对每个问题提供：
- 严重程度: Critical / High / Medium / Low
- 位置: 文件路径和行号
- 问题描述
- 潜在影响
- 修复建议
- 修复代码示例

### 3. 优先修复清单
按优先级排序的修复任务

### 4. 改进建议
代码质量、架构层面的长期改进建议"""

response = client.call(
    role="auditor",
    task_description=audit_prompt,
    model="qwen3.5-plus",
    temperature=0.3,
    max_tokens=8000
)

if response["success"]:
    print("=" * 80)
    print("📋 审计结果")
    print("=" * 80)
    print()
    print(response["content"])
    print()
    print("=" * 80)
    print("✅ 代码审计完成")
    print("=" * 80)
else:
    print(f"❌ 审计失败: {response.get('error')}")
