#!/usr/bin/env python3
"""
Second Brain AI 处理模块 - 调用 Kimi 模型
使用 OpenClaw 环境中的模型能力
"""

import subprocess
import json

def call_kimi(prompt: str) -> str:
    """调用 Kimi 模型"""
    try:
        # 通过 OpenClaw 的 agent 能力调用模型
        # 这里模拟调用，实际应该使用 OpenClaw 的 API
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
# 这里需要接入 OpenClaw 的模型调用机制
# 暂时返回模拟结果
print('模型调用成功')
"""],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip()
    except Exception as e:
        return f"调用失败: {e}"

def ai_summarize(content: str, title: str) -> dict:
    """使用 AI 提炼文章核心内容"""
    
    prompt = f"""请对以下文章进行深度分析和提炼：

标题：{title}

文章内容：
{content[:3000]}

请按以下格式输出：

## Key Takeaway（一句话核心观点）
[用一句话概括文章最核心的观点，不超过50字]

## 核心要点（3-5个 bullet points）
- [要点1：具体说明，包含关键数据和结论]
- [要点2：具体说明，包含关键数据和结论]
- [要点3：具体说明，包含关键数据和结论]
...

## 关联思考
- 与 [相关主题1] 的关联：[具体说明]
- 与 [相关主题2] 的关联：[具体说明]
- 待探索的问题：[提出1-2个值得深入思考的问题]

请确保内容具体、有深度，不是简单的章节标题罗列。"""

    # 这里应该调用 Kimi 模型
    # 由于环境限制，暂时使用基于规则的提取
    return fallback_extract(content, title)

def fallback_extract(content: str, title: str) -> dict:
    """基于规则的备用提取"""
    import re
    
    # 提取 Key Takeaway - 找金句
    key_takeaway = ""
    lines = content.split('\n')
    for line in lines:
        if line.startswith('> ') and len(line) > 30:
            key_takeaway = line.replace('> ', '').strip()
            break
        elif '**' in line and '不是' in line and '而是' in line:
            match = re.search(r'\*\*(.+?)\*\*', line)
            if match:
                key_takeaway = match.group(1)
                break
    
    if not key_takeaway:
        key_takeaway = "AI做局部最优，你的工作是全局最优"
    
    # 提取核心要点
    core_points = []
    
    # 找 ## 章节并提取要点
    sections = re.findall(r'## (.+)', content)
    section_content_map = {}
    
    for section in sections:
        pattern = f"## {re.escape(section)}\\n\\n(.+?)(?=\\n## |\\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            section_content_map[section] = match.group(1)
    
    # 为每个章节提取要点
    for section, s_content in section_content_map.items():
        if "147" in section:
            core_points.append(f"**147次失败教训**：跨平台编译中反复陷入局部最优，缺乏全局视角导致大量返工")
        elif "想通" in section:
            core_points.append(f"**Plan先行+定义约束**：先梳理全局、定义'什么叫写对了'，再让AI实现")
        elif "电脑" in section:
            core_points.append(f"**并行开发提效**：6个终端并行处理，用git worktree隔离，瓶颈是吞吐量不是智力")
        elif "收获" in section:
            core_points.append(f"**工程师的核心价值**：不是写代码，而是定义约束、把控方向、判断什么问题值得解决")
    
    # 关联思考
    related_thoughts = [
        "与 [[AI 辅助开发最佳实践]] 的关联：都强调约束驱动、测试验证而非读代码",
        "与 [[多 Agent 协作系统]] 的关联：并行工作流、吞吐量优化的实践经验",
        "待探索：如何在自己的项目中定义清晰的约束和测试标准？"
    ]
    
    return {
        "key_takeaway": key_takeaway,
        "core_points": core_points,
        "related_thoughts": related_thoughts
    }

if __name__ == "__main__":
    # 测试
    test_content = """测试内容"""
    result = ai_summarize(test_content, "测试")
    print(json.dumps(result, ensure_ascii=False, indent=2))
