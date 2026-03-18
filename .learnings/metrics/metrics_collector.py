#!/usr/bin/env python3
"""
自我进化系统 - 效果量化追踪器
自动收集和分析系统改进效果数据
"""

import json
import re
import subprocess
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any

class MetricsCollector:
    """核心指标收集器"""
    
    def __init__(self, workspace: str = "/root/.openclaw/workspace"):
        self.workspace = Path(workspace)
        self.learnings_dir = self.workspace / ".learnings"
        self.metrics_dir = self.learnings_dir / "metrics"
        self.metrics_dir.mkdir(exist_ok=True)
        
    # ============ 核心指标计算 ============
    
    def calculate_error_rate(self, days: int = 7) -> Dict[str, Any]:
        """
        计算错误率：每周错误数 / 总任务数
        从 ERRORS.md 提取数据
        """
        errors_file = self.learnings_dir / "ERRORS.md"
        if not errors_file.exists():
            return {"error": "ERRORS.md not found"}
        
        content = errors_file.read_text(encoding='utf-8')
        
        # 提取错误记录（支持多种格式）
        error_patterns = [
            # [ERR-YYYYMMDD-XXX] 格式
            r'\[ERR-(\d{8})-\d+\]',
            # ## ERR-YYYYMMDD-XXX 格式
            r'## ERR-(\d{8})-\d+',
            # - **时间**: YYYY-MM-DD 格式
            r'- \*\*时间\*\*: (\d{4}-\d{2}-\d{2})',
            # **Logged**: YYYY-MM-DD 格式
            r'\*\*Logged\*\*: (\d{4}-\d{2}-\d{2})',
        ]
        
        cutoff_date = datetime.now() - timedelta(days=days)
        period_errors = []
        
        for pattern in error_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                try:
                    if len(match) == 8:  # YYYYMMDD
                        date = datetime.strptime(match, "%Y%m%d")
                    else:  # YYYY-MM-DD
                        date = datetime.strptime(match, "%Y-%m-%d")
                    
                    if date >= cutoff_date:
                        period_errors.append({
                            "date": date.strftime("%Y-%m-%d"),
                            "source": "ERRORS.md"
                        })
                except ValueError:
                    continue
        
        # 去重（按日期）
        seen = set()
        unique_errors = []
        for err in period_errors:
            key = err["date"]
            if key not in seen:
                seen.add(key)
                unique_errors.append(err)
        
        # 按区域分类统计
        area_counts = defaultdict(int)
        area_pattern = r'\*\*Area\*\*:\s*(\w+)'
        for match in re.finditer(area_pattern, content):
            area_counts[match.group(1)] += 1
        
        # 按状态统计
        status_counts = defaultdict(int)
        status_pattern = r'\*\*Status\*\*:\s*(\w+)'
        for match in re.finditer(status_pattern, content):
            status_counts[match.group(1).lower()] += 1
        
        # 估算总任务数（从 cron 健康报告）
        cron_report = self.learnings_dir / "cron_health_report.json"
        total_tasks = 18  # 默认值
        if cron_report.exists():
            try:
                data = json.loads(cron_report.read_text())
                total_tasks = data.get("openclaw", {}).get("total", 11) + \
                             data.get("linux", {}).get("total", 7)
            except:
                pass
        
        error_count = len(unique_errors)
        error_rate = (error_count / total_tasks) * 100 if total_tasks > 0 else 0
        
        return {
            "period_days": days,
            "total_errors": error_count,
            "total_tasks": total_tasks,
            "error_rate": round(error_rate, 2),
            "error_rate_per_day": round(error_count / days, 2),
            "by_area": dict(area_counts),
            "by_status": dict(status_counts),
            "errors": unique_errors[:10]  # 只保留最近10个
        }
    
    def calculate_fix_time(self, days: int = 7) -> Dict[str, Any]:
        """
        计算平均修复时间：从发现到解决的平均时长
        需要错误记录中有 Logged 和 Resolved 时间
        """
        errors_file = self.learnings_dir / "ERRORS.md"
        if not errors_file.exists():
            return {"error": "ERRORS.md not found"}
        
        content = errors_file.read_text()
        
        # 匹配完整的错误块
        error_blocks = re.split(r'\n##\s+\[ERR-', content)[1:]  # 第一个为空
        
        fix_times = []
        resolved_count = 0
        pending_count = 0
        
        for block in error_blocks:
            # 提取 Logged 时间
            logged_match = re.search(r'\*\*Logged\*\*: (\d{4}-\d{2}-\d{2})', block)
            if not logged_match:
                continue
            
            logged_date = datetime.strptime(logged_match.group(1), "%Y-%m-%d")
            
            # 检查状态
            status_match = re.search(r'\*\*Status\*\*:\s*(\w+)', block)
            status = status_match.group(1).lower() if status_match else "pending"
            
            if status in ["resolved", "已解决"]:
                # 查找解决方案时间（简化处理：使用当前日期或Resolved标记）
                resolved_match = re.search(r'\*\*Resolved\*\*: (\d{4}-\d{2}-\d{2})', block)
                if resolved_match:
                    resolved_date = datetime.strptime(resolved_match.group(1), "%Y-%m-%d")
                else:
                    # 估算：使用 Logged 后第一次出现 "解决方案" 的位置
                    resolved_date = logged_date + timedelta(days=1)  # 默认1天
                
                fix_time = (resolved_date - logged_date).total_seconds() / 3600  # 小时
                fix_times.append(fix_time)
                resolved_count += 1
            else:
                pending_count += 1
        
        avg_fix_time = sum(fix_times) / len(fix_times) if fix_times else 0
        
        return {
            "period_days": days,
            "resolved_errors": resolved_count,
            "pending_errors": pending_count,
            "avg_fix_time_hours": round(avg_fix_time, 2),
            "median_fix_time_hours": round(sorted(fix_times)[len(fix_times)//2], 2) if fix_times else 0,
            "min_fix_time_hours": round(min(fix_times), 2) if fix_times else 0,
            "max_fix_time_hours": round(max(fix_times), 2) if fix_times else 0
        }
    
    def calculate_improvement_density(self, days: int = 7) -> Dict[str, Any]:
        """
        计算改进密度：每周新增改进数
        从 EVOLUTION_LOG.md 提取数据
        """
        evo_file = self.learnings_dir / "EVOLUTION_LOG.md"
        if not evo_file.exists():
            return {"error": "EVOLUTION_LOG.md not found"}
        
        content = evo_file.read_text()
        
        # 提取进化记录
        evo_pattern = r'## \[EVO-(\d{8})-(\d+)\]\s+(.+?)\n'
        matches = list(re.finditer(evo_pattern, content))
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        period_improvements = []
        for match in matches:
            date_str = match.group(1)
            evo_id = match.group(2)
            title = match.group(3).strip()
            
            try:
                date = datetime.strptime(date_str, "%Y%m%d")
                if date >= cutoff_date:
                    period_improvements.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "id": evo_id,
                        "title": title
                    })
            except ValueError:
                continue
        
        # 按类型统计
        type_counts = defaultdict(int)
        type_pattern = r'\*\*类型\*\*:\s*(.+)'
        for match in re.finditer(type_pattern, content):
            type_counts[match.group(1).strip()] += 1
        
        # 按状态统计
        status_counts = defaultdict(int)
        status_pattern = r'\*\*状态\*\*:\s*(.+)'
        for match in re.finditer(status_pattern, content):
            status_counts[match.group(1).strip()] += 1
        
        improvement_count = len(period_improvements)
        
        return {
            "period_days": days,
            "total_improvements": improvement_count,
            "improvements_per_week": round(improvement_count / (days / 7), 2),
            "improvements_per_day": round(improvement_count / days, 2),
            "by_type": dict(type_counts),
            "by_status": dict(status_counts),
            "improvements": period_improvements[:10]
        }
    
    def calculate_rule_stability(self, days: int = 7) -> Dict[str, Any]:
        """
        计算规则稳定性：规则修改频率
        从 git 历史提取 AGENTS.md 修改次数
        """
        try:
            # 获取 AGENTS.md 的最近修改
            result = subprocess.run(
                ["git", "log", "--since", f"{days} days ago", "--oneline", "--", "AGENTS.md"],
                cwd=self.workspace,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {"error": f"git command failed: {result.stderr}"}
            
            commits = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # 获取每次修改的详情
            modifications = []
            for commit_line in commits:
                if not commit_line:
                    continue
                commit_hash = commit_line.split()[0]
                
                # 获取提交详情
                detail_result = subprocess.run(
                    ["git", "show", "--stat", "--format=%H|%ci|%s", "-s", commit_hash],
                    cwd=self.workspace,
                    capture_output=True,
                    text=True
                )
                
                if detail_result.returncode == 0:
                    lines = detail_result.stdout.strip().split('\n')
                    if lines:
                        info = lines[0].split('|')
                        if len(info) >= 3:
                            modifications.append({
                                "commit": info[0][:8],
                                "date": info[1][:10],
                                "message": info[2]
                            })
            
            return {
                "period_days": days,
                "total_modifications": len(modifications),
                "modifications_per_week": round(len(modifications) / (days / 7), 2),
                "stability_score": max(0, 100 - len(modifications) * 10),  # 简单评分
                "modifications": modifications[:5]
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def calculate_cron_reliability(self, days: int = 7) -> Dict[str, Any]:
        """
        计算定时任务可靠性：成功执行率
        从 cron_health_report.json 和 send_records.json 提取
        """
        # 从健康报告获取
        cron_report = self.learnings_dir / "cron_health_report.json"
        health_data = {}
        if cron_report.exists():
            try:
                data = json.loads(cron_report.read_text())
                healthy = data.get("openclaw", {}).get("healthy", 0)
                total = data.get("openclaw", {}).get("total", 1)
                health_data = {
                    "healthy_tasks": healthy,
                    "total_tasks": total,
                    "health_rate": round(healthy / total * 100, 2) if total > 0 else 0
                }
            except:
                pass
        
        # 从发送记录获取
        send_records = self.learnings_dir / "send_records.json"
        send_data = {}
        if send_records.exists():
            try:
                data = json.loads(send_records.read_text())
                # 统计最近days天的记录
                cutoff = (datetime.now() - timedelta(days=days)).timestamp()
                recent_records = [r for r in data if r.get("timestamp", 0) > cutoff]
                
                success = len([r for r in recent_records if r.get("status") == "success"])
                failed = len([r for r in recent_records if r.get("status") == "failed"])
                
                send_data = {
                    "total_sends": len(recent_records),
                    "successful": success,
                    "failed": failed,
                    "success_rate": round(success / (success + failed) * 100, 2) if (success + failed) > 0 else 0
                }
            except:
                pass
        
        return {
            "period_days": days,
            "cron_health": health_data,
            "message_delivery": send_data
        }
    
    def calculate_roi(self, days: int = 7) -> Dict[str, Any]:
        """
        计算 ROI：改进投入 vs 效果提升
        简化版本，基于改进次数和错误减少趋势
        """
        # 获取当前周期数据
        current_errors = self.calculate_error_rate(days)
        current_improvements = self.calculate_improvement_density(days)
        
        # 获取上一周期数据用于比较
        prev_errors = self.calculate_error_rate(days * 2)  # 2倍天数，包含前一周
        prev_error_count = prev_errors.get("total_errors", 0)
        current_error_count = current_errors.get("total_errors", 0)
        
        # 计算错误变化趋势
        error_reduction = prev_error_count - current_error_count
        
        # 计算改进投入（简化：每个改进算作1单位投入）
        improvement_count = current_improvements.get("total_improvements", 0)
        
        # ROI 计算：错误减少量 / 改进投入
        roi = error_reduction / improvement_count if improvement_count > 0 else 0
        
        return {
            "period_days": days,
            "error_reduction": error_reduction,
            "improvement_investment": improvement_count,
            "roi_ratio": round(roi, 2),
            "efficiency_score": min(100, max(0, roi * 50 + 50)),  # 转换为0-100分
            "interpretation": self._interpret_roi(roi)
        }
    
    def _interpret_roi(self, roi: float) -> str:
        """解释 ROI 值"""
        if roi >= 2:
            return "优秀：每单位改进带来2+错误减少，效率极高"
        elif roi >= 1:
            return "良好：改进投入与错误减少基本持平"
        elif roi >= 0:
            return "需关注：改进效果不明显，可能需要调整策略"
        else:
            return "警告：错误数增加，需要检视改进方向"
    
    # ============ 报告生成 ============
    
    def generate_weekly_report(self) -> str:
        """生成周报"""
        metrics = {
            "error_rate": self.calculate_error_rate(7),
            "fix_time": self.calculate_fix_time(7),
            "improvement_density": self.calculate_improvement_density(7),
            "rule_stability": self.calculate_rule_stability(7),
            "cron_reliability": self.calculate_cron_reliability(7),
            "roi": self.calculate_roi(7),
            "generated_at": datetime.now().isoformat()
        }
        
        # 保存原始数据
        report_file = self.metrics_dir / f"weekly_report_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        
        # 生成 Markdown 报告
        return self._format_weekly_markdown(metrics)
    
    def generate_monthly_report(self) -> str:
        """生成月报"""
        metrics = {
            "error_rate": self.calculate_error_rate(30),
            "fix_time": self.calculate_fix_time(30),
            "improvement_density": self.calculate_improvement_density(30),
            "rule_stability": self.calculate_rule_stability(30),
            "cron_reliability": self.calculate_cron_reliability(30),
            "roi": self.calculate_roi(30),
            "generated_at": datetime.now().isoformat()
        }
        
        report_file = self.metrics_dir / f"monthly_report_{datetime.now().strftime('%Y%m')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        
        return self._format_monthly_markdown(metrics)
    
    def _format_weekly_markdown(self, metrics: Dict) -> str:
        """格式化周报 Markdown"""
        now = datetime.now()
        week_start = now - timedelta(days=7)
        
        report = f"""# 📊 系统改进效果周报

**报告周期**: {week_start.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}
**生成时间**: {now.strftime('%Y-%m-%d %H:%M')}

---

## 📈 核心指标总览

| 指标 | 本周数值 | 状态 |
|------|----------|------|
| 错误率 | {metrics['error_rate'].get('error_rate', 'N/A')}% | {self._rate_status(metrics['error_rate'].get('error_rate', 0))} |
| 平均修复时间 | {metrics['fix_time'].get('avg_fix_time_hours', 'N/A')}h | {self._fix_time_status(metrics['fix_time'].get('avg_fix_time_hours', 0))} |
| 改进密度 | {metrics['improvement_density'].get('total_improvements', 'N/A')}个/周 | - |
| 规则稳定性 | {metrics['rule_stability'].get('stability_score', 'N/A')}/100 | {self._stability_status(metrics['rule_stability'].get('stability_score', 100))} |
| ROI | {metrics['roi'].get('roi_ratio', 'N/A')} | {self._roi_status(metrics['roi'].get('roi_ratio', 0))} |

---

## 🔴 错误分析

**本周错误统计**:
- 总错误数: {metrics['error_rate'].get('total_errors', 'N/A')}
- 涉及任务数: {metrics['error_rate'].get('total_tasks', 'N/A')}
- 错误率: {metrics['error_rate'].get('error_rate', 'N/A')}%
- 日均错误: {metrics['error_rate'].get('error_rate_per_day', 'N/A')}

**按区域分布**:
{self._format_dict(metrics['error_rate'].get('by_area', {}))}

**按状态分布**:
{self._format_dict(metrics['error_rate'].get('by_status', {}))}

---

## ⏱️ 修复效率

**修复时间统计**:
- 已解决错误: {metrics['fix_time'].get('resolved_errors', 'N/A')}
- 待解决错误: {metrics['fix_time'].get('pending_errors', 'N/A')}
- 平均修复时间: {metrics['fix_time'].get('avg_fix_time_hours', 'N/A')}小时
- 中位数修复时间: {metrics['fix_time'].get('median_fix_time_hours', 'N/A')}小时

---

## 🚀 改进追踪

**本周改进**:
- 新增改进数: {metrics['improvement_density'].get('total_improvements', 'N/A')}
- 改进频率: {metrics['improvement_density'].get('improvements_per_day', 'N/A')}个/天

**按类型分布**:
{self._format_dict(metrics['improvement_density'].get('by_type', {}))}

**按状态分布**:
{self._format_dict(metrics['improvement_density'].get('by_status', {}))}

---

## 📏 规则稳定性

**规则修改统计**:
- 修改次数: {metrics['rule_stability'].get('total_modifications', 'N/A')}
- 修改频率: {metrics['rule_stability'].get('modifications_per_week', 'N/A')}次/周
- 稳定性评分: {metrics['rule_stability'].get('stability_score', 'N/A')}/100

---

## 💰 ROI 分析

**投入产出比**:
- 错误减少量: {metrics['roi'].get('error_reduction', 'N/A')}
- 改进投入: {metrics['roi'].get('improvement_investment', 'N/A')}个
- ROI 比率: {metrics['roi'].get('roi_ratio', 'N/A')}
- 效率评分: {metrics['roi'].get('efficiency_score', 'N/A')}/100

**解读**: {metrics['roi'].get('interpretation', 'N/A')}

---

## 📊 ASCII 趋势图

### 错误率趋势（最近7天）
{self._generate_ascii_trend(metrics['error_rate'].get('errors', []), 'error')}

### 改进频率趋势
{self._generate_improvement_trend(metrics['improvement_density'].get('improvements', []))}

---

*报告由自我进化系统自动生成*
"""
        return report
    
    def _format_monthly_markdown(self, metrics: Dict) -> str:
        """格式化月报 Markdown"""
        now = datetime.now()
        month_start = now - timedelta(days=30)
        
        report = f"""# 📊 系统改进效果月报

**报告周期**: {month_start.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}
**生成时间**: {now.strftime('%Y-%m-%d %H:%M')}

---

## 📈 核心指标对比

| 指标 | 本月 | 目标 | 达成率 |
|------|------|------|--------|
| 错误率 | {metrics['error_rate'].get('error_rate', 'N/A')}% | <5% | {'✅' if metrics['error_rate'].get('error_rate', 100) < 5 else '❌'} |
| 平均修复时间 | {metrics['fix_time'].get('avg_fix_time_hours', 'N/A')}h | <24h | {'✅' if metrics['fix_time'].get('avg_fix_time_hours', 999) < 24 else '❌'} |
| 改进密度 | {metrics['improvement_density'].get('total_improvements', 'N/A')}个 | >4个 | {'✅' if metrics['improvement_density'].get('total_improvements', 0) >= 4 else '❌'} |
| 规则稳定性 | {metrics['rule_stability'].get('stability_score', 'N/A')}/100 | >80 | {'✅' if metrics['rule_stability'].get('stability_score', 0) >= 80 else '❌'} |

---

## 📊 详细数据

{self._format_weekly_markdown(metrics)}

---

*月报由自我进化系统自动生成*
"""
        return report
    
    def _format_dict(self, d: Dict) -> str:
        """格式化字典为 Markdown 列表"""
        if not d:
            return "- 暂无数据"
        return "\n".join([f"- {k}: {v}" for k, v in sorted(d.items(), key=lambda x: -x[1])[:5]])
    
    def _generate_ascii_trend(self, data: List[Dict], data_type: str) -> str:
        """生成 ASCII 趋势图"""
        if not data:
            return "```\n暂无数据\n```"
        
        # 简化的趋势图
        chart = "```\n"
        chart += "错误数/天\n"
        chart += " 5 |\n"
        chart += " 4 |\n"
        chart += " 3 |\n"
        chart += " 2 |\n"
        chart += " 1 |\n"
        chart += " 0 |" + "~" * 7 + "\n"
        chart += "   | " + " ".join(["M", "T", "W", "T", "F", "S", "S"]) + "\n"
        chart += "```"
        return chart
    
    def _generate_improvement_trend(self, improvements: List[Dict]) -> str:
        """生成改进频率趋势图"""
        if not improvements:
            return "```\n暂无数据\n```"
        
        return f"""```
本周改进: {'█' * len(improvements)}
改进分布: {len(improvements)} 个改进分布在 {len(set(i['date'] for i in improvements))} 天
```"""
    
    def _rate_status(self, rate: float) -> str:
        if rate < 5:
            return "✅ 优秀"
        elif rate < 15:
            return "⚠️ 一般"
        else:
            return "❌ 需改进"
    
    def _fix_time_status(self, hours: float) -> str:
        if hours < 12:
            return "✅ 快速"
        elif hours < 48:
            return "⚠️ 正常"
        else:
            return "❌ 滞后"
    
    def _stability_status(self, score: float) -> str:
        if score >= 80:
            return "✅ 稳定"
        elif score >= 60:
            return "⚠️ 波动"
        else:
            return "❌ 频繁变更"
    
    def _roi_status(self, roi: float) -> str:
        if roi >= 1:
            return "✅ 正向"
        elif roi >= 0:
            return "⚠️ 持平"
        else:
            return "❌ 负向"


def main():
    """主函数 - CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="自我进化系统效果量化追踪")
    parser.add_argument("--weekly", action="store_true", help="生成周报")
    parser.add_argument("--monthly", action="store_true", help="生成月报")
    parser.add_argument("--metric", choices=["error_rate", "fix_time", "improvement", "stability", "roi", "all"],
                       default="all", help="计算特定指标")
    parser.add_argument("--days", type=int, default=7, help="统计天数")
    parser.add_argument("--output", type=str, help="输出文件路径")
    
    args = parser.parse_args()
    
    collector = MetricsCollector()
    
    if args.weekly:
        report = collector.generate_weekly_report()
        print(report)
        
        # 保存到文件
        output_file = args.output or f"/root/.openclaw/workspace/.learnings/metrics/weekly_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 周报已保存到: {output_file}")
        
    elif args.monthly:
        report = collector.generate_monthly_report()
        print(report)
        
        output_file = args.output or f"/root/.openclaw/workspace/.learnings/metrics/monthly_report_{datetime.now().strftime('%Y%m')}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 月报已保存到: {output_file}")
        
    else:
        # 打印特定指标
        results = {}
        if args.metric in ["error_rate", "all"]:
            results["error_rate"] = collector.calculate_error_rate(args.days)
        if args.metric in ["fix_time", "all"]:
            results["fix_time"] = collector.calculate_fix_time(args.days)
        if args.metric in ["improvement", "all"]:
            results["improvement_density"] = collector.calculate_improvement_density(args.days)
        if args.metric in ["stability", "all"]:
            results["rule_stability"] = collector.calculate_rule_stability(args.days)
        if args.metric in ["roi", "all"]:
            results["roi"] = collector.calculate_roi(args.days)
        
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
