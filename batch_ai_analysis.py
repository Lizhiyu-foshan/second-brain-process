#!/usr/bin/env python3
"""
AI待处理分析任务 - 主会话处理器

此脚本设计为由主会话（OpenClaw AI）调用，使用 sessions_spawn 工具
批量处理所有待处理的AI分析任务。

使用方法：
1. 先运行 process_pending_ai_analysis.py 生成任务列表
2. 然后运行此脚本，使用 sessions_spawn 处理每个任务
3. 更新原笔记文件
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

PENDING_DIR = Path("/tmp/ai_analysis_pending")
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")

def log(message: str):
    """日志输出"""
    print(f"[AI任务处理] {message}")

def get_pending_tasks():
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

def analyze_with_subagent(task: dict) -> dict:
    """
    使用子Agent进行深度分析
    通过调用 openclaw sessions_spawn 实现
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
    
    # 构建分析提示
    analysis_prompt = f"""请深度分析以下对话内容，提取核心观点和思考：

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
5. 只返回JSON，不要其他内容"""

    try:
        log(f"  调用子Agent分析: {title[:30]}...")
        
        # 使用 subprocess 调用 openclaw sessions_spawn
        cmd = [
            "openclaw", "sessions_spawn",
            "--task", analysis_prompt,
            "--model", "kimi-coding/k2p5",
            "--thinking", "high",
            "--timeout-seconds", "90",
            "--cleanup", "delete"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=100
        )
        
        if result.returncode == 0:
            # 尝试从输出中提取JSON
            output = result.stdout
            
            # 查找JSON块
            json_match = re.search(r'\{[\s\S]*\}', output)
            if json_match:
                try:
                    ai_result = json.loads(json_match.group())
                    log(f"  ✅ 分析成功")
                    return {
                        "success": True,
                        "result": ai_result
                    }
                except json.JSONDecodeError as e:
                    log(f"  JSON解析失败: {e}")
                    return {"success": False, "error": f"JSON解析失败: {e}"}
        
        log(f"  子Agent调用失败，返回码: {result.returncode}")
        if result.stderr:
            log(f"  错误: {result.stderr[:200]}")
        return {"success": False, "error": f"调用失败: {result.returncode}"}
        
    except Exception as e:
        log(f"  分析异常: {e}")
        return {"success": False, "error": str(e)}

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
    
    success_count = 0
    fail_count = 0
    
    for task in tasks:
        task_id = task.get('task_id', 'unknown')
        title = task.get('title', '无标题')
        task_file = task.get('_file')
        
        log(f"\n处理任务: {task_id} - {title[:40]}...")
        
        # 调用子Agent进行分析
        analysis_result = analyze_with_subagent(task)
        
        if analysis_result.get("success"):
            # 保存分析结果回任务文件（供后续更新笔记使用）
            task["ai_result"] = analysis_result["result"]
            task["status"] = "completed"
            
            if task_file:
                with open(task_file, 'w', encoding='utf-8') as f:
                    json.dump(task, f, ensure_ascii=False, indent=2)
            
            success_count += 1
        else:
            log(f"  分析失败: {analysis_result.get('error')}")
            fail_count += 1
    
    log(f"\n{'='*50}")
    log(f"处理完成: 成功 {success_count}, 失败 {fail_count}")
    
    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
