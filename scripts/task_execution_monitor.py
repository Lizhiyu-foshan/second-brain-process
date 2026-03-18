#!/usr/bin/env python3
"""
定时任务执行验证监控

主动检查定时任务是否真正执行（通过文件时间戳和内容验证）
而非仅仅依赖 cron status
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class TaskMonitor:
    def __init__(self):
        self.workspace = Path('/root/.openclaw/workspace')
        self.results = []
        
    def check_file_freshness(self, filepath: Path, max_age_hours: int) -> Dict:
        """检查文件是否在指定时间内更新过"""
        if not filepath.exists():
            return {
                'status': 'MISSING',
                'file': str(filepath),
                'message': f'文件不存在'
            }
        
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
        age = datetime.now() - mtime
        
        if age > timedelta(hours=max_age_hours):
            return {
                'status': 'STALE',
                'file': str(filepath),
                'last_update': mtime.strftime('%Y-%m-%d %H:%M:%S'),
                'age_hours': round(age.total_seconds() / 3600, 2),
                'message': f'超过{max_age_hours}小时未更新'
            }
        
        return {
            'status': 'OK',
            'file': str(filepath),
            'last_update': mtime.strftime('%Y-%m-%d %H:%M:%S'),
            'age_hours': round(age.total_seconds() / 3600, 2),
            'message': '正常'
        }
    
    def check_cron_task_execution(self, task_name: str, filepath: Path, 
                                   expected_frequency_hours: int) -> Dict:
        """检查定时任务是否按期执行"""
        freshness = self.check_file_freshness(filepath, expected_frequency_hours * 2)
        
        return {
            'task': task_name,
            'filepath': str(filepath),
            'expected_frequency': f'每{expected_frequency_hours}小时',
            **freshness
        }
    
    def check_content_updated(self, filepath: Path, keyword: str = None) -> Dict:
        """检查文件内容是否有实际更新（而非仅时间戳）"""
        if not filepath.exists():
            return {
                'status': 'MISSING',
                'file': str(filepath),
                'message': '文件不存在'
            }
        
        try:
            content = filepath.read_text(encoding='utf-8')
            
            if not content.strip():
                return {
                    'status': 'EMPTY',
                    'file': str(filepath),
                    'message': '文件为空'
                }
            
            # 检查是否包含今天的日期（简单验证内容是否更新）
            today = datetime.now().strftime('%Y-%m-%d')
            if today in content:
                return {
                    'status': 'OK',
                    'file': str(filepath),
                    'message': f'包含今天日期 ({today})'
                }
            else:
                return {
                    'status': 'SUSPICIOUS',
                    'file': str(filepath),
                    'message': f'不包含今天日期，可能未真正更新'
                }
        except Exception as e:
            return {
                'status': 'ERROR',
                'file': str(filepath),
                'message': f'读取失败：{e}'
            }
    
    def check_all_critical_tasks(self) -> List[Dict]:
        """检查所有关键定时任务"""
        tasks = [
            {
                'name': '晨间聊天记录整理',
                'file': self.workspace / 'memory' / datetime.now().strftime('%Y-%m-%d.md'),
                'frequency': 24,  # 每天
            },
            {
                'name': '每日复盘报告',
                'file': self.workspace / 'daily_review' / datetime.now().strftime('%Y-%m-%d.md'),
                'frequency': 24,
            },
            {
                'name': 'AI 学习分析',
                'file': self.workspace / '.learnings' / 'LEARNINGS.md',
                'frequency': 24,
            },
        ]
        
        results = []
        for task in tasks:
            result = self.check_cron_task_execution(
                task['name'],
                task['file'],
                task['frequency']
            )
            
            # 额外检查内容是否真正更新
            if result['status'] != 'MISSING':
                content_check = self.check_content_updated(task['file'])
                result['content_status'] = content_check['status']
                result['content_message'] = content_check['message']
            
            results.append(result)
        
        return results
    
    def generate_report(self, results: List[Dict]) -> str:
        """生成监控报告"""
        report = []
        report.append("=" * 70)
        report.append("定时任务执行验证报告")
        report.append("=" * 70)
        report.append(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        ok_count = 0
        warning_count = 0
        error_count = 0
        
        for result in results:
            status = result.get('status', 'UNKNOWN')
            content_status = result.get('content_status', 'N/A')
            
            if status == 'OK' and content_status == 'OK':
                icon = f'{Colors.GREEN}✓{Colors.RESET}'
                ok_count += 1
            elif status in ['STALE', 'SUSPICIOUS']:
                icon = f'{Colors.YELLOW}⚠{Colors.RESET}'
                warning_count += 1
            else:
                icon = f'{Colors.RED}✗{Colors.RESET}'
                error_count += 1
            
            report.append(f"{icon} {result['task']}")
            report.append(f"   文件：{result['filepath']}")
            report.append(f"   状态：{status} - {result.get('message', '')}")
            if result.get('last_update'):
                report.append(f"   最后更新：{result['last_update']} ({result.get('age_hours', 0)}小时前)")
            if content_status != 'N/A':
                report.append(f"   内容：{content_status} - {result.get('content_message', '')}")
            report.append("")
        
        report.append("=" * 70)
        report.append(f"总计：{ok_count} 正常，{warning_count} 警告，{error_count} 异常")
        report.append("=" * 70)
        
        return '\n'.join(report)
    
    def send_alert_if_needed(self, results: List[Dict]) -> Optional[str]:
        """如果有异常，生成告警消息"""
        errors = [r for r in results if r['status'] not in ['OK', 'MISSING']]
        
        if not errors:
            return None
        
        alert = "⚠️ **定时任务异常告警**\n\n"
        for error in errors:
            alert += f"❌ {error['task']}\n"
            alert += f"   状态：{error['status']}\n"
            alert += f"   原因：{error.get('message', '未知')}\n\n"
        
        alert += "请立即检查定时任务状态！"
        return alert

def main():
    monitor = TaskMonitor()
    
    print(f"{Colors.BLUE}开始检查定时任务执行情况...{Colors.RESET}\n")
    
    results = monitor.check_all_critical_tasks()
    report = monitor.generate_report(results)
    print(report)
    
    # 检查是否有告警
    alert = monitor.send_alert_if_needed(results)
    if alert:
        print(f"\n{Colors.RED}{alert}{Colors.RESET}")
        print("\n💡 建议操作:")
        print("1. 检查 cron 任务状态：openclaw cron list")
        print("2. 查看任务执行日志：cat /tmp/<task>.log")
        print("3. 手动触发任务验证：python3 <script>.py")
        return 1
    else:
        print(f"\n{Colors.GREEN}✅ 所有定时任务执行正常！{Colors.RESET}")
        return 0

if __name__ == '__main__':
    sys.exit(main())
