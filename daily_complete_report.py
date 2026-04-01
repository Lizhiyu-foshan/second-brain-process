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

def get_cron_errors():
    """检查前24小时的 cron 任务异常"""
    error_log = Path("/root/.openclaw/workspace/.learnings/cron_errors.log")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    errors = []
    if error_log.exists():
        content = error_log.read_text(encoding='utf-8')
        for line in content.strip().split('\n'):
            if yesterday in line and '[ERROR]' in line:
                # 提取任务名和错误信息
                try:
                    # 格式: [2026-03-30 04:00:00] [ERROR] task_name: error_msg
                    parts = line.split('[ERROR] ')
                    if len(parts) > 1:
                        task_info = parts[1].strip()
                        errors.append(task_info)
                except:
                    errors.append(line.strip())
    
    # 同时检查各任务的独立日志中的错误
    log_files = {
        "上下文压缩": Path("/root/.openclaw/workspace/.learnings/pure_compactor_cron.log"),
        "清理旧会话": Path("/root/.openclaw/workspace/.learnings/cleanup_cron.log"),
        "配置备份": Path("/root/.openclaw/workspace/.learnings/backup_cron.log"),
        "对话整理": Path("/root/.openclaw/workspace/.learnings/lightweight_retry.log"),
        "复盘报告": Path("/root/.openclaw/workspace/.learnings/daily_complete_report_cron.log"),
    }
    
    for task_name, log_file in log_files.items():
        if log_file.exists():
            try:
                content = log_file.read_text(encoding='utf-8')
                lines = content.strip().split('\n')
                # 检查昨天的最后几行是否有错误
                for line in reversed(lines[-50:]):  # 检查最后50行
                    if yesterday in line or (datetime.now().strftime("%Y-%m-%d") in line):
                        if any(err in line.lower() for err in ['error', 'fail', 'exception', 'timeout', '❌']):
                            if not any(e.startswith(task_name) for e in errors):
                                errors.append(f"{task_name}: {line.strip()[:80]}")
                            break
            except:
                pass
    
    return errors

def generate_report():
    """生成完整报告"""
    dialog_stats = get_dialog_stats()
    article_stats = get_article_stats()
    evolution = get_evolution_report()
    cron_errors = get_cron_errors()
    
    # 构建 cron 状态部分
    cron_section = ""
    if cron_errors:
        cron_section = f"\n⚠️ 定时任务异常 ({len(cron_errors)}个)\n"
        for err in cron_errors[:3]:  # 最多显示3个
            cron_section += f"  • {err[:60]}{'...' if len(err) > 60 else ''}\n"
        if len(cron_errors) > 3:
            cron_section += f"  ... 还有 {len(cron_errors) - 3} 个异常\n"
    else:
        cron_section = "\n✅ 定时任务运行正常\n"
    
    report = f"""📊 每日复盘报告 ({datetime.now().strftime("%Y-%m-%d")})

📅 昨日动态
  • 对话记录：{'✅ 已整理' if dialog_stats['exists'] else '❌ 未生成'} {dialog_stats.get('file_count', 0)}个文件 {dialog_stats.get('word_count', 0)}字
  • 新增文章：{article_stats['total_count']}篇 (微信{article_stats['wechat_count']} + 知乎{article_stats['zhihu_count']}){cron_section}
💡 系统进化
  • 新增错误：{evolution['new_errors']}个
  • 已解决：{evolution['resolved_errors']}个
  • 经验学习：{evolution['new_learnings']}条
  • 系统改进：{evolution['evolutions']}次

💬 如需深度整理昨日对话，回复「整理」即可触发 AI 分析"""
    
    return report, dialog_stats, article_stats, evolution

def verify_and_send(report_text):
    """验证发送链路并发送报告（规则7：发送链路验证 + 送达确认）"""
    
    print(f"[{datetime.now()}] 验证发送链路...")
    
    # 发送前记录指纹（用于后续验证）
    send_time_before = datetime.now().isoformat()
    send_fingerprint = f"daily_{send_time_before[:10]}_{hash(report_text[:50]) % 10000:04d}"
    
    try:
        # 尝试发送
        cmd = [
            "openclaw", "message", "send",
            "--channel", "feishu",
            "--target", "ou_363105a68ee112f714ed44e12c802051",
            "--message", report_text
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        print(f"[{datetime.now()}] 命令返回码: {result.returncode}")
        stdout_preview = result.stdout[:200] if result.stdout else '(无)'
        print(f"[{datetime.now()}] 命令输出: {stdout_preview}")
        
        if result.returncode != 0:
            error = result.stderr[:300] if result.stderr else "未知错误"
            print(f"[{datetime.now()}] ❌ 命令执行失败: {error}")
            log_send_failure(error, "命令返回非零")
            return False, error
        
        # ✅ 关键修复：直接检查命令输出中是否有成功发送的标识
        stdout_full = result.stdout or ""
        if "✅ Sent via Feishu" in stdout_full or "Message ID:" in stdout_full:
            print(f"[{datetime.now()}] ✅ 飞书消息发送成功")
            # 可选：写入 send_records.json 以便统一追踪
            _record_send_success(report_text)
            return True, None
        
        # 如果没有找到成功标识，尝试检查 send_records.json（向后兼容）
        print(f"[{datetime.now()}] ⏳ 等待 3 秒后验证发送记录...")
        import time
        time.sleep(3)
        
        # 检查 send_records.json 是否有新记录
        records_file = Path("/root/.openclaw/workspace/.learnings/send_records.json")
        if records_file.exists():
            try:
                with open(records_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    records = data.get('records', [])
                    
                    # 查找今天、相同类型、相同目标的记录
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    for record in reversed(records[-5:]):  # 检查最近5条
                        record_time = record.get('time', '')
                        if (today_str in record_time and 
                            record.get('type') == 'daily_report' and
                            record.get('success') == True):
                            print(f"[{datetime.now()}] ✅ 发送记录验证成功: {record_time}")
                            return True, None
                    
                    print(f"[{datetime.now()}] ❌ 未在 send_records.json 中找到今天的成功记录")
                    log_send_failure("send_records.json 无今日记录", "送达验证失败")
                    return False, "送达验证失败"
                    
            except Exception as e:
                print(f"[{datetime.now()}] ⚠️ 读取发送记录失败: {e}")
                # 记录不存在时，降级处理：继续认为成功，但发出警告
                print(f"[{datetime.now()}] ⚠️ 降级处理：命令返回成功，但无法验证送达")
                return True, "unverified"
        else:
            print(f"[{datetime.now()}] ⚠️ send_records.json 不存在，跳过验证")
            return True, "unverified"
            
    except Exception as e:
        print(f"[{datetime.now()}] ❌ 发送过程出错: {e}")
        log_send_failure(str(e), "异常捕获")
        return False, str(e)

def log_send_failure(error, reason):
    """记录发送失败到链路故障日志"""
    log_file = Path("/root/.openclaw/workspace/.learnings/SEND_LINK_FAILURES.md")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_file, "a", encoding='utf-8') as f:
        f.write(f"\n## [{datetime.now().isoformat()}] 发送链路中断\n")
        f.write(f"**任务**: 每日复盘报告推送\n")
        f.write(f"**错误**: {error}\n")
        f.write(f"**根因**: {reason}\n")
        f.write(f"**建议**: 检查 openclaw 飞书插件配置、网络连接，或重启 gateway\n\n")

def _record_send_success(report_text):
    """记录发送成功到 send_records.json"""
    try:
        records_file = Path("/root/.openclaw/workspace/.learnings/send_records.json")
        records_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 读取现有记录
        data = {"records": [], "last_cleanup": datetime.now().isoformat()}
        if records_file.exists():
            with open(records_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        # 添加新记录
        import hashlib
        fingerprint = hashlib.md5(report_text[:200].encode()).hexdigest()[:16]
        new_record = {
            "fingerprint": fingerprint,
            "time": datetime.now().isoformat(),
            "type": "daily_report",
            "target": "ou_363105a68ee112f714ed44e12c802051",
            "success": True,
            "error": "",
            "content_preview": report_text[:150].replace('\n', ' ')
        }
        data["records"].append(new_record)
        
        # 保存
        with open(records_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"[{datetime.now()}] 📝 已记录发送成功到 send_records.json")
    except Exception as e:
        print(f"[{datetime.now()}] ⚠️ 记录发送成功失败: {e}")

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
