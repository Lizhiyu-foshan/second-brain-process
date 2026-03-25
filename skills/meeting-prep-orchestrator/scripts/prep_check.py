#!/usr/bin/env python3
"""
讨论准备检查器 - Meeting Prep Orchestrator

功能：
1. 检查即将到来的讨论日程
2. 自动检索相关知识
3. 生成准备摘要
4. 定时推送到飞书
"""

import json
import re
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# 路径配置
WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
VAULT_DIR = WORKSPACE / "obsidian-vault"
LEARNINGS_DIR = WORKSPACE / ".learnings"
CONFIG_FILE = WORKSPACE / ".config" / "meeting_prep.json"
LOG_FILE = Path("/tmp/meeting_prep.log")
HISTORY_FILE = LEARNINGS_DIR / "meeting_prep_history.json"

FEISHU_USER = "ou_363105a68ee112f714ed44e12c802051"


def log(message: str):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    
    # 追加到日志文件
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')


def load_config() -> Dict:
    """加载配置"""
    default_config = {
        "check_interval_minutes": 30,
        "advance_notice_minutes": 30,
        "working_hours": {"start": 8, "end": 23},
        "auto_topics": ["OpenClaw", "技能", "复盘", "项目", "讨论"],
        "max_related_notes": 5,
        "max_key_points": 5
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return {**default_config, **json.load(f)}
        except Exception as e:
            log(f"[WARN] 配置加载失败: {e}")
    
    return default_config


def search_related_notes(topic: str, max_results: int = 5) -> List[Dict]:
    """搜索相关笔记"""
    related = []
    
    # 搜索关键词
    keywords = topic.lower().split()
    
    # 搜索 memory 目录
    if MEMORY_DIR.exists():
        for md_file in MEMORY_DIR.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8').lower()
                score = sum(1 for kw in keywords if kw in content)
                if score > 0:
                    related.append({
                        'path': str(md_file),
                        'name': md_file.name,
                        'score': score,
                        'source': 'memory'
                    })
            except Exception:
                continue
    
    # 搜索 vault 目录
    if VAULT_DIR.exists():
        for md_file in VAULT_DIR.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8').lower()
                score = sum(1 for kw in keywords if kw in content)
                if score > 0:
                    related.append({
                        'path': str(md_file),
                        'name': md_file.name,
                        'score': score,
                        'source': 'vault'
                    })
            except Exception:
                continue
    
    # 按相关度排序
    related.sort(key=lambda x: x['score'], reverse=True)
    return related[:max_results]


def generate_prep_summary(topic: str, meeting_time: datetime, related_notes: List[Dict]) -> str:
    """生成准备摘要"""
    lines = [
        f"📋 讨论准备摘要：{topic}",
        f"⏰ 会议时间：{meeting_time.strftime('%Y-%m-%d %H:%M')}（30分钟后）",
        "",
        "📚 相关背景："
    ]
    
    # 添加相关笔记
    for i, note in enumerate(related_notes[:5], 1):
        # 提取笔记标题（去掉日期前缀）
        name = note['name'].replace('.md', '')
        if '_' in name:
            name = '_'.join(name.split('_')[1:])  # 去掉日期前缀
        lines.append(f"{i}. [[{note['name']}]] - {name}")
    
    if not related_notes:
        lines.append("• 未找到直接相关笔记，建议补充关键词")
    
    lines.extend([
        "",
        "🎯 建议讨论要点：",
        "• 基于相关笔记准备核心问题",
        "• 确认上次讨论的待办事项状态",
        "• 明确本次讨论的预期产出"
    ])
    
    lines.extend([
        "",
        "💡 提示：回复\"开始讨论\"我将加载完整上下文"
    ])
    
    return '\n'.join(lines)


def send_feishu_notification(content: str) -> bool:
    """发送飞书通知"""
    try:
        # 导入飞书发送模块
        sys.path.insert(0, str(WORKSPACE / "second-brain-processor"))
        from feishu_guardian import send_feishu_safe
        
        result = send_feishu_safe(
            content,
            target=FEISHU_USER,
            msg_type="meeting_prep",
            max_retries=1
        )
        
        return result.get("success", False)
    except Exception as e:
        log(f"[ERROR] 飞书发送失败: {e}")
        return False


def record_prep(topic: str, meeting_time: datetime, notes_count: int):
    """记录准备历史"""
    try:
        LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
        
        history = []
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        history.append({
            'topic': topic,
            'meeting_time': meeting_time.isoformat(),
            'prep_time': datetime.now().isoformat(),
            'notes_count': notes_count
        })
        
        # 只保留最近50条记录
        history = history[-50:]
        
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"[WARN] 记录历史失败: {e}")


def check_upcoming_meetings(config: Dict) -> List[Dict]:
    """检查即将到来的会议 - v2.2: 真实实现
    
    从以下源检查:
    1. 配置文件中的预设会议
    2. 历史记录中的重复会议
    3. 文件系统中的会议标记文件
    """
    upcoming = []
    now = datetime.now()
    
    try:
        # 1. 检查配置文件中的预设会议
        meetings = config.get('meetings', [])
        for meeting in meetings:
            meeting_time = datetime.fromisoformat(meeting.get('time', '1970-01-01'))
            time_until = meeting_time - now
            
            # 检查24小时内即将开始的会议
            if timedelta(0) < time_until <= timedelta(hours=24):
                upcoming.append({
                    'topic': meeting.get('topic', '未命名会议'),
                    'time': meeting_time,
                    'time_until_minutes': int(time_until.total_seconds() / 60),
                    'source': 'config'
                })
        
        # 2. 检查历史记录中的重复会议
        history_file = Path(__file__).parent / '.prep_history.json'
        if history_file.exists():
            history = json.loads(history_file.read_text(encoding='utf-8'))
            
            # 分析历史模式，检测周期性会议
            from collections import defaultdict
            topic_times = defaultdict(list)
            
            for record in history.get('history', []):
                topic = record.get('topic', '')
                if topic:
                    topic_times[topic].append(datetime.fromisoformat(record.get('time', '1970-01-01')))
            
            # 检测周期（简单启发式：同一主题多次出现在相似时间）
            for topic, times in topic_times.items():
                if len(times) >= 2:
                    times.sort()
                    intervals = [(times[i+1] - times[i]).days for i in range(len(times)-1)]
                    avg_interval = sum(intervals) / len(intervals)
                    
                    # 如果上次会议后接近平均周期，预测下次会议
                    last_time = times[-1]
                    next_predicted = last_time + timedelta(days=avg_interval)
                    time_until = next_predicted - now
                    
                    if timedelta(hours=-12) < time_until <= timedelta(hours=24):
                        upcoming.append({
                            'topic': topic,
                            'time': next_predicted,
                            'time_until_minutes': int(time_until.total_seconds() / 60),
                            'source': 'pattern_prediction',
                            'confidence': min(len(times) * 0.2, 0.8)  # 历史越多，置信度越高
                        })
        
        # 3. 检查文件系统中的会议标记
        marker_dir = Path(__file__).parent / '.meeting_markers'
        if marker_dir.exists():
            for marker_file in marker_dir.glob('*.json'):
                try:
                    marker = json.loads(marker_file.read_text(encoding='utf-8'))
                    meeting_time = datetime.fromisoformat(marker.get('scheduled_time', '1970-01-01'))
                    time_until = meeting_time - now
                    
                    if timedelta(0) < time_until <= timedelta(hours=24):
                        upcoming.append({
                            'topic': marker.get('topic', '未命名会议'),
                            'time': meeting_time,
                            'time_until_minutes': int(time_until.total_seconds() / 60),
                            'source': 'marker_file'
                        })
                except Exception:
                    continue
        
        # 按时间排序
        upcoming.sort(key=lambda x: x['time'])
        
    except Exception as e:
        log(f"[WARN] 检查会议时出错: {e}")
    
    return upcoming


def main():
    parser = argparse.ArgumentParser(description='讨论准备检查器')
    parser.add_argument('--topic', type=str, help='讨论主题')
    parser.add_argument('--time', type=str, help='会议时间 (YYYY-MM-DD HH:MM)')
    parser.add_argument('--silent', action='store_true', help='静默模式')
    parser.add_argument('--check', action='store_true', help='检查即将到来的会议')
    args = parser.parse_args()
    
    config = load_config()
    
    if args.topic and args.time:
        # 手动触发特定讨论准备
        try:
            meeting_time = datetime.strptime(args.time, '%Y-%m-%d %H:%M')
        except ValueError:
            log("[ERROR] 时间格式错误，请使用: YYYY-MM-DD HH:MM")
            sys.exit(1)
        
        log(f"正在为\"{args.topic}\"生成准备摘要...")
        
        # 搜索相关笔记
        related_notes = search_related_notes(args.topic, config.get('max_related_notes', 5))
        log(f"找到 {len(related_notes)} 个相关笔记")
        
        # 生成摘要
        summary = generate_prep_summary(args.topic, meeting_time, related_notes)
        
        # 发送通知
        if not args.silent:
            success = send_feishu_notification(summary)
            if success:
                log("✅ 准备摘要已发送")
            else:
                log("⚠️ 发送失败，已保存到日志")
        else:
            log(summary)
        
        # 记录历史
        record_prep(args.topic, meeting_time, len(related_notes))
    
    elif args.check:
        # 检查即将到来的会议 - v2.2: 真实实现
        log("检查即将到来的会议...")
        config = load_config()
        upcoming = check_upcoming_meetings(config)
        
        if upcoming:
            log(f"发现 {len(upcoming)} 个即将开始的会议:")
            for meeting in upcoming:
                source_tag = f"[{meeting.get('source', 'unknown')}]"
                minutes = meeting.get('time_until_minutes', 0)
                time_str = f"{minutes//60}小时{minutes%60}分钟" if minutes > 60 else f"{minutes}分钟"
                log(f"  • {meeting['topic']} - 还有{time_str} {source_tag}")
                
                # 自动触发准备流程
                if minutes <= 60:  # 1小时内自动触发
                    log(f"    自动触发准备流程...")
                    related_notes = search_related_notes(meeting['topic'], config.get('max_related_notes', 5))
                    summary = generate_prep_summary(meeting['topic'], meeting['time'], related_notes)
                    send_feishu_notification(summary)
        else:
            log("未来24小时内没有即将开始的会议")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
