#!/usr/bin/env python3
"""
每日复盘报告推送（V3 - 绕过 openclaw CLI）
使用 message 工具直接发送，避免插件冲突问题
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

def get_dialog_stats():
    """获取对话整理统计"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    conversations_dir = Path("/root/.openclaw/workspace/obsidian-vault/02-Conversations")
    
    stats = {"exists": False, "file_count": 0, "word_count": 0, "files": []}
    
    if conversations_dir.exists():
        for file in conversations_dir.glob("*.md"):
            if yesterday in file.name:
                stats["exists"] = True
                stats["file_count"] += 1
                stats["files"].append(file.name)
                content = file.read_text(encoding='utf-8')
                stats["word_count"] += len(content)
    
    return stats

def get_article_stats():
    """获取文章整理统计"""
    articles_dir = Path("/root/.openclaw/workspace/obsidian-vault/03-Articles")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    stats = {"wechat_count": 0, "zhihu_count": 0, "total_count": 0}
    
    if articles_dir.exists():
        for subdir in articles_dir.iterdir():
            if subdir.is_dir():
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
    
    report = {"new_errors": 0, "resolved_errors": 0, "new_learnings": 0, "evolutions": 0}
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    if errors_file.exists():
        content = errors_file.read_text(encoding='utf-8')
        report["new_errors"] = content.count(f"[ERR-{yesterday}")
        report["resolved_errors"] = content.count("Status**: resolved")
    
    if learnings_file.exists():
        content = learnings_file.read_text(encoding='utf-8')
        report["new_learnings"] = content.count(yesterday)
    
    if evolution_log.exists():
        content = evolution_log.read_text(encoding='utf-8')
        report["evolutions"] = content.count(yesterday)
    
    return report

def generate_report():
    """生成完整报告"""
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

💬 如需深度整理昨日对话，回复「整理」即可触发 AI 分析"""
    
    return report

def main():
    """主函数 - 仅生成报告，不直接发送（通过 message 工具）"""
    print(f"[{datetime.now()}] 开始生成每日复盘报告...")
    
    report = generate_report()
    
    print("\n" + "="*60)
    print(report)
    print("="*60)
    
    # 保存到文件
    output_file = Path("/root/.openclaw/workspace/.learnings/daily_report.md")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report, encoding='utf-8')
    
    print(f"\n[{datetime.now()}] 报告已保存到 {output_file}")
    print(f"\n[{datetime.now()}] 报告内容已输出到 stdout，请使用 message 工具发送")
    
    # 将报告输出到 stdout，供外部调用者使用
    print("\n---FEISHU_MESSAGE_START---")
    print(report)
    print("---FEISHU_MESSAGE_END---")

if __name__ == "__main__":
    main()
