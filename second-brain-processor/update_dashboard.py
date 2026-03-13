#!/usr/bin/env python3
"""
Dashboard 自动更新脚本
每次处理完笔记后自动更新统计信息
"""

import re
from datetime import datetime
from pathlib import Path

VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
DASHBOARD_FILE = VAULT_DIR / "Dashboard.md"

# 分类目录映射
CATEGORIES = {
    "02-Conversations": ("💬 对话记录", "conversations"),
    "03-Articles": ("📄 文章剪藏", "articles"),
    "04-Documents": ("📚 文档解读", "documents"),
    "05-Videos": ("🎬 视频内容", "videos"),
    "06-Web": ("🌐 网络爬虫", "web"),
}

def count_files_in_category(category_dir: str) -> tuple:
    """统计某个分类下的文件数量和今日新增"""
    cat_path = VAULT_DIR / category_dir
    if not cat_path.exists():
        return 0, 0
    
    all_files = list(cat_path.rglob("*.md"))
    total = len(all_files)
    
    # 统计今日新增（基于文件修改时间）
    today = datetime.now().strftime("%Y-%m-%d")
    today_count = sum(
        1 for f in all_files
        if datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d") == today
    )
    
    return total, today_count

def get_recent_notes(limit: int = 5) -> list:
    """获取最近的笔记"""
    all_notes = []
    
    for cat_dir, (cat_name, _) in CATEGORIES.items():
        cat_path = VAULT_DIR / cat_dir
        if not cat_path.exists():
            continue
        
        for f in cat_path.rglob("*.md"):
            try:
                mtime = f.stat().st_mtime
                # 提取标题（第一行）
                title = f.stem
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        first_line = file.readline().strip()
                        if first_line.startswith('# '):
                            title = first_line[2:]
                except:
                    pass
                
                all_notes.append({
                    "title": title,
                    "category": cat_name,
                    "path": str(f.relative_to(VAULT_DIR)),
                    "mtime": mtime,
                    "date": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                })
            except:
                continue
    
    # 按时间排序
    all_notes.sort(key=lambda x: x["mtime"], reverse=True)
    return all_notes[:limit]

def get_recent_daily_notes(limit: int = 7) -> list:
    """获取最近的每日笔记"""
    daily_dir = VAULT_DIR / "01-Daily"
    if not daily_dir.exists():
        return []
    
    daily_notes = []
    for f in daily_dir.glob("*.md"):
        try:
            mtime = f.stat().st_mtime
            daily_notes.append({
                "filename": f.name,
                "path": str(f.relative_to(VAULT_DIR)),
                "mtime": mtime,
                "date": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            })
        except:
            continue
    
    daily_notes.sort(key=lambda x: x["mtime"], reverse=True)
    return daily_notes[:limit]

def generate_dashboard() -> str:
    """生成新的 Dashboard 内容"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 统计各类别
    stats = []
    total = 0
    total_today = 0
    
    for cat_dir, (cat_name, cat_key) in CATEGORIES.items():
        count, today_count = count_files_in_category(cat_dir)
        stats.append({
            "name": cat_name,
            "count": count,
            "today": today_count
        })
        total += count
        total_today += today_count
    
    # 获取最近笔记
    recent_notes = get_recent_notes(5)
    recent_daily = get_recent_daily_notes(7)
    
    # 构建 Dashboard
    lines = [
        "# Dashboard",
        "",
        f"> 第二大脑仪表盘",
        f"> 最后更新：{now}",
        "",
        "---",
        "",
        "## 📊 统计概览",
        "",
        "| 类别 | 数量 | 今日新增 |",
        "|------|------|----------|",
    ]
    
    for stat in stats:
        today_str = f"+{stat['today']}" if stat['today'] > 0 else "0"
        lines.append(f"| {stat['name']} | {stat['count']} | {today_str} |")
    
    lines.extend([
        f"| **总计** | **{total}** | **+{total_today}** |" if total_today > 0 else f"| **总计** | **{total}** | **0** |",
        "",
        "---",
        "",
        "## 📥 最近添加",
        ""
    ])
    
    if recent_notes:
        for note in recent_notes:
            date_str = "今天" if note['date'] == today else note['date'][5:]  # 显示 MM-DD
            lines.append(f"- [[{note['path']}|{note['title'][:40]}]] ({note['category']}) *{date_str}*")
    else:
        lines.append("*暂无内容*")
    
    lines.extend([
        "",
        "---",
        "",
        "## 📅 最近每日笔记",
        ""
    ])
    
    if recent_daily:
        for note in recent_daily:
            date_str = "今天" if note['date'] == today else note['date'][5:]
            lines.append(f"- [[{note['path']}|{note['filename'].replace('.md', '')}]] *{date_str}*")
    else:
        lines.append("*暂无每日笔记*")
    
    lines.extend([
        "",
        "---",
        "",
        "## 🏷️ 常用标签",
        "",
        "- #待整理",
        "- #已摘要",
        "- #核心",
        "- #归档",
        "",
        "---",
        "",
        "## 🔍 快速链接",
        "",
        "- [00-Inbox](00-Inbox/) - 收件箱",
        "- [01-Daily](01-Daily/) - 每日笔记",
        "- [02-Conversations](02-Conversations/) - 对话记录",
        "- [03-Articles](03-Articles/) - 文章剪藏",
        "- [04-Documents](04-Documents/) - 文档解读",
        "- [05-Videos](05-Videos/) - 视频内容",
        "- [06-Web](06-Web/) - 网络爬虫",
        "",
        "---",
        "",
        "*自动生成 by Kimi Claw*"
    ])
    
    return "\n".join(lines)

def update_dashboard() -> dict:
    """更新 Dashboard 文件"""
    try:
        content = generate_dashboard()
        
        with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "updated_at": datetime.now().isoformat(),
            "message": "Dashboard 已更新"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Update Dashboard')
    parser.add_argument('--dry-run', action='store_true', help='预览但不保存')
    
    args = parser.parse_args()
    
    result = update_dashboard()
    print(result)
