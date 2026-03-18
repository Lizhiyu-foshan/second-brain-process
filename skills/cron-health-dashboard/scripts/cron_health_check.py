#!/usr/bin/env python3
"""
Cron 健康监控器 - Cron Health Dashboard

功能：
1. 监控 OpenClaw cron 任务状态
2. 监控 Linux cron 任务
3. 检测"僵尸任务"（显示成功但无实际输出/文件未更新）
4. 异常告警和自动修复建议
5. 定期报告生成

使用方法：
    python3 cron_health_check.py [--verbose] [--notify] [--silent]

作者：Kimi Claw
创建时间：2026-03-15
项目ID: PROJ_20260315_165705_9460
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 路径配置
WORKSPACE = Path("/root/.openclaw/workspace")
LEARNINGS_DIR = WORKSPACE / ".learnings"
FEISHU_USER = "ou_363105a68ee112f714ed44e12c802051"

# 告警阈值
IDLE_TIMEOUT_MULTIPLIER = 2.0  # 超过预期间隔2倍视为异常
ERROR_STATUS_THRESHOLD = 1  # 只要有 error 状态就告警


class CronHealthChecker:
    """Cron 健康检查器"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "openclaw": {
                "total": 0,
                "healthy": 0,
                "warning": 0,
                "critical": 0,
                "tasks": []
            },
            "linux": {
                "total": 0,
                "healthy": 0,
                "tasks": []
            },
            "issues": [],
            "recommendations": []
        }
    
    def parse_openclaw_cron_list(self, output: str) -> List[Dict]:
        """解析 openclaw cron list 的输出"""
        tasks = []
        lines = output.strip().split('\n')
        
        for line in lines[1:]:  # 跳过标题
            line = line.strip()
            if not line or len(line) < 50:
                continue
            
            parts = line.split()
            if len(parts) < 8:
                continue
            
            # 从后往前找固定列
            agent = parts[-1]
            target = parts[-2]
            status = parts[-3]
            
            # 处理 last 列 (可能是 "-" 或 "13h ago")
            last_idx = -4
            last = parts[last_idx]
            if last == "ago" and len(parts) >= 5:
                last = parts[last_idx - 1] + " ago"
                last_idx -= 1
            
            # next 列 (可能是 "in 3h" 或 "at 2026...")
            # 从 last 往前找，直到遇到 'in' 或 'at'
            next_parts = []
            i = last_idx - 1
            # 使用 abs(i) <= len(parts) 来处理负索引
            while abs(i) <= len(parts) and parts[i] not in ['in', 'at']:
                next_parts.insert(0, parts[i])
                i -= 1
            # 如果找到了 'in' 或 'at'，包含它
            if abs(i) <= len(parts) and parts[i] in ['in', 'at']:
                next_parts.insert(0, parts[i])
            next_val = ' '.join(next_parts) if next_parts else "-"
            
            # schedule 从 'cron' 或 'at' 开始到 next 之前
            # 注意：next 列的 'at' 是时间前缀，schedule 的 'at' 或 'cron' 是标记
            schedule_parts = []
            if abs(i) <= len(parts):
                # 从 'in'/'at' 前面继续找 schedule 的 'cron' 或 'at'
                j = i - 1
                while abs(j) <= len(parts) and parts[j] not in ['cron', 'at']:
                    j -= 1
                # 现在 j 指向 schedule 的标记
                if abs(j) <= len(parts):
                    k = j
                    while k < i:  # 从 schedule 标记到 next 标记之前
                        schedule_parts.append(parts[k])
                        k += 1
            schedule = ' '.join(schedule_parts) if schedule_parts else "-"
            
            # name 是 ID 之后的部分
            task_id = parts[0]
            # name 在 parts[1] 到 schedule 开始之前
            name_end = i if i >= 0 else 2
            name_parts = parts[1:name_end]
            name = ' '.join(name_parts) if name_parts else "unknown"
            
            task = {
                "id": task_id,
                "name": name,
                "schedule": schedule,
                "next": next_val,
                "last": last,
                "status": status,
                "target": target,
                "agent": agent
            }
            tasks.append(task)
        
        return tasks
    
    def check_openclaw_cron(self) -> Tuple[bool, str, List[Dict]]:
        """
        检查 OpenClaw cron 任务状态
        
        Returns: (is_healthy, message, issues)
        """
        try:
            result = subprocess.run(
                ["openclaw", "cron", "list"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return False, f"无法获取 cron 列表: {result.stderr}", []
            
            tasks = self.parse_openclaw_cron_list(result.stdout)
            self.results["openclaw"]["total"] = len(tasks)
            self.results["openclaw"]["tasks"] = tasks
            
            issues = []
            healthy_count = 0
            warning_count = 0
            critical_count = 0
            
            for task in tasks:
                status = task.get("status", "").lower()
                last = task.get("last", "-")
                name = task.get("name", "unknown")
                task_id = task.get("id", "")
                
                # 检查 error 状态
                if status == "error":
                    issues.append({
                        "type": "error_status",
                        "system": "openclaw",
                        "task_id": task_id,
                        "task_name": name,
                        "message": f"任务状态为 error",
                        "severity": "critical"
                    })
                    critical_count += 1
                    continue
                
                # 检查 idle 但从未执行
                if status == "idle" and (last == "-" or "never" in last.lower() or last == "从未执行"):
                    # 如果是刚创建的任务，可能正常
                    # 这里简化处理，如果包含 GAP 或特定名称，认为是测试任务
                    if "GAP" in name or "test" in name.lower():
                        issues.append({
                            "type": "idle_never_ran",
                            "system": "openclaw",
                            "task_id": task_id,
                            "task_name": name,
                            "message": f"任务从未执行过",
                            "severity": "warning"
                        })
                        warning_count += 1
                    else:
                        healthy_count += 1
                    continue
                
                # 检查是否长期未执行
                if last != "-" and "ago" in last.lower():
                    # 解析 "Xh ago" 或 "Xd ago"
                    match = re.match(r'(\d+)([hd])\s*ago', last.lower())
                    if match:
                        value = int(match.group(1))
                        unit = match.group(2)
                        hours_ago = value if unit == 'h' else value * 24
                        
                        # 简化判断：超过 48 小时未执行视为异常
                        if hours_ago > 48:
                            issues.append({
                                "type": "long_idle",
                                "system": "openclaw",
                                "task_id": task_id,
                                "task_name": name,
                                "message": f"{hours_ago}小时未执行",
                                "severity": "warning"
                            })
                            warning_count += 1
                            continue
                
                # 正常任务
                if status in ["ok", "success", "idle"]:
                    healthy_count += 1
                else:
                    warning_count += 1
            
            self.results["openclaw"]["healthy"] = healthy_count
            self.results["openclaw"]["warning"] = warning_count
            self.results["openclaw"]["critical"] = critical_count
            
            # 总体状态判断
            if critical_count > 0:
                return False, f"发现 {critical_count} 个严重问题", issues
            elif warning_count > 0:
                return False, f"发现 {warning_count} 个警告", issues
            else:
                return True, f"所有 {healthy_count} 个任务正常", issues
                
        except subprocess.TimeoutExpired:
            return False, "获取 cron 列表超时", []
        except Exception as e:
            return False, f"检查异常: {e}", []
    
    def check_linux_cron(self) -> Tuple[bool, str]:
        """
        检查 Linux cron 任务
        
        Returns: (is_healthy, message)
        """
        try:
            # 获取当前用户的 crontab
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.split('\n') 
                        if l.strip() and not l.strip().startswith('#')]
                task_count = len(lines)
                self.results["linux"]["total"] = task_count
                self.results["linux"]["healthy"] = task_count
                return True, f"发现 {task_count} 个定时任务"
            else:
                # 可能是没有 crontab
                return True, "没有配置定时任务"
                
        except Exception as e:
            return False, f"检查异常: {e}"
    
    def detect_zombie_tasks(self) -> List[Dict]:
        """
        检测僵尸任务：显示成功但无实际输出/文件未更新
        
        检测方法：
        1. 检查任务对应的日志文件时间戳
        2. 检查预期输出文件是否更新
        """
        zombies = []
        
        # 获取最近一次健康报告的时间
        report_file = LEARNINGS_DIR / "cron_health_report.json"
        if report_file.exists():
            try:
                stat = report_file.stat()
                last_report_time = datetime.fromtimestamp(stat.st_mtime)
                hours_since_report = (datetime.now() - last_report_time).total_seconds() / 3600
                
                # 如果报告超过 6 小时未更新，可能存在僵尸任务
                if hours_since_report > 6:
                    # 检查是否有应该生成报告的任务
                    for task in self.results["openclaw"]["tasks"]:
                        if "health" in task.get("name", "").lower() or "监控" in task.get("name", ""):
                            if task.get("status") == "ok":
                                zombies.append({
                                    "task_id": task.get("id"),
                                    "task_name": task.get("name"),
                                    "issue": f"状态为ok但报告 {hours_since_report:.1f} 小时未更新",
                                    "severity": "warning"
                                })
            except Exception:
                pass
        
        # 检查 second-brain-processor 的输出
        processor_dir = WORKSPACE / "second-brain-processor"
        if processor_dir.exists():
            # 检查 process.log
            log_file = processor_dir / "process.log"
            if log_file.exists():
                try:
                    stat = log_file.stat()
                    last_log_time = datetime.fromtimestamp(stat.st_mtime)
                    hours_since_log = (datetime.now() - last_log_time).total_seconds() / 3600
                    
                    # 如果超过 24 小时没有新日志
                    if hours_since_log > 24:
                        # 查找相关的定时任务
                        for task in self.results["openclaw"]["tasks"]:
                            if "process" in task.get("name", "").lower() or "整理" in task.get("name", ""):
                                if task.get("status") in ["ok", "success"]:
                                    zombies.append({
                                        "task_id": task.get("id"),
                                        "task_name": task.get("name"),
                                        "issue": f"状态正常但日志 {hours_since_log:.1f} 小时未更新",
                                        "severity": "critical"
                                    })
                except Exception:
                    pass
        
        return zombies
    
    def run_full_check(self, verbose: bool = False) -> Dict:
        """执行完整检查"""
        print("=" * 60)
        print(f"Cron 健康检查 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60)
        
        all_healthy = True
        all_issues = []
        
        # 1. 检查 OpenClaw Cron
        print("\n🔍 检查 OpenClaw Cron 任务...")
        healthy, message, issues = self.check_openclaw_cron()
        all_issues.extend(issues)
        
        if healthy:
            print(f"   ✅ {message}")
        else:
            print(f"   ⚠️ {message}")
            all_healthy = False
        
        if verbose and self.results["openclaw"]["tasks"]:
            for task in self.results["openclaw"]["tasks"]:
                status_emoji = "✅" if task.get("status") in ["ok", "success"] else "⚠️"
                print(f"      {status_emoji} {task.get('name', 'unknown')[:30]:<30} [{task.get('status', 'unknown')}]")
        
        # 2. 检查 Linux Cron
        print("\n🔍 检查 Linux Cron 任务...")
        healthy, message = self.check_linux_cron()
        if healthy:
            print(f"   ✅ {message}")
        else:
            print(f"   ⚠️ {message}")
        
        # 3. 检测僵尸任务
        print("\n🔍 检测僵尸任务...")
        zombies = self.detect_zombie_tasks()
        if zombies:
            print(f"   ⚠️ 发现 {len(zombies)} 个僵尸任务")
            all_issues.extend(zombies)
            all_healthy = False
        else:
            print("   ✅ 未发现僵尸任务")
        
        # 汇总
        self.results["issues"] = all_issues
        self.results["overall_status"] = "healthy" if all_healthy else "issues_found"
        
        self._generate_recommendations()
        
        print("\n" + "=" * 60)
        print(f"📊 OpenClaw: {self.results['openclaw']['total']} 个任务")
        print(f"   ✅ 正常: {self.results['openclaw']['healthy']}")
        print(f"   ⚠️ 警告: {self.results['openclaw']['warning']}")
        print(f"   ❌ 严重: {self.results['openclaw']['critical']}")
        print(f"\n📊 Linux: {self.results['linux']['total']} 个任务")
        
        if all_issues:
            print(f"\n⚠️ 发现 {len(all_issues)} 个问题")
        else:
            print("\n✅ 所有检查通过，系统运行正常")
        print("=" * 60)
        
        return self.results
    
    def _generate_recommendations(self):
        """生成修复建议"""
        for issue in self.results["issues"]:
            issue_type = issue.get("type", "")
            severity = issue.get("severity", "warning")
            
            if issue_type == "error_status":
                self.results["recommendations"].append({
                    "priority": "high",
                    "action": f"重启失败任务: {issue.get('task_name', 'unknown')[:30]}",
                    "command": f"openclaw cron restart {issue.get('task_id', '')}",
                    "issue": issue
                })
            elif issue_type == "long_idle":
                self.results["recommendations"].append({
                    "priority": "medium",
                    "action": f"检查长期未执行的任务: {issue.get('task_name', 'unknown')[:30]}",
                    "command": f"openclaw cron logs {issue.get('task_id', '')}",
                    "issue": issue
                })
            elif issue_type == "zombie_task" or "僵尸" in issue.get("issue", ""):
                self.results["recommendations"].append({
                    "priority": "high",
                    "action": f"检查僵尸任务: {issue.get('task_name', 'unknown')[:30]}",
                    "command": "openclaw status && openclaw cron list",
                    "issue": issue
                })
        
        # 去重
        seen = set()
        unique_recommendations = []
        for rec in self.results["recommendations"]:
            key = rec.get("command", "")
            if key not in seen:
                seen.add(key)
                unique_recommendations.append(rec)
        self.results["recommendations"] = unique_recommendations
    
    def save_report(self):
        """保存检查报告"""
        report_file = LEARNINGS_DIR / "cron_health_report.json"
        try:
            LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            print(f"\n💾 报告已保存: {report_file}")
        except Exception as e:
            print(f"\n[WARN] 保存报告失败: {e}")
    
    def send_notification(self, force: bool = False):
        """发送通知（只在有问题或强制发送时）"""
        has_issues = len(self.results["issues"]) > 0
        
        if not has_issues and not force:
            print("\n✅ 系统健康，不发送通知")
            return
        
        status_emoji = "⚠️" if has_issues else "✅"
        status_text = "发现问题" if has_issues else "健康检查报告"
        
        message = f"""{status_emoji} **Cron 健康检查 - {status_text}**

检测时间：{datetime.now().strftime('%H:%M')}

**任务统计：**
- OpenClaw: {self.results['openclaw']['total']} 个任务
  - ✅ 正常: {self.results['openclaw']['healthy']}
  - ⚠️ 警告: {self.results['openclaw']['warning']}
  - ❌ 严重: {self.results['openclaw']['critical']}
- Linux: {self.results['linux']['total']} 个任务
"""
        
        if has_issues:
            message += "\n**发现问题：**\n"
            for issue in self.results["issues"][:10]:  # 最多显示10个
                severity_emoji = "❌" if issue.get("severity") == "critical" else "⚠️"
                message += f"\n{severity_emoji} `{issue.get('task_name', 'unknown')[:30]}`"
                message += f"\n   {issue.get('message', issue.get('issue', '未知问题'))}"
        
        if self.results["recommendations"]:
            message += "\n\n**修复建议：**"
            for rec in sorted(self.results["recommendations"], 
                            key=lambda x: 0 if x["priority"] == "high" else 1)[:5]:  # 最多5个
                priority_emoji = "🔴" if rec["priority"] == "high" else "🟡"
                message += f"\n\n{priority_emoji} {rec['action']}"
                message += f"\n   执行：`{rec['command']}`"
        
        # 尝试发送通知
        try:
            # 尝试导入飞书发送模块
            processor_dir = WORKSPACE / "second-brain-processor"
            if (processor_dir / "feishu_guardian.py").exists():
                sys.path.insert(0, str(processor_dir))
                from feishu_guardian import send_feishu_safe
                
                result = send_feishu_safe(
                    message,
                    target=FEISHU_USER,
                    msg_type="cron_health_check",
                    max_retries=1
                )
                
                if result.get("success"):
                    print("\n✅ 飞书通知已发送")
                else:
                    print(f"\n⚠️ 飞书通知发送失败: {result.get('message', '未知错误')}")
            else:
                # 记录到日志
                log_file = LEARNINGS_DIR / "cron_health_notifications.log"
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*50}\n")
                    f.write(f"[{datetime.now().isoformat()}]\n")
                    f.write(message)
                    f.write("\n")
                print(f"\n📝 通知已记录到日志: {log_file}")
                
        except Exception as e:
            print(f"\n⚠️ 通知发送异常: {e}")


def main():
    parser = argparse.ArgumentParser(description='Cron 健康检查')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='详细输出（显示所有任务详情）')
    parser.add_argument('--notify', '-n', action='store_true',
                       help='强制发送通知（即使没有发现问题）')
    parser.add_argument('--silent', '-s', action='store_true',
                       help='静默模式（只记录日志，不输出到控制台，不发送通知）')
    
    args = parser.parse_args()
    
    # 静默模式下重定向输出
    if args.silent:
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
    
    checker = CronHealthChecker()
    results = checker.run_full_check(verbose=args.verbose)
    checker.save_report()
    
    # 静默模式下恢复输出并只记录结果
    if args.silent:
        sys.stdout = old_stdout
        print(f"[静默模式] Cron健康检查完成 - 状态: {results['overall_status']}")
    else:
        # 非静默模式下发送通知
        checker.send_notification(force=args.notify)
    
    # 返回码: 0=健康, 1=有问题
    sys.exit(0 if results["overall_status"] == "healthy" else 1)


if __name__ == "__main__":
    main()
