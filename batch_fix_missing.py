#!/usr/bin/env python3
"""
批量对话修复工具 - 处理所有缺失的日期
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from message_index import IndexManager
from process_incremental import check_missing_conversations, reset_index_to_date, process_incremental

def process_all_missing():
    """处理所有缺失的对话日期"""
    import time
    start_time = time.time()
    
    print("=" * 60)
    print("批量处理缺失的对话记录")
    print("=" * 60)
    
    processed_dates = []
    max_iterations = 10
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- 第 {iteration} 轮处理 ---")
        
        has_missing, missing_date, missing_ts = check_missing_conversations(days=7)
        
        if not has_missing:
            print("✅ 所有对话文件已补齐")
            break
        
        if missing_date in processed_dates:
            print(f"⚠️ 日期 {missing_date} 已处理过但未生成文件，可能存在数据问题")
            break
        
        print(f"检测到缺失: {missing_date}")
        
        manager = IndexManager()
        if not reset_index_to_date(manager, missing_ts, missing_date):
            print(f"❌ 重置索引失败")
            break
        
        success = process_incremental()
        
        if success:
            processed_dates.append(missing_date)
            print(f"✅ 已处理: {missing_date}")
        else:
            print(f"❌ 处理失败: {missing_date}")
            break
    
    duration = int((time.time() - start_time) * 1000)
    print(f"\n{'=' * 60}")
    print(f"处理完成: {len(processed_dates)} 个日期")
    print(f"耗时: {duration}ms")
    print(f"{'=' * 60}")
    
    return processed_dates

if __name__ == "__main__":
    dates = process_all_missing()
    print(f"\n已处理的日期: {dates}")
