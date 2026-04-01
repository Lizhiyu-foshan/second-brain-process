#!/usr/bin/env python3
"""
Robust Incremental Processor - 鲁棒增量处理器 v2.0

设计原则:
1. 不依赖清理任务 - 自带时间窗口限制
2. 失败时降级 - 全量模式 vs 快速模式
3. 资源上限保护 - 文件数/大小限制
"""
import json
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional
import logging

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from message_index import IndexManager

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
CONVERSATIONS_DIR = VAULT_DIR / "02-Conversations"
SESSIONS_DIR = Path("/root/.openclaw/agents/main/sessions/")

# 保护阈值
MAX_FILES_TO_SCAN = 100  # 最多扫描100个文件
MAX_FILE_SIZE_MB = 10    # 单文件最大10MB
FAST_MODE_DAYS = 2       # 快速模式：只处理最近2天


class RobustScanner:
    """鲁棒扫描器 - 带有多重保护机制"""
    
    def __init__(self, index_manager: IndexManager, fast_mode: bool = False):
        self.index_manager = index_manager
        self.fast_mode = fast_mode
        self.stats = {
            "files_scanned": 0,
            "files_skipped": 0,
            "messages_found": 0,
            "mode": "fast" if fast_mode else "full"
        }
    
    def get_files_to_scan(self) -> List[Path]:
        """
        智能选择要扫描的文件
        
        策略:
        1. 快速模式: 只扫描最近N天的文件
        2. 全量模式: 扫描全部，但限制数量
        3. 总是优先扫描最新的文件
        """
        all_files = []
        cutoff_time = datetime.now() - timedelta(days=FAST_MODE_DAYS)
        
        for jsonl_file in SESSIONS_DIR.glob("*.jsonl"):
            try:
                stat = jsonl_file.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                size_mb = stat.st_size / (1024 * 1024)
                
                # 跳过超大文件（防止卡住）
                if size_mb > MAX_FILE_SIZE_MB:
                    logger.warning(f"跳过超大文件: {jsonl_file.name} ({size_mb:.1f}MB)")
                    self.stats["files_skipped"] += 1
                    continue
                
                all_files.append({
                    'path': jsonl_file,
                    'mtime': mtime,
                    'size': size_mb
                })
            except Exception as e:
                logger.warning(f"无法获取文件信息 {jsonl_file}: {e}")
                continue
        
        # 按修改时间排序（最新的优先）
        all_files.sort(key=lambda x: x['mtime'], reverse=True)
        
        if self.fast_mode:
            # 快速模式：只取最近N天的
            recent_files = [
                f['path'] for f in all_files 
                if f['mtime'] > cutoff_time
            ]
            logger.info(f"快速模式: 从 {len(all_files)} 个文件筛选出 {len(recent_files)} 个最近文件")
            return recent_files[:MAX_FILES_TO_SCAN]
        else:
            # 全量模式：限制数量
            logger.info(f"全量模式: 扫描最新的 {min(len(all_files), MAX_FILES_TO_SCAN)} 个文件")
            return [f['path'] for f in all_files[:MAX_FILES_TO_SCAN]]
    
    def scan(self) -> List[Dict]:
        """执行扫描"""
        files_to_scan = self.get_files_to_scan()
        last_ts = self.index_manager.get_last_timestamp()
        
        messages = []
        
        for jsonl_file in files_to_scan:
            try:
                new_messages = self._scan_file(jsonl_file, last_ts)
                messages.extend(new_messages)
                self.stats["files_scanned"] += 1
                
                # 资源保护：消息数过多时停止
                if len(messages) > 10000:
                    logger.warning(f"消息数超过10000，停止扫描")
                    break
                    
            except Exception as e:
                logger.error(f"扫描文件失败 {jsonl_file}: {e}")
                continue
        
        self.stats["messages_found"] = len(messages)
        logger.info(f"扫描完成: {self.stats}")
        return messages
    
    def _scan_file(self, jsonl_file: Path, last_ts: int) -> List[Dict]:
        """扫描单个文件"""
        messages = []
        
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    msg = json.loads(line)
                    
                    # 只处理 type=message 的记录
                    if msg.get('type') != 'message':
                        continue
                    
                    # 使用统一的 timestamp 解析
                    timestamp = parse_timestamp(msg.get('timestamp'))
                    
                    # 只取新增消息
                    if timestamp > last_ts:
                        # 正确解析嵌套的消息结构
                        msg_data = msg.get('message', {})
                        role = msg_data.get('role', 'unknown')
                        
                        # 解析 content 数组
                        content_parts = msg_data.get('content', [])
                        if isinstance(content_parts, list) and len(content_parts) > 0:
                            content_text = content_parts[0].get('text', '')
                        else:
                            content_text = str(content_parts)
                        
                        messages.append({
                            'timestamp': timestamp,
                            'role': role,
                            'content': content_text,
                            'source_file': jsonl_file.name
                        })
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.warning(f"解析消息失败 {jsonl_file}:{line_num}: {e}")
                    continue
        
        return messages


def parse_timestamp(ts) -> int:
    """
    统一解析 timestamp 为毫秒时间戳整数
    
    支持格式:
    - 整数/浮点数时间戳 (毫秒或秒)
    - ISO 8601 字符串 (如 "2026-03-29T20:26:18.911Z")
    """
    if ts is None:
        return 0
    
    # 已经是数字
    if isinstance(ts, (int, float)):
        # 判断是秒还是毫秒 (毫秒时间戳通常大于 1e10)
        if ts < 1e10:
            return int(ts * 1000)
        return int(ts)
    
    # 字符串格式 - 尝试 ISO 8601
    if isinstance(ts, str):
        try:
            # 处理带 Z 的 UTC 格式
            ts = ts.replace('Z', '+00:00')
            dt = datetime.fromisoformat(ts)
            # 转换为毫秒时间戳
            return int(dt.timestamp() * 1000)
        except (ValueError, AttributeError):
            # 尝试直接解析为数字
            try:
                num = float(ts)
                if num < 1e10:
                    return int(num * 1000)
                return int(num)
            except ValueError:
                return 0
    
    return 0


def format_timestamp(ms: int) -> str:
    """将毫秒时间戳格式化为可读字符串"""
    try:
        return datetime.fromtimestamp(ms / 1000).strftime('%H:%M')
    except:
        return "--:--"


def process_robust(force_full: bool = False) -> bool:
    """
    鲁棒处理流程
    
    Args:
        force_full: 强制全量模式（默认自动选择）
    
    Returns:
        bool: 是否成功
    """
    index_manager = IndexManager()
    
    # 智能模式选择
    total_files = len(list(SESSIONS_DIR.glob("*.jsonl")))
    fast_mode = not force_full and total_files > 200
    
    if fast_mode:
        logger.info(f"文件数({total_files})超过阈值，启用快速模式")
    
    # 执行扫描
    scanner = RobustScanner(index_manager, fast_mode=fast_mode)
    messages = scanner.scan()
    
    if not messages:
        logger.info("没有新消息需要处理")
        return True
    
    # 去重和排序
    seen_hashes = set()
    unique_messages = []
    
    for msg in sorted(messages, key=lambda x: x['timestamp']):
        content_hash = hashlib.md5(
            f"{msg['timestamp']}_{msg['content'][:100]}".encode()
        ).hexdigest()
        
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            unique_messages.append(msg)
    
    logger.info(f"去重后: {len(unique_messages)} 条消息")
    
    # 生成对话文件（简化版 - 实际应该按天分组）
    if unique_messages:
        today = datetime.now().strftime("%Y-%m-%d")
        output_file = CONVERSATIONS_DIR / f"auto_{today}.md"
        
        CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'a', encoding='utf-8') as f:
            for msg in unique_messages[:100]:  # 限制单次写入数量
                ts_str = format_timestamp(msg['timestamp'])
                f.write(f"\n## {ts_str} - {msg['role']}\n\n")
                f.write(f"{msg['content'][:500]}...\n")  # 截断长内容
        
        # 更新索引
        max_ts = max(m['timestamp'] for m in unique_messages)
        index_manager.update_last_timestamp(max_ts)
        
        logger.info(f"✅ 已写入 {len(unique_messages)} 条消息到 {output_file}")
    
    return True


if __name__ == "__main__":
    force_full = "--full" in sys.argv
    try:
        success = process_robust(force_full=force_full)
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"处理失败: {e}")
        sys.exit(1)
