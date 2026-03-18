#!/usr/bin/env python3
"""
AI待处理分析任务处理器

在定时任务中，AI深度分析被保存为待处理任务。
此脚本由主会话调用，批量处理这些任务，将AI分析结果写回原文件。
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import List, Dict

PENDING_DIR = Path("/tmp/ai_analysis_pending")
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")

def log(message: str):
    """日志输出"""
    print(f"[AI任务处理] {message}")

def get_pending_tasks() -> List[Dict]:
    """获取所有待处理的任务"""
    if not PENDING_DIR.exists():
        return []
    
    tasks = []
    for task_file in PENDING_DIR.glob("*.json"):
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task = json.load(f)
                task['_file'] = str(task_file)
                tasks.append(task)
        except Exception as e:
            log(f"读取任务文件失败 {task_file}: {e}")
    
    return tasks

def analyze_with_ai(task: Dict) -> Dict:
    """
    使用AI进行深度分析
    此函数在主会话上下文中执行，可以直接使用OpenClaw工具
    """
    title = task['title']
    content = task['content']
    related_notes = task.get('related_notes', [])
    
    # 构建关联笔记上下文
    related_context = ""
    if related_notes:
        related_context = "\n\n**已有关联笔记：**\n"
        for note in related_notes[:2]:
            related_context += f"- 《{note['title']}》\n"
    
    # 返回分析提示
    return {
        "prompt": f"""请深度分析以下对话内容，提取核心观点和思考：

**对话标题**：{title}

**对话内容**：
```
{content[:4000]}
```
{related_context}

请用JSON格式返回分析结果：
{{
    "key_takeaway": "一句话概括这段对话的核心观点（不超过100字）",
    "core_points": ["核心要点1", "核心要点2", "核心要点3"],
    "valuable_thoughts": ["有价值的思考1", "有价值的思考2"],
    "themes": ["主题标签1", "主题标签2"],
    "connections": ["与相关笔记的关联"]
}}

要求：
1. key_takeaway 必须是一句话，概括最重要的洞察
2. core_points 提取3-5个核心讨论点
3. valuable_thoughts 提取引发深思的观点
4. themes 给出2-3个主题标签
5. 只返回JSON，不要其他内容""",
        "title": title
    }

def update_note_with_analysis(note_path: Path, ai_result: Dict) -> bool:
    """将AI分析结果更新到笔记文件中"""
    try:
        if not note_path.exists():
            log(f"笔记文件不存在: {note_path}")
            return False
        
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 构建AI分析内容
        ai_section = f"""## AI深度分析

### 核心观点
{ai_result.get('key_takeaway', '')}

### 详细观点
"""
        for point in ai_result.get('core_points', []):
            ai_section += f"- {point}\n"
        
        if ai_result.get('valuable_thoughts'):
            ai_section += "\n### 引发的思考\n"
            for thought in ai_result.get('valuable_thoughts', []):
                ai_section += f"- {thought}\n"
        
        if ai_result.get('themes'):
            ai_section += f"\n### 主题标签\n{', '.join(ai_result.get('themes', []))}\n"
        
        if ai_result.get('connections'):
            ai_section += "\n### 知识关联\n"
            for conn in ai_result.get('connections', []):
                ai_section += f"- {conn}\n"
        
        # 替换或插入AI分析部分
        # 查找 【待AI分析】标记并替换
        if "【待AI分析】" in content:
            # 查找并替换旧的AI分析部分
            pattern = r'## AI深度分析.*?(?=## |\Z)'
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, ai_section.strip() + "\n\n", content, flags=re.DOTALL)
            else:
                # 在文件末尾添加
                content = content.rstrip() + "\n\n" + ai_section
        else:
            # 在文件末尾添加
            content = content.rstrip() + "\n\n" + ai_section
        
        # 更新状态标签
        content = content.replace("status: 待AI分析", "status: 已深度处理")
        content = content.replace("- 待AI分析", "- 已深度处理")
        
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        log(f"更新笔记失败: {e}")
        return False

def process_single_task(task: Dict) -> bool:
    """处理单个任务"""
    task_id = task.get('task_id')
    title = task.get('title')
    task_file = task.get('_file')
    
    log(f"处理任务: {task_id} - {title[:30]}...")
    
    # 生成分析提示（供主会话AI使用）
    analysis = analyze_with_ai(task)
    
    # 注意：这里只是准备任务，实际AI分析需要在主会话中完成
    # 因为此脚本可能在没有OpenClaw工具的上下文中运行
    
    log(f"  任务已准备，等待AI分析: {title[:30]}...")
    
    return True

def main():
    """主函数"""
    log("="*50)
    log("AI待处理分析任务处理器")
    log("="*50)
    
    tasks = get_pending_tasks()
    
    if not tasks:
        log("没有待处理的任务")
        return 0
    
    log(f"发现 {len(tasks)} 个待处理任务")
    
    # 准备所有任务的分析提示
    analyses = []
    for task in tasks:
        analysis = analyze_with_ai(task)
        analyses.append({
            "task": task,
            "analysis": analysis
        })
    
    # 输出结果（主会话可以捕获并调用AI进行分析）
    output = {
        "pending_count": len(tasks),
        "tasks": analyses
    }
    
    print("\n" + "="*50)
    print("PENDING_AI_ANALYSIS_TASKS_JSON_START")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print("PENDING_AI_ANALYSIS_TASKS_JSON_END")
    print("="*50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
