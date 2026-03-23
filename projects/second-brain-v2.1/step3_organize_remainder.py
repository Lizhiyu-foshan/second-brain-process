#!/usr/bin/env python3
"""
step3_organize_remainder.py - v2.1 四步法第3步
整理剩余内容
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict


def organize_remainder(
    conversation_file: Path,
    extracted_fragments: List[str],
    output_file: Path
) -> bool:
    """
    整理剩余对话内容
    
    Args:
        conversation_file: 原始对话文件
        extracted_fragments: 已提取的精华片段
        output_file: 输出文件路径
        
    Returns:
        是否成功
    """
    with open(conversation_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除已提取的片段
    remainder = content
    for fragment in extracted_fragments:
        remainder = remainder.replace(fragment, "")
    
    # 清理空行
    lines = [line for line in remainder.split('\n') if line.strip()]
    remainder = '\n'.join(lines)
    
    # 生成对话记录
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    doc = f"""---
date: {date_str}
type: 对话记录
source: 原始对话整理
---

# {date_str} 对话记录

## 剩余内容整理

{remainder[:3000] if remainder else "（已提取精华，剩余内容为日常对话）"}

---

*由Second Brain系统自动整理*
"""
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(doc)
    
    print(f"[Step3] 已保存对话记录: {output_file}")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fragments", default="[]")
    args = parser.parse_args()
    
    fragments = json.loads(args.fragments)
    organize_remainder(Path(args.input), fragments, Path(args.output))
