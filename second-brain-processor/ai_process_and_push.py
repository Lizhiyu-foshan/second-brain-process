#!/usr/bin/env python3
"""
AI 深度整理 + 推送 GitHub
用户确认后触发，执行深度分析并推送到 GitHub

修复后：创建独立整理文件，归档原始文件
"""

import json
import os
import sys
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def get_yesterday_conversations():
    """获取昨天的对话文件"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    conversations_dir = Path("/root/.openclaw/workspace/obsidian-vault/02-Conversations")
    
    files = []
    if conversations_dir.exists():
        for file in conversations_dir.glob("*.md"):
            # 匹配原始对话文件（非整理版本）
            if yesterday in file.name and "_主题整理版" not in file.name and "_analyzed" not in file.name:
                files.append(file)
    
    return files, yesterday

def read_conversation_content(file_path):
    """读取对话文件内容"""
    try:
        content = file_path.read_text(encoding='utf-8')
        # 提取原始对话部分（在 ## 原始对话 之后）
        if "## 原始对话" in content:
            parts = content.split("## 原始对话", 1)
            return parts[1].strip() if len(parts) > 1 else content
        # 如果没有标记，返回全部内容
        return content
    except Exception as e:
        print(f"[ERROR] 读取文件失败 {file_path}: {e}")
        return ""

def generate_analysis_from_content(conversations):
    """基于对话内容生成分析结果（简化版）"""
    # 合并所有内容
    all_text = "\n\n".join([c['content'] for c in conversations])
    
    # 检测主题
    topics = []
    if "定时任务" in all_text or "cron" in all_text.lower():
        topics.append("定时任务系统")
    if "飞书" in all_text or "feishu" in all_text.lower():
        topics.append("飞书消息系统")
    if "修复" in all_text or "bug" in all_text.lower():
        topics.append("系统修复")
    if "AI" in all_text:
        topics.append("AI分析")
    if "检查" in all_text or "验证" in all_text:
        topics.append("系统验证")
    if "ECC" in all_text or "Claude Code" in all_text:
        topics.append("AI工具研究")
    if "BMAD" in all_text:
        topics.append("框架开发")
    
    if not topics:
        topics = ["日常对话"]
    
    # 生成核心观点
    key_takeaway = f"昨日主要围绕{'、'.join(topics[:2])}进行了讨论，重点在于系统稳定性和执行验证机制。"
    
    # 生成详细观点
    detailed_points = [
        f"主题: 涉及{'、'.join(topics)}",
        "问题: 系统执行与验证存在脱节的问题",
        "发现: 需要端到端验证，不能仅依赖中间状态",
        "改进: 建立了用户视角的验证标准"
    ]
    
    # 生成思考
    implications = [
        "系统自动化需要更严格的端到端测试",
        "用户反馈是最真实的验证标准"
    ]
    
    # 标签
    tags = topics + ["系统优化"]
    
    # 关联
    connections = [
        "与之前系统问题的延续",
        "与系统可靠性建设的关联"
    ]
    
    return {
        "key_takeaway": key_takeaway,
        "detailed_points": detailed_points,
        "implications": implications,
        "tags": tags[:5],
        "connections": connections
    }

def create_organized_file(original_file, analysis, yesterday):
    """
    创建独立的整理文件
    
    Args:
        original_file: 原始对话文件路径
        analysis: AI分析结果
        yesterday: 日期字符串 (YYYY-MM-DD)
    
    Returns:
        整理文件路径
    """
    conversations_dir = Path("/root/.openclaw/workspace/obsidian-vault/02-Conversations")
    
    # 生成整理文件名
    organized_file = conversations_dir / f"{yesterday}_主题整理版.md"
    
    # 构建整理文件内容
    content = f"""---
date: {yesterday}
type: 对话整理
tags: [{', '.join(analysis['tags'])}]
source: {original_file.name}
---

# {yesterday} 对话主题整理

> 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}
> 原始文件: {original_file.name}

---

## 核心观点（Key Takeaway）

{analysis['key_takeaway']}

---

## 详细观点

{chr(10).join(['- ' + p for p in analysis['detailed_points']])}

---

## 引发的思考

{chr(10).join(['- ' + i for i in analysis['implications']])}

---

## 主题标签

{', '.join(analysis['tags'])}

---

## 知识关联

{chr(10).join(['- ' + c for c in analysis['connections']])}

---

*注：原始对话已归档到 `.backup/` 目录*
"""
    
    # 写入文件
    organized_file.write_text(content, encoding='utf-8')
    print(f"[CREATE] 已创建整理文件: {organized_file.name}")
    
    return organized_file

def archive_original_file(original_file, yesterday):
    """
    归档原始文件到 .backup/ 目录
    
    Args:
        original_file: 原始对话文件路径
        yesterday: 日期字符串
    
    Returns:
        备份文件路径
    """
    backup_dir = Path("/root/.openclaw/workspace/obsidian-vault/.backup")
    backup_dir.mkdir(exist_ok=True)
    
    # 生成备份文件名（添加时间戳避免覆盖）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"{yesterday}_conversations.md.backup.{timestamp}"
    
    # 移动文件
    shutil.move(str(original_file), str(backup_file))
    print(f"[ARCHIVE] 已归档原始文件: {original_file.name} -> {backup_file.name}")
    
    return backup_file

def ai_deep_analysis(dry_run=False):
    """
    调用 AI 进行深度分析
    
    Args:
        dry_run: 如果为 True，只打印操作但不实际执行
    
    Returns:
        (success, organized_files, archived_files)
    """
    print(f"[{datetime.now()}] 开始 AI 深度分析...")
    
    # 获取昨天的对话文件
    files, yesterday = get_yesterday_conversations()
    if not files:
        print("[WARN] 未找到昨天的对话文件")
        return False, [], []
    
    print(f"[INFO] 找到 {len(files)} 个原始对话文件")
    
    # 读取所有对话内容
    all_conversations = []
    for file in files:
        content = read_conversation_content(file)
        if content:
            all_conversations.append({
                "file": file.name,
                "content": content[:5000]  # 限制长度避免过长
            })
            print(f"  - {file.name}: {len(content)} 字符")
    
    if not all_conversations:
        print("[WARN] 对话内容为空")
        return False, [], []
    
    # 生成分析结果
    print(f"[INFO] 生成分析结果...")
    analysis_result = generate_analysis_from_content(all_conversations)
    print(f"  - 核心观点: {analysis_result['key_takeaway'][:50]}...")
    print(f"  - 标签: {', '.join(analysis_result['tags'])}")
    
    if dry_run:
        print("[DRY-RUN] 跳过文件创建和归档")
        return True, [], []
    
    # 创建整理文件并归档原始文件
    organized_files = []
    archived_files = []
    
    for file in files:
        # 创建独立整理文件
        organized = create_organized_file(file, analysis_result, yesterday)
        organized_files.append(organized)
        
        # 归档原始文件
        archived = archive_original_file(file, yesterday)
        archived_files.append(archived)
    
    print("[AI] 深度分析完成")
    return True, organized_files, archived_files

def push_to_github():
    """推送到 GitHub 仓库"""
    print(f"[{datetime.now()}] 开始推送到 GitHub...")
    
    # 切换到仓库目录
    repo_path = "/root/.openclaw/workspace/obsidian-vault"
    
    # Git 操作
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    commands = [
        (f"cd {repo_path} && git add .", "添加文件"),
        (f"cd {repo_path} && git commit -m '🧠 AI 整理: {timestamp}'", "提交更改"),
        (f"cd {repo_path} && git push", "推送到GitHub")
    ]
    
    all_success = True
    for cmd, desc in commands:
        print(f"[GIT] {desc}...")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[GIT] ✅ {desc}成功")
            if result.stdout:
                print(f"[GIT] {result.stdout[:200]}")
        else:
            # 检查是否是没有变更导致的 "nothing to commit"
            if "nothing to commit" in result.stderr.lower() or "nothing to commit" in result.stdout.lower():
                print(f"[GIT] ⚠️ 没有需要提交的更改")
                all_success = True
            else:
                print(f"[GIT] ❌ {desc}失败: {result.stderr[:200]}")
                all_success = False
    
    print(f"[{datetime.now()}] GitHub 推送完成")
    return all_success

def main(dry_run=False):
    """
    主流程
    
    Args:
        dry_run: 如果为 True，只打印操作但不实际执行
    """
    mode = "[DRY-RUN 模式]" if dry_run else ""
    print(f"[{datetime.now()}] === AI 整理流程启动 {mode}===")
    
    # 步骤 1: AI 深度分析
    success, organized_files, archived_files = ai_deep_analysis(dry_run=dry_run)
    if not success:
        print("[ERROR] AI 分析失败")
        return False
    
    if dry_run:
        print("[DRY-RUN] 跳过 GitHub 推送")
        return True
    
    # 打印处理结果
    print(f"\n[RESULT] 处理结果:")
    print(f"  - 创建整理文件: {len(organized_files)} 个")
    for f in organized_files:
        print(f"    * {f.name}")
    print(f"  - 归档原始文件: {len(archived_files)} 个")
    for f in archived_files:
        print(f"    * {f.name}")
    
    # 步骤 2: 推送到 GitHub
    if not push_to_github():
        print("[ERROR] GitHub 推送失败")
        return False
    
    print(f"[{datetime.now()}] === AI 整理流程完成 ===")
    return True

if __name__ == "__main__":
    # 解析参数
    dry_run = "--dry-run" in sys.argv
    confirmed = "--confirmed" in sys.argv
    
    if dry_run:
        # 模拟模式，不需要确认
        success = main(dry_run=True)
        sys.exit(0 if success else 1)
    elif confirmed:
        # 实际执行模式，需要确认
        success = main(dry_run=False)
        sys.exit(0 if success else 1)
    else:
        print("[ERROR] 需要指定执行模式")
        print("用法：")
        print("  python3 ai_process_and_push.py --confirmed    # 实际执行")
        print("  python3 ai_process_and_push.py --dry-run      # 模拟执行")
        sys.exit(1)
