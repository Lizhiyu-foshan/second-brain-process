#!/usr/bin/env python3
"""
collect_raw_conversations.py - v2.1
5:00定时任务 - 原始对话收集
功能：
1. 收集过去24小时对话
2. 按YYYY-MM-DD_raw.md格式保存到00-Inbox/
3. 自动清理7天前的旧文件（滚动保留）
4. 集成增量索引系统
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加lib到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from lib.message_index import IndexManager

# 配置
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
INBOX_DIR = VAULT_DIR / "00-Inbox"
SESSIONS_DIR = Path("/root/.openclaw/agents/main/sessions")
INDEX_PATH = Path("/root/.openclaw/workspace/.data/message_index.json")


def cleanup_old_raw_files(inbox_dir: Path, keep_days: int = 7) -> int:
    """
    v2.1: 清理7天前的raw对话文件
    保留最近7天的记录，自动删除更早的文件
    
    Args:
        inbox_dir: Inbox目录路径
        keep_days: 保留天数，默认7天
        
    Returns:
        删除的文件数量
    """
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    deleted_count = 0
    
    for file_path in inbox_dir.glob("*_raw.md"):
        # 从文件名提取日期: YYYY-MM-DD_raw.md
        date_str = file_path.stem.replace("_raw", "")
        try:
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < cutoff_date:
                file_path.unlink()
                deleted_count += 1
                print(f"[INFO] 删除过期文件: {file_path.name}")
        except ValueError:
            continue  # 日期格式不匹配，跳过
    
    return deleted_count


def collect_raw_conversations():
    """
    v2.1: 收集原始对话并使用增量索引
    """
    print(f"[{datetime.now()}] === 开始执行原始对话收集（v2.1 日期编号+7天滚动）===")
    
    # 确保目录存在
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    
    # v2.1: 清理7天前的旧文件
    print("[INFO] 清理过期文件...")
    deleted = cleanup_old_raw_files(INBOX_DIR, keep_days=7)
    print(f"[INFO] 已删除 {deleted} 个过期文件")
    
    # 计算目标日期（昨天）
    target_date = datetime.now() - timedelta(days=1)
    date_str = target_date.strftime("%Y-%m-%d")
    
    # v2.1: 使用日期编号格式
    output_file = INBOX_DIR / f"{date_str}_raw.md"
    
    print(f"[INFO] 处理时间: 过去24小时 (文件名: {date_str})")
    
    # 初始化增量索引
    index_manager = IndexManager(str(INDEX_PATH))
    
    # 加载现有索引
    index = index_manager.load()
    last_timestamp = index.get("last_processed", {}).get("timestamp_ms", 0)
    
    # 计算时间范围
    start_time = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000)
    
    print(f"[INFO] 时间范围: {start_time} - {end_time}")
    
    # 扫描会话文件
    all_messages = []
    session_files = list(SESSIONS_DIR.glob("*.jsonl"))
    print(f"[INFO] 扫描会话文件: {len(session_files)} 个")
    
    for session_file in session_files:
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line)
                        msg_time = msg.get("timestamp", 0)
                        if start_time <= msg_time <= end_time:
                            all_messages.append(msg)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[WARN] 读取文件失败 {session_file}: {e}")
    
    # 去重
    seen = set()
    unique_messages = []
    for msg in all_messages:
        msg_id = msg.get("id") or f"{msg.get('timestamp')}_{msg.get('content', '')[:50]}"
        if msg_id not in seen:
            seen.add(msg_id)
            unique_messages.append(msg)
    
    print(f"[INFO] 提取消息数: {len(unique_messages)}")
    
    if not unique_messages:
        print(f"[WARN] 昨天（{date_str}）没有对话记录")
        print(f"[{datetime.now()}] === 原始对话收集完成（无数据） ===")
        return
    
    # 按时间排序
    unique_messages.sort(key=lambda x: x.get("timestamp", 0))
    
    # 生成Markdown
    md_content = f"""---
date: {date_str}
type: 原始对话记录
source: 自动收集
message_count: {len(unique_messages)}
---

# {date_str} 原始对话记录

"""
    
    current_hour = None
    for msg in unique_messages:
        msg_time = datetime.fromtimestamp(msg.get("timestamp", 0) / 1000)
        hour = msg_time.hour
        
        # 按小时分组
        if current_hour != hour:
            current_hour = hour
            md_content += f"\n## {hour:02d}:00-{hour+1:02d}:00\n\n"
        
        role = "用户" if msg.get("role") == "user" else "AI"
        content = msg.get("content", "").strip()
        if content:
            md_content += f"[{role}] {content}\n\n"
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"[INFO] 已保存: {output_file}")
    
    # 更新索引
    if unique_messages:
        max_timestamp = max(m.get("timestamp", 0) for m in unique_messages)
        index_manager.update_last_timestamp(max_timestamp, len(unique_messages))
    
    print(f"[{datetime.now()}] === 原始对话收集完成 ===")
    print(f"[INFO] 输出文件: {output_file}")
    print(f"[INFO] 消息数量: {len(unique_messages)}")


if __name__ == "__main__":
    collect_raw_conversations()
