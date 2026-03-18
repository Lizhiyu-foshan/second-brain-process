#!/usr/bin/env python3
"""
BMAD-EVO 批量审计脚本
审计 second-brain-processor 项目的所有 Python 文件
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# 添加 BMAD-EVO 路径
sys.path.insert(0, '/root/.openclaw/skills/bmad-evo/lib')

from ast_auditor import audit_file, ASTSeverity

def audit_project(project_path: str, output_file: str = None):
    """审计项目中的所有 Python 文件"""
    
    project_dir = Path(project_path)
    
    # 统计信息
    stats = {
        'total_files': 0,
        'files_with_issues': 0,
        'total_violations': 0,
        'by_severity': {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        },
        'files': []
    }
    
    # 查找所有 Python 文件
    py_files = list(project_dir.rglob('*.py'))
    stats['total_files'] = len(py_files)
    
    print(f"🔍 开始审计项目：{project_path}")
    print(f"📊 发现 {len(py_files)} 个 Python 文件\n")
    
    # 审计每个文件
    for py_file in sorted(py_files):
        # 跳过虚拟环境、缓存目录和隐藏目录（但允许 .openclaw 工作区）
        relative_parts = py_file.relative_to(project_dir).parts
        if any(part.startswith('.') and part != '.bmad' or part == '__pycache__' for part in relative_parts):
            continue
        
        try:
            result = audit_file(str(py_file))
            
            if result.violations:
                stats['files_with_issues'] += 1
                stats['total_violations'] += len(result.violations)
                
                # 按严重程度统计
                for violation in result.violations:
                    severity = violation.severity.value
                    stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
                
                # 记录文件详情
                file_info = {
                    'file': str(py_file.relative_to(project_dir)),
                    'violations': len(result.violations),
                    'passed': result.passed,
                    'details': [
                        {
                            'severity': v.severity.value,
                            'rule': v.rule_type.value,
                            'line': v.line_number,
                            'description': v.description
                        }
                        for v in result.violations
                    ]
                }
                stats['files'].append(file_info)
                
                # 输出进度
                severity_summary = {
                    '🔴 CRITICAL': sum(1 for v in result.violations if v.severity == ASTSeverity.CRITICAL),
                    '🟠 HIGH': sum(1 for v in result.violations if v.severity == ASTSeverity.HIGH),
                    '🟡 MEDIUM': sum(1 for v in result.violations if v.severity == ASTSeverity.MEDIUM),
                    '🟢 LOW': sum(1 for v in result.violations if v.severity == ASTSeverity.LOW),
                }
                
                critical_high = severity_summary['🔴 CRITICAL'] + severity_summary['🟠 HIGH']
                if critical_high > 0:
                    print(f"  ❌ {py_file.relative_to(project_dir)}")
                    print(f"     {severity_summary['🔴 CRITICAL']} CRITICAL, {severity_summary['🟠 HIGH']} HIGH")
                else:
                    print(f"  ⚠️  {py_file.relative_to(project_dir)} - {len(result.violations)} 个问题")
            else:
                print(f"  ✅ {py_file.relative_to(project_dir)}")
                
        except Exception as e:
            print(f"  ⚠️  {py_file.relative_to(project_dir)} - 审计失败：{e}")
    
    # 输出统计
    print("\n" + "="*60)
    print("📊 审计统计")
    print("="*60)
    print(f"总文件数：{stats['total_files']}")
    print(f"有问题文件：{stats['files_with_issues']} ({stats['files_with_issues']/stats['total_files']*100:.1f}%)")
    print(f"总违规数：{stats['total_violations']}")
    print(f"  🔴 CRITICAL: {stats['by_severity'].get('critical', 0)}")
    print(f"  🟠 HIGH: {stats['by_severity'].get('high', 0)}")
    print(f"  🟡 MEDIUM: {stats['by_severity'].get('medium', 0)}")
    print(f"  🟢 LOW: {stats['by_severity'].get('low', 0)}")
    
    # 保存结果
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 详细结果已保存到：{output_path}")
    
    return stats


if __name__ == '__main__':
    # 项目路径
    project_path = '/root/.openclaw/workspace/second-brain-processor'
    
    # 输出文件
    output_file = '/root/.openclaw/workspace/second-brain-processor/.bmad/batch-audit-result.json'
    
    # 执行审计
    stats = audit_project(project_path, output_file)
    
    # 退出码
    sys.exit(0 if stats['total_violations'] == 0 else 1)
