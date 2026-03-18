#!/usr/bin/env python3
"""
文章链接触发 - 主题讨论
检测链接与知识库关联性，如相关则触发讨论
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

# 路径配置
WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
VAULT_DIR = WORKSPACE / "obsidian-vault"
LEARNINGS_DIR = WORKSPACE / ".learnings"
SCRIPT_DIR = WORKSPACE / "skills/meeting-prep-orchestrator/scripts"

FEISHU_USER = "ou_363105a68ee112f714ed44e12c802051"


def log(message: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def analyze_link_relevance(url: str) -> dict:
    """
    使用AI分析链接内容与知识库的关联性
    返回: {"related": bool, "matched_topic": str, "suggestion": str}
    """
    try:
        # 收集近期笔记标题作为知识库索引
        recent_titles = []
        for search_dir in [MEMORY_DIR, VAULT_DIR]:
            if not search_dir.exists():
                continue
            for md_file in sorted(search_dir.rglob("*.md"), 
                                  key=lambda x: x.stat().st_mtime, 
                                  reverse=True)[:20]:
                try:
                    content = md_file.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    title = lines[0].replace('#', '').strip()[:50] if lines else md_file.name
                    recent_titles.append(title)
                except:
                    continue
        
        # 使用AI分析关联性
        import openai
        
        client = openai.OpenAI(
            api_key=os.environ.get("ALICLOUD_API_KEY"),
            base_url="https://coding.dashscope.aliyuncs.com/v1"
        )
        
        prompt = f"""分析以下文章链接与知识库主题的关联性。

**文章链接**: {url}

**近期知识库主题**:
{chr(10).join([f"- {t}" for t in recent_titles[:10]])}

请判断：
1. 这个链接内容与上述哪个主题最相关？（如果没有，回答"无直接关联"）
2. 如果相关，从什么角度可以引发有价值的讨论？

以JSON格式返回：
{{
    "related": true/false,
    "matched_topic": "匹配的主题名或null",
    "suggestion": "讨论建议（一句话）",
    "reasoning": "判断理由"
}}"""

        response = client.chat.completions.create(
            model="kimi-k2.5",
            messages=[
                {"role": "system", "content": "你是知识关联分析专家，善于发现新内容与已有知识体系的连接点。只返回JSON格式，不要其他内容。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        log(f"AI分析失败: {e}")
        return {"related": False, "error": str(e)}


def send_related_discussion(url: str, matched_topic: str, suggestion: str):
    """发送关联讨论消息"""
    message = f"""🔗 **关联发现**

你分享的文章与「**{matched_topic}**」相关。

💭 **讨论建议**：
{suggestion}

（基于这个新材料，我们可以从什么角度重新审视这个话题？）"""

    try:
        result = subprocess.run(
            [
                "openclaw", "message", "send",
                "--channel", "feishu",
                "--target", FEISHU_USER,
                "--message", message
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        log(f"发送失败: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("用法: python3 topic_link_trigger.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    log(f"分析链接关联性: {url}")
    
    # 分析关联性
    analysis = analyze_link_relevance(url)
    
    if analysis.get("related"):
        matched_topic = analysis.get("matched_topic", "相关主题")
        suggestion = analysis.get("suggestion", "这个链接提供了新的视角，值得深入探讨。")
        
        log(f"发现关联: {matched_topic}")
        
        # 发送讨论邀请
        if send_related_discussion(url, matched_topic, suggestion):
            log("✅ 关联讨论消息已发送")
        else:
            log("❌ 发送失败")
    else:
        log(f"链接与知识库无直接关联: {analysis.get('reasoning', '未找到相关主题')}")
        # 静默处理，不发送消息


if __name__ == "__main__":
    main()
