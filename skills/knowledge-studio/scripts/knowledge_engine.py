#!/usr/bin/env python3
"""
Knowledge Studio - 知识处理与创新引擎
基于 Obsidian Vault 的笔记进行归纳、组合、创新
"""

import json
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")

def get_all_notes() -> List[Dict]:
    """获取所有笔记"""
    notes = []
    if not VAULT_DIR.exists():
        return notes
    
    for md_file in VAULT_DIR.rglob("*.md"):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 frontmatter
            frontmatter = {}
            content_body = content
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    fm_text = parts[1]
                    content_body = parts[2]
                    # 简单解析 YAML
                    for line in fm_text.strip().split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            frontmatter[key.strip()] = value.strip().strip('"').strip("'")
            
            # 提取标题
            title = md_file.stem
            for line in content_body.split('\n'):
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
            
            notes.append({
                "path": str(md_file.relative_to(VAULT_DIR)),
                "title": title,
                "content": content_body[:2000],  # 限制长度
                "tags": frontmatter.get('tags', []),
                "keywords": frontmatter.get('keywords', []),
                "source": frontmatter.get('source', '未知'),
                "date": frontmatter.get('date', '')
            })
        except Exception as e:
            continue
    
    return notes

def find_related_notes(notes: List[Dict], topic: str = None, keywords: List[str] = None) -> List[Dict]:
    """查找相关笔记"""
    if not topic and not keywords:
        return notes[:10]  # 返回最近的10篇
    
    scored_notes = []
    search_terms = []
    if topic:
        search_terms.extend(topic.lower().split())
    if keywords:
        search_terms.extend([k.lower() for k in keywords])
    
    for note in notes:
        score = 0
        content_lower = note['content'].lower()
        title_lower = note['title'].lower()
        
        for term in search_terms:
            if term in title_lower:
                score += 3
            if term in content_lower:
                score += 1
        
        if score > 0:
            scored_notes.append((score, note))
    
    # 按分数排序
    scored_notes.sort(key=lambda x: x[0], reverse=True)
    return [note for _, note in scored_notes[:10]]

def combine_notes_for_inspiration(notes: List[Dict]) -> Dict:
    """组合笔记生成创新灵感"""
    if len(notes) < 2:
        return {
            "success": False,
            "error": "需要至少2篇笔记才能进行组合创新"
        }
    
    # 提取关键主题
    all_keywords = []
    for note in notes:
        if isinstance(note.get('keywords'), str):
            all_keywords.extend([k.strip() for k in note['keywords'].split(',')])
        elif isinstance(note.get('keywords'), list):
            all_keywords.extend(note['keywords'])
    
    # 生成组合提示
    combination_prompt = f"""基于以下 {len(notes)} 篇笔记，探索可能的创新组合：

笔记列表：
{chr(10).join([f"{i+1}. {note['title']} ({note.get('source', '未知')})" for i, note in enumerate(notes[:5])])}

关键概念：{', '.join(list(set(all_keywords))[:15])}

请思考：
1. 这些笔记之间有什么隐藏的联系？
2. 跨领域组合会产生什么新想法？
3. 可以衍生出什么新工具/项目/方法？
4. 有哪些值得深入探索的方向？
"""
    
    return {
        "success": True,
        "prompt": combination_prompt,
        "note_count": len(notes),
        "keywords": list(set(all_keywords))[:15]
    }

def generate_discussion_context(topic: str, stance: str = "socratic") -> Dict:
    """生成思辨讨论上下文"""
    notes = get_all_notes()
    related = find_related_notes(notes, topic=topic)
    
    if not related:
        return {
            "success": False,
            "error": f"未找到与'{topic}'相关的笔记"
        }
    
    # 构建讨论上下文
    context = f"""基于你的知识库中 {len(related)} 篇相关笔记，作为你的思辨伙伴进行讨论。

相关笔记：
{chr(10).join([f"- 《{note['title']}》({note.get('source', '未知')})" for note in related[:5]])}

讨论主题：{topic}
讨论模式：{stance}（苏格拉底式追问）

角色设定：
- 你不是在回答我，而是在和我平等地思辨
- 你可以质疑我的观点，提出反例，挑战假设
- 引用我的笔记中的内容来支持或反驳
- 目的是通过对话让思考更深入，而不是给出标准答案

让我们开始讨论：{topic}
"""
    
    return {
        "success": True,
        "context": context,
        "related_notes": [note['title'] for note in related[:5]],
        "topic": topic,
        "stance": stance
    }

def generate_learning_plan(subject: str) -> Dict:
    """基于笔记生成学习计划"""
    notes = get_all_notes()
    related = find_related_notes(notes, topic=subject)
    
    # 按日期排序，找出学习路径
    dated_notes = [n for n in related if n.get('date')]
    dated_notes.sort(key=lambda x: x.get('date', ''))
    
    plan = {
        "success": True,
        "subject": subject,
        "existing_knowledge": [note['title'] for note in related[:10]],
        "knowledge_gaps": [],  # 待AI分析
        "suggested_path": [],  # 待AI生成
        "practice_questions": []  # 待AI生成
    }
    
    return plan

def generate_tool_idea(requirement: str) -> Dict:
    """基于笔记生成工具创意"""
    notes = get_all_notes()
    
    # 查找相关笔记
    related = find_related_notes(notes, topic=requirement)
    
    # 提取代码片段和工具相关笔记
    code_notes = []
    for note in related:
        if '```' in note['content'] or '代码' in note['title'] or '工具' in note['title']:
            code_notes.append(note)
    
    tool_prompt = f"""基于你的知识库，为以下需求生成工具创意：

需求：{requirement}

相关笔记（{len(related)} 篇）：
{chr(10).join([f"- {note['title']}" for note in related[:5]])}

代码/工具相关笔记（{len(code_notes)} 篇）：
{chr(10).join([f"- {note['title']}" for note in code_notes[:3]])}

请生成：
1. 工具名称和一句话描述
2. 核心功能设计
3. 技术实现思路（可以引用笔记中的代码片段）
4. 使用示例
5. 可能的扩展方向
"""
    
    return {
        "success": True,
        "prompt": tool_prompt,
        "related_count": len(related),
        "code_notes_count": len(code_notes)
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Knowledge Studio - 知识处理引擎')
    parser.add_argument('--action', choices=['list', 'combine', 'discuss', 'learn', 'tool'], required=True)
    parser.add_argument('--topic', help='主题/话题')
    parser.add_argument('--keywords', help='关键词（逗号分隔）')
    parser.add_argument('--requirement', help='工具需求描述')
    
    args = parser.parse_args()
    
    if args.action == 'list':
        notes = get_all_notes()
        print(json.dumps({
            "total": len(notes),
            "notes": [{"title": n["title"], "source": n["source"]} for n in notes[:20]]
        }, ensure_ascii=False, indent=2))
    
    elif args.action == 'combine':
        notes = get_all_notes()
        keywords = args.keywords.split(',') if args.keywords else None
        related = find_related_notes(notes, topic=args.topic, keywords=keywords)
        result = combine_notes_for_inspiration(related)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.action == 'discuss':
        result = generate_discussion_context(args.topic)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.action == 'learn':
        result = generate_learning_plan(args.topic)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.action == 'tool':
        result = generate_tool_idea(args.requirement)
        print(json.dumps(result, ensure_ascii=False, indent=2))
