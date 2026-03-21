#!/usr/bin/env python3
"""
article_handler.py - v2.1
文章链接处理 - 入口B
"""

import re
import sys
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
ARTICLES_DIR = VAULT_DIR / "03-Articles"


def identify_source(url: str) -> str:
    """识别文章来源"""
    if "zhihu.com" in url or "zhuanlan.zhihu.com" in url:
        return "Zhihu"
    elif "mp.weixin.qq.com" in url or "weixin.qq.com" in url:
        return "WeChat"
    elif "substack.com" in url:
        return "Substack"
    else:
        return "Other"


def fetch_or_wait_content(url: str) -> str:
    """
    获取文章内容
    v2.1: 简化版本，提示用户手动复制内容
    """
    return f"""# 待获取文章

URL: {url}

> 请复制文章内容到这里
"""


def handle_article_link(url: str) -> dict:
    """
    处理文章链接 - 入口B
    
    Args:
        url: 文章URL
        
    Returns:
        处理结果
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # 1. 识别来源
    source = identify_source(url)
    print(f"[Article] 识别来源: {source}")
    
    # 2. 获取内容
    content = fetch_or_wait_content(url)
    
    # 3. 生成文件名
    # 从URL提取标题或使用日期
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "").split(".")[0]
    filename = f"{date_str}_{domain}_article.md"
    
    # 4. 保存到对应目录
    save_dir = ARTICLES_DIR / source
    save_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = save_dir / filename
    
    # 添加frontmatter
    full_content = f"""---
date: {date_str}
type: 文章剪藏
source: {source}
url: {url}
status: 待讨论
---

{content}
"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    print(f"[Article] 已保存: {file_path}")
    
    # 5. 返回处理结果
    return {
        "success": True,
        "file_path": str(file_path),
        "source": source,
        "url": url,
        "message": f"""
📄 文章已保存到 03-Articles/{source}/{filename}

请选择：
1. 回复"讨论" → 现在开始讨论
2. 回复"稍后 X小时" → 设置定时任务（如：稍后 2小时）
3. 回复"AI自动整理" → AI自动整理分类
        """
    }


def is_article_link(text: str) -> bool:
    """检测是否为文章链接"""
    patterns = [
        r'https?://zhuanlan\.zhihu\.com',
        r'https?://mp\.weixin\.qq\.com',
        r'https?://.*\.substack\.com',
        r'https?://.*zhihu\.com',
    ]
    return any(re.search(p, text) for p in patterns)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="文章URL")
    args = parser.parse_args()
    
    result = handle_article_link(args.url)
    print(result["message"])
