#!/usr/bin/env python3
"""
step5_quality_check.py - v1.0 精华质量检查
四步法第5步：质量检查闭环

检查标准：
1. 核心洞察：必须有一句话概括，放在引用框里
2. 详细观点：3-5个分论点，每个有具体论据（不能只有标题）
3. 关键引用：至少保留1句原文金句
4. 思考延伸：有原创理解和联想
5. 关联与启示：与其他知识的连接
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

@dataclass
class QualityIssue:
    """质量问题"""
    file: str
    check_item: str
    severity: str  # critical, warning, info
    description: str
    suggestion: str

@dataclass
class QualityReport:
    """质量报告"""
    file: str
    passed: bool
    score: int  # 0-100
    issues: List[QualityIssue]
    summary: str


class EssenceQualityChecker:
    """精华文档质量检查器"""
    
    # 质量标准定义
    QUALITY_STANDARDS = {
        "core_insight": {
            "name": "核心洞察",
            "weight": 25,
            "check": lambda content: bool(re.search(r'>\s*\*\*[^*]+\*\*', content)),
            "description": '必须有一句话概括，放在引用框里 (>)',
        },
        "detailed_points": {
            "name": "详细观点",
            "weight": 30,
            "check": lambda content: len(re.findall(r'^#{3,4}\s+', content, re.M)) >= 3,
            "description": "至少3个分论点 (### 标题)",
        },
        "substantive_content": {
            "name": "内容充实度",
            "weight": 20,
            "check": lambda content: len(content) > 2000,  # 至少2000字符
            "description": "文档内容充实 (>2000字符)",
        },
        "key_quotes": {
            "name": "关键引用",
            "weight": 10,
            "check": lambda content: bool(re.search(r'>[^>\n]{20,}', content)),
            "description": "有原文引用或金句 (>20字符的引用)",
        },
        "reflection": {
            "name": "思考延伸",
            "weight": 10,
            "check": lambda content: "思考延伸" in content or "思考" in content,
            "description": "包含思考延伸部分",
        },
        "connections": {
            "name": "关联与启示",
            "weight": 5,
            "check": lambda content: "关联" in content or "启示" in content or "连接" in content,
            "description": "包含关联与启示",
        },
    }
    
    def __init__(self, vault_dir: Path = None):
        self.vault_dir = vault_dir or Path("/root/.openclaw/workspace/obsidian-vault")
        self.discussions_dir = self.vault_dir / "01-Discussions"
        self.quality_log_file = Path("/root/.openclaw/workspace/.learnings/quality_check_log.jsonl")
        
    def check_file(self, file_path: Path) -> QualityReport:
        """检查单个文件质量"""
        content = file_path.read_text(encoding='utf-8')
        issues = []
        score = 0
        
        for key, standard in self.QUALITY_STANDARDS.items():
            passed = standard["check"](content)
            if passed:
                score += standard["weight"]
            else:
                issues.append(QualityIssue(
                    file=str(file_path.name),
                    check_item=standard["name"],
                    severity="critical" if standard["weight"] >= 20 else "warning",
                    description=standard["description"],
                    suggestion=f"补充{standard['name']}部分"
                ))
        
        # 额外检查：内容空洞（只有标题没有实质内容）
        if self._is_hollow_content(content):
            issues.append(QualityIssue(
                file=str(file_path.name),
                check_item="内容空洞",
                severity="critical",
                description="文档只有标题框架，没有实质内容",
                suggestion="每个分论点下写完整论述，保留关键数字、案例、具体措施"
            ))
            score -= 30  # 严重扣分
        
        passed = score >= 70  # 70分以上通过
        
        return QualityReport(
            file=str(file_path.name),
            passed=passed,
            score=max(0, score),
            issues=issues,
            summary=f"得分 {score}/100，{'通过' if passed else '不通过，需要修复'}"
        )
    
    def _is_hollow_content(self, content: str) -> bool:
        """检查内容是否空洞（只有标题没有实质内容）"""
        # 查找 ### 标题后的内容
        sections = re.findall(r'###\s+.+?\n(.+?)(?=###|\Z)', content, re.DOTALL)
        
        hollow_count = 0
        for section in sections:
            # 清理空白
            section_clean = section.strip()
            # 如果章节内容少于100字符，认为是空洞
            if len(section_clean) < 100:
                hollow_count += 1
        
        # 超过50%的章节空洞，判定为整体空洞
        if sections and hollow_count / len(sections) > 0.5:
            return True
        
        return False
    
    def check_date_files(self, date_str: str = None) -> List[QualityReport]:
        """检查指定日期的所有精华文档"""
        if date_str is None:
            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        reports = []
        pattern = f"*_{date_str}.md"
        
        for file_path in self.discussions_dir.glob(pattern):
            if file_path.is_file():
                report = self.check_file(file_path)
                reports.append(report)
        
        return reports
    
    def check_latest_files(self, count: int = 5) -> List[QualityReport]:
        """检查最新的N个精华文档"""
        files = sorted(
            self.discussions_dir.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:count]
        
        reports = []
        for file_path in files:
            report = self.check_file(file_path)
            reports.append(report)
        
        return reports
    
    def log_quality_check(self, reports: List[QualityReport]):
        """记录质量检查结果"""
        self.quality_log_file.parent.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(reports),
            "passed": sum(1 for r in reports if r.passed),
            "failed": sum(1 for r in reports if not r.passed),
            "reports": [
                {
                    "file": r.file,
                    "passed": r.passed,
                    "score": r.score,
                    "issues_count": len(r.issues),
                    "issues": [{"item": i.check_item, "severity": i.severity, "description": i.description} for i in r.issues]
                }
                for r in reports
            ]
        }
        
        with open(self.quality_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def generate_quality_report(self, reports: List[QualityReport]) -> str:
        """生成质量检查报告"""
        lines = [
            "## 精华文档质量检查报告",
            "",
            f"**检查时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**检查文件数**: {len(reports)}",
            f"**通过**: {sum(1 for r in reports if r.passed)} | **不通过**: {sum(1 for r in reports if not r.passed)}",
            "",
            "---",
            "",
        ]
        
        for report in reports:
            status = "✅ 通过" if report.passed else "❌ 不通过"
            lines.append(f"### {report.file} - {status} (得分: {report.score})")
            lines.append("")
            
            if report.issues:
                lines.append("**问题列表**:")
                for issue in report.issues:
                    emoji = "🔴" if issue.severity == "critical" else "🟡"
                    lines.append(f"- {emoji} **{issue.check_item}**: {issue.description}")
                    lines.append(f"  - 建议: {issue.suggestion}")
            else:
                lines.append("**无质量问题**")
            
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        # 如果有失败的，添加处理建议
        failed = [r for r in reports if not r.passed]
        if failed:
            lines.append("## 待修复文件")
            lines.append("")
            for r in failed:
                lines.append(f"- `{r.file}` - 得分 {r.score}")
            lines.append("")
            lines.append("**建议操作**: 重新运行四步法，或手动补充缺失内容")
        
        return '\n'.join(lines)


def main():
    """命令行入口"""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description='精华文档质量检查')
    parser.add_argument('--date', help='检查指定日期 (YYYY-MM-DD)')
    parser.add_argument('--latest', type=int, default=5, help='检查最新的N个文件')
    parser.add_argument('--file', help='检查指定文件')
    parser.add_argument('--notify', action='store_true', help='发送通知')
    
    args = parser.parse_args()
    
    checker = EssenceQualityChecker()
    
    if args.file:
        reports = [checker.check_file(Path(args.file))]
    elif args.date:
        reports = checker.check_date_files(args.date)
    else:
        reports = checker.check_latest_files(args.latest)
    
    if not reports:
        print("没有找到需要检查的文件")
        return
    
    # 输出报告
    report_text = checker.generate_quality_report(reports)
    print(report_text)
    
    # 记录日志
    checker.log_quality_check(reports)
    
    # 如果有失败的，返回非0退出码
    failed = [r for r in reports if not r.passed]
    if failed:
        print(f"\n⚠️ 发现 {len(failed)} 个文件质量不通过")
        sys.exit(1)
    else:
        print(f"\n✅ 所有 {len(reports)} 个文件质量检查通过")


if __name__ == "__main__":
    main()
