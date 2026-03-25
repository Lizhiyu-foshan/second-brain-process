#!/usr/bin/env python3
"""
run_four_step_process.py - v2.1 四步法主控
协调四个步骤完成深度整理
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

# 导入各步骤
from step1_identify_essence import identify_essence
from step2_generate_essence import generate_essence_doc
from step3_organize_remainder import organize_remainder
from step4_push_to_github import push_to_github, send_completion_notification
from step5_quality_check import EssenceQualityChecker

VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
DISCUSSIONS_DIR = VAULT_DIR / "01-Discussions"
CONVERSATIONS_DIR = VAULT_DIR / "02-Conversations"


def run_four_step_process(
    content: str = None,
    content_file: Path = None,
    source_type: str = "原始对话",
    source_url: str = None
) -> str:
    """
    运行四步法深度整理
    
    Args:
        content: 直接传入内容（文章自动处理）
        content_file: 内容文件路径
        source_type: 来源类型
        source_url: 来源URL
        
    Returns:
        处理结果消息
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    print(f"[{datetime.now()}] === 启动四步法深度整理 ===")
    
    # 确定输入
    if content_file:
        input_file = content_file
    elif content:
        # 临时保存内容到文件
        temp_file = Path("/tmp/temp_content.md")
        temp_file.write_text(content, encoding='utf-8')
        input_file = temp_file
    else:
        return "❌ 错误：未提供内容或文件"
    
    # Step 1: 识别主题精华
    print("\n[Step 1/4] 识别主题精华...")
    step1_result = identify_essence(input_file)
    topics = step1_result.get("topics", [])
    
    if not topics:
        print("[INFO] 未识别到主题讨论精华，按普通讨论处理")
        # 普通讨论直接整理
        output_file = CONVERSATIONS_DIR / f"{date_str}_对话记录.md"
        organize_remainder(input_file, [], output_file)
        push_to_github([(output_file, output_file.read_text())], str(input_file))
        return "✅ 普通讨论已整理并推送"
    
    print(f"[Step 1] 识别到 {len(topics)} 个主题")
    
    # 准备生成的文件
    files_to_push: List[Tuple[Path, str]] = []
    all_fragments = []
    
    # Step 2: 生成每个主题的精华文档
    print("\n[Step 2/4] 生成主题精华文档...")
    for topic in topics:
        doc = generate_essence_doc(topic, date_str)
        
        # 文件名：主题_日期.md
        safe_name = topic.get("name", "未命名").replace(" ", "_")[:20]
        output_file = DISCUSSIONS_DIR / f"{safe_name}_{date_str}.md"
        
        files_to_push.append((output_file, doc))
        all_fragments.extend(topic.get("fragments", []))
        print(f"[Step 2] 生成: {output_file.name}")
    
    # Step 3: 整理剩余内容
    print("\n[Step 3/4] 整理剩余对话...")
    remainder_file = CONVERSATIONS_DIR / f"{date_str}_对话记录.md"
    organize_remainder(input_file, all_fragments, remainder_file)
    
    # 读取生成的文件内容
    if remainder_file.exists():
        files_to_push.append((remainder_file, remainder_file.read_text()))
    
    # Step 4: 推送GitHub
    print("\n[Step 4/5] 推送GitHub...")
    success = push_to_github(files_to_push, str(input_file))
    
    if not success:
        return "❌ 推送失败"
    
    # Step 5: 质量检查闭环
    print("\n[Step 5/5] 质量检查闭环...")
    checker = EssenceQualityChecker(VAULT_DIR)
    quality_reports = []
    
    for file_path, _ in files_to_push:
        if "01-Discussions" in str(file_path):
            report = checker.check_file(file_path)
            quality_reports.append(report)
            status = "✅" if report.passed else "❌"
            print(f"  {status} {file_path.name}: {report.score}分")
    
    # 记录质量日志
    if quality_reports:
        checker.log_quality_check(quality_reports)
    
    # 生成质量报告
    failed_reports = [r for r in quality_reports if not r.passed]
    
    if failed_reports:
        print(f"\n⚠️ 发现 {len(failed_reports)} 个文件质量不通过，需要修复:")
        for r in failed_reports:
            print(f"  - {r.file} ({r.score}分)")
            for issue in r.issues[:2]:  # 只显示前2个问题
                print(f"    • {issue.check_item}: {issue.description}")
        
        # 生成详细报告供参考
        quality_report_text = checker.generate_quality_report(quality_reports)
        report_file = VAULT_DIR / ".learnings" / f"quality_report_{date_str}.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(quality_report_text, encoding='utf-8')
        print(f"\n详细质量报告: {report_file}")
    else:
        print(f"\n✅ 所有精华文档质量检查通过")
    
    msg = send_completion_notification(files_to_push)
    print(f"\n[{datetime.now()}] === 四步法完成 (含质量检查) ===")
    
    # 如果有质量问题，在消息中提示
    if failed_reports:
        msg += f"\n\n⚠️ 注意: {len(failed_reports)} 个精华文档质量需要优化，详见 .learnings/quality_report_{date_str}.md"
    
    return msg


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="四步法深度整理")
    parser.add_argument("--file", help="输入文件路径")
    parser.add_argument("--source-type", default="原始对话")
    args = parser.parse_args()
    
    if args.file:
        result = run_four_step_process(content_file=Path(args.file), source_type=args.source_type)
        print(result)
    else:
        print("用法: python3 run_four_step_process.py --file 对话文件.md")
