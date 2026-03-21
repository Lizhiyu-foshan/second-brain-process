#!/usr/bin/env python3
"""
AI 深度整理 - 手动触发版（更新版）
整理最近几天的碎片对话，归纳聚焦后更新到Obsidian Vault
- 删除原始碎片文件
- 聚焦笔记放在 02-Conversations/ 目录下
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta

# 路径配置
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
PROCESSOR_DIR = Path("/root/.openclaw/workspace/second-brain-processor")
CONVERSATIONS_DIR = VAULT_DIR / "02-Conversations"

sys.path.insert(0, str(PROCESSOR_DIR))

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def clean_fragmented_content(content: str) -> str:
    """清理碎片化的系统消息"""
    patterns_to_remove = [
        r'\[.*?GMT.*?\].*?\[Queued announce messages.*?\]',
        r'Queued #\d+',
        r'A subagent task .*? just completed successfully\.',
        r'Findings:',
        r'━━━━━━━━━━━━━━━━━━━━━━━━━━',
        r'Process still running \(session [a-z-]+, pid \d+\)',
        r'Use process \(list/poll/log/write/kill/clear/remove\) for follow-up',
        r'Command still running \(session [a-z-]+, pid \d+\)',
        r'Exec completed \([a-z-]+, code \d+\) ::',
        r'System: \[.*?\] Exec (completed|failed)',
        r'Conversation info \(untrusted metadata\):',
        r'```json\s*\{[^}]*\}\s*```',
        r'HEARTBEAT_OK',
        r'## 原始对话\s*$',
    ]
    
    cleaned = content
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL)
    
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

def extract_core_topics(content: str) -> list:
    """提取核心主题"""
    topics = []
    topic_patterns = [
        r'#+\s*(.+?)(?:\n|$)',
        r'【(.+?)】',
        r'\*\*(.+?)\*\*(?:\s*[:：])',
    ]
    
    for pattern in topic_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            match = match.strip()
            if len(match) > 5 and len(match) < 100 and 'http' not in match:
                topics.append(match)
    
    return list(set(topics))[:10]

def process_file(filepath: Path) -> dict:
    """处理单个对话文件"""
    log(f"处理: {filepath.name}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    cleaned = clean_fragmented_content(content)
    
    date_match = re.search(r'date:\s*(\d{4}-\d{2}-\d{2})', content)
    date_str = date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d')
    
    title_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else filepath.stem
    
    topics = extract_core_topics(cleaned)
    has_ai_analysis = 'AI深度分析' in content or 'AI分析' in content
    
    return {
        'filepath': filepath,
        'title': title,
        'date': date_str,
        'content': cleaned,
        'topics': topics,
        'has_ai_analysis': has_ai_analysis,
        'original_length': len(content),
        'cleaned_length': len(cleaned),
    }

def group_by_theme(files_data: list) -> dict:
    """按主题分组文件"""
    themes = {
        '多Agent架构与任务编排': [],
        '自我进化与系统改进': [],
        'GitHub与开发流程': [],
        '定时任务与监控': [],
        'Skill开发与工具': [],
        '其他对话': [],
    }
    
    for data in files_data:
        title_lower = data['title'].lower()
        topics_str = ' '.join(data['topics']).lower()
        
        if any(k in title_lower or k in topics_str for k in ['agent', 'orchestrator', 'pipeline', 'layer', '角色', '编排']):
            themes['多Agent架构与任务编排'].append(data)
        elif any(k in title_lower or k in topics_str for k in ['进化', 'evolution', '改进', '缺口', 'gap', '复盘']):
            themes['自我进化与系统改进'].append(data)
        elif any(k in title_lower or k in topics_str for k in ['github', 'git', '推送', '安全']):
            themes['GitHub与开发流程'].append(data)
        elif any(k in title_lower or k in topics_str for k in ['cron', '定时任务', '监控', 'health']):
            themes['定时任务与监控'].append(data)
        elif any(k in title_lower or k in topics_str for k in ['skill', '工具']):
            themes['Skill开发与工具'].append(data)
        else:
            themes['其他对话'].append(data)
    
    return themes

def generate_focused_note(theme_name: str, files_data: list) -> str:
    """为每个主题生成聚焦的笔记"""
    if not files_data:
        return None
    
    dates = sorted(set(d['date'] for d in files_data))
    
    all_content = []
    all_topics = []
    for data in files_data:
        content = data['content']
        ai_match = re.search(r'## AI深度分析.*?(?=## 原始对话|$)', content, re.DOTALL)
        if ai_match:
            all_content.append(ai_match.group(0))
        else:
            all_content.append(content[:2000])
        all_topics.extend(data['topics'])
    
    unique_topics = list(set(all_topics))[:15]
    
    note = f"""---
date: {dates[0] if dates else datetime.now().strftime('%Y-%m-%d')}
type: 主题归纳
tags: [{theme_name}, AI整理, 聚焦]
---

# {theme_name} - 聚焦整理

## 概述
从 {len(files_data)} 个碎片对话中提取的核心观点整理。

## 涉及日期
{chr(10).join(['- ' + d for d in dates])}

## 核心主题
{chr(10).join(['- ' + t for t in unique_topics])}

## 关键洞察

"""
    
    for i, data in enumerate(files_data[:5], 1):
        note += f"\n### {i}. {data['title'][:50]}\n\n"
        points = re.findall(r'[-*]\s*(.+?)(?:\n|$)', data['content'])
        for point in points[:5]:
            if len(point.strip()) > 10 and len(point.strip()) < 200:
                note += f"- {point.strip()}\n"
    
    note += f"""

## 原始来源
{chr(10).join(['- ' + d['filepath'].name for d in files_data])}

---
*整理时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
*文件数: {len(files_data)} | 压缩率: {sum(d['cleaned_length'] for d in files_data) / sum(d['original_length'] for d in files_data) * 100:.1f}%*
"""
    
    return note

def main():
    log("=" * 50)
    log("AI 深度整理 - 碎片对话聚焦")
    log("=" * 50)
    
    # 1. 获取最近3天的对话文件
    cutoff_date = datetime.now() - timedelta(days=3)
    files = []
    
    for filepath in CONVERSATIONS_DIR.glob("*.md"):
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
        if mtime >= cutoff_date:
            files.append(filepath)
    
    log(f"找到 {len(files)} 个最近3天的对话文件")
    
    if not files:
        log("没有需要整理的文件")
        return
    
    # 2. 处理每个文件
    files_data = []
    for filepath in files:
        try:
            data = process_file(filepath)
            files_data.append(data)
            log(f"  ✓ {filepath.name} (清理后: {data['cleaned_length']}/{data['original_length']} 字符)")
        except Exception as e:
            log(f"  ✗ {filepath.name} 处理失败: {e}")
    
    # 3. 按主题分组
    themes = group_by_theme(files_data)
    
    log(f"\n按主题分组:")
    for theme_name, theme_files in themes.items():
        if theme_files:
            log(f"  - {theme_name}: {len(theme_files)} 个文件")
    
    # 4. 为每个主题生成聚焦笔记（放在 02-Conversations/ 目录下）
    created_files = []
    deleted_files = []
    
    for theme_name, theme_files in themes.items():
        if not theme_files:
            continue
        
        note_content = generate_focused_note(theme_name, theme_files)
        if note_content:
            # 生成文件名 - 放在 conversations 目录下
            date_prefix = datetime.now().strftime('%Y-%m-%d')
            theme_slug = theme_name.replace('与', '_').replace('和', '_')
            filename = f"{date_prefix}_{theme_slug}_聚焦整理.md"
            filepath = CONVERSATIONS_DIR / filename
            
            # 检查是否已存在
            if filepath.exists():
                log(f"  ⚠️ {filename} 已存在，跳过")
                continue
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(note_content)
            
            created_files.append(filepath)
            log(f"  ✓ 创建: {filename}")
            
            # 删除原始碎片文件
            for data in theme_files:
                original_file = data['filepath']
                try:
                    original_file.unlink()
                    deleted_files.append(original_file.name)
                    log(f"    🗑️ 删除: {original_file.name}")
                except Exception as e:
                    log(f"    ⚠️ 删除失败 {original_file.name}: {e}")
    
    # 5. 总结
    log("\n" + "=" * 50)
    log(f"整理完成！")
    log(f"  - 处理文件: {len(files_data)}")
    log(f"  - 生成聚焦笔记: {len(created_files)}")
    log(f"  - 删除原始碎片: {len(deleted_files)}")
    log(f"  - 输出目录: {CONVERSATIONS_DIR}")
    log("=" * 50)
    
    # 6. 推送到GitHub的提示
    if created_files:
        log("\n下一步:")
        log("  cd /root/.openclaw/workspace/obsidian-vault")
        log("  git add .")
        log("  git commit -m 'AI聚焦整理: 归纳碎片对话，保留聚焦笔记'")
        log("  git push")

if __name__ == "__main__":
    main()
