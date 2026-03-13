#!/usr/bin/env python3
"""
AI 深度整理模块 v2.0 - 真正的AI理解版

使用子Agent调用进行：
1. 主题识别与分类
2. 核心观点提炼
3. 有价值思考生成
4. 关联已有知识
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict

VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
PROCESSOR_DIR = Path("/root/.openclaw/workspace/second-brain-processor")

def log(message: str):
    """日志输出"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def find_related_notes(title: str, content: str, top_k: int = 3) -> List[Dict]:
    """查找相关笔记（使用现有TF-IDF方法）"""
    try:
        sys.path.insert(0, str(PROCESSOR_DIR))
        from ai_processor import find_related_notes_tfidf
        
        related = find_related_notes_tfidf(content, title, top_k)
        return [{"title": note['title'], "path": note['path'], "similarity": sim} 
                for note, sim in related]
    except Exception as e:
        log(f"查找相关笔记失败: {e}")
        return []

def call_ai_for_deep_processing(content: str, title: str, related_notes: List[Dict]) -> Dict:
    """
    调用子Agent进行深度AI处理
    
    返回: {
        "key_takeaway": "一句话核心观点",
        "core_points": ["要点1", "要点2", ...],
        "valuable_thoughts": ["思考1", "思考2", ...],
        "themes": ["主题1", "主题2"],
        "connections": ["与XX的关联"]
    }
    """
    
    # 构建提示
    related_context = ""
    if related_notes:
        related_context = "\n\n**已有关联笔记：**\n"
        for note in related_notes[:3]:
            related_context += f"- 《{note['title']}>\n"
    
    prompt = f"""请深度分析以下内容，进行主题归纳和核心观点提炼：

**原文标题**：{title}

**原文内容**：
```
{content[:5000]}
```
{related_context}

请按以下JSON格式输出分析结果：
{{
    "key_takeaway": "一句话核心观点（20字以内）",
    "core_points": [
        "详细观点1：具体内容",
        "详细观点2：具体内容",
        "详细观点3：具体内容"
    ],
    "valuable_thoughts": [
        "思考1：由内容引发的有价值思考",
        "思考2：可以进一步探索的方向"
    ],
    "themes": ["主题标签1", "主题标签2"],
    "connections": ["与 [[XXX]] 的关联：具体联系"]
}}

要求：
1. 核心观点要准确提炼，不是简单复述
2. 思考要有深度，不是表面观察
3. 主题分类要准确，便于归类
4. 如有相关笔记，建立有意义的关联
"""
    
    # 调用子Agent
    try:
        import openclaw
        result = openclaw.sessions_spawn(
            task=prompt,
            model="k2p5",
            thinking="high",
            timeout_seconds=120
        )
        
        # 解析结果
        if isinstance(result, dict) and 'result' in result:
            text_result = result['result']
        else:
            text_result = str(result)
        
        # 提取JSON
        json_match = re.search(r'\{[\s\S]*\}', text_result)
        if json_match:
            return json.loads(json_match.group())
        else:
            raise ValueError("无法从AI响应中提取JSON")
            
    except Exception as e:
        log(f"AI深度处理失败: {e}")
        # 返回降级结果
        return {
            "key_takeaway": f"关于{title}的讨论",
            "core_points": ["待进一步提炼"],
            "valuable_thoughts": ["待进一步思考"],
            "themes": ["待分类"],
            "connections": []
        }

def ai_deep_process(content: str, title: str, source_type: str = "general") -> Dict:
    """
    深度AI处理入口
    
    Args:
        content: 原始内容
        title: 标题
        source_type: 来源类型 (chat/article/note)
    
    Returns:
        处理结果字典
    """
    log(f"开始深度处理: {title}")
    
    # 1. 查找相关笔记
    related_notes = find_related_notes(title, content)
    log(f"  找到 {len(related_notes)} 个相关笔记")
    
    # 2. AI深度处理
    ai_result = call_ai_for_deep_processing(content, title, related_notes)
    log(f"  AI处理完成: {len(ai_result.get('core_points', []))} 个要点")
    
    # 3. 组装结果
    return {
        "key_takeaway": ai_result.get("key_takeaway", "待提炼"),
        "core_points": ai_result.get("core_points", []),
        "valuable_thoughts": ai_result.get("valuable_thoughts", []),
        "themes": ai_result.get("themes", []),
        "connections": ai_result.get("connections", []),
        "related_notes": related_notes,
        "processed_at": time.strftime('%Y-%m-%d %H:%M:%S')
    }

def process_chat_record(content: str, title: str, date_str: str) -> Dict:
    """
    专门处理聊天记录
    
    特点：
    - 识别多个主题
    - 提取有价值的讨论点
    - 记录决策和思考过程
    """
    log(f"处理聊天记录: {title}")
    
    # 先进行普通深度处理
    result = ai_deep_process(content, title, source_type="chat")
    
    # 聊天记录特有：识别多主题
    themes_prompt = f"""请分析以下聊天记录，识别其中的**不同主题**，每个主题单独分析：

**聊天记录**：
```
{content[:3000]}
```

请输出：
1. 主题数量及每个主题的名称
2. 每个主题的核心讨论点
3. 重要决策或结论
4. 有价值的思考片段

格式：
- 主题1：[主题名]
  - 核心观点：...
  - 重要决策：...
  - 引发思考：...
"""
    
    try:
        import openclaw
        themes_result = openclaw.sessions_spawn(
            task=themes_prompt,
            model="k2p5",
            thinking="high",
            timeout_seconds=120
        )
        
        result["multi_themes_analysis"] = str(themes_result.get('result', themes_result))
        
    except Exception as e:
        log(f"多主题分析失败: {e}")
        result["multi_themes_analysis"] = "待进一步分析多主题"
    
    return result

def generate_obsidian_note(processed: Dict, original_content: str, title: str, 
                           source: str = "聊天记录", tags: List[str] = None) -> str:
    """
    生成Obsidian格式的笔记
    """
    if tags is None:
        tags = ["聊天记录", "待整理"]
    
    # 添加处理完成标签
    if "待整理" in tags:
        tags.remove("待整理")
    tags.append("已深度处理")
    
    # 主题标签
    themes = processed.get("themes", [])
    for theme in themes:
        clean_theme = theme.replace(" ", "-")
        if clean_theme not in tags:
            tags.append(clean_theme)
    
    # 构建笔记内容
    note_content = f"""---
title: {title}
date: {processed.get('processed_at', time.strftime('%Y-%m-%d %H:%M:%S'))}
tags: {json.dumps(tags, ensure_ascii=False)}
source: {source}
status: 已深度处理
---

# {title}

## 🎯 一句话核心观点

{processed.get('key_takeaway', '待提炼')}

## 💡 详细观点

"""
    
    # 添加核心观点
    for point in processed.get("core_points", []):
        note_content += f"- {point}\n"
    
    note_content += "\n## 🤔 引发的思考\n\n"
    
    # 添加思考
    for thought in processed.get("valuable_thoughts", []):
        note_content += f"- {thought}\n"
    
    # 添加关联
    if processed.get("connections"):
        note_content += "\n## 🔗 关联知识\n\n"
        for conn in processed.get("connections", []):
            note_content += f"- {conn}\n"
    
    # 添加多主题分析（如果是聊天记录）
    if "multi_themes_analysis" in processed:
        note_content += f"\n## 📋 多主题分析\n\n{processed['multi_themes_analysis']}\n"
    
    # 添加原始内容（折叠）
    note_content += f"""

---

<details>
<summary>📝 原始内容</summary>

{original_content}

</details>
"""
    
    return note_content

if __name__ == "__main__":
    # 测试
    test_content = """
用户：我觉得AI的发展会改变整个社会的就业结构

AI：这是一个复杂的议题。从历史来看，技术进步确实会淘汰一些岗位，但同时也会创造新的就业机会。

用户：但这次的AI不一样，它的学习能力太强了

AI：确实，生成式AI的能力边界在不断扩展。但关键可能在于如何重新定义"工作"和"价值"。

用户：你觉得人类还有什么是AI替代不了的？

AI：创造力、情感连接、道德判断...但这些边界也在模糊。或许更重要的是思考人类想走向何方。
"""
    
    result = process_chat_record(test_content, "AI与人类未来讨论", "2026-03-09")
    print("\n=== 处理结果 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 生成笔记
    note = generate_obsidian_note(result, test_content, "AI与人类未来讨论")
    print("\n=== 生成笔记 ===")
    print(note[:1000] + "...")
