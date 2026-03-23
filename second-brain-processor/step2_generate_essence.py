#!/usr/bin/env python3
"""
step2_generate_essence.py - v2.2 四步法第2步
生成高质量主题讨论精华文档

核心改进：
1. 使用新的主题格式（key_takeaway, detailed_points, reflection, connections）
2. 生成结构化的精华文档，非简单复制原文
3. 强调信息增量和思考深度
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


def sanitize_filename(name: str) -> str:
    """将主题名称转换为安全的文件名"""
    # 移除或替换不安全字符
    safe = re.sub(r'[<>:"/\\|?*]', '', name)
    safe = safe.strip().replace(' ', '_')
    return safe[:50]  # 限制长度


def generate_essence_doc(topic: Dict[str, Any], date_str: str) -> str:
    """
    生成主题讨论精华文档
    
    Args:
        topic: 主题信息（包含新的结构化字段）
        date_str: 日期字符串
        
    Returns:
        Markdown格式的高质量精华文档
    """
    topic_name = topic.get("name", "未命名主题")
    confidence = topic.get("confidence", "medium")
    source_type = topic.get("source_type", "纯对话")
    
    # 核心观点
    key_takeaway = topic.get("key_takeaway", topic.get("core_value", ""))
    
    # 详细观点
    detailed_points = topic.get("detailed_points", [])
    if not detailed_points and "fragments" in topic:
        # 兼容旧格式
        detailed_points = [f"**原文片段**: {f[:200]}..." for f in topic.get("fragments", [])[:3]]
    
    # 思考延伸
    reflection = topic.get("reflection", "")
    
    # 知识关联
    connections = topic.get("connections", [])
    
    # 原文片段（仅保留关键部分）
    fragments = topic.get("fragments", [])
    
    # 构建文档
    doc_lines = [
        f"---",
        f"date: {date_str}",
        f"type: 主题讨论精华",
        f"theme: {topic_name}",
        f"confidence: {confidence}",
        f"source_type: {source_type}",
        f"---",
        f"",
        f"# {topic_name}",
        f"",
        f"> **核心洞察**：{key_takeaway}",
        f"",
        f"---",
        f"",
    ]
    
    # 详细观点
    if detailed_points:
        doc_lines.extend([
            f"## 详细观点",
            f"",
        ])
        for i, point in enumerate(detailed_points, 1):
            doc_lines.append(f"### {i}. {point}")
            doc_lines.append("")
    
    # 思考延伸
    if reflection:
        doc_lines.extend([
            f"## 思考延伸",
            f"",
            f"{reflection}",
            f"",
        ])
    
    # 知识关联
    if connections:
        doc_lines.extend([
            f"## 关联与启示",
            f"",
        ])
        for conn in connections:
            doc_lines.append(f"- {conn}")
        doc_lines.append("")
    
    # 原文参考（折叠，仅保留关键片段）
    if fragments:
        doc_lines.extend([
            f"## 原文参考",
            f"",
            f"<details>",
            f"<summary>展开查看原文片段</summary>",
            f"",
        ])
        for fragment in fragments[:5]:  # 最多5个片段
            doc_lines.append(f"> {fragment}")
            doc_lines.append("")
        doc_lines.extend([
            f"</details>",
            f"",
        ])
    
    # 元信息
    doc_lines.extend([
        f"---",
        f"",
        f"**来源**：{source_type}  ",
        f"**整理时间**：{date_str}  ",
        f"**置信度**：{confidence}  ",
        f"**整理工具**：Second Brain四步法",
        f"",
    ])
    
    return "\n".join(doc_lines)


def generate_summary_doc(topics: List[Dict[str, Any]], date_str: str, source_file: str = "") -> str:
    """
    生成当日讨论汇总文档（当没有深度主题时使用）
    """
    doc_lines = [
        f"---",
        f"date: {date_str}",
        f"type: 对话记录",
        f"source: 原始对话整理",
        f"---",
        f"",
        f"# {date_str} 对话记录",
        f"",
        f"## 概述",
        f"",
        f"本次对话未识别到需要深度提炼的主题讨论，已按普通对话记录归档。",
        f"",
    ]
    
    if topics:
        doc_lines.extend([
            f"## 潜在主题",
            f"",
        ])
        for topic in topics:
            doc_lines.append(f"- **{topic.get('name')}**：{topic.get('key_takeaway', topic.get('core_value', ''))}")
        doc_lines.append("")
    
    if source_file:
        doc_lines.extend([
            f"## 来源",
            f"",
            f"- 原始文件：{source_file}",
            f"",
        ])
    
    doc_lines.extend([
        f"---",
        f"",
        f"*由Second Brain系统自动整理*",
        f"",
    ])
    
    return "\n".join(doc_lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", help="主题JSON字符串")
    parser.add_argument("--topics-file", help="包含多个主题的JSON文件")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output-dir", help="输出目录")
    args = parser.parse_args()
    
    if args.topic:
        topic = json.loads(args.topic)
        doc = generate_essence_doc(topic, args.date)
        print(doc)
    elif args.topics_file:
        with open(args.topics_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        topics = data.get("topics", [])
        for topic in topics:
            doc = generate_essence_doc(topic, args.date)
            print(f"\n{'='*60}\n")
            print(doc)
    else:
        # 测试模式
        test_topic = {
            "name": "示例主题",
            "confidence": "high",
            "source_type": "纯对话",
            "key_takeaway": "这是核心洞察的一句话总结",
            "detailed_points": [
                "详细观点1：展开说明核心论点和论据",
                "详细观点2：补充说明相关思考"
            ],
            "reflection": "这个观点 implications 是什么？引发什么新的思考？",
            "connections": [
                "与其他主题或已有知识的联系",
                "可能的实践应用或后续探索方向"
            ],
            "fragments": ["[用户] 原文关键片段"]
        }
        print(generate_essence_doc(test_topic, args.date))
