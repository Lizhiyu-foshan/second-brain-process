#!/usr/bin/env python3
"""
自动会话压缩工具 - Auto Compact

功能：
1. 监控会话文件大小
2. 超过阈值时自动压缩
3. 支持定时检查和即时压缩

使用方法：
    python3 auto_compact.py [--check] [--force]

作者：Kimi Claw
创建时间：2026-03-12
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple, Optional

# 路径配置
SESSIONS_DIR = Path("/root/.openclaw/agents/main/sessions")
LEARNINGS_DIR = Path("/root/.openclaw/workspace/.learnings")
FEISHU_USER = "ou_363105a68ee112f714ed44e12c802051"

# 阈值配置（MB）
WARNING_THRESHOLD = 10    # 警告阈值
COMPACT_THRESHOLD = 20    # 自动压缩阈值
CRITICAL_THRESHOLD = 50   # 紧急阈值

# 状态文件
COMPACT_STATE_FILE = LEARNINGS_DIR / "auto_compact_state.json"


class AutoCompactor:
    """自动压缩器"""
    
    def __init__(self):
        self.state = self._load_state()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "action_taken": False,
            "message": ""
        }
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if COMPACT_STATE_FILE.exists():
            try:
                with open(COMPACT_STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "last_check": None,
            "last_compact": None,
            "compact_count": 0
        }
    
    def _save_state(self):
        """保存状态"""
        try:
            LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
            with open(COMPACT_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] 保存状态失败: {e}")
    
    def get_session_stats(self) -> Tuple[int, float, Path]:
        """
        获取会话文件统计
        
        Returns: (count, max_size_mb, largest_file)
        """
        if not SESSIONS_DIR.exists():
            return 0, 0.0, None
        
        session_files = list(SESSIONS_DIR.glob("*.jsonl"))
        if not session_files:
            return 0, 0.0, None
        
        # 获取最大文件
        largest_file = max(session_files, key=lambda f: f.stat().st_size)
        max_size = largest_file.stat().st_size
        max_size_mb = max_size / (1024 * 1024)
        
        return len(session_files), max_size_mb, largest_file
    
    def should_compact(self) -> Tuple[bool, str]:
        """
        判断是否需要压缩
        
        Returns: (should_compact, reason)
        """
        count, max_size_mb, largest_file = self.get_session_stats()
        
        if count == 0:
            return False, "无会话文件"
        
        # 检查上次压缩时间（避免频繁压缩）
        if self.state.get("last_compact"):
            last_compact = datetime.fromisoformat(self.state["last_compact"])
            if datetime.now() - last_compact < timedelta(hours=1):
                return False, f"上次压缩在 {(datetime.now() - last_compact).total_seconds() // 60} 分钟前，跳过"
        
        # 根据大小判断
        if max_size_mb >= CRITICAL_THRESHOLD:
            return True, f"会话文件严重过大 ({max_size_mb:.1f}MB > {CRITICAL_THRESHOLD}MB)"
        elif max_size_mb >= COMPACT_THRESHOLD:
            return True, f"会话文件过大 ({max_size_mb:.1f}MB > {COMPACT_THRESHOLD}MB)"
        elif max_size_mb >= WARNING_THRESHOLD:
            return False, f"会话文件偏大 ({max_size_mb:.1f}MB)，但未达自动压缩阈值"
        else:
            return False, f"会话文件正常 ({max_size_mb:.1f}MB)"
    
    def compact_session(self, dry_run: bool = False) -> Tuple[bool, str]:
        """
        执行会话压缩
        
        策略：
        1. 删除已完成对话的旧会话文件（非当前活跃会话）
        2. 保留最近24小时的会话
        3. 压缩当前会话（如果可能）
        
        Returns: (success, message)
        """
        count, max_size_mb, largest_file = self.get_session_stats()
        
        if dry_run:
            return True, f"[模拟] 将清理 {count} 个会话文件中的旧文件"
        
        try:
            # 获取当前活跃会话ID（从sessions.json）
            sessions_json = SESSIONS_DIR / "sessions.json"
            active_sessions = set()
            
            if sessions_json.exists():
                try:
                    with open(sessions_json, 'r', encoding='utf-8') as f:
                        sessions_data = json.load(f)
                    # 获取所有活跃会话ID
                    for key in sessions_data.keys():
                        if key.startswith("agent:"):
                            session_id = key.split(":")[-1]
                            active_sessions.add(session_id)
                except Exception:
                    pass
            
            # 清理策略：
            # 1. 保留活跃会话
            # 2. 删除超过24小时的非活跃会话
            # 3. 保留最大的文件（当前活跃会话）
            
            deleted_count = 0
            freed_bytes = 0
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for session_file in SESSIONS_DIR.glob("*.jsonl"):
                # 跳过活跃会话
                session_id = session_file.stem
                if session_id in active_sessions:
                    continue
                
                # 跳过最大的文件（可能是当前活跃会话）
                if session_file == largest_file:
                    continue
                
                # 检查文件修改时间
                try:
                    mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
                    if mtime < cutoff_time:
                        # 删除旧会话文件
                        file_size = session_file.stat().st_size
                        session_file.unlink()
                        deleted_count += 1
                        freed_bytes += file_size
                except Exception:
                    continue
            
            # 更新状态
            self.state["last_compact"] = datetime.now().isoformat()
            self.state["compact_count"] = self.state.get("compact_count", 0) + 1
            self._save_state()
            
            freed_mb = freed_bytes / (1024 * 1024)
            return True, f"已清理 {deleted_count} 个旧会话文件，释放 {freed_mb:.1f}MB"
            
        except Exception as e:
            return False, f"压缩失败: {e}"
    
    def run_check(self, force: bool = False, dry_run: bool = False) -> Dict:
        """运行检查和处理"""
        print("=" * 50)
        print(f"自动会话压缩 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 50)
        
        if dry_run:
            print("\n📝 模拟模式\n")
        
        # 获取统计
        count, max_size_mb, largest_file = self.get_session_stats()
        print(f"📊 当前状态:")
        print(f"   会话文件数: {count}")
        print(f"   最大文件: {max_size_mb:.1f}MB")
        print(f"   压缩阈值: {COMPACT_THRESHOLD}MB")
        
        # 判断是否需要压缩
        should_compact_result, reason = self.should_compact()
        print(f"\n🔍 检查: {reason}")
        
        # 执行压缩
        if should_compact_result or force:
            print(f"\n🔧 执行压缩...")
            success, message = self.compact_session(dry_run=dry_run)
            
            self.results["action_taken"] = success
            self.results["message"] = message
            
            status = "✅" if success else "❌"
            print(f"   {status} {message}")
        else:
            print(f"\n⏭️  跳过压缩")
            self.results["action_taken"] = False
            self.results["message"] = reason
        
        # 保存结果
        self._save_results()
        
        print("\n" + "=" * 50)
        print("检查完成")
        print("=" * 50)
        
        return self.results
    
    def _save_results(self):
        """保存结果"""
        result_file = LEARNINGS_DIR / "auto_compact_result.json"
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] 保存结果失败: {e}")
    
    def send_notification(self, force: bool = False):
        """发送通知"""
        # 只有实际执行了压缩才通知
        if not self.results["action_taken"] and not force:
            print("\n⏭️  未执行压缩，不发送通知")
            return
        
        message = f"""🗜️ **自动会话压缩报告**

时间：{datetime.now().strftime('%H:%M')}

**操作结果：**
{self.results["message"]}

**当前状态：**
• 阈值：{COMPACT_THRESHOLD}MB
• 策略：超过阈值自动压缩，保留最近24小时

**提示：**
压缩是自动执行的，无需手动干预。
"""
        
        try:
            sys.path.insert(0, str(Path("/root/.openclaw/workspace/second-brain-processor")))
            from feishu_guardian import send_feishu_safe
            
            result = send_feishu_safe(
                message,
                target=FEISHU_USER,
                msg_type="auto_compact",
                max_retries=1
            )
            
            if result["success"]:
                print("\n✅ 通知已发送")
            else:
                print(f"\n⚠️ 通知发送失败: {result['message']}")
        except Exception as e:
            print(f"\n⚠️ 通知发送异常: {e}")


def main():
    parser = argparse.ArgumentParser(description='自动会话压缩')
    parser.add_argument('--check', action='store_true',
                       help='检查是否需要压缩')
    parser.add_argument('--force', action='store_true',
                       help='强制压缩（忽略阈值）')
    parser.add_argument('--dry-run', action='store_true',
                       help='模拟模式')
    parser.add_argument('--notify', action='store_true',
                       help='发送通知')
    parser.add_argument('--silent', action='store_true',
                       help='静默模式')
    
    args = parser.parse_args()
    
    if args.silent:
        sys.stdout = open('/dev/null', 'w')
    
    compactor = AutoCompactor()
    
    # 仅检查模式
    if args.check:
        should_compact, reason = compactor.should_compact()
        print(f"需要压缩: {should_compact}")
        print(f"原因: {reason}")
        sys.exit(0 if should_compact else 0)
    
    # 运行检查和处理
    results = compactor.run_check(force=args.force, dry_run=args.dry_run)
    
    # 发送通知
    compactor.send_notification(force=args.notify)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
