#!/usr/bin/env python3
"""
step2_generate_essence.py - v2.1 四步法第2步
生成主题讨论精华文档
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def generate_essence_doc(topic: Dict[str, Any], date_str: str) -> str:
    """
    生成主题讨论精华文档
    
    Args:
        topic: 主题信息（包含name, confidence, fragments, core_value等）
        date_str: 日期字符串
        
    Returns:
        Markdown格式的精华文档
    """
    topic_name = topic.get("name", "未命名主题")
    core_value = topic.get("core_value", "")
    fragments = topic.get("fragments", [])
    
    # 构建文档
    doc = f"""---
date: {date_str}
type: 主题讨论精华
theme: 深度讨论
confidence: {topic.get('confidence', 'medium')}
---

# {topic_name}

> {core_value}

---

## 核心要点

### 1. 讨论背景
本次讨论涉及{topic_name}相关话题。

### 2. 关键观点
"""
    
    # 添加对话片段
    for i, fragment in enumerate(fragments[:3], 1):
        doc += f"\n**片段{i}**: {fragment[:200]}...\n"
    
    doc += f"""

## 关联思考

- 与其他主题的关联：待补充
- 实践启示：待补充

## 来源

- 类型：{topic.get('source_type', '纯对话')}
- 整理时间：{date_str}

---

*由Second Brain系统自动生成*
"""
    
    return doc


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True, help="主题JSON")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()
    
    topic = json.loads(args.topic)
    doc = generate_essence_doc(topic, args.date)
    print(doc)
