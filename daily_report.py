#!/usr/bin/env python3
"""
Second Brain 每日复盘报告 - 每天早上 8:30 推送
修复版：基于 vault git 提交记录统计，确保捕获所有处理方式
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

QUEUE_DIR = Path("/root/.openclaw/workspace/second-brain-processor/queue")
PROCESSED_DIR = Path("/root/.openclaw/workspace/second-brain-processor/processed")
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
MEMORY_DIR = Path("/root/.openclaw/workspace/memory")
LEARNINGS_DIR = Path("/root/.openclaw/workspace/.learnings")

def get_fix_stats():
    """获取修复问题统计"""
    fix_stats = {
        'fixed_yesterday': 0,
        'pending_fixes': 0,
        'evolution_count': 0
    }
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 检查 FAKE_IMPLEMENTATIONS.md
    fake_impl_file = LEARNINGS_DIR / 'FAKE_IMPLEMENTATIONS.md'
    if fake_impl_file.exists():
        try:
            content = fake_impl_file.read_text(encoding='utf-8')
            # 统计已修复（✅）和待修复（❌/⚠️）
            fix_stats['fixed_yesterday'] = content.count('✅')
            fix_stats['pending_fixes'] = content.count('❌') + content.count('⚠️')
        except (IOError, OSError) as e:
            print(f"⚠️ 读取 FAKE_IMPLEMENTATIONS.md 失败: {e}")
        except UnicodeDecodeError as e:
            print(f"⚠️ 文件编码错误: {e}")
    
    # 检查 EVOLUTION_LOG.md
    evolution_file = LEARNINGS_DIR / 'EVOLUTION_LOG.md'
    if evolution_file.exists():
        try:
            content = evolution_file.read_text(encoding='utf-8')
            # 统计昨天的进化记录
            fix_stats['evolution_count'] = content.count(yesterday)
        except (IOError, OSError) as e:
            print(f"⚠️ 读取 EVOLUTION_LOG.md 失败: {e}")
        except UnicodeDecodeError as e:
            print(f"⚠️ 文件编码错误: {e}")
    
    # 检查 ERRORS.md 新增错误
    errors_file = LEARNINGS_DIR / 'ERRORS.md'
    if errors_file.exists():
        try:
            content = errors_file.read_text(encoding='utf-8')
            # 统计昨天新增的错误
            fix_stats['evolution_count'] += content.count(f'Logged**: {yesterday}')
        except (IOError, OSError) as e:
            print(f"⚠️ 读取 ERRORS.md 失败: {e}")
        except UnicodeDecodeError as e:
            print(f"⚠️ 文件编码错误: {e}")
    
    return fix_stats

def get_yesterday_git_commits():
    """
    获取昨天（0:00-23:59）的 git 提交记录
    这是最可靠的统计来源，包含：
    - 定时任务处理
    - 即时处理
    - 补救处理
    """
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    commits = {
        "date": yesterday,
        "total_commits": 0,
        "processed_count": 0,  # 处理笔记的提交数
        "sync_count": 0,       # 同步提交数
        "details": []
    }
    
    if not VAULT_DIR.exists():
        return commits
    
    try:
        # 获取昨天的所有提交
        # 格式：hash|date|message
        cmd = [
            "git", "log",
            "--since", f"{yesterday} 00:00:00",
            "--until", f"{yesterday} 23:59:59",
            "--pretty=format:%H|%ci|%s",
            "--all"
        ]
        result = subprocess.run(
            cmd, cwd=VAULT_DIR, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode != 0:
            print(f"Git log failed: {result.stderr}", file=sys.stderr)
            return commits
        
        for line in result.stdout.strip().split('\n'):
            if not line or '|' not in line:
                continue
            
            parts = line.split('|', 2)
            if len(parts) < 3:
                continue
            
            commit_hash, commit_date, message = parts
            commits["total_commits"] += 1
            
            # 识别处理类提交（处理X篇 或 添加X篇）
            if ("处理" in message or "添加" in message or "修正" in message) and "篇" in message:
                commits["processed_count"] += 1
                # 提取处理数量
                match = re.search(r'(处理|添加|修正)\s*(\d+)\s*篇', message)
                if match:
                    count = int(match.group(2))
                    commits["details"].append({
                        "hash": commit_hash[:8],
                        "time": commit_date[11:16],  # HH:MM
                        "message": message,
                        "count": count
                    })
                else:
                    # 没有数字，可能是单篇
                    commits["details"].append({
                        "hash": commit_hash[:8],
                        "time": commit_date[11:16],
                        "message": message,
                        "count": 1
                    })
            elif "sync" in message.lower() or "同步" in message:
                commits["sync_count"] += 1
            else:
                commits["details"].append({
                    "hash": commit_hash[:8],
                    "time": commit_date[11:16],
                    "message": message,
                    "count": 0
                })
        
    except Exception as e:
        print(f"Error getting git commits: {e}", file=sys.stderr)
    
    return commits

def get_yesterday_stats():
    """
    获取昨日统计（综合多个来源）
    优先级：git提交 > queue目录 > processed目录
    """
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 从 git 获取处理记录
    git_commits = get_yesterday_git_commits()
    
    # 统计 git 中处理的总数
    git_processed = sum(d.get("count", 0) for d in git_commits.get("details", []))
    
    # 备用：检查 processed 目录（兼容旧数据）
    processed_dir_count = 0
    if PROCESSED_DIR.exists():
        for f in PROCESSED_DIR.glob("*.md"):
            file_date = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
            if file_date == yesterday:
                processed_dir_count += 1
    
    # 检查 queue 目录当前状态
    pending = len(list(QUEUE_DIR.glob("*.md"))) if QUEUE_DIR.exists() else 0
    
    # 计算昨日新增（基于 git 或 processed 目录）
    new_articles = max(git_processed, processed_dir_count)
    
    return {
        "date": yesterday,
        "new_articles": new_articles,
        "processed": new_articles,  # 已处理 = 新增（因为处理后直接入库）
        "pending": pending,
        "git_commits": git_commits["total_commits"],
        "git_details": git_commits.get("details", [])
    }

def has_user_interaction_yesterday():
    """
    检查昨天（0:00-23:59）是否有用户交互
    用于每日复盘报告的免打扰逻辑
    
    注意：使用"昨天"而非"过去24小时"，确保每天8:30的复盘报告
    能正确识别前一天的全部活动，不受当前时间影响
    """
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 1. 检查 vault git 提交（最可靠）- 检查昨天的提交
    try:
        cmd = [
            "git", "log",
            "--since", f"{yesterday} 00:00:00",
            "--until", f"{yesterday} 23:59:59",
            "--pretty=format:%H",
            "--all"
        ]
        result = subprocess.run(
            cmd, cwd=VAULT_DIR, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return True
    except:
        pass
    
    # 2. 检查待读队列（检查昨天创建的文件）
    if QUEUE_DIR.exists():
        yesterday_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(days=1)
        for f in QUEUE_DIR.glob("*.md"):
            try:
                file_mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if yesterday_start <= file_mtime < yesterday_end:
                    return True
            except:
                continue
    
    # 3. 检查 memory 文件（检查昨天的文件）
    if MEMORY_DIR.exists():
        for f in MEMORY_DIR.glob("*.md"):
            try:
                file_date = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
                if file_date == yesterday:
                    with open(f, 'r', encoding='utf-8') as file:
                        if file.read().strip():
                            return True
            except:
                continue
    
    return False
    if QUEUE_DIR.exists() and list(QUEUE_DIR.glob("*.md")):
        return True
    
    # 3. 检查 memory 文件
    if MEMORY_DIR.exists():
        cutoff_time = datetime.now() - timedelta(hours=24)
        for f in MEMORY_DIR.glob("*.md"):
            try:
                file_date = datetime.fromtimestamp(f.stat().st_mtime)
                if file_date >= cutoff_time:
                    with open(f, 'r', encoding='utf-8') as file:
                        if file.read().strip():
                            return True
            except:
                continue
    
    return False

def get_vault_stats():
    """获取知识库统计（包含昨日增量）"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    stats = {
        "conversations": 0,
        "articles": 0,
        "documents": 0,
        "videos": 0,
        "web": 0,
        "total": 0,
        "yesterday_new": {
            "conversations": 0,
            "articles": 0,
            "documents": 0,
            "videos": 0,
            "web": 0,
            "total": 0
        }
    }
    
    if not VAULT_DIR.exists():
        return stats
    
    categories = {
        "02-Conversations": "conversations",
        "03-Articles": "articles",
        "04-Documents": "documents",
        "05-Videos": "videos",
        "06-Web": "web"
    }
    
    for cat_dir, key in categories.items():
        cat_path = VAULT_DIR / cat_dir
        if cat_path.exists():
            all_files = list(cat_path.rglob("*.md"))
            count = len(all_files)
            stats[key] = count
            stats["total"] += count
            
            # 统计昨日新增（基于文件修改时间）
            yesterday_count = 0
            for f in all_files:
                file_date = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
                if file_date == yesterday:
                    yesterday_count += 1
            stats["yesterday_new"][key] = yesterday_count
            stats["yesterday_new"]["total"] += yesterday_count
    
    return stats

def generate_report():
    """生成每日复盘报告"""
    # 免打扰逻辑：检查昨天是否有交互
    if not has_user_interaction_yesterday():
        return ""
    
    yesterday_stats = get_yesterday_stats()
    vault_stats = get_vault_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = yesterday_stats["date"]
    
    # 构建昨日增量字符串
    yd = vault_stats['yesterday_new']
    def delta_str(n):
        return f" (+{n})" if n > 0 else ""
    
    report_lines = [
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄",
        f"📊 每日复盘报告（{today}）",
        f"   统计周期：{yesterday} 00:00 - 23:59",
        "",
        f"📅 昨日动态（{yesterday}）",
        f"  • 新增笔记：{yesterday_stats['new_articles']} 篇",
        f"  • Git 提交：{yesterday_stats['git_commits']} 次",
    ]
    
    # 显示详细提交记录
    if yesterday_stats.get("git_details"):
        report_lines.append("  • 处理记录：")
        for detail in yesterday_stats["git_details"]:
            if detail.get("count", 0) > 0:
                report_lines.append(f"    - {detail['time']} {detail['message']}")
            else:
                report_lines.append(f"    - {detail['time']} {detail['message'][:40]}...")
    
    report_lines.extend([
        f"  • 待处理：{yesterday_stats['pending']} 篇",
        "",
        "📚 知识库统计",
        f"  • 对话记录：{vault_stats['conversations']} 篇{delta_str(yd['conversations'])}",
        f"  • 文章剪藏：{vault_stats['articles']} 篇{delta_str(yd['articles'])}",
        f"  • 文档解读：{vault_stats['documents']} 篇{delta_str(yd['documents'])}",
        f"  • 视频内容：{vault_stats['videos']} 篇{delta_str(yd['videos'])}",
        f"  • 网络爬虫：{vault_stats['web']} 篇{delta_str(yd['web'])}",
        f"  • 总计：{vault_stats['total']} 篇{delta_str(yd['total'])}",
        "",
        "💡 今日建议",
    ])
    
    # 根据待处理数量给出建议
    if yesterday_stats['pending'] > 5:
        report_lines.append(f"  • 待处理笔记较多（{yesterday_stats['pending']} 篇），建议优先处理")
    elif yesterday_stats['pending'] > 0:
        report_lines.append(f"  • 有 {yesterday_stats['pending']} 篇笔记待确认，记得查看")
    else:
        report_lines.append("  • 所有笔记已处理完毕，保持这个节奏！")
    
    # 根据总数给出建议
    if vault_stats['total'] > 100:
        report_lines.append("  • 知识库已积累超过 100 篇，建议定期回顾整理")
    
    # 如果昨天没有处理记录但应该有，给出提示
    if yesterday_stats['new_articles'] == 0 and yesterday_stats['git_commits'] > 0:
        report_lines.append("  • 检测到 Git 活动但无处理记录，可能包含同步/合并操作")
    
    # 添加修复问题统计
    fix_stats = get_fix_stats()
    if fix_stats['fixed_yesterday'] > 0 or fix_stats['pending_fixes'] > 0 or fix_stats['evolution_count'] > 0:
        report_lines.extend([
            "",
            "🔧 系统修复统计",
            f"  • 昨日修复问题：{fix_stats['fixed_yesterday']} 个",
            f"  • 待修复问题：{fix_stats['pending_fixes']} 个",
            f"  • 系统进化次数：{fix_stats['evolution_count']} 次",
        ])
    
    report_lines.extend([
        "",
        "🔗 快捷操作",
        "  • 发送链接给我，自动添加到待处理队列",
        "  • 回复'队列'查看待处理列表",
        "  • 回复'统计'查看详细统计",
        "",
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
    ])
    
    return "\n".join(report_lines)

def generate_report_for_date(target_date: str = None):
    """
    生成指定日期的复盘报告（用于补发）
    target_date: YYYY-MM-DD 格式，默认为昨天
    """
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 临时修改日期计算逻辑
    original_now = datetime.now()
    
    # 获取目标日期的统计
    commits = {
        "date": target_date,
        "total_commits": 0,
        "processed_count": 0,
        "details": []
    }
    
    try:
        cmd = [
            "git", "log",
            "--since", f"{target_date} 00:00:00",
            "--until", f"{target_date} 23:59:59",
            "--pretty=format:%H|%ci|%s",
            "--all"
        ]
        result = subprocess.run(
            cmd, cwd=VAULT_DIR, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if not line or '|' not in line:
                    continue
                parts = line.split('|', 2)
                if len(parts) < 3:
                    continue
                commit_hash, commit_date, message = parts
                commits["total_commits"] += 1
                
                if "处理" in message or "添加" in message or "修正" in message:
                    commits["processed_count"] += 1
                    match = re.search(r'(处理|添加|修正)\s*(\d+)\s*篇', message)
                    if match:
                        count = int(match.group(2))
                        commits["details"].append({
                            "hash": commit_hash[:8],
                            "time": commit_date[11:16],
                            "message": message,
                            "count": count
                        })
                    else:
                        commits["details"].append({
                            "hash": commit_hash[:8],
                            "time": commit_date[11:16],
                            "message": message,
                            "count": 1
                        })
                else:
                    commits["details"].append({
                        "hash": commit_hash[:8],
                        "time": commit_date[11:16],
                        "message": message,
                        "count": 0
                    })
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    
    # 计算处理总数
    git_processed = sum(d.get("count", 0) for d in commits.get("details", []))
    
    # 获取知识库统计
    stats = get_vault_stats()
    
    # 构建报告
    def delta_str(n):
        return f" (+{n})" if n > 0 else ""
    
    yd = stats['yesterday_new']
    
    report_lines = [
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄",
        f"📊 复盘报告（补发）",
        f"   统计周期：{target_date} 00:00 - 23:59",
        "",
        f"📅 当日动态",
        f"  • 新增笔记：{git_processed} 篇",
        f"  • Git 提交：{commits['total_commits']} 次",
    ]
    
    if commits.get("details"):
        report_lines.append("  • 提交记录：")
        for detail in commits["details"]:
            if detail.get("count", 0) > 0:
                report_lines.append(f"    - {detail['time']} {detail['message']}")
            else:
                report_lines.append(f"    - {detail['time']} {detail['message'][:40]}")
    
    report_lines.extend([
        "",
        "📚 知识库统计",
        f"  • 对话记录：{stats['conversations']} 篇",
        f"  • 文章剪藏：{stats['articles']} 篇",
        f"  • 文档解读：{stats['documents']} 篇",
        f"  • 视频内容：{stats['videos']} 篇",
        f"  • 网络爬虫：{stats['web']} 篇",
        f"  • 总计：{stats['total']} 篇",
        "",
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
    ])
    
    return "\n".join(report_lines)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Second Brain Daily Report')
    parser.add_argument('--date', type=str, help='生成指定日期的报告 (YYYY-MM-DD)')
    parser.add_argument('--check', action='store_true', help='检查是否有交互')
    
    args = parser.parse_args()
    
    if args.check:
        result = has_user_interaction_last_24h()
        print(json.dumps({"has_interaction": result}, ensure_ascii=False))
    elif args.date:
        print(generate_report_for_date(args.date))
    else:
        print(generate_report())
