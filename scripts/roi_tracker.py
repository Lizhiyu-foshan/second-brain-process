#!/usr/bin/env python3
"""
自动化检查任务 ROI 追踪器

追踪每个自动化检查任务的价值，识别低价值任务并建议停用。
连续追踪 7 天，生成周报。

核心指标：
- 执行次数
- 发现问题数（真正检测出问题的次数）
- 触发改进数（导致实际修复/优化的次数）
- 空跑率 = 无问题执行次数 / 总执行次数
- 价值评分 = (发现问题数 + 改进行动数) / 执行次数

判定规则：
- 🟢 高价值：价值评分 > 0.1
- 🟡 中价值：价值评分 0.01-0.1
- 🔴 低价值：价值评分 < 0.01 → 建议停用
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

# 配置
WORKSPACE = Path("/root/.openclaw/workspace")
TRACKING_DIR = WORKSPACE / ".learnings" / "roi_tracker"
DATA_FILE = TRACKING_DIR / "execution_records.json"
REPORT_FILE = TRACKING_DIR / "roi_weekly_report.md"
TRACKING_DIR.mkdir(parents=True, exist_ok=True)


class ROITracker:
    """ROI 追踪器核心类"""
    
    def __init__(self):
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        """加载追踪数据"""
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "tasks": {},
            "tracking_start": None,
            "tracking_end": None,
            "last_updated": None
        }
    
    def _save_data(self):
        """保存追踪数据"""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def _get_task_key(self, task_name: str, task_type: str = "openclaw_cron") -> str:
        """生成任务唯一标识"""
        return f"{task_type}:{task_name}"
    
    def record_execution(self, task_name: str, 
                        found_issues: bool = False,
                        improvements_triggered: int = 0,
                        execution_duration_ms: Optional[int] = None,
                        details: Optional[str] = None,
                        task_type: str = "openclaw_cron"):
        """
        记录一次任务执行
        
        Args:
            task_name: 任务名称
            found_issues: 是否发现问题
            improvements_triggered: 触发的改进数
            execution_duration_ms: 执行时长（毫秒）
            details: 详细说明
            task_type: 任务类型 (openclaw_cron/linux_cron)
        """
        task_key = self._get_task_key(task_name, task_type)
        
        if task_key not in self.data["tasks"]:
            self.data["tasks"][task_key] = {
                "name": task_name,
                "type": task_type,
                "executions": [],
                "total_executions": 0,
                "total_issues_found": 0,
                "total_improvements": 0,
                "total_duration_ms": 0,
                "first_execution": None,
                "last_execution": None
            }
        
        task = self.data["tasks"][task_key]
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "found_issues": found_issues,
            "improvements_triggered": improvements_triggered,
            "duration_ms": execution_duration_ms,
            "details": details
        }
        
        task["executions"].append(execution_record)
        task["total_executions"] += 1
        if found_issues:
            task["total_issues_found"] += 1
        task["total_improvements"] += improvements_triggered
        if execution_duration_ms:
            task["total_duration_ms"] += execution_duration_ms
        
        if not task["first_execution"]:
            task["first_execution"] = execution_record["timestamp"]
        task["last_execution"] = execution_record["timestamp"]
        
        # 自动设置追踪周期
        if not self.data["tracking_start"]:
            self.data["tracking_start"] = execution_record["timestamp"]
        
        self._save_data()
    
    def get_task_stats(self, task_name: str, task_type: str = "openclaw_cron") -> Optional[Dict]:
        """获取单个任务的统计数据"""
        task_key = self._get_task_key(task_name, task_type)
        if task_key not in self.data["tasks"]:
            return None
        
        task = self.data["tasks"][task_key]
        total = task["total_executions"]
        if total == 0:
            return None
        
        issues = task["total_issues_found"]
        improvements = task["total_improvements"]
        value_score = (issues + improvements) / total if total > 0 else 0
        empty_run_rate = (total - issues) / total if total > 0 else 1
        avg_duration = task["total_duration_ms"] / total if task["total_duration_ms"] > 0 else 0
        
        # 价值等级
        if value_score > 0.1:
            value_level = "🟢 高价值"
        elif value_score > 0.01:
            value_level = "🟡 中价值"
        else:
            value_level = "🔴 低价值"
        
        return {
            "name": task_name,
            "type": task_type,
            "total_executions": total,
            "issues_found": issues,
            "improvements_triggered": improvements,
            "value_score": round(value_score, 4),
            "empty_run_rate": round(empty_run_rate, 4),
            "avg_duration_ms": round(avg_duration, 2),
            "value_level": value_level,
            "recommendation": "保留" if value_score > 0.01 else "建议停用",
            "first_execution": task["first_execution"],
            "last_execution": task["last_execution"]
        }
    
    def get_all_stats(self) -> List[Dict]:
        """获取所有任务的统计数据"""
        stats = []
        for task_key in self.data["tasks"]:
            task = self.data["tasks"][task_key]
            stats_obj = self.get_task_stats(task["name"], task["type"])
            if stats_obj:
                stats.append(stats_obj)
        
        # 按价值评分排序
        stats.sort(key=lambda x: x["value_score"], reverse=True)
        return stats
    
    def generate_weekly_report(self) -> str:
        """生成周报"""
        stats = self.get_all_stats()
        
        # 分类
        high_value = [s for s in stats if s["value_score"] > 0.1]
        mid_value = [s for s in stats if 0.01 < s["value_score"] <= 0.1]
        low_value = [s for s in stats if s["value_score"] <= 0.01]
        
        report = []
        report.append("# 📊 自动化检查任务 ROI 周报")
        report.append(f"\n**追踪周期**: {self.data.get('tracking_start', 'N/A')} 至 {self.data.get('last_updated', 'N/A')}")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**追踪任务总数**: {len(stats)}")
        report.append("")
        
        # 总体概览
        report.append("## 📈 总体概览")
        total_executions = sum(s["total_executions"] for s in stats)
        total_issues = sum(s["issues_found"] for s in stats)
        total_improvements = sum(s["improvements_triggered"] for s in stats)
        overall_value_score = (total_issues + total_improvements) / total_executions if total_executions > 0 else 0
        
        report.append(f"- **总执行次数**: {total_executions}")
        report.append(f"- **发现问题总数**: {total_issues}")
        report.append(f"- **触发改进总数**: {total_improvements}")
        report.append(f"- **整体价值评分**: {overall_value_score:.4f}")
        report.append(f"- **高价值任务**: {len(high_value)} 个")
        report.append(f"- **中价值任务**: {len(mid_value)} 个")
        report.append(f"- **低价值任务**: {len(low_value)} 个 🔴")
        report.append("")
        
        # 低价值任务（重点关注）
        if low_value:
            report.append("## 🔴 低价值任务（建议停用）")
            report.append("这些任务连续多日空跑，未产生实际价值，建议逐步停用：")
            report.append("")
            report.append("| 任务名称 | 类型 | 执行次数 | 发现问题 | 价值评分 | 空跑率 | 建议 |")
            report.append("|---------|------|---------|---------|---------|-------|------|")
            for s in low_value:
                report.append(f"| {s['name']} | {s['type']} | {s['total_executions']} | {s['issues_found']} | {s['value_score']:.4f} | {s['empty_run_rate']:.2%} | ❌ 停用 |")
            report.append("")
            report.append("**停用建议**：")
            report.append("1. 先停用 1-2 个最低价值的任务")
            report.append("2. 观察 1-2 周，确认无负面影响")
            report.append("3. 如无问题，继续停用其他低价值任务")
            report.append("")
        
        # 中价值任务
        if mid_value:
            report.append("## 🟡 中价值任务（可优化）")
            report.append("这些任务有一定价值，但可以优化检测逻辑，提高准确性：")
            report.append("")
            report.append("| 任务名称 | 类型 | 执行次数 | 发现问题 | 价值评分 | 优化建议 |")
            report.append("|---------|------|---------|---------|---------|---------|")
            for s in mid_value:
                report.append(f"| {s['name']} | {s['type']} | {s['total_executions']} | {s['issues_found']} | {s['value_score']:.4f} | 优化检测条件 |")
            report.append("")
        
        # 高价值任务
        if high_value:
            report.append("## 🟢 高价值任务（保留）")
            report.append("这些任务持续发现问题，价值显著：")
            report.append("")
            report.append("| 任务名称 | 类型 | 执行次数 | 发现问题 | 价值评分 | 备注 |")
            report.append("|---------|------|---------|---------|---------|------|")
            for s in high_value:
                report.append(f"| {s['name']} | {s['type']} | {s['total_executions']} | {s['issues_found']} | {s['value_score']:.4f} | ✅ 保留 |")
            report.append("")
        
        # 详细执行记录（最近 10 次）
        report.append("## 📋 最近执行记录（抽样）")
        for s in stats[:5]:  # 只显示前 5 个任务的记录
            task_key = self._get_task_key(s["name"], s["type"])
            task = self.data["tasks"][task_key]
            recent = task["executions"][-10:]  # 最近 10 次
            report.append(f"\n### {s['name']}")
            for exec_rec in recent[-5:]:  # 只显示最近 5 次
                timestamp = exec_rec["timestamp"][:16].replace('T', ' ')
                status = "🔍" if exec_rec["found_issues"] else "✓"
                report.append(f"- {timestamp} {status} {exec_rec.get('details', '')}")
        
        report.append("")
        report.append("---")
        report.append("*报告由 ROI Tracker 自动生成*")
        
        report_text = "\n".join(report)
        
        # 保存报告
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        return report_text
    
    def reset_tracking(self):
        """重置追踪数据（开始新周期）"""
        self.data = {
            "tasks": {},
            "tracking_start": None,
            "tracking_end": None,
            "last_updated": None
        }
        self._save_data()
        return "追踪数据已重置"


# 便捷函数
def record_task_execution(task_name: str, found_issues: bool = False, 
                         improvements: int = 0, duration_ms: int = None,
                         details: str = None, task_type: str = "openclaw_cron"):
    """便捷函数：记录任务执行"""
    tracker = ROITracker()
    tracker.record_execution(task_name, found_issues, improvements, duration_ms, details, task_type)


def get_roi_report() -> str:
    """便捷函数：生成并返回周报"""
    tracker = ROITracker()
    return tracker.generate_weekly_report()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "report":
            # 生成周报
            report = get_roi_report()
            print(report)
        
        elif cmd == "reset":
            # 重置追踪
            tracker = ROITracker()
            print(tracker.reset_tracking())
        
        elif cmd == "stats":
            # 显示统计
            tracker = ROITracker()
            stats = tracker.get_all_stats()
            for s in stats:
                print(f"{s['value_level']} {s['name']}: 价值评分={s['value_score']:.4f}, 执行={s['total_executions']}, 问题={s['issues_found']}")
        
        else:
            print("用法：python3 roi_tracker.py [report|reset|stats]")
    else:
        print("ROI Tracker 已就绪")
        print("用法：python3 roi_tracker.py [report|reset|stats]")
