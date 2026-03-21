#!/usr/bin/env python3
"""
每日复盘报告推送（增强版 - 含发送链路验证）
按照 AGENTS.md 规则7：主动发送任务必须验证发送链路
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# 添加路径
sys.path.insert(0, '/root/.openclaw/workspace/second-brain-processor')

def get_dialog_stats():
    """获取对话整理统计"""
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    conversations_dir = Path("/root/.openclaw/workspace/obsidian-vault/02-Conversations")
    
    stats = {
        "exists": False,
        "file_count": 0,
        "word_count": 0,
        "files": []
    }
    
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
    
    stats = {
        "wechat_count": 0,
        "zhihu_count": 0,
        "total_count": 0
    }
    
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
    
    report = {
        "new_errors": 0,
        "resolved_errors": 0,
        "new_learnings": 0,
        "evolutions": 0
    }
    
    if errors_file.exists():
        content = errors_file.read_text(encoding='utf-8')
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        new_errors = content.count(f"[ERR-{yesterday}")
        report["new_errors"] = new_errors
        resolved = content.count("Status**: resolved")
        report["resolved_errors"] = resolved
    
    if learnings_file.exists():
        content = learnings_file.read_text(encoding='utf-8')
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        report["new_learnings"] = content.count(yesterday)
    
    if evolution_log.exists():
        content = evolution_log.read_text(encoding='utf-8')
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
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
    
    return report, dialog_stats, article_stats, evolution

def verify_and_send(report_text):
    """验证发送链路并发送报告（规则7：发送链路验证）"""
    
    print(f"[{datetime.now()}] 验证发送链路...")
    
    # 构建消息
    feishu_msg = report_text
    
    try:
        # 尝试发送
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
            print(f"[{datetime.now()}] ✅ 飞书通知已发送")
            return True, None
        else:
            error = result.stderr[:300] if result.stderr else "未知错误"
            print(f"[{datetime.now()}] ❌ 飞书通知发送失败: {error}")
            
            # 记录到链路故障日志（规则7要求）
            log_file = Path("/root/.openclaw/workspace/.learnings/SEND_LINK_FAILURES.md")
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_file, "a", encoding='utf-8') as f:
                f.write(f"\n## [{datetime.now().isoformat()}] 发送链路中断\n")
                f.write(f"**任务**: 每日复盘报告推送\n")
                f.write(f"**错误**: {error}\n")
                f.write(f"**根因分析**: 飞书插件配置警告 - duplicate plugin id detected\n")
                f.write(f"**建议**: 检查 openclaw 飞书插件配置，或重启 gateway\n\n")
            
            return False, error
            
    except Exception as e:
        print(f"[{datetime.now()}] ❌ 发送过程出错: {e}")
        return False, str(e)

def main():
    """主函数"""
    print(f"[{datetime.now()}] 开始生成每日复盘报告（增强版）...")
    
    # 生成报告
    report, dialog_stats, article_stats, evolution = generate_report()
    
    # 输出报告
    print("\n" + "="*60)
    print(report)
    print("="*60)
    
    # 保存到文件
    output_file = Path("/root/.openclaw/workspace/.learnings/daily_report.md")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report, encoding='utf-8')
    
    print(f"\n[{datetime.now()}] 报告已保存到 {output_file}")
    
    # 验证并发送（规则7：发送链路验证）
    if "--dry-run" in sys.argv:
        print("\n[DRY-RUN] 模拟模式，跳过发送")
        return
    
    success, error = verify_and_send(report)
    
    if not success:
        # 发送失败时，在当前会话记录（以便用户看到）
        print(f"\n⚠️ 发送链路异常，已记录到 SEND_LINK_FAILURES.md")
        print(f"建议：检查 openclaw 飞书配置或重启 gateway")
        
        # 返回非零退出码，让 cron 知道失败了
        sys.exit(1)
    
    print(f"\n[{datetime.now()}] 每日复盘报告推送完成")

if __name__ == "__main__":
    main()
