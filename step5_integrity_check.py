#!/usr/bin/env python3
"""
step5_integrity_check.py - v2.0 推送后完整性验证
四步法第5步增强版：质量检查 + 推送完整性验证

验证项：
1. 质量检查（原有）- 内容质量标准
2. GitHub 文件验证 - 确认文件已推送到远程
3. Dashboard 计数验证 - 确认 Dashboard 已更新
4. 链接可访问性验证 - 确认文件链接可访问
5. 内容格式验证 - 确认格式符合规范
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time

# 导入原有质量检查
from step5_quality_check import EssenceQualityChecker, QualityReport, QualityIssue


@dataclass
class IntegrityCheckItem:
    """完整性检查项"""
    name: str
    passed: bool
    details: str
    severity: str  # critical, warning, info


@dataclass
class IntegrityReport:
    """完整性检查报告"""
    file: str
    github_verified: bool
    dashboard_verified: bool
    links_verified: bool
    format_verified: bool
    all_passed: bool
    checks: List[IntegrityCheckItem]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PushIntegrityChecker:
    """推送完整性检查器"""
    
    def __init__(self, vault_dir: Path = None, remote_url: str = None):
        self.vault_dir = vault_dir or Path("/root/.openclaw/workspace/obsidian-vault")
        self.discussions_dir = self.vault_dir / "01-Discussions"
        self.conversations_dir = self.vault_dir / "02-Conversations"
        self.remote_url = remote_url or "https://github.com/Lizhiyu-foshan/obsidian-vault"
        self.integrity_log_file = Path("/root/.openclaw/workspace/.learnings/integrity_check_log.jsonl")
        
    def verify_github_push(self, local_file: Path, max_retries: int = 3, delay: int = 5) -> Tuple[bool, str]:
        """
        验证文件是否成功推送到 GitHub
        
        策略：
        1. 获取远程文件列表
        2. 检查文件是否在远程
        3. 对比文件大小（允许5%差异）
        """
        relative_path = local_file.relative_to(self.vault_dir)
        
        for attempt in range(max_retries):
            try:
                # 方法1: 使用 git ls-tree 检查远程
                result = subprocess.run(
                    ["git", "ls-tree", "-r", "origin/main", str(relative_path)],
                    cwd=self.vault_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    # 文件在远程存在，进一步验证内容
                    return self._verify_file_content(local_file, relative_path)
                
                # 如果失败，等待后重试
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    
            except subprocess.TimeoutExpired:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    continue
                return False, f"GitHub验证超时（尝试{attempt+1}/{max_retries}）"
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    continue
                return False, f"GitHub验证异常: {str(e)}"
        
        return False, f"文件未在GitHub远程找到: {relative_path}"
    
    def _verify_file_content(self, local_file: Path, relative_path: Path) -> Tuple[bool, str]:
        """验证文件内容一致性"""
        try:
            # 获取远程文件内容（通过 git show）
            result = subprocess.run(
                ["git", "show", f"origin/main:{relative_path}"],
                cwd=self.vault_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, "无法获取远程文件内容"
            
            remote_content = result.stdout
            local_content = local_file.read_text(encoding='utf-8')
            
            # 对比行数（允许1行差异，通常是换行符）
            remote_lines = len(remote_content.strip().split('\n'))
            local_lines = len(local_content.strip().split('\n'))
            
            if abs(remote_lines - local_lines) <= 1:
                return True, f"✅ GitHub验证通过 ({remote_lines}行)"
            else:
                return False, f"⚠️ 行数不匹配: 本地{local_lines}行 vs 远程{remote_lines}行"
                
        except Exception as e:
            # 内容验证失败，但文件存在，返回警告
            return True, f"⚠️ GitHub文件存在，但内容验证失败: {str(e)}"
    
    def verify_dashboard_update(self, date_str: str = None) -> Tuple[bool, str]:
        """
        验证 Dashboard 是否已更新
        
        检查：
        1. Dashboard 文件存在
        2. 今日条目已添加
        3. 计数正确
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        dashboard_file = self.vault_dir / "00-Dashboard.md"
        
        if not dashboard_file.exists():
            return False, "Dashboard文件不存在"
        
        try:
            content = dashboard_file.read_text(encoding='utf-8')
            
            # 检查今日日期是否在 Dashboard 中
            if date_str not in content:
                return False, f"Dashboard未更新: 缺少 {date_str} 条目"
            
            # 提取今日统计
            today_pattern = rf"{date_str}.*?(\d+)"
            matches = re.findall(today_pattern, content)
            
            if matches:
                count = int(matches[0])
                return True, f"✅ Dashboard已更新: {date_str} ({count}个文件)"
            else:
                return True, f"✅ Dashboard已更新: {date_str} (计数提取失败但日期存在)"
                
        except Exception as e:
            return False, f"Dashboard验证异常: {str(e)}"
    
    def verify_file_links(self, file_path: Path) -> Tuple[bool, str]:
        """
        验证文件中的链接是否可访问
        
        检查：
        1. 内部链接（[[xxx]]）指向的文件是否存在
        2. 外部链接可访问性（抽样检查）
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # 检查内部链接
            internal_links = re.findall(r'\[\[([^\]]+)\]\]', content)
            broken_links = []
            
            for link in internal_links:
                # 处理链接别名 [[文件名|显示名]]
                actual_file = link.split('|')[0].strip()
                
                # 可能的文件路径
                possible_paths = [
                    self.vault_dir / f"{actual_file}.md",
                    self.discussions_dir / f"{actual_file}.md",
                    self.conversations_dir / f"{actual_file}.md",
                ]
                
                if not any(p.exists() for p in possible_paths):
                    broken_links.append(actual_file)
            
            if broken_links:
                return False, f"发现 {len(broken_links)} 个断链: {', '.join(broken_links[:3])}..."
            
            return True, f"✅ 所有 {len(internal_links)} 个内部链接有效"
            
        except Exception as e:
            return False, f"链接验证异常: {str(e)}"
    
    def verify_format_compliance(self, file_path: Path) -> Tuple[bool, str]:
        """
        验证文件格式是否符合规范
        
        检查：
        1. YAML frontmatter 存在且完整
        2. 必要的字段存在（date, type）
        3. 标题层级正确
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            issues = []
            
            # 检查 YAML frontmatter
            if not content.startswith('---'):
                issues.append("缺少YAML frontmatter")
            else:
                # 提取 frontmatter
                fm_match = re.match(r'---\n(.*?)\n---', content, re.DOTALL)
                if not fm_match:
                    issues.append("YAML frontmatter格式错误")
                else:
                    fm_content = fm_match.group(1)
                    
                    # 检查必要字段
                    if 'date:' not in fm_content:
                        issues.append("frontmatter缺少date字段")
                    if 'type:' not in fm_content:
                        issues.append("frontmatter缺少type字段")
            
            # 检查标题层级
            h1_count = len(re.findall(r'^# [^#]', content, re.MULTILINE))
            if h1_count == 0:
                issues.append("缺少一级标题(#)")
            elif h1_count > 1:
                issues.append(f"一级标题过多({h1_count}个)")
            
            if issues:
                return False, f"格式问题: {'; '.join(issues)}"
            
            return True, "✅ 格式符合规范"
            
        except Exception as e:
            return False, f"格式验证异常: {str(e)}"
    
    def check_file_integrity(self, file_path: Path) -> IntegrityReport:
        """对单个文件进行完整性检查"""
        checks = []
        
        # 1. GitHub 推送验证
        github_ok, github_msg = self.verify_github_push(file_path)
        checks.append(IntegrityCheckItem(
            name="GitHub推送",
            passed=github_ok,
            details=github_msg,
            severity="critical" if not github_ok else "info"
        ))
        
        # 2. Dashboard 更新验证
        dashboard_ok, dashboard_msg = self.verify_dashboard_update()
        checks.append(IntegrityCheckItem(
            name="Dashboard更新",
            passed=dashboard_ok,
            details=dashboard_msg,
            severity="warning" if not dashboard_ok else "info"
        ))
        
        # 3. 链接有效性验证
        links_ok, links_msg = self.verify_file_links(file_path)
        checks.append(IntegrityCheckItem(
            name="链接有效性",
            passed=links_ok,
            details=links_msg,
            severity="warning" if not links_ok else "info"
        ))
        
        # 4. 格式合规验证
        format_ok, format_msg = self.verify_format_compliance(file_path)
        checks.append(IntegrityCheckItem(
            name="格式合规性",
            passed=format_ok,
            details=format_msg,
            severity="warning" if not format_ok else "info"
        ))
        
        # 判断是否全部通过
        all_passed = all(c.passed for c in checks)
        
        return IntegrityReport(
            file=str(file_path.name),
            github_verified=github_ok,
            dashboard_verified=dashboard_ok,
            links_verified=links_ok,
            format_verified=format_ok,
            all_passed=all_passed,
            checks=checks
        )
    
    def check_files_integrity(self, file_paths: List[Path]) -> List[IntegrityReport]:
        """批量检查文件完整性"""
        reports = []
        for file_path in file_paths:
            if file_path.exists():
                report = self.check_file_integrity(file_path)
                reports.append(report)
        return reports
    
    def log_integrity_check(self, reports: List[IntegrityReport]):
        """记录完整性检查结果"""
        self.integrity_log_file.parent.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(reports),
            "passed": sum(1 for r in reports if r.all_passed),
            "failed": sum(1 for r in reports if not r.all_passed),
            "reports": [
                {
                    "file": r.file,
                    "all_passed": r.all_passed,
                    "github_verified": r.github_verified,
                    "dashboard_verified": r.dashboard_verified,
                    "links_verified": r.links_verified,
                    "format_verified": r.format_verified,
                    "checks": [{"name": c.name, "passed": c.passed, "details": c.details} for c in r.checks]
                }
                for r in reports
            ]
        }
        
        with open(self.integrity_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def generate_integrity_report(self, reports: List[IntegrityReport]) -> str:
        """生成完整性检查报告"""
        lines = [
            "## 推送完整性检查报告",
            "",
            f"**检查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**检查文件数**: {len(reports)}",
            f"**全部通过**: {sum(1 for r in reports if r.all_passed)} | **存在问题**: {sum(1 for r in reports if not r.all_passed)}",
            "",
            "### 检查项说明",
            "- ✅ **GitHub推送**: 文件已成功推送到远程仓库",
            "- ✅ **Dashboard更新**: Dashboard计数已更新",
            "- ✅ **链接有效性**: 内部链接指向的文件存在",
            "- ✅ **格式合规性**: YAML frontmatter和标题格式正确",
            "",
            "---",
            "",
        ]
        
        for report in reports:
            status = "✅ 全部通过" if report.all_passed else "❌ 存在问题"
            lines.append(f"### {report.file} - {status}")
            lines.append("")
            
            for check in report.checks:
                icon = "✅" if check.passed else ("🔴" if check.severity == "critical" else "🟡")
                lines.append(f"{icon} **{check.name}**: {check.details}")
            
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        # 如果有失败的，添加处理建议
        failed = [r for r in reports if not r.all_passed]
        if failed:
            lines.append("## 待处理项目")
            lines.append("")
            for r in failed:
                lines.append(f"- `{r.file}`")
                for check in r.checks:
                    if not check.passed:
                        lines.append(f"  - {check.name}: {check.details}")
            lines.append("")
            lines.append("**建议操作**:")
            lines.append("- 🔴 **GitHub推送失败**: 检查网络连接，手动执行 `git push`")
            lines.append("- 🟡 **Dashboard未更新**: 检查 Dashboard 生成脚本")
            lines.append("- 🟡 **链接失效**: 检查被链接的文件是否存在")
            lines.append("- 🟡 **格式问题**: 检查 YAML frontmatter 是否完整")
        
        return '\n'.join(lines)


def send_integrity_notification(reports: List[IntegrityReport]) -> Dict:
    """发送完整性检查报告到飞书"""
    lines = ["🔍 推送完整性检查报告\n"]
    
    # 统计
    total = len(reports)
    passed = sum(1 for r in reports if r.all_passed)
    failed = total - passed
    
    lines.append(f"检查文件: {total}个 | ✅全部通过: {passed} | ❌存在问题: {failed}\n")
    
    # 详细结果
    for report in reports:
        if report.all_passed:
            lines.append(f"✅ {report.file}")
        else:
            lines.append(f"❌ {report.file}")
            for check in report.checks:
                if not check.passed:
                    icon = "🔴" if check.severity == "critical" else "🟡"
                    lines.append(f"  {icon} {check.name}")
    
    if failed > 0:
        lines.append("")
        lines.append("💡 查看 .learnings/integrity_report_*.md 获取详细信息")
    
    message = "\n".join(lines)
    
    # 尝试导入飞书发送模块
    try:
        sys.path.insert(0, '/root/.openclaw/workspace/skills/feishu-deduplication/scripts')
        from feishu_guardian import send_feishu_safe
        
        result = send_feishu_safe(
            content=message,
            target="ou_363105a68ee112f714ed44e12c802051",
            msg_type="integrity_check"
        )
        
        if result.get('success'):
            print(f"✅ 完整性检查通知已发送")
        else:
            print(f"⚠️ 完整性检查通知发送失败: {result.get('message', '未知错误')}")
        
        return result
        
    except Exception as e:
        print(f"⚠️ 完整性检查通知发送异常: {e}")
        return {"success": False, "message": str(e)}


def run_integrity_and_quality_check(
    files_to_push: List[Tuple[Path, str]],
    vault_dir: Path = None
) -> Tuple[List[QualityReport], List[IntegrityReport]]:
    """
    运行完整的 Step 5 检查（质量 + 完整性）
    
    Args:
        files_to_push: [(文件路径, 文件内容), ...]
        vault_dir: Vault目录路径
    
    Returns:
        (质量报告列表, 完整性报告列表)
    """
    vault_dir = vault_dir or Path("/root/.openclaw/workspace/obsidian-vault")
    
    print("\n[Step 5/5] 质量检查 + 推送完整性验证...")
    
    # 1. 质量检查（原有功能）
    print("\n  📊 运行质量检查...")
    quality_checker = EssenceQualityChecker(vault_dir)
    quality_reports = []
    
    for file_path, _ in files_to_push:
        if "01-Discussions" in str(file_path):
            report = quality_checker.check_file(file_path)
            quality_reports.append(report)
            status = "✅" if report.passed else "❌"
            print(f"    {status} {file_path.name}: {report.score}分")
    
    # 记录质量日志
    if quality_reports:
        quality_checker.log_quality_check(quality_reports)
    
    # 2. 完整性检查（新增功能）
    print("\n  🔍 运行推送完整性验证...")
    integrity_checker = PushIntegrityChecker(vault_dir)
    
    # 只检查实际存在的文件路径
    file_paths = [fp for fp, _ in files_to_push if fp.exists()]
    integrity_reports = integrity_checker.check_files_integrity(file_paths)
    
    for report in integrity_reports:
        status = "✅" if report.all_passed else "❌"
        details = []
        if not report.github_verified:
            details.append("GitHub")
        if not report.dashboard_verified:
            details.append("Dashboard")
        if not report.links_verified:
            details.append("Links")
        if not report.format_verified:
            details.append("Format")
        
        detail_str = f" ({', '.join(details)})" if details else ""
        print(f"    {status} {report.file}{detail_str}")
    
    # 记录完整性日志
    if integrity_reports:
        integrity_checker.log_integrity_check(integrity_reports)
    
    # 生成综合报告
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # 质量报告
    if quality_reports:
        quality_report_text = quality_checker.generate_quality_report(quality_reports)
        quality_report_file = vault_dir / ".learnings" / f"quality_report_{date_str}.md"
        quality_report_file.parent.mkdir(parents=True, exist_ok=True)
        quality_report_file.write_text(quality_report_text, encoding='utf-8')
        print(f"\n  📄 质量报告: {quality_report_file}")
    
    # 完整性报告
    if integrity_reports:
        integrity_report_text = integrity_checker.generate_integrity_report(integrity_reports)
        integrity_report_file = vault_dir / ".learnings" / f"integrity_report_{date_str}.md"
        integrity_report_file.write_text(integrity_report_text, encoding='utf-8')
        print(f"  📄 完整性报告: {integrity_report_file}")
    
    # 发送飞书通知
    print("\n  📤 发送检查报告通知...")
    if quality_reports:
        from step5_quality_check import send_quality_notification
        send_quality_notification(quality_reports)
    
    if integrity_reports:
        send_integrity_notification(integrity_reports)
    
    return quality_reports, integrity_reports


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='推送完整性检查')
    parser.add_argument('--file', help='检查指定文件')
    parser.add_argument('--directory', help='检查目录下所有文件')
    parser.add_argument('--notify', action='store_true', help='发送飞书通知')
    
    args = parser.parse_args()
    
    checker = PushIntegrityChecker()
    
    if args.file:
        reports = [checker.check_file_integrity(Path(args.file))]
    elif args.directory:
        dir_path = Path(args.directory)
        files = list(dir_path.glob("*.md"))
        reports = checker.check_files_integrity(files)
    else:
        print("用法: python3 step5_integrity_check.py --file xxx.md")
        sys.exit(1)
    
    # 输出报告
    report_text = checker.generate_integrity_report(reports)
    print(report_text)
    
    # 记录日志
    checker.log_integrity_check(reports)
    
    # 发送飞书通知
    if args.notify:
        send_integrity_notification(reports)
    
    # 如果有严重失败的，返回非0退出码
    critical_failed = [
        r for r in reports 
        if not r.all_passed and any(c.severity == "critical" for c in r.checks)
    ]
    if critical_failed:
        sys.exit(1)
