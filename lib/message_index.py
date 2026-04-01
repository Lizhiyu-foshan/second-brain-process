#!/usr/bin/env python3
"""
Message Index Manager - 消息索引管理器

职责:
- 读取/写入索引文件
- 备份和恢复
- 完整性验证
- 自动重建

约束覆盖:
- R1: 索引损坏时自动重建
- R2: 支持异常恢复
- R3: 双重验证（校验和）
- R4: 保留7天备份

作者: Kimi Claw
创建时间: 2026-03-21
"""

import json
import hashlib
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class IndexManager:
    """
    索引管理器
    
    管理消息处理索引，确保数据完整性和系统可靠性。
    """
    
    def __init__(self, index_path: str = None):
        """
        初始化索引管理器
        
        Args:
            index_path: 索引文件路径，默认 .data/message_index.json
        """
        if index_path is None:
            # 默认路径
            workspace = Path("/root/.openclaw/workspace")
            self.index_path = workspace / ".data" / "message_index.json"
        else:
            self.index_path = Path(index_path)
        
        # 备份目录
        self.backup_dir = self.index_path.parent / "index_backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 确保数据目录存在
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"IndexManager initialized: {self.index_path}")
    
    def load(self) -> Dict:
        """
        加载索引文件
        
        如果索引文件不存在或损坏，自动触发重建。
        
        Returns:
            索引数据字典
        """
        # 检查索引文件是否存在
        if not self.index_path.exists():
            logger.info("Index file not found, triggering rebuild")
            return self.rebuild()
        
        try:
            # 读取索引文件
            with open(self.index_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证索引完整性
            if not self.validate(data):
                logger.warning("Index validation failed, triggering rebuild")
                return self.rebuild()
            
            logger.info(f"Index loaded successfully: last_processed={data.get('last_processed', {}).get('date_str', 'N/A')}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Index file corrupted (JSON error): {e}")
            return self.rebuild()
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return self.rebuild()
    
    def save(self, index: Dict) -> bool:
        """
        保存索引文件
        
        自动备份旧索引，计算校验和。
        
        Args:
            index: 索引数据字典
            
        Returns:
            是否保存成功
        """
        try:
            # 先备份现有索引
            if self.index_path.exists():
                self._backup_current()
            
            # 添加元数据
            index['_meta'] = {
                'saved_at': datetime.now(timezone.utc).isoformat(),
                'version': '1.0'
            }
            
            # 计算校验和
            index['checksum'] = self._calculate_checksum(index)
            
            # 原子写入（先写临时文件，再重命名）
            temp_path = self.index_path.with_suffix('.tmp')
            
            # 先序列化为字符串（不含校验和）
            index_copy = {k: v for k, v in index.items() if k != 'checksum'}
            json_str = json.dumps(index_copy, sort_keys=True, indent=2, ensure_ascii=False)
            
            # 计算校验和
            index['checksum'] = hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]
            
            # 重新序列化完整数据（带校验和）
            final_json_str = json.dumps(index, sort_keys=True, indent=2, ensure_ascii=False)
            
            # 写入文件
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(final_json_str)
            
            # 重命名（原子操作）
            temp_path.rename(self.index_path)
            
            logger.info(f"Index saved successfully: {self.index_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            return False
    
    def validate(self, index: Dict) -> bool:
        """
        验证索引完整性
        
        检查必需字段和校验和。
        
        Args:
            index: 索引数据字典
            
        Returns:
            是否通过验证
        """
        # 检查必需字段
        required_fields = ['last_processed', 'statistics']
        for field in required_fields:
            if field not in index:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # 检查 last_processed 字段
        last_processed = index.get('last_processed', {})
        if 'timestamp_ms' not in last_processed:
            logger.warning("Missing last_processed.timestamp_ms")
            return False
        
        # 验证校验和（如果存在）
        if 'checksum' in index:
            stored_checksum = index['checksum']
            # 创建副本并序列化（与save使用相同的序列化逻辑）
            index_copy = {k: v for k, v in index.items() if k != 'checksum'}
            json_str = json.dumps(index_copy, sort_keys=True, indent=2, ensure_ascii=False)
            calculated_checksum = hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]
            
            if stored_checksum != calculated_checksum:
                logger.warning(f"Checksum mismatch: stored={stored_checksum}, calculated={calculated_checksum}")
                return False
        
        logger.debug("Index validation passed")
        return True
    
    def rebuild(self) -> Dict:
        """
        全量重建索引
        
        扫描所有会话文件，建立完整索引。
        用于首次运行或索引损坏时。
        
        Returns:
            重建后的索引数据
        """
        logger.info("Starting full index rebuild...")
        
        try:
            # 扫描所有会话文件
            sessions_dir = Path("/root/.openclaw/agents/main/sessions/")
            
            max_timestamp = 0
            total_messages = 0
            total_files = 0
            
            for jsonl_file in sessions_dir.glob("*.jsonl"):
                if "deleted" in jsonl_file.name:
                    continue
                
                total_files += 1
                
                # 扫描文件中的消息
                try:
                    with open(jsonl_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                msg = json.loads(line.strip())
                                if msg.get("type") != "message":
                                    continue
                                
                                ts_str = msg.get("timestamp", "")
                                if ts_str:
                                    dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                    msg_ts = int(dt.timestamp() * 1000)
                                    max_timestamp = max(max_timestamp, msg_ts)
                                    total_messages += 1
                            except:
                                continue
                except Exception as e:
                    logger.warning(f"Error scanning {jsonl_file}: {e}")
            
            # 创建新索引
            new_index = {
                "version": "1.0",
                "last_processed": {
                    "timestamp_ms": max_timestamp,
                    "iso_time": datetime.fromtimestamp(max_timestamp / 1000, tz=timezone.utc).isoformat(),
                    "date_str": datetime.fromtimestamp(max_timestamp / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                },
                "statistics": {
                    "total_messages_processed": total_messages,
                    "total_files_scanned": total_files,
                    "total_files_with_new_messages": total_files,
                    "last_run_duration_ms": 0,
                    "last_run_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "rebuilt_at": datetime.now(timezone.utc).isoformat()
                },
                "daily_history": []
            }
            
            # 保存新索引
            self.save(new_index)
            
            logger.info(f"Index rebuilt successfully: max_timestamp={max_timestamp}, total_messages={total_messages}")
            return new_index
            
        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")
            # 返回空索引
            return {
                "version": "1.0",
                "last_processed": {
                    "timestamp_ms": 0,
                    "iso_time": datetime.now(timezone.utc).isoformat(),
                    "date_str": datetime.now(timezone.utc).strftime("%Y-%m-%d")
                },
                "statistics": {
                    "total_messages_processed": 0,
                    "total_files_scanned": 0,
                    "total_files_with_new_messages": 0,
                    "last_run_duration_ms": 0,
                    "last_run_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
                }
            }
    
    def backup(self, days: int = 7):
        """
        备份当前索引
        
        保留最近N天的备份。
        
        Args:
            days: 保留天数，默认7天
        """
        try:
            if not self.index_path.exists():
                return
            
            # 创建备份文件名（带时间戳）
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            backup_file = self.backup_dir / f"message_index_{timestamp}.json"
            
            # 复制文件
            shutil.copy2(self.index_path, backup_file)
            
            # 清理旧备份
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            for old_backup in self.backup_dir.glob("message_index_*.json"):
                try:
                    mtime = datetime.fromtimestamp(old_backup.stat().st_mtime, tz=timezone.utc)
                    if mtime < cutoff:
                        old_backup.unlink()
                        logger.debug(f"Removed old backup: {old_backup}")
                except:
                    pass
            
            logger.info(f"Index backup created: {backup_file}")
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
    
    def _backup_current(self):
        """备份当前索引（内部方法）"""
        try:
            if self.index_path.exists():
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                backup_file = self.backup_dir / f"message_index_{timestamp}.json"
                shutil.copy2(self.index_path, backup_file)
        except Exception as e:
            logger.warning(f"Failed to backup current index: {e}")
    
    def _calculate_checksum(self, data: Dict) -> str:
        """
        计算索引校验和
        
        使用SHA256计算数据哈希。
        
        Args:
            data: 索引数据（不含checksum字段）
            
        Returns:
            校验和字符串
        """
        # 序列化为JSON字符串（使用与save相同的格式）
        json_str = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False, separators=(', ', ': '))
        
        # 计算SHA256
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]
    
    def get_last_timestamp(self) -> int:
        """
        获取上次处理的最后时间戳
        
        Returns:
            时间戳（毫秒）
        """
        index = self.load()
        return index.get('last_processed', {}).get('timestamp_ms', 0)
    
    def update_last_timestamp(self, timestamp_ms: int, message_count: int = 0):
        """
        更新最后处理时间戳
        
        Args:
            timestamp_ms: 新的时间戳（毫秒）
            message_count: 本次处理的消息数量
        """
        index = self.load()
        
        # 更新最后处理时间
        index['last_processed'] = {
            "timestamp_ms": timestamp_ms,
            "iso_time": datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat(),
            "date_str": datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        }
        
        # 更新统计
        if 'statistics' not in index:
            index['statistics'] = {}
        
        index['statistics']['total_messages_processed'] = \
            index['statistics'].get('total_messages_processed', 0) + message_count
        index['statistics']['last_run_date'] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        index['statistics']['last_run_duration_ms'] = 0  # 由调用方更新
        
        # 添加历史记录
        if 'daily_history' not in index:
            index['daily_history'] = []
        
        # 保存
        self.save(index)


if __name__ == "__main__":
    # 测试代码
    print("Testing IndexManager...")
    
    manager = IndexManager()
    
    # 测试加载（会触发重建如果索引不存在）
    index = manager.load()
    print(f"Loaded index: {json.dumps(index, indent=2, ensure_ascii=False)}")
    
    # 测试更新
    manager.update_last_timestamp(1774093355299, 100)
    print("Index updated")
    
    # 测试备份
    manager.backup()
    print("Backup created")
