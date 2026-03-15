#!/usr/bin/env python3
"""
链接主题关联检测器 - Link Topic Associator

功能：
1. 检测用户发送的链接
2. 提取链接内容主题
3. 使用AI判断是否与知识库内容关联
4. 关联度高时触发主题讨论

Author: Kimi Claw
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
VAULT_DIR = WORKSPACE / "obsidian-vault"
LEARNINGS_DIR = WORKSPACE / ".learnings"

# API配置 - 阿里云百炼 Kimi K2.5 API
API_KEY = os.environ.get('ALICLOUD_API_KEY', '')
BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"
MODEL = "kimi-k2.5"


def log(message: str):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def extract_urls(text: str) -> List[str]:
    """从文本中提取URL"""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(url_pattern, text)


def fetch_url_content(url: str) -> str:
    """获取链接内容"""
    try:
        import subprocess
        result = subprocess.run(
            ['curl', '-s', '-L', '--max-time', '10', url],
            capture_output=True,
            text=True,
            timeout=15
        )
        # 简单提取标题和正文
        html = result.stdout
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        
        # 提取meta description
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)', html, re.IGNORECASE)
        description = desc_match.group(1) if desc_match else ""
        
        return f"{title}\n{description}"[:2000]  # 限制长度
    except Exception as e:
        log(f"获取链接内容失败: {e}")
        return ""


def get_recent_knowledge(days: int = 30) -> str:
    """获取近期知识库内容摘要"""
    knowledge_snippets = []
    
    for search_dir in [MEMORY_DIR, VAULT_DIR]:
        if not search_dir.exists():
            continue
        for md_file in search_dir.rglob("*.md"):
            try:
                import time
                mtime = time.time() - os.path.getmtime(md_file)
                if mtime <= days * 24 * 3600:  # 最近days天
                    content = md_file.read_text(encoding='utf-8')[:500]
                    knowledge_snippets.append(f"[{md_file.name}]\n{content}")
            except:
                continue
    
    return "\n\n".join(knowledge_snippets[:5])  # 取前5个


def analyze_association(link_content: str, knowledge_base: str) -> Dict:
    """
    使用AI分析链接主题与知识库的关联度
    
    Returns:
        {
            'associated': bool,  # 是否关联
            'association_type': str,  # 关联类型
            'relevant_topics': List[str],  # 相关主题
            'discussion_angle': str,  # 讨论角度建议
            'confidence': float  # 置信度 0-1
        }
    """
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        
        prompt = f"""分析以下链接内容与知识库的关联度。

【链接内容】
{link_content}

【知识库近期内容】
{knowledge_base}

请判断：
1. 链接主题是否与知识库内容有关联？（是/否）
2. 如果有关联，关联类型是什么？（延伸/对比/补充/反思）
3. 相关的知识库主题有哪些？
4. 建议的讨论角度是什么？
5. 置信度（0-1）

输出JSON格式：
{{
    "associated": true/false,
    "association_type": "延伸/对比/补充/反思/无",
    "relevant_topics": ["主题1", "主题2"],
    "discussion_angle": "建议讨论角度",
    "confidence": 0.8
}}"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "你是一个主题关联分析专家，擅长发现内容之间的联系。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        result_text = response.choices[0].message.content
        
        # 提取JSON
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            return json.loads(json_match.group())
        
        return {'associated': False, 'confidence': 0}
        
    except Exception as e:
        log(f"AI分析失败: {e}")
        return {'associated': False, 'confidence': 0}


def trigger_topic_discussion(link_url: str, analysis: Dict):
    """触发主题讨论"""
    if not analysis.get('associated') or analysis.get('confidence', 0) < 0.6:
        log("关联度不足，不触发讨论")
        return
    
    # 构建讨论引导
    discussion_prompt = f"""💡 **主题关联发现**

检测到链接与您的知识库内容有关联：

🔗 **链接**：{link_url}

📚 **关联知识**：{', '.join(analysis.get('relevant_topics', []))}

💭 **关联类型**：{analysis.get('association_type', '未知')}

🎯 **讨论角度**：{analysis.get('discussion_angle', '无')}

是否展开深入讨论？
回复 **讨论** 开始4阶段主题讨论。
"""
    
    # 发送消息
    try:
        import subprocess
        result = subprocess.run(
            ['openclaw', 'message', 'send', 
             '--target', 'ou_363105a68ee112f714ed44e12c802051',
             '--message', discussion_prompt],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            log("✅ 主题讨论触发成功")
        else:
            log(f"❌ 发送失败: {result.stderr}")
    except Exception as e:
        log(f"发送失败: {e}")


def process_message(message_text: str):
    """处理用户消息，检测链接并判断关联"""
    urls = extract_urls(message_text)
    
    if not urls:
        return
    
    log(f"检测到 {len(urls)} 个链接")
    
    for url in urls[:1]:  # 只处理第一个链接
        log(f"分析链接: {url}")
        
        # 获取链接内容
        link_content = fetch_url_content(url)
        if not link_content:
            continue
        
        # 获取知识库
        knowledge_base = get_recent_knowledge(days=30)
        
        # AI分析关联度
        analysis = analyze_association(link_content, knowledge_base)
        
        log(f"关联分析结果: associated={analysis.get('associated')}, confidence={analysis.get('confidence')}")
        
        # 触发讨论
        if analysis.get('associated') and analysis.get('confidence', 0) >= 0.6:
            trigger_topic_discussion(url, analysis)
        else:
            log("不触发讨论（关联度不足）")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--message', type=str, help='用户消息内容')
    parser.add_argument('--test', action='store_true', help='测试模式')
    args = parser.parse_args()
    
    if args.test:
        # 测试模式
        test_message = "看看这篇文章 https://example.com/article 很有意思"
        process_message(test_message)
    elif args.message:
        process_message(args.message)
    else:
        parser.print_help()
