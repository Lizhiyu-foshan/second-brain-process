#!/usr/bin/env python3
"""
AGENTS.md 熵管理器
每月1日执行，检测并清理过时规则

功能：
1. 检测僵尸规则（90天未触发）
2. 检测重复规则（关键词/触发条件相似）
3. 检测复杂规则（描述>50行）
4. 检测低健康度规则（<70分）
5. 检测循环依赖
6. 生成优化建议报告

使用方法：
    python3 agents_entropy_manager.py [--dry-run]

选项：
    --dry-run    模拟运行，不实际修改任何文件
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional


class AgentsEntropyManager:
    """AGENTS.md 熵管理器"""
    
    def __init__(self, dry_run: bool = False):
        self.workspace = Path("/root/.openclaw/workspace")
        self.registry_path = self.workspace / "RULES_REGISTRY.json"
        self.details_path = self.workspace / "AGENTS_DETAILS.md"
        self.report_path = self.workspace / "reports" / f"agents_entropy_{datetime.now().strftime('%Y%m')}.md"
        self.dry_run = dry_run
        
        # 确保reports目录存在
        self.report_path.parent.mkdir(exist_ok=True)
        
        # 加载数据
        self.registry = self._load_registry()
        self.details_content = self._load_details()
    
    def _load_registry(self) -> Dict:
        """加载规则注册表"""
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  无法加载注册表: {e}")
            return {"rules": []}
    
    def _load_details(self) -> str:
        """加载详细规则文档"""
        try:
            with open(self.details_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"⚠️  无法加载详细文档: {e}")
            return ""
    
    def analyze(self) -> Dict[str, Any]:
        """执行全部分析"""
        print("🔍 开始AGENTS.md熵管理分析...")
        
        report = {
            "scan_date": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "findings": [],
            "recommendations": [],
            "stats": {
                "total_rules": len(self.registry.get("rules", [])),
                "zombie_rules": 0,
                "duplicate_rules": 0,
                "complex_rules": 0,
                "unhealthy_rules": 0,
                "circular_deps": 0
            }
        }
        
        # 1. 检测僵尸规则
        zombies = self._find_zombie_rules(days=90)
        if zombies:
            report["findings"].append({
                "type": "zombie_rules",
                "severity": "medium",
                "count": len(zombies),
                "rules": zombies,
                "description": f"{len(zombies)}条规则90天未触发，建议审查是否仍需要"
            })
            report["stats"]["zombie_rules"] = len(zombies)
            report["recommendations"].append(
                f"建议将以下规则标记为deprecated或删除：{', '.join(zombies)}"
            )
        
        # 2. 检测重复规则
        duplicates = self._find_duplicate_rules()
        if duplicates:
            report["findings"].append({
                "type": "duplicate_rules",
                "severity": "high",
                "count": len(duplicates),
                "pairs": duplicates,
                "description": f"发现{len(duplicates)}对可能重复的规则"
            })
            report["stats"]["duplicate_rules"] = len(duplicates)
            for pair in duplicates:
                report["recommendations"].append(
                    f"建议合并规则 {pair[0]} 和 {pair[1]}"
                )
        
        # 3. 检测复杂规则
        complex_rules = self._find_complex_rules(max_lines=50)
        if complex_rules:
            report["findings"].append({
                "type": "complex_rules",
                "severity": "low",
                "count": len(complex_rules),
                "rules": complex_rules,
                "description": f"{len(complex_rules)}条规则描述超过50行，考虑拆分"
            })
            report["stats"]["complex_rules"] = len(complex_rules)
            for rule_id, lines in complex_rules:
                report["recommendations"].append(
                    f"建议拆分规则 {rule_id}（当前{lines}行）"
                )
        
        # 4. 检测低健康度规则
        unhealthy = self._find_unhealthy_rules(threshold=70)
        if unhealthy:
            report["findings"].append({
                "type": "unhealthy_rules",
                "severity": "high",
                "count": len(unhealthy),
                "rules": unhealthy,
                "description": f"{len(unhealthy)}条规则健康度低于70分，需要优化"
            })
            report["stats"]["unhealthy_rules"] = len(unhealthy)
            for rule_id, score in unhealthy:
                report["recommendations"].append(
                    f"优先优化规则 {rule_id}（健康度{score}分）"
                )
        
        # 5. 检测循环依赖
        circular = self._find_circular_dependencies()
        if circular:
            report["findings"].append({
                "type": "circular_dependencies",
                "severity": "high",
                "count": len(circular),
                "cycles": circular,
                "description": f"发现{len(circular)}个循环依赖"
            })
            report["stats"]["circular_deps"] = len(circular)
            for cycle in circular:
                report["recommendations"].append(
                    f"解决循环依赖：{' → '.join(cycle)}"
                )
        
        # 6. 分析规则覆盖度
        coverage_gaps = self._analyze_coverage_gaps()
        if coverage_gaps:
            report["findings"].append({
                "type": "coverage_gaps",
                "severity": "medium",
                "gaps": coverage_gaps,
                "description": f"发现{len(coverage_gaps)}个可能未覆盖的场景"
            })
            for gap in coverage_gaps:
                report["recommendations"].append(
                    f"考虑增加规则覆盖场景：{gap}"
                )
        
        return report
    
    def _find_zombie_rules(self, days: int = 90) -> List[str]:
        """查找N天未触发的规则"""
        zombie_rules = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for rule in self.registry.get("rules", []):
            last_triggered = rule.get("health_metrics", {}).get("last_triggered")
            if last_triggered:
                try:
                    last_date = datetime.fromisoformat(last_triggered.replace('Z', '+00:00'))
                    if last_date < cutoff_date:
                        zombie_rules.append(rule["id"])
                except:
                    pass
            else:
                # 从未触发过的规则也视为僵尸
                created_at = rule.get("created_at", "")
                if created_at:
                    try:
                        created_date = datetime.strptime(created_at, "%Y-%m-%d")
                        if created_date < cutoff_date:
                            zombie_rules.append(rule["id"])
                    except:
                        pass
        
        return zombie_rules
    
    def _find_duplicate_rules(self) -> List[tuple]:
        """查找可能重复的规则"""
        duplicates = []
        rules = self.registry.get("rules", [])
        
        for i, rule1 in enumerate(rules):
            for rule2 in rules[i+1:]:
                # 检查关键词重叠
                keywords1 = set(rule1.get("triggers", {}).get("keywords", []))
                keywords2 = set(rule2.get("triggers", {}).get("keywords", []))
                
                if keywords1 and keywords2:
                    overlap = keywords1.intersection(keywords2)
                    overlap_ratio = len(overlap) / min(len(keywords1), len(keywords2))
                    
                    if overlap_ratio >= 0.5:  # 50%以上关键词重叠
                        duplicates.append((rule1["id"], rule2["id"]))
                        break
        
        return duplicates
    
    def _find_complex_rules(self, max_lines: int = 50) -> List[tuple]:
        """查找描述过长的规则"""
        complex_rules = []
        
        # 从AGENTS_DETAILS.md中统计各规则行数
        for rule in self.registry.get("rules", []):
            rule_id = rule["id"]
            # 查找规则在文档中的位置 - 转义特殊字符
            escaped_id = re.escape(rule_id)
            pattern = rf"## {escaped_id}.*?(?=## \w+\d+|$)"
            match = re.search(pattern, self.details_content, re.DOTALL)
            if match:
                lines = match.group(0).count('\n')
                if lines > max_lines:
                    complex_rules.append((rule_id, lines))
        
        return complex_rules
    
    def _find_unhealthy_rules(self, threshold: int = 70) -> List[tuple]:
        """查找健康度低的规则"""
        unhealthy = []
        
        for rule in self.registry.get("rules", []):
            score = rule.get("health_metrics", {}).get("health_score", 100)
            if score < threshold:
                unhealthy.append((rule["id"], score))
        
        return unhealthy
    
    def _find_circular_dependencies(self) -> List[List[str]]:
        """查找循环依赖"""
        cycles = []
        
        # 构建依赖图
        graph = {}
        for rule in self.registry.get("rules", []):
            graph[rule["id"]] = rule.get("dependencies", [])
        
        # DFS检测循环
        def dfs(node, visited, rec_stack, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    result = dfs(neighbor, visited, rec_stack, path)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    # 发现循环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    return cycle
            
            path.pop()
            rec_stack.remove(node)
            return None
        
        visited = set()
        for node in graph:
            if node not in visited:
                cycle = dfs(node, visited, set(), [])
                if cycle:
                    cycles.append(cycle)
        
        return cycles
    
    def _analyze_coverage_gaps(self) -> List[str]:
        """分析规则覆盖缺口"""
        gaps = []
        
        # 定义常见场景
        common_scenarios = [
            ("文件操作", ["文件", "读写", "保存", "删除"]),
            ("网络请求", ["API", "HTTP", "请求", "超时"]),
            ("数据库", ["数据库", "查询", "存储", "备份"]),
            ("安全配置", ["密码", "密钥", "Token", "权限"]),
        ]
        
        # 收集所有规则的关键词
        all_keywords = set()
        for rule in self.registry.get("rules", []):
            keywords = rule.get("triggers", {}).get("keywords", [])
            all_keywords.update(keywords)
        
        # 检查哪些场景未被覆盖
        for scenario, keywords in common_scenarios:
            if not any(kw in all_keywords for kw in keywords):
                gaps.append(scenario)
        
        return gaps
    
    def generate_report(self, report: Dict) -> str:
        """生成人类可读报告"""
        lines = [
            "# AGENTS.md 熵管理报告",
            "",
            f"**扫描时间**：{report['scan_date']}",
            f"**运行模式**：{'模拟运行' if report['dry_run'] else '实际执行'}",
            "",
            "## 统计概览",
            "",
            f"- 总规则数：{report['stats']['total_rules']} 条",
            f"- 僵尸规则：{report['stats']['zombie_rules']} 条",
            f"- 重复规则：{report['stats']['duplicate_rules']} 对",
            f"- 复杂规则：{report['stats']['complex_rules']} 条",
            f"- 低健康度：{report['stats']['unhealthy_rules']} 条",
            f"- 循环依赖：{report['stats']['circular_deps']} 个",
            "",
            "## 发现详情",
            ""
        ]
        
        if not report["findings"]:
            lines.append("🎉 本次扫描未发现异常！")
        else:
            for finding in report["findings"]:
                emoji = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(finding["severity"], "⚪")
                
                lines.append(f"### {emoji} {finding['type']}")
                lines.append("")
                lines.append(finding["description"])
                lines.append("")
                
                if "rules" in finding:
                    lines.append(f"**涉及规则**：{', '.join(finding['rules'])}")
                if "pairs" in finding:
                    lines.append("**重复对**：")
                    for pair in finding["pairs"]:
                        lines.append(f"- {pair[0]} ↔ {pair[1]}")
                if "cycles" in finding:
                    lines.append("**循环链**：")
                    for cycle in finding["cycles"]:
                        lines.append(f"- {' → '.join(cycle)}")
                lines.append("")
        
        if report["recommendations"]:
            lines.append("## 优化建议")
            lines.append("")
            for i, rec in enumerate(report["recommendations"], 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("*本报告由AGENTS.md熵管理器自动生成*")
        
        return "\n".join(lines)
    
    def save_report(self, report_text: str):
        """保存报告到文件"""
        if not self.dry_run:
            with open(self.report_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"✅ 报告已保存：{self.report_path}")
        else:
            print(f"[模拟] 报告将保存到：{self.report_path}")
    
    def run(self):
        """运行完整流程"""
        print(f"{'='*60}")
        print("AGENTS.md 熵管理器")
        print(f"{'='*60}")
        print(f"模式：{'模拟运行' if self.dry_run else '实际执行'}")
        print()
        
        # 执行分析
        report = self.analyze()
        
        # 生成报告
        report_text = self.generate_report(report)
        
        # 保存报告
        self.save_report(report_text)
        
        # 输出摘要
        print()
        print("="*60)
        print("扫描完成")
        print("="*60)
        print(f"发现问题：{len(report['findings'])} 类")
        print(f"优化建议：{len(report['recommendations'])} 条")
        print()
        
        if report["findings"]:
            print("📋 发现摘要：")
            for finding in report["findings"]:
                emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(finding["severity"], "⚪")
                print(f"  {emoji} {finding['type']}: {finding.get('count', finding.get('description', ''))}")
        else:
            print("✨ 系统健康，未发现需要优化的问题")
        
        return report


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AGENTS.md 熵管理器")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不修改文件")
    args = parser.parse_args()
    
    manager = AgentsEntropyManager(dry_run=args.dry_run)
    manager.run()


if __name__ == "__main__":
    main()
