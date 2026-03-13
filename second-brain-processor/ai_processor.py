#!/usr/bin/env python3
"""
Second Brain AI 处理模块 - 轻量向量搜索版 v5
使用 sklearn TF-IDF + 余弦相似度，无需下载大模型
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")

# 全局变量，延迟初始化
_vectorizer = None
_note_vectors = None
_notes_cache = None

def get_vectorizer():
    """延迟加载向量化器"""
    global _vectorizer
    if _vectorizer is None:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            _vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.95
            )
        except Exception as e:
            print(f"Vectorizer init failed: {e}", file=sys.stderr)
            _vectorizer = False
    return _vectorizer if _vectorizer is not False else None

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
                "source": frontmatter.get('source', '未知'),
                "full_text": f"{title}\n{content_body}"  # 用于向量化的完整文本
            })
        except Exception as e:
            continue
    
    return notes

def compute_tfidf_vectors(notes: List[Dict]) -> Tuple:
    """计算笔记的 TF-IDF 向量"""
    vectorizer = get_vectorizer()
    if vectorizer is None:
        return None, None
    
    # 准备文本
    texts = [note['full_text'][:3000] for note in notes]  # 限制长度
    
    try:
        # 拟合并转换
        vectors = vectorizer.fit_transform(texts)
        return vectorizer, vectors
    except Exception as e:
        print(f"TF-IDF computation failed: {e}", file=sys.stderr)
        return None, None

def cosine_similarity(vec1, vec2) -> float:
    """计算余弦相似度"""
    from sklearn.metrics.pairwise import cosine_similarity as sk_cosine
    return sk_cosine(vec1, vec2)[0][0]

def find_related_notes_tfidf(content: str, title: str, top_k: int = 3) -> List[Tuple[Dict, float]]:
    """使用 TF-IDF 找到相关笔记"""
    
    # 获取所有笔记
    all_notes = get_all_notes()
    if not all_notes:
        return []
    
    # 排除自己
    filtered_notes = []
    for note in all_notes:
        if title not in note['title'] and note['title'] not in title:
            filtered_notes.append(note)
    
    if not filtered_notes:
        return []
    
    # 计算笔记向量
    vectorizer, note_vectors = compute_tfidf_vectors(filtered_notes)
    if vectorizer is None:
        # 回退到关键词匹配
        return find_related_notes_fallback(content, title, top_k)
    
    # 计算查询向量
    query_text = f"{title}\n{content[:2000]}"
    try:
        query_vector = vectorizer.transform([query_text])
    except Exception as e:
        print(f"Query vector failed: {e}", file=sys.stderr)
        return find_related_notes_fallback(content, title, top_k)
    
    # 计算相似度
    from sklearn.metrics.pairwise import cosine_similarity
    similarities = cosine_similarity(query_vector, note_vectors)[0]
    
    # 排序并返回 top_k
    results = []
    for idx, sim in enumerate(similarities):
        results.append((filtered_notes[idx], float(sim)))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]

def find_related_notes_fallback(content: str, title: str, top_k: int = 3) -> List[Tuple[Dict, float]]:
    """备用方案：基于关键词匹配"""
    # 简单关键词匹配
    keywords = set(re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}', title))
    content_keywords = set(re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}', content[:1000]))
    keywords.update(content_keywords)
    
    all_notes = get_all_notes()
    scored = []
    
    for note in all_notes:
        if title in note['title'] or note['title'] in title:
            continue
        
        score = 0
        note_text = f"{note['title']} {note['content'][:500]}".lower()
        
        for kw in keywords:
            if kw.lower() in note_text:
                score += 1
        
        if score > 0:
            scored.append((note, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return [(note, 0.5) for note, _ in scored[:top_k]]

def generate_related_thoughts(content: str, title: str) -> List[str]:
    """生成关联思考"""
    related = find_related_notes_tfidf(content, title, top_k=3)
    
    thoughts = []
    
    if related:
        for note, similarity in related:
            note_title = note['title']
            
            # 根据相似度生成不同描述
            if similarity > 0.3:
                depth = "深度关联"
            elif similarity > 0.15:
                depth = "主题相关"
            else:
                depth = "有一定关联"
            
            thought = f"与 [[{note_title}]] 的{depth}：两篇文章在核心观点上有共鸣，可对比阅读深化理解"
            thoughts.append(thought)
    
    # 添加探索性问题
    thoughts.append("待探索：如何将本文的核心方法论应用到自己的实际工作流中？")
    
    return thoughts

def extract_key_takeaway(content: str) -> str:
    """提取一句话核心观点"""
    lines = content.split('\n')
    
    # 优先找 > 引用的内容
    for line in lines:
        if line.startswith('> ') and len(line) > 20:
            return line.replace('> ', '').strip()
    
    # 找 ** 强调的内容
    for line in lines:
        if '**' in line and len(line) > 20:
            match = re.search(r'\*\*(.+?)\*\*', line)
            if match:
                return match.group(1)
    
    # 返回第一段非空行
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and len(line) > 30:
            return line[:100] + "..." if len(line) > 100 else line
    
    return "待提炼核心观点"

def extract_core_points(content: str) -> List[str]:
    """提取核心要点"""
    points = []
    
    # 找 ## 章节标题
    sections = re.findall(r'##\s+(.+)', content)
    
    for section in sections[:5]:
        pattern = f"##\\s+{re.escape(section)}\\n\\n(.+?)(?=\\n## |\\Z)"
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            section_content = match.group(1)
            bold_match = re.search(r'\*\*(.+?)\*\*', section_content)
            if bold_match:
                points.append(f"**{section}**：{bold_match.group(1)}")
            else:
                first_line = section_content.strip().split('\n')[0]
                if len(first_line) > 10:
                    points.append(f"**{section}**：{first_line[:80]}")
                else:
                    points.append(section)
        else:
            points.append(section)
    
    return points if points else ["待提炼核心要点"]

def ai_process_content(content: str, title: str) -> dict:
    """AI 处理内容"""
    key_takeaway = extract_key_takeaway(content)
    core_points = extract_core_points(content)
    related_thoughts = generate_related_thoughts(content, title)
    
    return {
        "key_takeaway": key_takeaway,
        "core_points": core_points,
        "related_thoughts": related_thoughts
    }

def process_and_sync(commit_msg: str = None) -> dict:
    """处理内容并同步到 GitHub"""
    from git_sync import commit_and_sync
    result = commit_and_sync(commit_msg)
    return result

if __name__ == "__main__":
    test_content = """**核心观点**

AI 辅助开发的关键在于约束驱动。

## 第一章：约束的重要性

**约束让 AI 更聚焦**：明确的约束条件能帮助 AI 生成更符合需求的代码。

## 第二章：实践方法

> 先定义约束，再让 AI 实现。

这是最佳实践。"""
    
    result = ai_process_content(test_content, "AI辅助开发测试")
    print("Key Takeaway:", result["key_takeaway"])
    print("Core Points:", result["core_points"])
    print("Related Thoughts:", result["related_thoughts"])
