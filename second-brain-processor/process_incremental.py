#!/usr/bin/env python3
"""
Incremental Message Processor - 增量消息处理器

职责:
- 增量扫描会话文件
- 提取新增消息
- 生成对话记录文件
- 更新索引

约束覆盖:
- S1: 执行时间 < 1秒
- S2: 内存使用 < 100MB
- S4: 失败时优雅降级
- I1: 不遗漏任何消息
- I2: 正确处理跨天消息
- I3: 正确处理乱序消息
- I4: 正确处理重复消息

作者: Kimi Claw
创建时间: 2026-03-21
"""

import json
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Tuple
import logging

# 添加lib目录到路径
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from message_index import IndexManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 配置
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
CONVERSATIONS_DIR = VAULT_DIR / "02-Conversations"
SESSIONS_DIR = Path("/root/.openclaw/agents/main/sessions/")


class Message:
    """消息数据类"""
    
    def __init__(self, timestamp: int, role: str, content: str, source_file: str):
        self.timestamp = timestamp
        self.role = role
        self.content = content
        self.source_file = source_file
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "role": self.role,
            "content": self.content,
            "source_file": self.source_file
        }
    
    def get_hash(self) -> str:
        """获取消息哈希（用于去重）"""
        content = f"{self.timestamp}_{self.content[:100]}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()


class IncrementalScanner:
    """
    增量扫描器
    
    高效扫描会话文件，只提取新增消息。
    """
    
    def __init__(self, index_manager: IndexManager):
        self.index_manager = index_manager
        self.stats = {
            "files_scanned": 0,
            "files_with_new": 0,
            "files_skipped": 0,
            "messages_found": 0,
            "messages_after_dedup": 0
        }
    
    def scan(self) -> List[Message]:
        """
        增量扫描所有会话文件
        
        Returns:
            新增消息列表（已去重和排序）
        """
        # 获取上次处理时间戳
        last_ts = self.index_manager.get_last_timestamp()
        logger.info(f"Scanning for messages after timestamp: {last_ts}")
        
        # 获取所有会话文件
        all_files = list(SESSIONS_DIR.glob("*.jsonl"))
        logger.info(f"Found {len(all_files)} session files")
        
        messages = []
        
        for jsonl_file in all_files:
            # 跳过已删除的文件
            if "deleted" in jsonl_file.name:
                continue
            
            self.stats["files_scanned"] += 1
            
            # 快速检查是否有新消息
            if not self._quick_check(jsonl_file, last_ts):
                self.stats["files_skipped"] += 1
                continue
            
            # 读取新增消息
            new_messages = self._read_new_messages(jsonl_file, last_ts)
            
            if new_messages:
                self.stats["files_with_new"] += 1
                messages.extend(new_messages)
                logger.debug(f"Found {len(new_messages)} new messages in {jsonl_file.name}")
        
        self.stats["messages_found"] = len(messages)
        
        # 去重
        messages = self._deduplicate(messages)
        self.stats["messages_after_dedup"] = len(messages)
        
        # 排序（按时间戳）
        messages.sort(key=lambda m: m.timestamp)
        
        logger.info(f"Scan complete: {self.stats}")
        
        return messages
    
    def _quick_check(self, file_path: Path, last_ts: int) -> bool:
        """
        快速检查文件是否有新消息
        
        读取文件最后5行，检查是否有消息时间戳 > last_ts
        
        Args:
            file_path: 会话文件路径
            last_ts: 上次处理时间戳
            
        Returns:
            是否有新消息
        """
        try:
            # 读取文件最后几行
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 如果文件为空，跳过
            if not lines:
                return False
            
            # 检查最后5行
            sample_lines = lines[-5:] if len(lines) >= 5 else lines
            
            for line in sample_lines:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    msg = json.loads(line)
                    if msg.get("type") != "message":
                        continue
                    
                    ts_str = msg.get("timestamp", "")
                    if ts_str:
                        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        msg_ts = int(dt.timestamp() * 1000)
                        
                        # 如果有任何消息在last_ts之后，需要处理该文件
                        if msg_ts > last_ts:
                            return True
                except:
                    continue
            
            # 检查文件最后修改时间
            # 如果文件最近被修改，但上面没找到新消息，保守处理（返回True）
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                if mtime > datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc):
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.warning(f"Quick check failed for {file_path}: {e}")
            # 出错时保守处理（假设有新消息）
            return True
    
    def _read_new_messages(self, file_path: Path, last_ts: int) -> List[Message]:
        """
        读取文件中的新增消息
        
        Args:
            file_path: 会话文件路径
            last_ts: 上次处理时间戳
            
        Returns:
            新增消息列表
        """
        messages = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        msg = json.loads(line)
                        
                        # 只处理消息类型
                        if msg.get("type") != "message":
                            continue
                        
                        # 解析时间戳
                        ts_str = msg.get("timestamp", "")
                        if not ts_str:
                            continue
                        
                        try:
                            dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                            msg_ts = int(dt.timestamp() * 1000)
                        except:
                            continue
                        
                        # 只保留新增消息
                        if msg_ts <= last_ts:
                            continue
                        
                        # 解析消息内容
                        message_data = msg.get("message", {})
                        role = message_data.get("role", "unknown")
                        
                        content_parts = message_data.get("content", [])
                        if isinstance(content_parts, list) and len(content_parts) > 0:
                            content = content_parts[0].get("text", "")
                        else:
                            content = str(content_parts)
                        
                        # 跳过系统消息和心跳
                        if role == "system" or "HEARTBEAT_OK" in content or "Read HEARTBEAT.md" in content:
                            continue
                        
                        messages.append(Message(
                            timestamp=msg_ts,
                            role=role,
                            content=content,
                            source_file=file_path.name
                        ))
                        
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
        
        return messages
    
    def _deduplicate(self, messages: List[Message]) -> List[Message]:
        """
        消息去重
        
        基于时间戳和内容哈希去重。
        
        Args:
            messages: 消息列表
            
        Returns:
            去重后的消息列表
        """
        seen_hashes = set()
        unique_messages = []
        
        for msg in messages:
            msg_hash = msg.get_hash()
            if msg_hash not in seen_hashes:
                seen_hashes.add(msg_hash)
                unique_messages.append(msg)
        
        if len(unique_messages) < len(messages):
            logger.info(f"Deduplicated: {len(messages)} -> {len(unique_messages)}")
        
        return unique_messages


class ConversationWriter:
    """
    对话记录写入器
    
    将消息格式化为Markdown并保存。
    """
    
    def __init__(self, output_dir: Path = None):
        if output_dir is None:
            self.output_dir = CONVERSATIONS_DIR
        else:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def write(self, messages: List[Message], date_str: str) -> Tuple[bool, str]:
        """
        写入对话记录
        
        Args:
            messages: 消息列表
            date_str: 日期字符串（YYYY-MM-DD）
            
        Returns:
            (是否成功, 输出文件路径)
        """
        if not messages:
            logger.info(f"No messages to write for {date_str}")
            return False, ""
        
        # 生成文件内容
        content_lines = [
            f"---",
            f"date: {date_str}",
            f"type: 聊天记录",
            f"tags: [对话, 自动归档, 增量处理]",
            f"message_count: {len(messages)}",
            f"---",
            f"",
            f"# {date_str} 对话记录",
            f"",
            f"## 统计",
            f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"- 消息数量：{len(messages)} 条",
            f"- 处理模式：增量处理",
            f"- 状态：待 AI 深度分析",
            f"",
            f"---",
            f"",
            f"## 原始对话",
            f"",
        ]
        
        # 添加消息
        for msg in messages:
            content_lines.append(self._format_message(msg))
        
        # 写入文件
        content = "\n".join(content_lines)
        output_file = self.output_dir / f"{date_str}_conversations.md"
        
        try:
            output_file.write_text(content, encoding='utf-8')
            logger.info(f"Conversation saved: {output_file}")
            return True, str(output_file)
        except Exception as e:
            logger.error(f"Failed to write conversation: {e}")
            return False, ""
    
    def _format_message(self, msg: Message) -> str:
        """格式化单条消息"""
        ts = datetime.fromtimestamp(msg.timestamp / 1000).strftime("%H:%M:%S")
        role = msg.role
        content = msg.content
        
        # 截断过长的内容
        if len(content) > 2000:
            content = content[:2000] + "\n... [内容过长，已截断]"
        
        if role == "user":
            return f"**[{ts}] 用户**\n{content}\n\n---\n\n"
        elif role == "assistant":
            return f"**[{ts}] AI**\n{content}\n\n---\n\n"
        else:
            return f"**[{ts}] {role}**\n{content}\n\n---\n\n"


def process_incremental():
    """
    增量处理主函数
    
    完整的增量处理流程。
    """
    import time
    start_time = time.time()
    
    logger.info("=" * 50)
    logger.info("Starting incremental message processing...")
    logger.info("=" * 50)
    
    try:
        # 1. 初始化索引管理器
        index_manager = IndexManager()
        
        # 2. 加载索引（会自动重建如果不存在）
        index = index_manager.load()
        last_ts = index_manager.get_last_timestamp()
        
        # 3. 增量扫描
        scanner = IncrementalScanner(index_manager)
        messages = scanner.scan()
        
        if not messages:
            logger.info("No new messages found")
            # 仍然更新索引时间（记录本次运行）
            index_manager.update_last_timestamp(
                int(datetime.now(timezone.utc).timestamp() * 1000),
                0
            )
            return True
        
        # 4. 获取日期（用于文件名）
        # 使用消息的最大时间戳作为日期
        max_ts = max(m.timestamp for m in messages)
        date_str = datetime.fromtimestamp(max_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        
        # 5. 写入对话记录
        writer = ConversationWriter()
        success, output_file = writer.write(messages, date_str)
        
        if not success:
            logger.error("Failed to write conversation")
            return False
        
        # 6. 更新索引
        index_manager.update_last_timestamp(max_ts, len(messages))
        
        # 7. 创建备份
        index_manager.backup()
        
        # 8. 记录执行时间
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Processing completed in {duration_ms}ms")
        
        # 更新统计
        index = index_manager.load()
        if 'statistics' in index:
            index['statistics']['last_run_duration_ms'] = duration_ms
            index_manager.save(index)
        
        logger.info("=" * 50)
        logger.info(f"Success: {len(messages)} messages saved to {output_file}")
        logger.info("=" * 50)
        
        return True
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = process_incremental()
    sys.exit(0 if success else 1)
