#!/usr/bin/env python3
"""
验证step1修复 - 带完整日志
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 添加路径
sys.path.insert(0, '/root/.openclaw/workspace/second-brain-processor')
from step1_identify_essence import identify_essence

# 测试文件
test_file = Path('/root/.openclaw/workspace/obsidian-vault/02-Conversations/2026-03-24_对话记录.md')

print("=" * 70)
print("STEP1 修复验证")
print("=" * 70)
print(f"\n[1/3] 输入文件: {test_file}")
print(f"      大小: {test_file.stat().st_size} 字节")

# 读取输入内容（用于后续对比）
input_content = test_file.read_text(encoding='utf-8')
print(f"      内容: 包含Harness Engineering文章讨论")

print("\n" + "-" * 70)
print("[2/3] 调用AI分析...")
print("-" * 70)

start_time = time.time()

try:
    result = identify_essence(test_file)
    
    elapsed = time.time() - start_time
    
    print(f"\n✅ 分析完成")
    print(f"   耗时: {elapsed:.2f}秒")
    print(f"   识别主题数: {len(result.get('topics', []))}")
    
    print("\n" + "=" * 70)
    print("[3/3] 输出结果")
    print("=" * 70)
    
    if result.get('topics'):
        for i, topic in enumerate(result['topics'], 1):
            print(f"\n主题 {i}: {topic.get('name', '未命名')}")
            print(f"  核心观点: {topic.get('key_takeaway', '无')[:80]}...")
            print(f"  置信度: {topic.get('confidence', 'unknown')}")
            
            # 检查是否有详细观点
            points = topic.get('detailed_points', [])
            print(f"  详细观点数: {len(points)}")
            
            # 检查反思
            reflection = topic.get('reflection', '')
            print(f"  思考延伸: {'有' if reflection else '无'} ({len(reflection)}字符)")
    else:
        print("\n⚠️ 未识别到主题")
        print(f"总结: {result.get('summary', '无')}")
    
    # 记录完整日志
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "file": str(test_file),
        "file_size": test_file.stat().st_size,
        "elapsed_seconds": elapsed,
        "topics_count": len(result.get('topics', [])),
        "result": result
    }
    
    log_file = Path('/root/.openclaw/workspace/.learnings/step1_verify_log.json')
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 完整日志: {log_file}")
    
    # 验证检查
    print("\n" + "=" * 70)
    print("验证检查")
    print("=" * 70)
    
    checks = []
    
    # 检查1: 是否耗时合理（API调用应该需要几秒）
    if elapsed > 2:
        checks.append(("✅", f"耗时合理 ({elapsed:.2f}秒) - 可能真的调用了API"))
    else:
        checks.append(("⚠️", f"耗时过短 ({elapsed:.2f}秒) - 可能没有调用API"))
    
    # 检查2: 输出是否与输入相关
    if result.get('topics'):
        first_topic = result['topics'][0]
        topic_name = first_topic.get('name', '')
        
        # 检查是否包含Harness相关内容
        if 'harness' in topic_name.lower() or 'engineer' in topic_name.lower():
            checks.append(("✅", f"主题与输入相关: '{topic_name[:50]}'"))
        else:
            checks.append(("⚠️", f"主题可能不相关: '{topic_name[:50]}'"))
        
        # 检查3: 是否有原创内容（非硬编码）
        key_takeaway = first_topic.get('key_takeaway', '')
        if key_takeaway and len(key_takeaway) > 30:
            checks.append(("✅", f"核心观点有内容 ({len(key_takeaway)}字符)"))
        else:
            checks.append(("⚠️", f"核心观点过短"))
    else:
        checks.append(("❌", "未生成任何主题"))
    
    for status, msg in checks:
        print(f"{status} {msg}")
    
    print("\n" + "=" * 70)
    
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()
