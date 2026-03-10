#!/usr/bin/env python3
"""
Second Brain 内容处理器 - 增强版
支持关键字提取、Key Takeaway、关联思考
"""

import json
import re
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# 配置
QUEUE_DIR = Path("/root/.openclaw/workspace/second-brain-processor/queue")
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")

def ensure_dirs():
    """确保目录存在"""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

def extract_url(text: str) -> str | None:
    """从文本中提取 URL"""
    url_pattern = r'https?://[^\s\u3000\uff0c\uff0e\uff01\uff1f\uff08\uff09\[\]"\'\n\r]+'
    match = re.search(url_pattern, text)
    return match.group(0) if match else None

def get_source_from_url(url: str) -> str:
    """根据 URL 判断来源"""
    domain = urlparse(url).netloc.lower()
    
    if "zhihu.com" in domain:
        return "知乎"
    elif "weixin.qq.com" in domain or "mp.weixin.qq.com" in domain:
        return "微信"
    elif "substack.com" in domain:
        return "Substack"
    elif "bilibili.com" in domain:
        return "Bilibili"
    elif "youtube.com" in domain or "youtu.be" in domain:
        return "YouTube"
    else:
        return "网页"

def extract_keywords(title: str, content: str) -> list:
    """提取关键字"""
    # 合并标题和内容
    text = title + " " + content[:2000]
    
    # 技术关键词库
    tech_keywords = [
        "AI", "Agent", "LLM", "GPT", "Claude", "OpenAI", "Anthropic",
        "RAG", "Prompt", "Workflow", "API", "SDK", "MCP",
        "Obsidian", "Notion", "GitHub", "Git", "Docker",
        "Python", "JavaScript", "TypeScript", "Node.js",
        "数据库", "向量", "Embedding", "微调", "训练",
        "产品", "设计", "运营", "增长", "商业模式"
    ]
    
    found_keywords = []
    for keyword in tech_keywords:
        if keyword.lower() in text.lower():
            found_keywords.append(keyword)
    
    # 额外提取大写字母组合（可能是专有名词）
    proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    for noun in proper_nouns:
        if len(noun) > 3 and noun not in found_keywords:
            found_keywords.append(noun)
    
    return found_keywords[:10]  # 最多10个关键字

def generate_enhanced_markdown(title: str, full_content: str, url: str, source: str) -> dict:
    """生成增强版 Markdown"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M")
    
    # 确定分类
    if source == "知乎":
        category = "03-Articles/Zhihu"
    elif source == "微信":
        category = "03-Articles/WeChat"
    elif source == "Substack":
        category = "03-Articles/Substack"
    else:
        category = "03-Articles"
    
    # 生成文件名
    title_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)[:50]
    filename = f"{safe_title}_{title_hash}.md"
    
    # 提取关键字
    keywords = extract_keywords(title, full_content)
    keywords_str = ", ".join([f'"{k}"' for k in keywords])
    
    # 提取章节结构用于要点
    sections = []
    for line in full_content.split('\n'):
        if line.startswith('## ') or line.startswith('### '):
            section_title = line.replace('#', '').strip()
            if section_title and section_title not in ['核心要点', '内容整理', '原文全文']:
                sections.append(section_title)
    
    bullet_points = "\n".join([f"- {s}" for s in sections[:5]]) if sections else "- 待提炼要点"
    
    markdown = f"""---
aliases: []
tags: [文章剪藏, {source}, 待整理]
keywords: [{keywords_str}]
date: {date_str}
source: "{source}"
author: "待确认"
url: "{url}"
---

# {title}

> 来源：{source} | 作者：待确认 | 时间：{time_str}

---

## 🔑 Key Takeaway

_待 AI 提炼一句话核心观点_

---

## 📋 核心要点

{bullet_points}

---

## 💭 关联思考

- 与 [[待补充]] 的关联：...
- 与 [[待补充]] 的关联：...
- 待探索的问题：
  - ...

---

## 📝 原文摘录

{full_content}

---

## 🔗 相关链接

- 原文：{url}
- 相关笔记：[[待补充]]

---

## 🏷️ 标签

#文章剪藏 #{source} #待整理

---

*生成时间：{time_str}*
"""
    
    return {
        "filename": filename,
        "category": category,
        "content": markdown,
        "title": title,
        "url": url,
        "source": source,
        "keywords": keywords
    }

def fetch_url_content(url: str) -> str:
    """抓取网页内容，使用增强版抓取器"""
    try:
        # 导入增强版抓取器
        sys.path.insert(0, str(Path(__file__).parent))
        from wechat_fetcher import WeChatArticleFetcher
        
        # 使用新的抓取器
        fetcher = WeChatArticleFetcher(timeout=60)
        result = fetcher.fetch(url)
        
        if result.success:
            if result.source == "fallback":
                # 降级方案返回的内容已经格式化好了
                return result.content
            else:
                return f"{result.title}\n\n{result.content}"
        else:
            return f"待抓取内容\n\n链接：{url}\n\n错误：{result.error}"
            
    except Exception as e:
        print(f"抓取异常: {e}")
        return f"待抓取内容\n\n链接：{url}\n\n（请手动复制链接到浏览器查看原文）"
        return f"待抓取内容\n\n链接：{url}"

def extract_text_from_html(html: str, url: str) -> str:
    """从HTML中提取正文文本"""
    import re
    
    # 移除 script 和 style
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    
    # 提取 title
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL)
    title = title_match.group(1).strip() if title_match else "未知标题"
    
    # 提取正文（简单策略：找最多文字的区域）
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', ' ', html)
    # 合并空白
    text = re.sub(r'\s+', ' ', text)
    # 解码HTML实体
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    
    # 清理
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    text = '\n'.join(lines)
    
    if len(text) > 100:
        return f"{title}\n\n{text[:5000]}"  # 限制长度
    return ""

def process_link(url: str, full_content: str = None) -> dict:
    """处理链接，生成增强版笔记"""
    ensure_dirs()
    
    print(f"处理 URL: {url}")
    
    # 如果没有提供内容，自动抓取
    if full_content is None or full_content == "待抓取内容":
        full_content = fetch_url_content(url)
    
    source = get_source_from_url(url)
    
    # 解析标题
    lines = full_content.split('\n')
    title = lines[0].strip() if lines else "未知标题"
    if title.startswith('# '):
        title = title[2:]
    elif title.startswith('**') and title.endswith('**'):
        title = title[2:-2]
    
    # 生成增强版 Markdown
    note = generate_enhanced_markdown(title, full_content, url, source)
    
    # 保存到队列
    queue_file = QUEUE_DIR / note['filename']
    with open(queue_file, "w", encoding="utf-8") as f:
        f.write(note['content'])
    
    print(f"已保存到队列: {queue_file}")
    print(f"提取关键字: {', '.join(note['keywords'])}")
    
    return {
        "success": True,
        "filename": note['filename'],
        "category": note['category'],
        "title": note['title'],
        "url": note['url'],
        "source": note['source'],
        "keywords": note['keywords'],
        "queue_path": str(queue_file),
        "message": f"已添加「{note['title']}」到待处理队列"
    }

def get_queue_list() -> list:
    """获取待处理队列列表"""
    ensure_dirs()
    files = sorted(QUEUE_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
    return [
        {
            "filename": f.name,
            "path": str(f),
            "title": extract_title(f),
            "source": extract_source(f),
            "tags": extract_tags(f),
            "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        }
        for f in files
    ]

def extract_tags(file_path: Path) -> list:
    """提取标签"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'tags: \[(.+)\]', content)
            if match:
                tags_str = match.group(1)
                # 解析标签列表
                tags = [t.strip().strip('"').strip("'") for t in tags_str.split(',')]
                return tags
    except:
        pass
    return []

def extract_title(file_path: Path) -> str:
    """提取标题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'^# (.+)$', content, re.MULTILINE)
            if match:
                return match.group(1).strip()
    except:
        pass
    return file_path.stem

def extract_source(file_path: Path) -> str:
    """提取来源"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'source: "(.+)"', content)
            if match:
                return match.group(1)
    except:
        pass
    return "未知"

if __name__ == "__main__":
    # 测试
    test_content = """测试文章标题

这是关于 AI Agent 的内容。

## 模块一：基础概念

Agent 是什么？

## 模块二：实际应用

如何使用 Agent？

## 模块三：最佳实践

一些建议。"""
    
    result = process_link("https://example.com/test", test_content)
    print(json.dumps(result, ensure_ascii=False, indent=2))
