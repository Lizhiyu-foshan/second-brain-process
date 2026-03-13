#!/usr/bin/env python3
"""
自动修复工具 - Auto Fix

功能：
1. 读取健康检查报告
2. 自动执行修复建议
3. 生成修复报告

使用方法：
    python3 auto_fix.py [--dry-run] [--notify]

作者：Kimi Claw
创建时间：2026-03-12
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

WORKSPACE = Path("/root/.openclaw/workspace")
LEARNINGS_DIR = WORKSPACE / ".learnings"
FEISHU_USER = "ou_363105a68ee112f714ed44e12c802051"


class AutoFixer:
    """自动修复器"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "fixes": [],
            "failures": [],
            "skipped": []
        }
    
    def load_health_report(self) -> Dict:
        """加载健康检查报告"""
        report_file = LEARNINGS_DIR / "health_check_report.json"
        if not report_file.exists():
            print("❌ 未找到健康检查报告")
            return {}
        
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 读取报告失败: {e}")
            return {}
    
    def fix_session_compact(self) -> Tuple[bool, str]:
        """修复：压缩会话文件"""
        print("\n🔧 执行：压缩会话上下文")
        
        if self.dry_run:
            self.results["fixes"].append({
                "action": "session_compact",
                "status": "dry_run",
                "message": "模拟执行：/compact"
            })
            return True, "[模拟] 执行 /compact"
        
        try:
            # 清理旧会话文件
            result = subprocess.run(
                ["bash", "/root/.openclaw/workspace/second-brain-processor/cleanup_old_sessions.sh"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            self.results["fixes"].append({
                "action": "session_compact",
                "status": "success",
                "output": result.stdout[:200] if result.stdout else "cleaned"
            })
            return True, "已清理旧会话文件"
            
        except Exception as e:
            self.results["failures"].append({
                "action": "session_compact",
                "error": str(e)
            })
            return False, f"修复失败: {e}"
    
    def fix_queue_backlog(self) -> Tuple[bool, str]:
        """修复：清理队列积压"""
        print("\n🔧 执行：清理消息队列")
        
        if self.dry_run:
            self.results["fixes"].append({
                "action": "queue_cleanup",
                "status": "dry_run",
                "message": "模拟执行队列清理"
            })
            return True, "[模拟] 清理队列"
        
        try:
            # 检查队列文件
            queue_file = WORKSPACE / "second-brain-processor" / "article_queue.json"
            if queue_file.exists():
                with open(queue_file, 'r', encoding='utf-8') as f:
                    queue = json.load(f)
                
                pending_count = len(queue.get('pending', []))
                
                if pending_count > 0:
                    # 执行队列处理
                    result = subprocess.run(
                        ["python3", "process_queue.py"],
                        cwd=WORKSPACE / "second-brain-processor",
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    
                    self.results["fixes"].append({
                        "action": "queue_cleanup",
                        "status": "success",
                        "processed": pending_count,
                        "output": result.stdout[:200] if result.stdout else "processed"
                    })
                    return True, f"已处理 {pending_count} 个队列项"
                else:
                    self.results["skipped"].append({
                        "action": "queue_cleanup",
                        "reason": "队列为空"
                    })
                    return True, "队列为空，无需处理"
            else:
                self.results["skipped"].append({
                    "action": "queue_cleanup",
                    "reason": "队列文件不存在"
                })
                return True, "队列文件不存在"
                
        except Exception as e:
            self.results["failures"].append({
                "action": "queue_cleanup",
                "error": str(e)
            })
            return False, f"修复失败: {e}"
    
    def fix_disk_space(self) -> Tuple[bool, str]:
        """修复：清理磁盘空间"""
        print("\n🔧 执行：清理磁盘空间")
        
        if self.dry_run:
            self.results["fixes"].append({
                "action": "disk_cleanup",
                "status": "dry_run",
                "message": "模拟清理磁盘"
            })
            return True, "[模拟] 清理磁盘"
        
        try:
            # 清理临时文件
            subprocess.run(
                ["find", "/tmp", "-name", "*.tmp", "-mtime", "+1", "-delete"],
                capture_output=True,
                timeout=30
            )
            
            # 清理旧日志
            result = subprocess.run(
                ["bash", "/root/.openclaw/workspace/second-brain-processor/cleanup_old_sessions.sh"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            self.results["fixes"].append({
                "action": "disk_cleanup",
                "status": "success"
            })
            return True, "已清理临时文件和旧会话"
            
        except Exception as e:
            self.results["failures"].append({
                "action": "disk_cleanup",
                "error": str(e)
            })
            return False, f"修复失败: {e}"
    
    def run_auto_fix(self) -> Dict:
        """执行自动修复"""
        print("=" * 50)
        print(f"自动修复工具 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 50)
        
        if self.dry_run:
            print("\n📝 模拟模式（不实际执行修复）")
        
        # 加载健康报告
        health_report = self.load_health_report()
        if not health_report:
            return self.results
        
        # 检查问题并执行修复
        issues = health_report.get("issues", [])
        
        if not issues:
            print("\n✅ 没有发现需要修复的问题")
            self.results["overall_status"] = "no_issues"
            return self.results
        
        print(f"\n发现 {len(issues)} 个问题，开始修复...")
        
        for issue in issues:
            component = issue.get("component", "")
            message = issue.get("message", "")
            
            print(f"\n📋 问题: {component} - {message}")
            
            # 根据问题类型执行修复
            if "会话文件" in message and "compact" in message:
                success, msg = self.fix_session_compact()
                print(f"   {'✅' if success else '❌'} {msg}")
                
            elif "队列积压" in message:
                success, msg = self.fix_queue_backlog()
                print(f"   {'✅' if success else '❌'} {msg}")
                
            elif "磁盘空间" in message:
                success, msg = self.fix_disk_space()
                print(f"   {'✅' if success else '❌'} {msg}")
                
            else:
                print(f"   ⏭️  暂不支持自动修复此问题")
                self.results["skipped"].append({
                    "component": component,
                    "message": message,
                    "reason": "unsupported"
                })
        
        # 总结
        print("\n" + "=" * 50)
        print("修复完成")
        print(f"   ✅ 成功: {len(self.results['fixes'])}")
        print(f"   ❌ 失败: {len(self.results['failures'])}")
        print(f"   ⏭️  跳过: {len(self.results['skipped'])}")
        print("=" * 50)
        
        self.results["overall_status"] = "completed"
        return self.results
    
    def save_report(self):
        """保存修复报告"""
        report_file = LEARNINGS_DIR / "auto_fix_report.json"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            print(f"\n💾 修复报告已保存: {report_file}")
        except Exception as e:
            print(f"\n[WARN] 保存报告失败: {e}")
    
    def send_notification(self, force: bool = False):
        """发送通知"""
        if not force and len(self.results['fixes']) == 0:
            print("\n✅ 无需发送通知")
            return
        
        # 构建消息
        if self.dry_run:
            message = "📝 **自动修复报告（模拟模式）**\n\n"
        else:
            message = "🔧 **自动修复报告**\n\n"
        
        message += f"修复时间：{datetime.now().strftime('%H:%M')}\n\n"
        message += f"✅ 成功：{len(self.results['fixes'])}\n"
        message += f"❌ 失败：{len(self.results['failures'])}\n"
        message += f"⏭️ 跳过：{len(self.results['skipped'])}\n"
        
        if self.results['fixes']:
            message += "\n**修复详情：**\n"
            for fix in self.results['fixes']:
                status = "✅" if fix['status'] == 'success' else "📝"
                message += f"\n{status} {fix['action']}\n"
        
        if self.results['failures']:
            message += "\n**失败项：**\n"
            for failure in self.results['failures']:
                message += f"\n❌ {failure['action']}: {failure['error'][:50]}\n"
        
        # 发送
        try:
            sys.path.insert(0, str(WORKSPACE / "second-brain-processor"))
            from feishu_guardian import send_feishu_safe
            
            result = send_feishu_safe(
                message,
                target=FEISHU_USER,
                msg_type="auto_fix",
                max_retries=1
            )
            
            if result["success"]:
                print("\n✅ 通知已发送")
            else:
                print(f"\n⚠️ 通知发送失败: {result['message']}")
        except Exception as e:
            print(f"\n⚠️ 通知发送异常: {e}")


def main():
    parser = argparse.ArgumentParser(description='自动修复工具')
    parser.add_argument('--dry-run', action='store_true',
                       help='模拟模式（不实际执行）')
    parser.add_argument('--notify', action='store_true',
                       help='强制发送通知')
    
    args = parser.parse_args()
    
    fixer = AutoFixer(dry_run=args.dry_run)
    fixer.run_auto_fix()
    fixer.save_report()
    fixer.send_notification(force=args.notify)


if __name__ == "__main__":
    main()
