#!/usr/bin/env python3
"""
Kimi Claw 智能处理系统 v2.2 - 修复版

修复内容：
1. 大文件性能问题：限制文件大小和解析行数
2. 循环逻辑bug：修复 while 循环索引问题
3. 添加超时和进度日志
4. 添加文件锁防止并发执行（使用Linux flock）
5. 改进错误处理和重试机制
"""

import fcntl
import json
import hashlib
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 文件锁配置 - 使用Linux flock
LOCK_FILE = "/tmp/kimiclaw_v2.lock"
LOCK_FD = None

def acquire_lock():
    """获取文件锁，使用Linux flock确保可靠性"""
    global LOCK_FD
    try:
        LOCK_FD = os.open(LOCK_FILE, os.O_RDWR | os.O_CREAT)
        fcntl.flock(LOCK_FD, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # 写入进程ID
        os.write(LOCK_FD, str(os.getpid()).encode())
        return True
    except (IOError, OSError):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 另一个实例正在运行，退出")
        sys.exit(0)

def release_lock():
    """释放文件锁"""
    global LOCK_FD
    try:
        if LOCK_FD is not None:
            fcntl.flock(LOCK_FD, fcntl.LOCK_UN)
            os.close(LOCK_FD)
            LOCK_FD = None
            # 尝试删除锁文件
            try:
                os.unlink(LOCK_FILE)
            except:
                pass
    except:
        pass

# 路径配置
WORKSPACE = Path("/root/.openclaw/workspace")
QUEUE_DIR = WORKSPACE / "second-brain-processor" / "queue"
VAULT_DIR = WORKSPACE / "obsidian-vault"
MEMORY_DIR = WORKSPACE / "memory"
SESSION_DIR = Path("/root/.openclaw/agents/main/sessions")
LEARNINGS_DIR = WORKSPACE / ".learnings"
ERRORS_FILE = LEARNINGS_DIR / "ERRORS.md"

def log_error(error_type: str, details: str, area: str = "general", priority: str = "medium"):
    """自动记录错误到 ERRORS.md"""
    try:
        LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # 生成错误ID
        timestamp = datetime.now()
        error_id = f"ERR-{timestamp.strftime('%Y%m%d')}-{timestamp.strftime('%H%M%S')}"
        
        error_entry = f"""\n## [{error_id}] {error_type}

**Logged**: {timestamp.isoformat()}
**Priority**: {priority}
**Status**: pending
**Area**: {area}

### 问题
{details}

### 解决方案
待记录

---
"""
        
        # 追加到文件
        with open(ERRORS_FILE, 'a', encoding='utf-8') as f:
            f.write(error_entry)
        
        log(f"[错误已记录] {error_id}: {error_type}")
    except Exception as e:
        log(f"[错误记录失败] {e}")

# 性能限制
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB   # 2MB - 覆盖截图文章场景
MAX_LINES_PER_FILE = 10000        # 最多解析10000行
MAX_FILES_TO_PROCESS = 15         # 最多处理15个文件
MAX_FILE_AGE_HOURS = 24           # 24小时窗口 - 每天整理的逻辑

# 状态文件
STATE_FILE = WORKSPACE / "second-brain-processor" / "link_state.json"
LAST_PROCESS_FILE = WORKSPACE / "second-brain-processor" / "last_process_time.txt"

def log(msg):
    """打印并记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line)

def load_state():
    """加载链接状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_state(state):
    """保存链接状态"""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_last_process_time():
    """获取上次整理时间 - 限制为6小时内防止处理过多文件"""
    if LAST_PROCESS_FILE.exists():
        with open(LAST_PROCESS_FILE, 'r') as f:
            last_time = datetime.fromisoformat(f.read().strip())
            # 如果上次处理时间超过6小时前，只处理最近6小时的
            six_hours_ago = datetime.now() - timedelta(hours=6)
            return max(last_time, six_hours_ago)
    return datetime.now() - timedelta(hours=6)  # 默认只处理最近6小时

def get_fixed_daily_window(target_date=None):
    """
    获取固定的每日处理窗口（只处理完整的"昨天"，前天5:00到昨天5:00）
    修改：不再包含今天凌晨的内容，避免话题未聊完就被整理
    """
    if target_date is None:
        target_date = datetime.now()
    
    # 昨天5:00（作为结束时间）
    yesterday_5am = target_date.replace(hour=5, minute=0, second=0, microsecond=0) - timedelta(days=1)
    if target_date.hour < 5:
        # 如果当前时间早于5:00，则昨天5:00是前天的5:00
        yesterday_5am = yesterday_5am - timedelta(days=1)
    
    # 前天5:00（作为开始时间）
    day_before_yesterday_5am = yesterday_5am - timedelta(days=1)
    
    return day_before_yesterday_5am, yesterday_5am

def save_last_process_time(dt=None):
    """保存本次整理时间"""
    if dt is None:
        dt = datetime.now()
    with open(LAST_PROCESS_FILE, 'w') as f:
        f.write(dt.isoformat())

def extract_url(text):
    """从文本中提取URL"""
    if not text:
        return None
    url_pattern = r'https?://[^\s\u3000\uff0c\uff0e\uff01\uff1f\uff08\uff09\[\]"\'\n\r]+'
    match = re.search(url_pattern, text)
    return match.group(0) if match else None

def parse_session_messages_safe(session_content, max_lines=MAX_LINES_PER_FILE):
    """
    安全地解析session中的消息，限制行数防止大文件卡住
    """
    messages = []
    lines = session_content.split('\n')
    
    # 只处理前 max_lines 行
    for line in lines[:max_lines]:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            if data.get('type') == 'message':
                msg_data = data.get('message', {})
                if msg_data.get('role') == 'user':
                    msg_content = msg_data.get('content', [])
                    if msg_content and len(msg_content) > 0:
                        text = msg_content[0].get('text', '')
                        timestamp = data.get('timestamp', '')
                        if text and len(text) > 5:  # 过滤太短的消息
                            messages.append({
                                'text': text,
                                'timestamp': timestamp
                            })
        except (json.JSONDecodeError, IndexError):
            continue
    
    return messages

def get_session_content_since(since_time):
    """
    获取从since_time到现在的所有session内容
    修复：限制文件大小和数量，防止性能问题
    增加：强制时间窗口限制
    """
    all_content = []
    
    if not SESSION_DIR.exists():
        log(f"Session目录不存在: {SESSION_DIR}")
        return all_content
    
    # 强制限制：只处理最近 MAX_FILE_AGE_HOURS 小时的文件
    # 防止since_time太早导致处理过多文件
    max_age = datetime.now() - timedelta(hours=MAX_FILE_AGE_HOURS)
    effective_since = max(since_time, max_age)
    
    log(f"有效时间窗口: {effective_since} 至现在 (最大回溯 {MAX_FILE_AGE_HOURS} 小时)")
    
    # 获取所有文件，按修改时间排序（最新的在前）
    all_files = sorted(
        SESSION_DIR.glob("*.jsonl"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    processed_count = 0
    skipped_count = 0
    
    for session_file in all_files:
        # 限制处理文件数量
        if processed_count >= MAX_FILES_TO_PROCESS:
            log(f"已达到最大文件处理数量 {MAX_FILES_TO_PROCESS}，跳过剩余 {len(all_files) - processed_count} 个文件")
            break
        
        try:
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
            
            # 跳过太旧的文件（使用effective_since）
            if mtime < effective_since:
                continue
            
            # 检查文件大小
            file_size = session_file.stat().st_size
            if file_size > MAX_FILE_SIZE:
                log(f"跳过超大文件: {session_file.name} ({file_size/1024:.0f}KB > {MAX_FILE_SIZE/1024:.0f}KB)")
                skipped_count += 1
                continue
            
            # 读取文件内容
            with open(session_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            all_content.append({
                'file': session_file.name,
                'mtime': mtime,
                'content': content,
                'path': session_file  # 保存路径用于后续删除
            })
            processed_count += 1
            
        except Exception as e:
            log(f"读取文件失败 {session_file.name}: {e}")
            continue
    
    log(f"处理了 {processed_count} 个文件，跳过了 {skipped_count} 个超大文件")
    return all_content

def get_session_content_in_window(start_time, end_time):
    """
    获取指定时间窗口内的所有session内容（固定窗口版本）
    用于凌晨5:00整理任务，处理前一天5:00到今天5:00的固定24小时窗口
    """
    all_content = []
    
    if not SESSION_DIR.exists():
        log(f"Session目录不存在: {SESSION_DIR}")
        return all_content
    
    log(f"固定时间窗口: {start_time} 至 {end_time} (24小时)")
    
    # 获取所有文件
    all_files = sorted(
        SESSION_DIR.glob("*.jsonl"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    processed_count = 0
    skipped_count = 0
    
    for session_file in all_files:
        # 限制处理文件数量
        if processed_count >= MAX_FILES_TO_PROCESS:
            log(f"已达到最大文件处理数量 {MAX_FILES_TO_PROCESS}，跳过剩余 {len(all_files) - processed_count} 个文件")
            break
        
        try:
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
            
            # 只处理在指定时间窗口内的文件
            if mtime < start_time or mtime > end_time:
                continue
            
            # 检查文件大小
            file_size = session_file.stat().st_size
            if file_size > MAX_FILE_SIZE:
                log(f"跳过超大文件: {session_file.name} ({file_size/1024:.0f}KB > {MAX_FILE_SIZE/1024:.0f}KB)")
                skipped_count += 1
                continue
            
            # 读取文件内容
            with open(session_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            all_content.append({
                'file': session_file.name,
                'mtime': mtime,
                'content': content,
                'path': session_file  # 保存路径用于后续删除
            })
            processed_count += 1
            
        except Exception as e:
            log(f"读取文件失败 {session_file.name}: {e}")
            continue
    
    log(f"处理了 {processed_count} 个文件，跳过了 {skipped_count} 个超大文件")
    return all_content


# 系统消息过滤模式
SKIP_PATTERNS = [
    r'scheduled\s+reminder',
    r'compaction\s+memory',
    r'pre[-_]?compaction',
    r'replied\s+message.*untrusted',
    r'HEARTBEAT_OK',
    r'NO_REPLY',
    r'conversation\s+info.*untrusted',
    r'system:\s*\[',
]

def is_system_message(text):
    """检查是否是系统消息"""
    text_lower = text.lower()
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False

def extract_topic_key(text):
    """提取主题关键词，用于合并相似对话"""
    keywords = []
    text_lower = text.lower()
    
    # 艺术相关主题
    if any(k in text_lower for k in ['艺术', '美术', '展览', '鉴赏', '启蒙', '策展', '博物馆', '美术馆']):
        keywords.append('艺术启蒙')
    
    # 系统相关主题  
    if any(k in text_lower for k in ['系统', 'skill', 'github', '推送', '整理']):
        keywords.append('系统优化')
    
    if not keywords:
        keywords.append(text[:10])
    
    return tuple(sorted(keywords))

def categorize_content(sessions_data, since_time):
    """
    将内容分类 - 修复版：修复循环逻辑bug
    """
    links_with_discussion = []
    standalone_chats = []
    pending_links = []
    link_auto_process = []
    temp_chats = []  # 用于收集和合并主题
    
    for session in sessions_data:
        messages = parse_session_messages_safe(session['content'])
        
        if not messages:
            continue
        
        i = 0
        while i < len(messages):
            msg = messages[i]
            url = extract_url(msg['text'])
            
            if url:
                # 找到链接，检查后面是否有讨论
                discussion = []
                j = i + 1
                
                while j < len(messages):
                    next_msg = messages[j]
                    # 如果下一条也是链接，说明当前链接的讨论结束
                    if extract_url(next_msg['text']):
                        break
                    
                    # 提取实际内容（去除系统信息）
                    actual_text = re.sub(
                        r'System:.*Conversation info.*?\n\n', 
                        '', 
                        next_msg['text'], 
                        flags=re.DOTALL
                    )
                    
                    # 过滤 HEARTBEAT、系统消息和太短的文本
                    if ('HEARTBEAT' not in next_msg['text'] and 
                        actual_text.strip() and 
                        len(actual_text.strip()) > 10 and
                        not is_system_message(actual_text)):
                        discussion.append({
                            'text': actual_text.strip(),
                            'timestamp': next_msg['timestamp']
                        })
                    
                    j += 1
                
                # 分类处理
                if discussion:
                    # 判断是我参与的讨论，还是AI主动整理
                    my_participation = any(len(d['text']) > 50 for d in discussion)
                    
                    item = {
                        'url': url,
                        'first_msg': msg['text'][:200],  # 限制长度
                        'discussion': discussion[:10],   # 最多保存10条讨论
                        'timestamp': msg['timestamp']
                    }
                    
                    if my_participation:
                        item['type'] = 'B'
                        links_with_discussion.append(item)
                    else:
                        item['type'] = 'C'
                        link_auto_process.append(item)
                else:
                    pending_links.append({
                        'url': url,
                        'timestamp': msg['timestamp'],
                        'type': 'pending'
                    })
                
                # 修复：确保 i 前进，避免无限循环
                i = max(j, i + 1)
            else:
                # 不是链接，检查是否是独立对话
                actual_text = re.sub(
                    r'System:.*Conversation info.*?\n\n', 
                    '', 
                    msg['text'], 
                    flags=re.DOTALL
                )
                
                if ('HEARTBEAT' not in msg['text'] and 
                    actual_text.strip() and 
                    len(actual_text.strip()) > 20 and
                    not is_system_message(actual_text)):
                    temp_chats.append({
                        'text': actual_text.strip()[:1000],
                        'timestamp': msg['timestamp'],
                        'topic_key': extract_topic_key(actual_text)
                    })
                
                i += 1
    
    return {
        'links_with_discussion': links_with_discussion,
        'standalone_chats': standalone_chats,
        'link_auto_process': link_auto_process,
        'pending_links': pending_links
    }

def retry_failed_pushes():
    """检查并补推之前已本地提交但GitHub推送失败的内容"""
    if not VAULT_DIR.exists():
        return
    
    try:
        result = subprocess.run(
            ['git', 'log', 'origin/main..HEAD', '--oneline'],
            cwd=VAULT_DIR, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode != 0:
            return
        
        unpushed_commits = result.stdout.strip()
        if not unpushed_commits:
            return
        
        commit_count = len(unpushed_commits.split('\n'))
        log(f"发现 {commit_count} 个未推送的提交，开始推送...")
        
        push_result = subprocess.run(
            ['git', 'push', '--force-with-lease'],
            cwd=VAULT_DIR, capture_output=True, text=True, timeout=60
        )
        
        if push_result.returncode == 0:
            log("✅ 补推成功")
        else:
            error_msg = f"补推失败: {push_result.stderr[:200]}"
            log(f"⚠️ {error_msg}")
            log_error("git_push_failed", error_msg, area="git_sync", priority="high")
            
    except Exception as e:
        error_msg = f"补推检查失败: {str(e)}"
        log(error_msg)
        log_error("git_retry_failed", error_msg, area="git_sync", priority="medium")

def commit_and_push(message):
    """提交并推送到GitHub，带重试和指数退避"""
    max_retries = 3
    base_delay = 2  # 基础延迟2秒
    
    for i in range(max_retries):
        try:
            # 每次重试增加延迟（指数退避）
            if i > 0:
                delay = base_delay * (2 ** i)
                log(f"第{i+1}次重试，等待{delay}秒...")
                time.sleep(delay)
            # 添加
            subprocess.run(
                ['git', 'add', '.'],
                cwd=VAULT_DIR, capture_output=True, text=True, timeout=30
            )
            
            # 提交
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=VAULT_DIR, capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0 and 'nothing to commit' not in result.stderr:
                continue
            
            # 推送
            result = subprocess.run(
                ['git', 'push', '--force-with-lease'],
                cwd=VAULT_DIR, capture_output=True, text=True, timeout=60
            )
            
            if result.returncode == 0:
                return {'success': True}
            
        except Exception as e:
            if i == max_retries - 1:
                error_msg = f"Git操作失败: {str(e)}"
                log_error("git_operation_failed", error_msg, area="git_sync", priority="high")
                return {'success': False, 'error': str(e)}
    
    return {'success': False, 'error': 'Max retries exceeded'}

def get_vault_stats():
    """获取知识库统计"""
    stats = {
        'conversations': 0,
        'articles': 0,
        'total': 0
    }
    
    if not VAULT_DIR.exists():
        return stats
    
    conv_dir = VAULT_DIR / '02-Conversations'
    if conv_dir.exists():
        stats['conversations'] = len(list(conv_dir.rglob('*.md')))
    
    art_dir = VAULT_DIR / '03-Articles'
    if art_dir.exists():
        stats['articles'] = len(list(art_dir.rglob('*.md')))
    
    stats['total'] = stats['conversations'] + stats['articles']
    return stats

if __name__ == '__main__':
    import argparse
    
    # 获取文件锁，防止并发执行
    acquire_lock()
    
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--check-pending', action='store_true', help='检查待处理的链接')
        parser.add_argument('--morning-process', action='store_true', help='凌晨5:00整理')
        parser.add_argument('--generate-report', action='store_true', help='生成复盘报告')
        # 新增：支持自定义日期范围
        parser.add_argument('--days-ago', type=int, default=None, 
                            help='处理N天前的数据 (1=昨天, 2=前天, 以此类推)')
        parser.add_argument('--from-date', type=str, default=None,
                            help='处理从指定日期开始的数据 (格式: YYYY-MM-DD)')
        parser.add_argument('--to-date', type=str, default=None,
                            help='处理到指定日期为止的数据 (格式: YYYY-MM-DD)')
        args = parser.parse_args()
        
        if args.check_pending:
            state = load_state()
            pending = [k for k, v in state.items() if v.get('status') == 'linked']
            print(json.dumps({'pending_links': pending}, ensure_ascii=False))
        
        elif args.morning_process:
            log("=== 凌晨5:00整理任务开始 ===")
            
            # 第1步：补推历史失败记录
            log("【步骤1】检查并补推历史失败记录...")
            retry_failed_pushes()
            
            # 第2步：整理新内容 - 支持自定义日期范围
            # 根据命令行参数确定时间窗口
            if args.days_ago is not None:
                # 使用 --days-ago 参数：处理N天前的数据
                target_date = datetime.now() - timedelta(days=args.days_ago)
                start_time, end_time = get_fixed_daily_window(target_date)
                log(f"【步骤2】整理 {start_time} 至 {end_time} 的内容（{args.days_ago}天前）...")
            elif args.from_date or args.to_date:
                # 使用 --from-date 和/或 --to-date 参数
                if args.from_date:
                    start_time = datetime.strptime(args.from_date, '%Y-%m-%d').replace(hour=5, minute=0, second=0)
                else:
                    start_time = datetime.now() - timedelta(days=7)  # 默认7天前
                if args.to_date:
                    end_time = datetime.strptime(args.to_date, '%Y-%m-%d').replace(hour=5, minute=0, second=0) + timedelta(days=1)
                else:
                    end_time = datetime.now()
                log(f"【步骤2】整理 {start_time} 至 {end_time} 的内容（自定义日期范围）...")
            else:
                # 默认：只处理完整的"昨天"（前天5:00到昨天5:00），不包含今天
                start_time, end_time = get_fixed_daily_window()
                log(f"【步骤2】整理 {start_time} 至 {end_time} 的内容（只处理昨天，不包含今天）...")
            
            # 使用固定窗口获取内容
            sessions = get_session_content_in_window(start_time, end_time)
            categorized = categorize_content(sessions, start_time)
            
            log(f"  - 独立对话：{len(categorized['standalone_chats'])} 条")
            log(f"  - 链接+讨论：{len(categorized['links_with_discussion'])} 个")
            log(f"  - 链接+AI整理：{len(categorized['link_auto_process'])} 个")
            log(f"  - 待处理链接：{len(categorized['pending_links'])} 个")
            
            # 保存独立对话到 vault
            saved_count = 0
            for chat in categorized['standalone_chats']:
                try:
                    # 生成文件名
                    chat_date = datetime.now().strftime('%Y-%m-%d')
                    chat_title = chat['text'][:30].replace('\n', ' ').strip()
                    safe_title = re.sub(r'[^\w\u4e00-\u9fa5]', '_', chat_title)[:30]
                    filename = f"{chat_date}_{safe_title}.md"
                    
                    # 构建内容
                    content = f"""---
date: {chat_date}
type: 聊天记录
tags: [对话, 自动归档]
---

# {chat['text'][:50]}

## 统计
- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

---

{chat['text']}
"""
                    # 保存到 vault
                    target_dir = VAULT_DIR / '02-Conversations'
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_file = target_dir / filename
                    
                    with open(target_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    log(f"  已保存对话: {filename}")
                    saved_count += 1
                except Exception as e:
                    log(f"  保存对话失败: {e}")
                    log_error("chat_save_failed", str(e), area="chat_processing", priority="medium")
            
            if saved_count > 0:
                log(f"  共保存 {saved_count} 条独立对话")
                # 提交到 GitHub
                commit_and_push(f"auto: 凌晨整理 - 保存 {saved_count} 条对话记录")
            
            # 第3步：删除已处理的文章截图
            log("【步骤3】清理已处理的文章截图...")
            deleted_count = 0
            skipped_count = 0
            
            for session in sessions:
                file_path = session.get('path')
                if not file_path or not file_path.exists():
                    continue
                
                # 获取实际文件大小
                file_size = file_path.stat().st_size
                
                # 条件1：文件大小 > 1MB（可能是截图）
                if file_size <= 1024 * 1024:
                    continue
                
                # 条件2：判断是否为文章截图（文件名或内容特征）
                is_article_screenshot = False
                session_content = session.get('content', '')
                
                # 检查文件名是否包含截图相关关键词
                filename_lower = file_path.name.lower()
                screenshot_keywords = ['screenshot', '截图', 'image', 'img_', 'photo', 'pic_']
                if any(kw in filename_lower for kw in screenshot_keywords):
                    is_article_screenshot = True
                
                # 检查内容是否包含文章相关特征（长文本、URL等）
                if not is_article_screenshot and len(session_content) > 1000:
                    # 检查是否包含文章处理相关的关键词
                    article_markers = ['http', '原文', '作者', '来源', '文章', '阅读', 'key takeaway', '核心观点']
                    if any(marker in session_content.lower() for marker in article_markers):
                        is_article_screenshot = True
                
                if not is_article_screenshot:
                    log(f"  跳过非文章截图: {file_path.name} ({file_size/1024/1024:.1f}MB)")
                    skipped_count += 1
                    continue
                
                # 条件3：确认信息已提取（检查是否已保存到笔记）
                info_extracted = False
                url = None
                
                # 从session内容中提取URL
                url_match = re.search(r'https?://[^\s\n\r]+', session_content)
                if url_match:
                    url = url_match.group(0)
                    # 检查该URL是否已处理（通过检查笔记文件是否存在）
                    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                    
                    # 检查各个分类目录中是否存在对应笔记
                    for category in ['03-Articles', '03-Articles/Zhihu', '03-Articles/WeChat', '03-Articles/Substack']:
                        category_dir = VAULT_DIR / category
                        if category_dir.exists():
                            # 查找包含该hash的笔记文件
                            for note_file in category_dir.glob(f"*_{url_hash}.md"):
                                if note_file.exists():
                                    info_extracted = True
                                    log(f"  确认已提取: {url[:60]}... -> {note_file.name}")
                                    break
                        if info_extracted:
                            break
                
                # 如果无法提取URL或无法确认已提取，保守起见不删除
                if not info_extracted:
                    log(f"  跳过未确认提取: {file_path.name} (无法确认信息已保存)")
                    skipped_count += 1
                    continue
                
                # 三个条件都满足：是截图、是文章、信息已提取 -> 删除
                try:
                    file_path.unlink()
                    log(f"  已删除文章截图: {file_path.name} ({file_size/1024/1024:.1f}MB)")
                    deleted_count += 1
                except Exception as e:
                    log(f"  删除失败 {file_path.name}: {e}")
            
            if deleted_count > 0 or skipped_count > 0:
                log(f"  共删除 {deleted_count} 个文章截图，跳过 {skipped_count} 个文件")
            
            # 第4步：保存本次整理时间
            save_last_process_time()
            log("【步骤4】记录本次整理时间")
            
            # 第5步：系统论复盘与自动进化
            log("【步骤5】系统论复盘与自动进化...")
            try:
                # 导入并运行系统进化模块
                sys.path.insert(0, str(WORKSPACE / "second-brain-processor"))
                from system_evolution import daily_review
                evolution_report = daily_review()
                log("✅ 系统进化复盘完成")
                # 将报告保存到日志
                report_file = WORKSPACE / "second-brain-processor" / "evolution_report.txt"
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(evolution_report)
            except Exception as e:
                log(f"⚠️ 系统进化复盘失败: {e}")
                log_error("evolution_review_failed", str(e), area="system_evolution", priority="medium")
            
            log("=== 凌晨5:00整理任务完成 ===")
        
        elif args.generate_report:
            stats = get_vault_stats()
            print(json.dumps(stats, ensure_ascii=False, indent=2))
    
    finally:
        # 确保锁被释放
        release_lock()
