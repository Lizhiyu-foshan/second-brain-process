#!/usr/bin/env python3
"""
step4_push_to_github.py - v2.2 四步法第4步
分类推送GitHub（含Dashboard自动更新）
修复：v2.2 真正写入Dashboard.md文件
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
DASHBOARD_FILE = VAULT_DIR / "Dashboard.md"
DISCUSSIONS_DIR = VAULT_DIR / "01-Discussions"
CONVERSATIONS_DIR = VAULT_DIR / "02-Conversations"
ARTICLES_DIR = VAULT_DIR / "03-Articles"
DOCUMENTS_DIR = VAULT_DIR / "04-Documents"


def get_recent_files(directory: Path, pattern: str = "*.md", count: int = 5) -> List[Path]:
    """获取目录下最近修改的文件"""
    if not directory.exists():
        return []
    files = [f for f in directory.glob(pattern) if f.is_file()]
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return files[:count]


def update_dashboard() -> dict:
    """
    v2.2: 真正更新Dashboard.md文件
    """
    try:
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M")
        
        # 统计各类文件数量
        discussions = len(list(DISCUSSIONS_DIR.glob("*.md"))) if DISCUSSIONS_DIR.exists() else 0
        conversations = len(list(CONVERSATIONS_DIR.glob("*.md"))) if CONVERSATIONS_DIR.exists() else 0
        
        # 统计文章和文档
        articles_wechat = len(list((ARTICLES_DIR / "WeChat").glob("*.md"))) if (ARTICLES_DIR / "WeChat").exists() else 0
        articles_zhihu = len(list((ARTICLES_DIR / "Zhihu").glob("*.md"))) if (ARTICLES_DIR / "Zhihu").exists() else 0
        articles_other = len(list((ARTICLES_DIR / "Other").glob("*.md"))) if (ARTICLES_DIR / "Other").exists() else 0
        articles = articles_wechat + articles_zhihu + articles_other
        
        documents = len(list(DOCUMENTS_DIR.glob("*.md"))) if DOCUMENTS_DIR.exists() else 0
        
        # 获取最近添加的文件
        recent_discussions = get_recent_files(DISCUSSIONS_DIR, count=3)
        recent_articles_wechat = get_recent_files(ARTICLES_DIR / "WeChat", count=2)
        recent_articles_zhihu = get_recent_files(ARTICLES_DIR / "Zhihu", count=2)
        
        # 生成最近添加列表
        recent_additions = []
        for f in recent_discussions:
            recent_additions.append(f"- [[01-Discussions/{f.name}|{f.stem}]] (💬 主题讨论) *{f.stat().st_mtime.strftime("%m-%d") if hasattr(f.stat().st_mtime, 'strftime') else '最近'}*")
        for f in recent_articles_wechat:
            recent_additions.append(f"- [[03-Articles/WeChat/{f.name}|{f.stem}]] (📄 文章剪藏) *最近*")
        for f in recent_articles_zhihu:
            recent_additions.append(f"- [[03-Articles/Zhihu/{f.name}|{f.stem}]] (📄 文章剪藏) *最近*")
        
        recent_additions_str = "\n".join(recent_additions[:5]) if recent_additions else "*暂无最近更新*"
        
        # 生成 Dashboard 内容
        dashboard_content = f"""# Dashboard

> 第二大脑仪表盘
> 最后更新：{now_str}

---

## 📊 统计概览

| 类别 | 数量 | 今日新增 |
|------|------|----------|
| 💬 主题讨论 | {discussions} | - |
| 📝 对话记录 | {conversations} | - |
| 📄 文章剪藏 | {articles} | - |
| 📚 文档解读 | {documents} | - |
| **总计** | **{discussions + conversations + articles + documents}** | **-** |

---

## 📥 最近添加

{recent_additions_str}

---

## 📅 最近每日笔记

*暂无每日笔记*

---

## 🏷️ 常用标签

- #待整理
- #已摘要
- #核心
- #归档

---

## 🔍 快速链接

- [00-Inbox](00-Inbox/) - 收件箱
- [01-Daily](01-Daily/) - 每日笔记
- [02-Conversations](02-Conversations/) - 对话记录
- [03-Articles](03-Articles/) - 文章剪藏
- [04-Documents](04-Documents/) - 文档解读
- [05-Videos](05-Videos/) - 视频内容
- [06-Web](06-Web/) - 网络爬虫

---

*自动生成 by Kimi Claw*
*更新脚本: step4_push_to_github.py v2.2*
"""
        
        # 写入 Dashboard.md 文件
        DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
            f.write(dashboard_content)
        
        result = {
            "success": True,
            "updated_at": now.isoformat(),
            "stats": {
                "discussions": discussions,
                "conversations": conversations,
                "articles": articles,
                "documents": documents
            },
            "message": "Dashboard 已更新"
        }
        print(f"[Dashboard] 更新成功: {result['stats']}")
        return result
    except Exception as e:
        print(f"[Dashboard] 更新失败: {e}")
        return {"success": False, "error": str(e)}


def push_to_github(files_created: List[Tuple[Path, str]], source_file: str) -> bool:
    """
    v2.2: 推送GitHub并自动更新Dashboard
    
    Args:
        files_created: [(文件路径, 内容), ...]
        source_file: 源文件路径
        
    Returns:
        是否成功
    """
    print("[Step4] 开始推送GitHub...")
    
    try:
        # 1. 写入所有文件
        for file_path, content in files_created:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[Step4] 写入文件: {file_path}")
        
        # 2. v2.2: 自动更新Dashboard（真正写入文件）
        print("[Step4] 更新Dashboard...")
        dashboard_result = update_dashboard()
        
        # 3. Git提交
        print("[Step4] Git提交...")
        subprocess.run(["git", "add", "-A"], cwd=VAULT_DIR, check=True)
        
        file_list = "\\n".join([f"- {f.name}" for f, _ in files_created])
        commit_msg = f"""discussions: 提取主题讨论精华

新增：
{file_list}

来源：{source_file}

Dashboard: {'已更新' if dashboard_result['success'] else '更新失败'}"""
        
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=VAULT_DIR, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=VAULT_DIR, check=True)
        
        print("[Step4] ✅ 推送完成")
        return True
        
    except Exception as e:
        print(f"[Step4] ❌ 推送失败: {e}")
        return False


def send_completion_notification(files_created: List[Tuple[Path, str]]) -> str:
    """发送完成通知"""
    discussions = [f.name for f, _ in files_created if "Discussions" in str(f)]
    conversations = [f.name for f, _ in files_created if "Conversations" in str(f)]
    
    msg = "✅ 整理完成\\n\\n"
    
    if discussions:
        msg += "生成主题讨论精华：\\n"
        for f in discussions:
            msg += f"• 01-Discussions/{f}\\n"
        msg += "\\n"
    
    if conversations:
        msg += "对话记录：\\n"
        for f in conversations:
            msg += f"• 02-Conversations/{f}\\n"
        msg += "\\n"
    
    msg += "Dashboard：已更新\\n\\n已推送到GitHub"
    
    return msg


if __name__ == "__main__":
    print("[Step4] v2.2 GitHub推送模块")
    print("包含功能：文件推送 + Dashboard自动更新（真正写入文件）")
    
    # 测试更新 Dashboard
    print("\\n测试更新 Dashboard...")
    result = update_dashboard()
    print(f"结果: {result}")
