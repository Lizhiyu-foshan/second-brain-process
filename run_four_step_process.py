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
from step5_integrity_check import run_integrity_and_quality_check

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
    
    # Step 5: 质量检查 + 推送完整性验证（增强版）
    print("\n[Step 5/5] 质量检查 + 推送完整性验证...")
    quality_reports, integrity_reports = run_integrity_and_quality_check(
        files_to_push, 
        VAULT_DIR
    )
    
    # 汇总结果
    failed_quality = [r for r in quality_reports if not r.passed]
    failed_integrity = [r for r in integrity_reports if not r.all_passed]
    
    if failed_quality:
        print(f"\n⚠️ 发现 {len(failed_quality)} 个文件质量不通过")
        for r in failed_quality[:3]:  # 只显示前3个
            print(f"  - {r.file} ({r.score}分)")
    
    if failed_integrity:
        print(f"\n⚠️ 发现 {len(failed_integrity)} 个文件完整性检查存在问题")
        for r in failed_integrity[:3]:
            issues = [c.name for c in r.checks if not c.passed]
            print(f"  - {r.file}: {', '.join(issues)}")
    
    if not failed_quality and not failed_integrity:
        print(f"\n✅ 所有文件质量检查和完整性验证通过")

    # 生成完成通知消息
    msg_lines = ["✅ 四步法深度整理完成\n"]
    
    # 文件列表
    msg_lines.append("📁 生成文件:")
    for file_path, _ in files_to_push:
        msg_lines.append(f"  • {file_path.name}")
    
    msg_lines.append("")
    
    # 质量检查摘要
    if quality_reports:
        passed_q = sum(1 for r in quality_reports if r.passed)
        msg_lines.append(f"📊 质量检查: {passed_q}/{len(quality_reports)} 通过")
    
    # 完整性检查摘要
    if integrity_reports:
        passed_i = sum(1 for r in integrity_reports if r.all_passed)
        msg_lines.append(f"🔍 完整性验证: {passed_i}/{len(integrity_reports)} 通过")
    
    # 如果有问题，添加提示
    if failed_quality or failed_integrity:
        msg_lines.append("")
        msg_lines.append("⚠️ 注意:")
        if failed_quality:
            msg_lines.append(f"  - {len(failed_quality)} 个文件质量需要优化")
        if failed_integrity:
            critical = sum(
                1 for r in failed_integrity 
                if any(c.severity == "critical" for c in r.checks)
            )
            if critical > 0:
                msg_lines.append(f"  - {critical} 个文件存在严重完整性问题（需立即处理）")
            else:
                msg_lines.append(f"  - {len(failed_integrity)} 个文件存在轻微完整性问题")
        msg_lines.append("  查看 .learnings/*_report_*.md 获取详细信息")
    
    msg = "\n".join(msg_lines)
    
    print(f"\n[{datetime.now()}] === 四步法完成 (含质量检查+完整性验证) ===")
    
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
