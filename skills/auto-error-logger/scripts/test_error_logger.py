#!/usr/bin/env python3
"""
auto-error-logger 测试脚本

测试所有核心功能是否正常工作。
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

# 添加模块路径
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from auto_error_logger import (
    log_error,
    catch_errors,
    error_context,
    analyze_error_patterns
)


def test_manual_logging():
    """测试手动错误记录"""
    print("\n1. 测试手动错误记录...")
    
    try:
        raise ValueError("测试手动记录的错误")
    except Exception as e:
        error_id = log_error(
            exception=e,
            context="test_manual_logging",
            metadata={"test": True, "timestamp": datetime.now().isoformat()},
            notify=False
        )
        print(f"   ✅ 错误已记录: {error_id}")
    
    return True


def test_decorator():
    """测试装饰器"""
    print("\n2. 测试错误捕获装饰器...")
    
    @catch_errors(context="test_decorator", retry=2, retry_delay=0.1)
    def failing_function():
        raise ConnectionError("测试连接错误")
    
    try:
        failing_function()
    except ConnectionError:
        print("   ✅ 错误被捕获并重新抛出")
    
    return True


def test_decorator_success():
    """测试装饰器（正常情况）"""
    print("\n3. 测试装饰器（正常情况）...")
    
    @catch_errors(context="test_decorator_success")
    def success_function():
        return "success"
    
    result = success_function()
    if result == "success":
        print("   ✅ 正常执行不受影响")
        return True
    return False


def test_context_manager():
    """测试上下文管理器"""
    print("\n4. 测试上下文管理器...")
    
    # 正常情况
    with error_context("test_context_normal"):
        pass
    print("   ✅ 正常情况正常退出")
    
    # 异常情况
    try:
        with error_context("test_context_error", reraise=True):
            raise RuntimeError("测试上下文管理器错误")
    except RuntimeError:
        print("   ✅ 异常被捕获并重新抛出")
    
    return True


def test_context_manager_suppress():
    """测试上下文管理器（抑制异常）"""
    print("\n5. 测试上下文管理器（抑制异常）...")
    
    with error_context("test_context_suppress", reraise=False):
        raise RuntimeError("这个错误会被抑制")
    
    print("   ✅ 异常被抑制")
    return True


def test_error_analysis():
    """测试错误模式分析"""
    print("\n6. 测试错误模式分析...")
    
    analysis = analyze_error_patterns()
    
    if analysis.get("status") == "analyzed":
        print(f"   ✅ 分析完成")
        print(f"   - 错误类型数: {analysis.get('total_types', 0)}")
        if 'error_types' in analysis:
            print(f"   - 错误类型: {list(analysis['error_types'].keys())}")
        return True
    elif analysis.get("status") == "no_errors":
        print("   ⚠️  没有错误记录可分析")
        return True
    
    return False


def test_file_structure():
    """测试文件结构"""
    print("\n7. 测试文件结构...")
    
    required_files = [
        SCRIPTS_DIR / "auto_error_logger.py",
        SCRIPTS_DIR / "error_analyzer.py",
        SCRIPTS_DIR.parent / "SKILL.md"
    ]
    
    all_exist = True
    for f in required_files:
        if f.exists():
            print(f"   ✅ {f.name}")
        else:
            print(f"   ❌ {f.name} 不存在")
            all_exist = False
    
    return all_exist


def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("🧪 auto-error-logger 测试套件")
    print(f"⏰ {datetime.now().isoformat()}")
    print("="*60)
    
    tests = [
        ("文件结构检查", test_file_structure),
        ("手动错误记录", test_manual_logging),
        ("装饰器-失败", test_decorator),
        ("装饰器-成功", test_decorator_success),
        ("上下文管理器", test_context_manager),
        ("上下文管理器-抑制", test_context_manager_suppress),
        ("错误模式分析", test_error_analysis),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, "✅ PASS" if passed else "❌ FAIL"))
        except Exception as e:
            print(f"   ❌ 异常: {e}")
            results.append((name, f"❌ ERROR: {e}"))
    
    # 输出总结
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    for name, result in results:
        print(f"  {result}: {name}")
    
    passed = sum(1 for _, r in results if "PASS" in r)
    total = len(results)
    
    print(f"\n通过: {passed}/{total}")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)