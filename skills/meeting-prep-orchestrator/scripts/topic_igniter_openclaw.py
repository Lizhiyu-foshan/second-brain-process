#!/usr/bin/env python3
"""
主题讨论激发器 - OpenClaw版本
通过OpenClaw框架调用，使用KIMI_API_KEY和kimi_search

启动方式：
1. 用户主动发送"主题讨论" → 立即执行
2. OpenClaw定时任务 → 每天检查一次
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# 路径配置
WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
VAULT_DIR = WORKSPACE / "obsidian-vault"
LEARNINGS_DIR = WORKSPACE / ".learnings"
TOPIC_STATE_FILE = LEARNINGS_DIR / "topic_discussion_state.json"

FEISHU_USER = "ou_363105a68ee112f714ed44e12c802051"


def log(message: str):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def discover_topics_from_recent_notes(days: int = 3) -> list:
    """从近期笔记中发现潜在讨论主题"""
    topics = []
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # 收集近期笔记
    recent_notes = []
    
    for search_dir in [MEMORY_DIR, VAULT_DIR]:
        if not search_dir.exists():
            continue
        for md_file in search_dir.rglob("*.md"):
            try:
                mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
                if mtime >= cutoff_date:
                    content = md_file.read_text(encoding='utf-8')
                    # 检查是否有发散思考标记
                    if any(marker in content for marker in [
                        '发散', '联想', '思考', '疑问', '?', '待讨论',
                        'TODO', 'FIXME', '待确认', '可以深入'
                    ]):
                        recent_notes.append({
                            'file': md_file.name,
                            'path': str(md_file),
                            'content': content[:3000]
                        })
            except:
                continue
    
    # 按时间排序
    recent_notes.sort(key=lambda x: x['mtime'] if hasattr(x, 'mtime') else x['file'], reverse=True)
    
    # 提取候选主题
    for note in recent_notes[:5]:
        lines = note['content'].split('\n')
        title = lines[0].replace('#', '').strip()[:50] if lines else note['file']
        topics.append({
            'title': title,
            'file': note['file'],
            'preview': note['content'][:500]
        })
    
    return topics[:3]


def analyze_with_openclaw(topic_title: str, topic_preview: str) -> str:
    """使用OpenClaw框架调用AI分析"""
    
    # 构建prompt
    prompt = f"""作为主题讨论引导者，分析以下内容，设计激发用户思考的讨论路径。

**主题**: {topic_title}

**材料预览**:
```
{topic_preview}
```

请生成以下格式的讨论引导（用中文）：

💡 **主题讨论：{topic_title}**

[用一句话引发兴趣，点出核心矛盾或价值]

💭 **启动问题**：
[一个开放式问题，能激发深入思考，不是简单的是/否]

（回复你的想法，我们继续深入）

要求：
1. 基于材料中的具体内容
2. 问题要开放式
3. 要激发用户自己的思考
4. 不要一次性抛出所有内容"""

    # 使用openclaw命令调用AI
    try:
        result = subprocess.run(
            [
                "openclaw", "sessions", "spawn",
                "--task", prompt,
                "--model", "k2p5",
                "--timeout", "60"
            ],
            capture_output=True,
            text=True,
            timeout=90
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            log(f"OpenClaw调用失败: {result.stderr}")
            return generate_fallback_message(topic_title)
            
    except Exception as e:
        log(f"调用失败: {e}")
        return generate_fallback_message(topic_title)


def generate_fallback_message(topic_title: str) -> str:
    """降级处理"""
    return f"""💡 **主题讨论：{topic_title}**

注意到你最近在关注这个主题，有一个角度可能值得探讨...

💭 **启动问题**：
从新的视角重新审视这个主题，你会有什么不同的发现？

（回复你的想法，我们继续深入）"""


def send_discussion_to_user(message: str) -> bool:
    """发送讨论消息到飞书"""
    try:
        # 使用openclaw message send
        result = subprocess.run(
            [
                "openclaw", "message", "send",
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
    import argparse
    parser = argparse.ArgumentParser(description='主题讨论激发器')
    parser.add_argument('--discover', action='store_true', help='自动发现主题并推送')
    parser.add_argument('--topic', type=str, help='指定主题分析')
    parser.add_argument('--test', action='store_true', help='测试模式')
    args = parser.parse_args()
    
    if args.topic:
        # 分析指定主题
        log(f"分析指定主题: {args.topic}")
        message = analyze_with_openclaw(args.topic, "")
        if args.test:
            print("\n【测试模式】生成的消息：")
            print("=" * 60)
            print(message)
            print("=" * 60)
        else:
            if send_discussion_to_user(message):
                log("✅ 讨论消息已发送")
            else:
                log("❌ 发送失败")
    
    elif args.discover:
        # 自动发现主题
        log("正在发现近期主题...")
        topics = discover_topics_from_recent_notes(days=3)
        
        if not topics:
            log("近期没有发现值得讨论的主题")
            # 发送静默通知（可选）
            return
        
        log(f"发现 {len(topics)} 个候选主题")
        
        # 选择第一个主题进行分析
        selected = topics[0]
        log(f"选择主题: {selected['title']}")
        
        message = analyze_with_openclaw(selected['title'], selected['preview'])
        
        if args.test:
            print("\n【测试模式】生成的消息：")
            print("=" * 60)
            print(message)
            print("=" * 60)
        else:
            if send_discussion_to_user(message):
                log("✅ 讨论消息已发送")
            else:
                log("❌ 发送失败")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
