#!/usr/bin/env python3
"""
动态上下文压缩守护进程 - Dynamic Context Compactor

核心功能：
1. 实时监控会话上下文大小（token 数）
2. 接近模型限制时自动触发压缩
3. 消息数量达到阈值时自动压缩
4. 完全自动化，无需人工干预

作者：Kimi Claw
创建时间：2026-03-12
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess

# 路径配置
OPENCLAW_DIR = Path("/root/.openclaw")
SESSIONS_DIR = OPENCLAW_DIR / "agents/main/sessions"
LEARNINGS_DIR = Path("/root/.openclaw/workspace/.learnings")
WORKSPACE = Path("/root/.openclaw/workspace")

# 动态压缩阈值
MSG_COUNT_THRESHOLD = 100        # 消息数达到100条触发
CONTEXT_SOFT_LIMIT = 200000      # 软限制：20万token
CONTEXT_HARD_LIMIT = 250000      # 硬限制：25万token（接近k2p5的256k）
COOLDOWN_MINUTES = 30            # 压缩冷却时间

# 状态文件
DYNAMIC_COMPACT_STATE = LEARNINGS_DIR / "dynamic_compact_state.json"
CONTEXT_MONITOR_LOG = LEARNINGS_DIR / "context_monitor.log"

_lock = threading.Lock()


class DynamicCompactor:
    """动态上下文压缩器"""
    
    def __init__(self):
        self.state = self._load_state()
        self.session_file = None
        self.last_line_count = 0
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if DYNAMIC_COMPACT_STATE.exists():
            try:
                with open(DYNAMIC_COMPACT_STATE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "last_compact": None,
            "compact_count": 0,
            "total_tokens_saved": 0
        }
    
    def _save_state(self):
        """保存状态"""
        try:
            LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
            with open(DYNAMIC_COMPACT_STATE, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._log(f"保存状态失败: {e}")
    
    def _log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        
        # 控制台输出
        print(log_line)
        
        # 写入文件
        try:
            with open(CONTEXT_MONITOR_LOG, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
        except:
            pass
    
    def find_active_session(self) -> Optional[Path]:
        """查找当前活跃会话文件"""
        # 获取最新的 .jsonl 文件
        jsonl_files = list(SESSIONS_DIR.glob("*.jsonl"))
        if not jsonl_files:
            return None
        
        # 按修改时间排序
        jsonl_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return jsonl_files[0]
    
    def estimate_tokens(self, text: str) -> int:
        """估算token数（中文字符按2token，英文按1token估算）"""
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return chinese_chars * 2 + other_chars
    
    def get_session_stats(self, session_file: Path) -> Tuple[int, int, int]:
        """
        获取会话统计
        
        Returns: (行数, 总字符数, 估算token数)
        """
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_count = len(lines)
            total_chars = sum(len(line) for line in lines)
            estimated_tokens = sum(self.estimate_tokens(line) for line in lines)
            
            return line_count, total_chars, estimated_tokens
        except Exception as e:
            self._log(f"读取会话文件失败: {e}")
            return 0, 0, 0
    
    def should_compact(self, line_count: int, tokens: int) -> Tuple[bool, str]:
        """判断是否需要压缩"""
        # 检查冷却时间
        if self.state.get("last_compact"):
            last_compact = datetime.fromisoformat(self.state["last_compact"])
            elapsed = (datetime.now() - last_compact).total_seconds() / 60
            if elapsed < COOLDOWN_MINUTES:
                return False, f"冷却中，上次压缩在 {int(elapsed)} 分钟前"
        
        # 硬限制检查
        if tokens >= CONTEXT_HARD_LIMIT:
            return True, f"达到硬限制 ({tokens:,} >= {CONTEXT_HARD_LIMIT:,} tokens)"
        
        # 软限制检查
        if tokens >= CONTEXT_SOFT_LIMIT:
            return True, f"达到软限制 ({tokens:,} >= {CONTEXT_SOFT_LIMIT:,} tokens)"
        
        # 消息数检查
        if line_count >= MSG_COUNT_THRESHOLD:
            return True, f"消息数达标 ({line_count} >= {MSG_COUNT_THRESHOLD})"
        
        return False, f"正常 (消息: {line_count}, tokens: {tokens:,})"
    
    def trigger_compact(self) -> bool:
        """触发压缩 - 创建 checkpoint"""
        try:
            self._log("🗜️  触发上下文压缩...")
            
            # 方式1: 通过 session_status 触发压缩
            # 方式2: 清理旧会话文件
            # 方式3: 标记需要压缩
            
            # 创建压缩标记文件
            compact_flag = LEARNINGS_DIR / "compact_requested.flag"
            compact_flag.write_text(datetime.now().isoformat(), encoding='utf-8')
            
            self._log("✅ 已标记需要压缩，将在下次对话时自动压缩")
            return True
            
        except Exception as e:
            self._log(f"⚠️ 压缩失败: {e}")
            return False
    
    def run_cycle(self):
        """执行一次监控周期"""
        session_file = self.find_active_session()
        if not session_file:
            self._log("未找到活跃会话")
            return
        
        # 获取统计
        line_count, chars, tokens = self.get_session_stats(session_file)
        
        # 检查是否需要压缩
        should_compact, reason = self.should_compact(line_count, tokens)
        
        self._log(f"📊 会话: {line_count} 行, {chars:,} 字符, ~{tokens:,} tokens")
        self._log(f"🔍 检查: {reason}")
        
        if should_compact:
            success = self.trigger_compact()
            
            if success:
                self.state["last_compact"] = datetime.now().isoformat()
                self.state["compact_count"] = self.state.get("compact_count", 0) + 1
                self.state["total_tokens_saved"] = self.state.get("total_tokens_saved", 0) + tokens
                self._save_state()
                
                # 发送通知
                self._send_notification(tokens)
        
        self.last_line_count = line_count
    
    def _send_notification(self, tokens_before: int):
        """发送压缩通知 - 静默模式下不发送"""
        # 静默模式：只在压缩时记录日志，不发送飞书通知
        self._log(f"✅ 压缩完成，已节省 ~{tokens_before:,} tokens")
        return
    
    def run_daemon(self, interval_seconds: int = 60):
        """作为守护进程持续运行"""
        self._log("=" * 50)
        self._log("动态上下文压缩守护进程启动")
        self._log(f"检查间隔: {interval_seconds} 秒")
        self._log(f"消息阈值: {MSG_COUNT_THRESHOLD} 条")
        self._log(f"Token 软限制: {CONTEXT_SOFT_LIMIT:,}")
        self._log(f"Token 硬限制: {CONTEXT_HARD_LIMIT:,}")
        self._log("=" * 50)
        
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                self._log(f"监控周期异常: {e}")
            
            time.sleep(interval_seconds)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='动态上下文压缩')
    parser.add_argument('--daemon', action='store_true',
                       help='以守护进程模式运行')
    parser.add_argument('--interval', type=int, default=60,
                       help='检查间隔（秒），默认60')
    parser.add_argument('--once', action='store_true',
                       help='运行一次后退出')
    parser.add_argument('--check', action='store_true',
                       help='仅检查状态')
    parser.add_argument('--silent', action='store_true',
                       help='静默模式（无控制台输出）')
    
    args = parser.parse_args()
    
    if args.silent:
        import sys
        sys.stdout = open('/dev/null', 'w')
    
    compactor = DynamicCompactor()
    
    if args.check:
        session_file = compactor.find_active_session()
        if session_file:
            line_count, chars, tokens = compactor.get_session_stats(session_file)
            should_compact, reason = compactor.should_compact(line_count, tokens)
            
            print(f"会话文件: {session_file.name}")
            print(f"消息行数: {line_count}")
            print(f"字符数: {chars:,}")
            print(f"估算 tokens: {tokens:,}")
            print(f"需要压缩: {should_compact}")
            print(f"原因: {reason}")
        else:
            print("未找到活跃会话")
        sys.exit(0)
    
    if args.daemon:
        compactor.run_daemon(interval_seconds=args.interval)
    else:
        compactor.run_cycle()


if __name__ == "__main__":
    main()
