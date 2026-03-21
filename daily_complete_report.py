#!/usr/bin/env python3
"""
每日复盘报告推送（完整版本）
包含：
1. 笔记整理统计
2. 文章整理统计
3. 自我进化复盘报告
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加路径
sys.path.insert(0, '/root/.openclaw/workspace/second-brain-processor')

def get_dialog_stats():
    """获取对话整理统计"""
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 查找 02-Conversations 目录下昨天的所有对话文件
    conversations_dir = Path("/root/.openclaw/workspace/obsidian-vault/02-Conversations")
    
    stats = {
        "exists": False,
        "file_count": 0,
        "word_count": 0,
        "files": []
    }
    
    if conversations_dir.exists():
        # 查找昨天创建的文件（文件名包含日期）
        for file in conversations_dir.glob("*.md"):
            if yesterday in file.name:
                stats["exists"] = True
                stats["file_count"] += 1
                stats["files"].append(file.name)
                # 累加字数
                content = file.read_text(encoding='utf-8')
                stats["word_count"] += len(content)
    
    return stats

def get_article_stats():
    """获取文章整理统计"""
    articles_dir = Path("/root/.openclaw/workspace/obsidian-vault/03-Articles")
    
    # 统计昨天的文章
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    stats = {
        "wechat_count": 0,
        "zhihu_count": 0,
        "total_count": 0
    }
    
    if articles_dir.exists():
        # 遍历所有子目录
        for subdir in articles_dir.iterdir():
            if subdir.is_dir():
                # 查找昨天创建的文件
                for file in subdir.glob(f"{yesterday}*.md"):
                    if "WeChat" in str(subdir):
                        stats["wechat_count"] += 1
                    elif "Zhihu" in str(subdir):
                        stats["zhihu_count"] += 1
                    stats["total_count"] += 1
    
    return stats

def get_evolution_report():
    """生成自我进化复盘报告"""
    errors_file = Path("/root/.openclaw/workspace/.learnings/ERRORS.md")
    learnings_file = Path("/root/.openclaw/workspace/.learnings/LEARNINGS.md")
    evolution_log = Path("/root/.openclaw/workspace/.learnings/EVOLUTION_LOG.md")
    
    report = {
        "new_errors": 0,
        "resolved_errors": 0,
        "new_learnings": 0,
        "evolutions": 0
    }
    
    # 统计昨天的错误
    if errors_file.exists():
        content = errors_file.read_text(encoding='utf-8')
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 统计新错误
        new_errors = content.count(f"[ERR-{yesterday}")
        report["new_errors"] = new_errors
        
        # 统计已解决
        resolved = content.count("Status**: resolved")
        report["resolved_errors"] = resolved
    
    # 统计新学习
    if learnings_file.exists():
        content = learnings_file.read_text(encoding='utf-8')
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        new_learnings = content.count(f"[LEARN-{yesterday}")
        report["new_learnings"] = new_learnings
    
    # 统计进化
    if evolution_log.exists():
        content = evolution_log.read_text(encoding='utf-8')
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        evolutions = content.count(f"## {yesterday}")
        report["evolutions"] = evolutions
    
    return report

def generate_report():
    """生成完整复盘报告"""
    dialog_stats = get_dialog_stats()
    article_stats = get_article_stats()
    evolution = get_evolution_report()
    
    report = f"""📊 每日复盘报告 ({datetime.now().strftime("%Y-%m-%d")})

📅 昨日动态
  • 对话记录：{'✅ 已整理' if dialog_stats['exists'] else '❌ 未生成'} {dialog_stats.get('file_count', 0)}个文件 {dialog_stats.get('word_count', 0)}字
  • 新增文章：{article_stats['total_count']}篇 (微信{article_stats['wechat_count']} + 知乎{article_stats['zhihu_count']})

💡 系统进化
  • 新增错误：{evolution['new_errors']}个
  • 已解决：{evolution['resolved_errors']}个
  • 经验学习：{evolution['new_learnings']}条
  • 系统改进：{evolution['evolutions']}次

🔗 详细记录
  • 对话存档：/root/.openclaw/workspace/obsidian-vault/02-Conversations/
  • 错误日志：/root/.openclaw/workspace/.learnings/ERRORS.md
  • 经验学习：/root/.openclaw/workspace/.learnings/LEARNINGS.md
  • 进化日志：/root/.openclaw/workspace/.learnings/EVOLUTION_LOG.md"""
    
    # 如果有新错误，添加提醒
    if evolution['new_errors'] > 0:
        report += f"\n\n⚠️ 注意：昨日新增{evolution['new_errors']}个错误，建议检查 ERRORS.md"
    
    return report

def main():
    """主函数"""
    print(f"[{datetime.now()}] 开始生成每日复盘报告...")
    
    # 生成报告
    report = generate_report()
    
    # 输出报告
    print("\n" + "="*60)
    print(report)
    print("="*60)
    
    # 保存到文件
    output_file = Path("/root/.openclaw/workspace/.learnings/daily_report.md")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report, encoding='utf-8')
    
    print(f"\n[{datetime.now()}] 报告已保存到 {output_file}")
    
    # 发送飞书通知
    try:
        import subprocess
        
        # 构建飞书消息（简化版，不带详细链接）
        dialog_stats = get_dialog_stats()
        article_stats = get_article_stats()
        evolution = get_evolution_report()
        
        feishu_msg = f"""📊 每日复盘报告 ({datetime.now().strftime("%Y-%m-%d")})

📅 昨日动态
  • 对话记录：{'✅ 已整理' if dialog_stats['exists'] else '❌ 未生成'} {dialog_stats.get('file_count', 0)}个文件 {dialog_stats.get('word_count', 0)}字
  • 新增文章：{article_stats['total_count']}篇 (微信{article_stats['wechat_count']} + 知乎{article_stats['zhihu_count']})

💡 系统进化
  • 新增错误：{evolution['new_errors']}个
  • 已解决：{evolution['resolved_errors']}个
  • 经验学习：{evolution['new_learnings']}条
  • 系统改进：{evolution['evolutions']}次

💬 如需深度整理昨日对话，回复「整理」即可触发 AI 分析"""
        
        # 使用 subprocess 直接调用 openclaw，指定 channel
        cmd = [
            "openclaw", "message", "send",
            "--channel", "feishu",
            "--target", "ou_363105a68ee112f714ed44e12c802051",
            "--message", feishu_msg
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            print(f"\n[{datetime.now()}] ✅ 飞书通知已发送")
        else:
            error = result.stderr[:200] if result.stderr else "未知错误"
            print(f"\n[{datetime.now()}] ❌ 飞书通知发送失败: {error}")
            
    except Exception as e:
        print(f"\n[{datetime.now()}] ❌ 发送飞书通知时出错: {e}")
    
    return report

if __name__ == "__main__":
    main()
