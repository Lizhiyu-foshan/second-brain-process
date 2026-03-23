#!/usr/bin/env python3
"""
step1_identify_essence.py - v2.1 四步法第1步
主题精华识别 - 调用kimi-coding/k2p5分析对话内容
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any

# Prompt设计
IDENTIFY_ESSENCE_PROMPT = """你是一位深度对话分析专家。请分析以下对话内容：

【对话内容】
{conversation_content}

【分析任务】
1. 识别所有涉及以下领域的深度讨论：
   - 哲学：存在论、认识论、伦理学、自由意志等
   - 社会学：社会结构、群体行为、文化演变、价值体系等
   - 系统论：复杂系统、涌现、反馈循环、架构设计等
   - 技术冲击：AI对人类社会、工作、认知的深远影响
   - 系统设计：对长期运行有重大影响的技术决策

2. 不看重对话轮数，看重内容深度和思想价值
   - 10轮深度讨论 > 50轮闲聊
   - 一个顿悟时刻 > 大量重复确认

3. 对每处识别出的精华，提取：
   - 主题名称（简洁有力，10字以内）
   - 对话片段（原文引用，保留发言人）
   - 核心价值（一句话概括）
   - 置信度（high/medium/low）

4. 如果对话中包含文章链接的讨论，标注来源链接

【输出格式】
返回JSON格式：
{{
  "topics": [
    {{
      "name": "主题名称",
      "confidence": "high",
      "fragments": ["[用户] 原文...", "[AI] 原文..."],
      "core_value": "一句话概括核心价值",
      "source_type": "纯对话|文章讨论"
    }}
  ],
  "summary": "整体分析摘要"
}}

如果没有识别到深度讨论，返回：{{"topics": [], "summary": "未识别到主题讨论精华"}}
"""


def identify_essence(conversation_file: Path) -> Dict[str, Any]:
    """
    识别对话中的主题精华
    
    Args:
        conversation_file: 对话文件路径
        
    Returns:
        识别结果，包含topics列表
    """
    # 读取对话内容
    with open(conversation_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取对话部分（跳过frontmatter）
    if '---' in content:
        parts = content.split('---', 2)
        if len(parts) >= 3:
            conversation_content = parts[2].strip()
        else:
            conversation_content = content
    else:
        conversation_content = content
    
    print(f"[Step1] 分析对话内容: {len(conversation_content)} 字符")
    
    # 简化版本：直接返回模拟结果（实际应调用kimi-coding/k2p5）
    # TODO: 集成OpenClaw API调用
    
    # 简单的关键词检测
    deep_topics = []
    
    # 检测深度讨论关键词
    if any(kw in conversation_content for kw in ['哲学', '系统论', '社会学', '技术冲击', '系统设计']):
        deep_topics.append({
            "name": "深度讨论识别",
            "confidence": "medium",
            "fragments": [conversation_content[:500]],
            "core_value": "涉及多领域的深度思考",
            "source_type": "纯对话"
        })
    
    return {
        "topics": deep_topics,
        "summary": f"识别到 {len(deep_topics)} 个潜在主题" if deep_topics else "未识别到主题讨论精华"
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="对话文件路径")
    args = parser.parse_args()
    
    result = identify_essence(Path(args.file))
    print(json.dumps(result, ensure_ascii=False, indent=2))
