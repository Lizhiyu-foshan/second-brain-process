#!/usr/bin/env python3
"""
Second Brain AI 处理模块 - 备用版本（关键词匹配）
当向量模型加载失败时使用
"""

import re
from pathlib import Path
from typing import List, Dict

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
                "content": content_body[:2000],
                "tags": frontmatter.get('tags', []),
                "keywords": frontmatter.get('keywords', []),
                "source": frontmatter.get('source', '未知')
            })
        except Exception as e:
            continue
    
    return notes

def extract_keywords(content: str, title: str) -> List[str]:
    """提取文章关键词"""
    keywords = set()
    
    # 从标题提取
    title_words = re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}', title)
    keywords.update(title_words)
    
    # 从内容提取
    content_lower = content.lower()
    
    # 技术关键词库
    tech_keywords = [
        "AI", "Agent", "LLM", "GPT", "Claude", "OpenAI",
        "约束", "测试", "工程", "代码", "开发",
        "效率", "并行", "优化", "性能",
        "记忆", "学习", "进化", "迭代",
        "龙虾", "OpenClaw", "MCP", "RAG",
        "工作流", "自动化", "提示词", "Prompt"
    ]
    
    for kw in tech_keywords:
        if kw.lower() in content_lower or kw in content:
            keywords.add(kw)
    
    # 提取 ## 章节标题作为关键词
    sections = re.findall(r'##\s+(.+)', content)
    for section in sections:
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', section)
        keywords.update(chinese_words[:3])
    
    return list(keywords)[:15]

def calculate_similarity(note: Dict, article_keywords: List[str], article_content: str) -> float:
    """计算笔记与文章的相似度"""
    score = 0.0
    
    # 1. 标题匹配
    note_title_lower = note['title'].lower()
    for kw in article_keywords:
        if kw.lower() in note_title_lower:
            score += 3.0
    
    # 2. 关键词匹配
    note_keywords = note.get('keywords', [])
    if isinstance(note_keywords, str):
        note_keywords = [k.strip() for k in note_keywords.split(',')]
    
    for kw in article_keywords:
        if kw in note_keywords:
            score += 2.0
    
    # 3. 内容匹配
    note_content_lower = note['content'].lower()
    article_content_lower = article_content.lower()
    
    for kw in article_keywords:
        kw_lower = kw.lower()
        if kw_lower in note_content_lower:
            score += 1.0
            article_count = article_content_lower.count(kw_lower)
            if article_count > 2:
                score += 0.5
    
    # 4. 标签匹配
    note_tags = note.get('tags', [])
    if isinstance(note_tags, str):
        note_tags = [t.strip() for t in note_tags.split(',')]
    
    common_tags = set(note_tags) & set(['AI', 'Agent', '开发', '效率', '记忆'])
    score += len(common_tags) * 0.5
    
    return score

def find_related_notes(content: str, title: str, top_k: int = 3) -> List[Dict]:
    """找到与文章最相关的笔记（关键词匹配版）"""
    article_keywords = extract_keywords(content, title)
    
    all_notes = get_all_notes()
    if not all_notes:
        return []
    
    # 计算相似度
    scored_notes = []
    for note in all_notes:
        # 排除自己
        if title in note['title'] or note['title'] in title:
            continue
        
        score = calculate_similarity(note, article_keywords, content)
        if score > 0:
            scored_notes.append((score, note))
    
    # 排序并返回 top_k
    scored_notes.sort(key=lambda x: x[0], reverse=True)
    return [note for _, note in scored_notes[:top_k]]
