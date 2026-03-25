#!/usr/bin/env python3
"""
质量检查快捷脚本 - 检查最近整理的精华文档质量
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加处理器路径
sys.path.insert(0, str(Path(__file__).parent))

from step5_quality_check import EssenceQualityChecker

def main():
    """检查最近3天的精华质量"""
    checker = EssenceQualityChecker()
    
    # 检查最近3天
    reports = []
    for i in range(3):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_reports = checker.check_date_files(date)
        reports.extend(day_reports)
    
    if not reports:
        print("📭 最近3天没有精华文档")
        return
    
    print(f"\n📊 质量检查报告 (最近3天，共{len(reports)}个文件)\n")
    print("="*60)
    
    for report in reports:
        status = "✅ 通过" if report.passed else "❌ 需修复"
        print(f"\n{report.file}")
        print(f"  状态: {status} | 得分: {report.score}/100")
        
        if report.issues:
            print("  问题:")
            for issue in report.issues[:3]:
                emoji = "🔴" if issue.severity == "critical" else "🟡"
                print(f"    {emoji} {issue.check_item}")
    
    print("\n" + "="*60)
    
    failed = [r for r in reports if not r.passed]
    if failed:
        print(f"\n⚠️  共 {len(failed)} 个文件需要优化")
        print("\n建议操作:")
        print("1. 查看详细报告: .learnings/quality_report_*.md")
        print("2. 手动修复或重新整理")
    else:
        print(f"\n✅ 所有文件质量检查通过！")

if __name__ == "__main__":
    main()
