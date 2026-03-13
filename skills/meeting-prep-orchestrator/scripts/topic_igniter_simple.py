#!/usr/bin/env python3
"""
主题讨论激发器 - 简化版
通过OpenClaw方式调用，但实际上由主会话处理

使用方式：
1. 用户发送"主题讨论" → 触发分析
2. OpenClaw定时任务每天14:00检查 → 如有主题则发送提醒
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
VAULT_DIR = WORKSPACE / "obsidian-vault"
LEARNINGS_DIR = WORKSPACE / ".learnings"
STATE_FILE = LEARNINGS_DIR / "topic_discussion_state.json"

FEISHU_USER = "ou_363105a68ee112f714ed44e12c802051"


def log(message: str):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def discover_topics(days: int = 3) -> list:
    """发现近期主题"""
    topics = []
    cutoff = datetime.now() - timedelta(days=days)
    
    for search_dir in [MEMORY_DIR, VAULT_DIR]:
        if not search_dir.exists():
            continue
        for md_file in search_dir.rglob("*.md"):
            try:
                mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
                if mtime >= cutoff:
                    content = md_file.read_text(encoding='utf-8')
                    # 检查发散思考标记
                    if any(m in content for m in ['发散','联想','思考','疑问','TODO','待讨论']):
                        lines = content.split('\n')
                        title = lines[0].replace('#','').strip()[:50] if lines else md_file.name
                        topics.append({
                            'title': title,
                            'file': md_file.name,
                            'preview': content[:500],
                            'path': str(md_file)
                        })
            except:
                continue
    
    return topics[:3]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--discover', action='store_true', help='发现主题')
    parser.add_argument('--test', action='store_true', help='测试模式')
    args = parser.parse_args()
    
    if args.discover:
        log("发现近期主题...")
        topics = discover_topics(3)
        
        if not topics:
            log("没有发现值得讨论的主题")
            return
        
        log(f"发现 {len(topics)} 个主题")
        
        # 构建触发消息（让主会话处理AI分析）
        selected = topics[0]
        trigger_message = f"""【主题讨论激发器】

发现潜在讨论主题：{selected['title']}

相关材料：{selected['file']}

预览：
{selected['preview'][:300]}...

请使用AI深度分析这个主题，生成4阶段讨论引导（引入→展开→关联→行动）。"""

        if args.test:
            print("\n【测试模式】将触发以下消息：")
            print("="*60)
            print(trigger_message)
            print("="*60)
        else:
            # 发送给主会话（通过feishu或直接输出）
            print(trigger_message)
            log("✅ 已生成触发消息，等待主会话处理")


if __name__ == "__main__":
    main()
