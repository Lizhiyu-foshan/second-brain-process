#!/usr/bin/env python3
"""
手动补发每日复盘报告（包含自我进化）
用于修复之前缺失的自我进化复盘部分
"""

import subprocess
import sys
from datetime import datetime

def main():
    print(f"[{datetime.now()}] 开始补发完整复盘报告...")
    
    # 1. 生成报告
    result = subprocess.run([
        'python3',
        '/root/.openclaw/workspace/second-brain-processor/daily_complete_report.py'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[ERROR] 生成报告失败：{result.stderr}")
        sys.exit(1)
    
    report = result.stdout
    
    # 2. 显示报告
    print("\n" + "="*60)
    print("📊 完整复盘报告")
    print("="*60)
    print(report)
    
    # 3. 提取报告内容（去掉日志行）
    report_content = ""
    for line in report.split('\n'):
        if line.startswith('📊') or line.startswith('📅') or line.startswith('💡') or line.startswith('🔗') or line.startswith('⚠️') or line.startswith('  •') or line.startswith('='):
            report_content += line + '\n'
    
    print("\n✅ 报告已生成，包含：")
    print("   - 对话整理统计")
    print("   - 文章整理统计")
    print("   - 自我进化复盘（错误、学习、改进）")
    print(f"\n📁 保存位置：/root/.openclaw/workspace/.learnings/daily_report.md")
    print(f"\n⏰ 下次自动推送时间：明天 8:30")
    
    return report_content

if __name__ == "__main__":
    main()
