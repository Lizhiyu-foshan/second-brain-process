#!/usr/bin/env python3
"""
复盘报告行动项闭环追踪 - Action Item Closer

自动提取复盘报告中的行动项，创建追踪任务，监控执行状态，
到期提醒，完成验证，形成'识别-分配-执行-验证'的完整闭环。
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

WORKSPACE = Path("/root/.openclaw/workspace")
LEARNINGS_DIR = WORKSPACE / ".learnings"
ACTION_ITEMS_FILE = LEARNINGS_DIR / "action_items.json"
LOG_FILE = Path("/tmp/action_item_closer.log")

FEISHU_USER = "ou_363105a68ee112f714ed44e12c802051"


def log(message: str):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')


def load_action_items() -> List[Dict]:
    """加载行动项列表"""
    if ACTION_ITEMS_FILE.exists():
        try:
            with open(ACTION_ITEMS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"[WARN] 加载行动项失败: {e}")
    return []


def save_action_items(items: List[Dict]):
    """保存行动项列表"""
    try:
        LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(ACTION_ITEMS_FILE, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"[ERROR] 保存行动项失败: {e}")


def extract_action_items_from_report(report_content: str, report_date: str) -> List[Dict]:
    """从复盘报告中提取行动项 - 优化版"""
    items = []
    
    # 解析报告中的建议条目，提取完整描述
    # 模式1: 带编号的建议条目（如 "1. 🔴 动态上下文压缩阈值管理"）
    numbered_suggestion_pattern = r'(?m)^\s*(\d+)\.\s*[🔴🟡🟢]?\s*\*\*(.+?)\*\*.*?\n.*?💡\s*建议[：:]\s*(.+?)(?=\n|$)'
    
    # 模式2: 简化的安装指令（如 "👉 回复 `安装1` 执行"）
    install_pattern = r'回复\s*[`\']?安装(\d+)[`\']?\s*执行'
    
    # 先提取所有带编号的建议条目
    suggestions = {}
    for match in re.finditer(numbered_suggestion_pattern, report_content, re.DOTALL):
        num = match.group(1)
        title = match.group(2).strip()
        suggestion = match.group(3).strip()[:100]  # 限制长度
        suggestions[num] = {
            'title': title,
            'suggestion': suggestion
        }
    
    # 然后查找安装指令，匹配对应的建议描述
    for match in re.finditer(install_pattern, report_content):
        num = match.group(1)
        if num in suggestions:
            # 使用完整的建议描述
            full_text = f"{suggestions[num]['title']} - {suggestions[num]['suggestion']}"
        else:
            # 降级：使用编号
            full_text = f"安装建议 #{num}"
        
        # 检查是否已存在相同的行动项
        existing = [i for i in items if i['text'] == full_text]
        if not existing:
            items.append({
                'id': f"{report_date}_{len(items)+1}",
                'text': full_text,
                'source': 'daily_report',
                'created_date': report_date,
                'due_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                'status': 'pending',
                'completed': False
            })
    
    return items


def check_overdue_items(items: List[Dict]) -> List[Dict]:
    """检查过期未完成的行动项"""
    today = datetime.now().strftime('%Y-%m-%d')
    overdue = []
    
    for item in items:
        if not item.get('completed') and item.get('due_date', '') < today:
            overdue.append(item)
    
    return overdue


def generate_reminder_message(items: List[Dict]) -> str:
    """生成提醒消息"""
    lines = [
        "⏰ **行动项提醒**",
        "",
        f"📅 今日: {datetime.now().strftime('%Y-%m-%d')}",
        ""
    ]
    
    # 待完成
    pending = [i for i in items if not i.get('completed')]
    if pending:
        lines.append(f"📝 待完成 ({len(pending)}项):")
        for i, item in enumerate(pending[:10], 1):
            status = "🔴 已过期" if item.get('due_date', '') < datetime.now().strftime('%Y-%m-%d') else "⏳ 进行中"
            lines.append(f"{i}. {status} {item.get('text', '')}")
            if item.get('due_date'):
                lines.append(f"   截止: {item['due_date']}")
    
    # 已完成
    completed = [i for i in items if i.get('completed')]
    if completed:
        lines.append("")
        lines.append(f"✅ 已完成 ({len(completed)}项):")
        for i, item in enumerate(completed[-5:], 1):
            lines.append(f"{i}. {item.get('text', '')}")
    
    lines.append("")
    lines.append("💡 操作: 回复 `完成{n}` 标记第n项完成")
    
    return '\n'.join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='行动项闭环追踪')
    parser.add_argument('--check', action='store_true', help='检查并提醒过期行动项')
    parser.add_argument('--list', action='store_true', help='列出所有行动项')
    parser.add_argument('--complete', type=str, help='标记行动项完成 (ID或序号)')
    parser.add_argument('--extract', type=str, help='从报告文件提取行动项')
    args = parser.parse_args()
    
    items = load_action_items()
    
    if args.check:
        log("检查行动项状态...")
        
        # 清理已完成的旧项目
        today = datetime.now()
        cutoff = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        items = [i for i in items if not (i.get('completed') and i.get('due_date', '') < cutoff)]
        
        # 检查过期
        overdue = check_overdue_items(items)
        if overdue:
            log(f"发现 {len(overdue)} 个过期行动项")
            # 发送提醒
            try:
                sys.path.insert(0, str(WORKSPACE / "second-brain-processor"))
                from feishu_guardian import send_feishu_safe
                
                message = generate_reminder_message(items)
                result = send_feishu_safe(message, target=FEISHU_USER, msg_type="action_reminder")
                
                if result.get("success"):
                    log("✅ 提醒已发送")
                else:
                    log("⚠️ 发送失败")
            except Exception as e:
                log(f"[ERROR] 发送失败: {e}")
        else:
            log("无过期行动项")
        
        save_action_items(items)
    
    elif args.list:
        print(generate_reminder_message(items))
    
    elif args.complete:
        # 标记完成
        target = args.complete
        for item in items:
            if item.get('id') == target or item.get('text', '').startswith(target):
                item['completed'] = True
                item['completed_date'] = datetime.now().isoformat()
                log(f"✅ 标记完成: {item.get('text', '')[:50]}")
                break
        save_action_items(items)
    
    elif args.extract:
        # 从报告提取
        report_file = Path(args.extract)
        if report_file.exists():
            content = report_file.read_text(encoding='utf-8')
            report_date = datetime.now().strftime('%Y-%m-%d')
            new_items = extract_action_items_from_report(content, report_date)
            
            if new_items:
                items.extend(new_items)
                save_action_items(items)
                log(f"✅ 提取 {len(new_items)} 个行动项")
            else:
                log("未找到行动项")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
