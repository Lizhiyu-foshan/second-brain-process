#!/usr/bin/env python3
"""
系统论进化引擎 - 时间解析全面测试
测试所有时间处理边界情况
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/second-brain-processor')

from datetime import datetime, timedelta
from pathlib import Path

# 测试用例
TEST_CASES = [
    # (输入时间字符串, 描述, 是否应该成功)
    ("2026-03-13T10:49:19+08:00", "带+08:00时区", True),
    ("2026-03-13T16:06:04+08:00", "带+08:00时区", True),
    ("2026-03-13T16:16:27+08:00", "带+08:00时区", True),
    ("2026-03-13T16:48:38+08:00", "带+08:00时区", True),
    ("2026-03-13T10:49:19Z", "带Z结尾", True),
    ("2026-03-13 10:49:19", "无时区格式", True),
    ("2026-03-13T10:49:19+00:00", "带+00:00时区", True),
]

def test_time_parsing():
    """测试时间解析逻辑"""
    print("=" * 60)
    print("测试1: 时间解析逻辑")
    print("=" * 60)
    
    all_passed = True
    
    # 模拟get_recent_errors中的时间解析
    cutoff_time = datetime.now().astimezone() - timedelta(hours=24)
    print(f" cutoff_time: {cutoff_time}")
    print()
    
    for time_str, desc, should_succeed in TEST_CASES:
        try:
            # 复制实际代码中的逻辑
            time_str_clean = time_str.strip()
            if time_str_clean.endswith('Z'):
                time_str_clean = time_str_clean[:-1] + '+00:00'
            
            log_dt = datetime.fromisoformat(time_str_clean)
            if log_dt.tzinfo is None:
                log_dt = log_dt.astimezone()
            
            # 尝试比较
            is_recent = log_dt > cutoff_time
            
            print(f"✅ {desc}")
            print(f"   输入: {time_str}")
            print(f"   解析: {log_dt}")
            print(f"   时区: {log_dt.tzinfo}")
            print(f"   是否最近: {is_recent}")
            print()
            
        except Exception as e:
            print(f"❌ {desc}")
            print(f"   输入: {time_str}")
            print(f"   错误: {e}")
            print()
            if should_succeed:
                all_passed = False
    
    return all_passed

def test_cleanup_function():
    """测试清理函数的时间处理"""
    print("=" * 60)
    print("测试2: 清理函数时间处理")
    print("=" * 60)
    
    ERROR_RETENTION_DAYS = 30
    cutoff_time = datetime.now().astimezone() - timedelta(days=ERROR_RETENTION_DAYS)
    print(f" cutoff_time (30天前): {cutoff_time}")
    print()
    
    all_passed = True
    
    for time_str, desc, should_succeed in TEST_CASES:
        try:
            # 复制cleanup_old_errors中的逻辑
            time_str_clean = time_str.strip()
            if time_str_clean.endswith('Z'):
                time_str_clean = time_str_clean[:-1] + '+00:00'
            
            log_time = datetime.fromisoformat(time_str_clean)
            if log_time.tzinfo is None:
                log_time = log_time.astimezone()
            
            should_keep = log_time > cutoff_time
            
            print(f"✅ {desc}")
            print(f"   输入: {time_str}")
            print(f"   是否保留: {should_keep}")
            print()
            
        except Exception as e:
            print(f"❌ {desc}")
            print(f"   错误: {e}")
            print()
            if should_succeed:
                all_passed = False
    
    return all_passed

def test_edge_cases():
    """测试边界情况"""
    print("=" * 60)
    print("测试3: 边界情况")
    print("=" * 60)
    
    edge_cases = [
        ("", "空字符串"),
        ("invalid", "无效格式"),
        ("2026-13-45", "无效日期"),
        ("2026-03-13T25:00:00", "无效时间"),
    ]
    
    for time_str, desc in edge_cases:
        try:
            time_str_clean = time_str.strip()
            if time_str_clean.endswith('Z'):
                time_str_clean = time_str_clean[:-1] + '+00:00'
            
            log_dt = datetime.fromisoformat(time_str_clean)
            if log_dt.tzinfo is None:
                log_dt = log_dt.astimezone()
            
            print(f"⚠️ {desc} - 意外成功: {log_dt}")
            
        except Exception as e:
            print(f"✅ {desc} - 正确抛出异常: {type(e).__name__}")

def main():
    print("\n" + "=" * 60)
    print("系统论进化引擎 - 时间解析全面测试")
    print("=" * 60 + "\n")
    
    result1 = test_time_parsing()
    result2 = test_cleanup_function()
    test_edge_cases()
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    if result1 and result2:
        print("✅ 所有测试通过")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
