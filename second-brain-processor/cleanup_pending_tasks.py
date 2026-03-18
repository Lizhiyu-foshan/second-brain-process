#!/usr/bin/env python3
"""
清理AI分析pending任务队列

用途：
1. 清理历史堆积的pending任务（修复前遗留）
2. 作为独立脚本批量处理待分析任务（备用方案）

使用方法：
    python3 cleanup_pending_tasks.py --clean      # 清理所有pending任务
    python3 cleanup_pending_tasks.py --process    # 批量处理所有pending任务
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

PENDING_DIR = Path("/tmp/ai_analysis_pending")

def log(message: str):
    """日志输出"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def clean_pending_tasks():
    """清理所有pending任务"""
    if not PENDING_DIR.exists():
        log("✅ pending目录不存在，无需清理")
        return 0
    
    task_files = list(PENDING_DIR.glob("*.json"))
    if not task_files:
        log("✅ 没有pending任务需要清理")
        return 0
    
    log(f"🧹 发现 {len(task_files)} 个pending任务，开始清理...")
    
    for task_file in task_files:
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            task_id = task_data.get('task_id', 'unknown')
            title = task_data.get('title', 'unknown')
            created_at = task_data.get('created_at', 'unknown')
            
            # 删除任务文件
            task_file.unlink()
            log(f"  已清理: {task_id} - {title[:30]}... (创建于 {created_at})")
            
        except Exception as e:
            log(f"  ⚠️ 清理失败 {task_file.name}: {e}")
    
    log(f"✅ 清理完成，共清理 {len(task_files)} 个任务")
    return len(task_files)

def process_pending_tasks():
    """批量处理所有pending任务（备用方案）"""
    if not PENDING_DIR.exists():
        log("⚠️ pending目录不存在")
        return 0
    
    task_files = list(PENDING_DIR.glob("*.json"))
    if not task_files:
        log("✅ 没有pending任务需要处理")
        return 0
    
    log(f"🤖 发现 {len(task_files)} 个pending任务，开始批量处理...")
    
    # 导入AI处理器
    sys.path.insert(0, str(Path(__file__).parent))
    from ai_deep_processor import process_conversation_with_ai
    
    processed = 0
    failed = 0
    
    for task_file in task_files:
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            task_id = task_data.get('task_id', 'unknown')
            title = task_data.get('title', 'unknown')
            content = task_data.get('content', '')
            
            log(f"  处理: {task_id} - {title[:30]}...")
            
            # 调用AI分析
            result = process_conversation_with_ai(content, title)
            
            # 更新任务状态
            task_data['status'] = 'completed'
            task_data['result'] = result
            task_data['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 保存结果
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, ensure_ascii=False, indent=2)
            
            log(f"    ✅ 完成: {result.get('key_takeaway', 'N/A')[:50]}...")
            processed += 1
            
        except Exception as e:
            log(f"    ❌ 失败: {e}")
            failed += 1
    
    log(f"✅ 批量处理完成: 成功 {processed}, 失败 {failed}")
    return processed

def main():
    parser = argparse.ArgumentParser(description='清理AI分析pending任务')
    parser.add_argument('--clean', action='store_true', help='清理所有pending任务')
    parser.add_argument('--process', action='store_true', help='批量处理所有pending任务')
    
    args = parser.parse_args()
    
    if args.clean:
        clean_pending_tasks()
    elif args.process:
        process_pending_tasks()
    else:
        # 默认显示状态
        if not PENDING_DIR.exists():
            print("pending目录不存在")
            return
        
        task_files = list(PENDING_DIR.glob("*.json"))
        print(f"当前pending任务数量: {len(task_files)}")
        
        for task_file in task_files:
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    task_data = json.load(f)
                print(f"  - {task_data.get('task_id', 'unknown')}: {task_data.get('title', 'unknown')[:40]}... ({task_data.get('status', 'unknown')})")
            except:
                print(f"  - {task_file.name}: 无法读取")

if __name__ == "__main__":
    main()
