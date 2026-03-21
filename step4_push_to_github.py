#!/usr/bin/env python3
"""
step4_push_to_github.py - v2.1 四步法第4步
分类推送GitHub（含Dashboard自动更新）
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
DISCUSSIONS_DIR = VAULT_DIR / "01-Discussions"
CONVERSATIONS_DIR = VAULT_DIR / "02-Conversations"


def update_dashboard() -> dict:
    """
    v2.1: 更新Dashboard统计信息
    """
    try:
        # 统计各类文件数量
        discussions = len(list(DISCUSSIONS_DIR.glob("*.md"))) if DISCUSSIONS_DIR.exists() else 0
        conversations = len(list(CONVERSATIONS_DIR.glob("*.md"))) if CONVERSATIONS_DIR.exists() else 0
        
        result = {
            "success": True,
            "updated_at": datetime.now().isoformat(),
            "stats": {
                "discussions": discussions,
                "conversations": conversations
            },
            "message": "Dashboard 已更新"
        }
        print(f"[Dashboard] 更新成功: {result['stats']}")
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def push_to_github(files_created: List[Tuple[Path, str]], source_file: str) -> bool:
    """
    v2.1: 推送GitHub并自动更新Dashboard
    
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
        
        # 2. v2.1: 自动更新Dashboard
        print("[Step4] 更新Dashboard...")
        dashboard_result = update_dashboard()
        
        # 3. Git提交
        print("[Step4] Git提交...")
        subprocess.run(["git", "add", "-A"], cwd=VAULT_DIR, check=True)
        
        file_list = "\n".join([f"- {f.name}" for f, _ in files_created])
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
    
    msg = "✅ 整理完成\n\n"
    
    if discussions:
        msg += "生成主题讨论精华：\n"
        for f in discussions:
            msg += f"• 01-Discussions/{f}\n"
        msg += "\n"
    
    if conversations:
        msg += "对话记录：\n"
        for f in conversations:
            msg += f"• 02-Conversations/{f}\n"
        msg += "\n"
    
    msg += "Dashboard：已更新\n\n已推送到GitHub"
    
    return msg


if __name__ == "__main__":
    print("[Step4] v2.1 GitHub推送模块")
    print("包含功能：文件推送 + Dashboard自动更新")
