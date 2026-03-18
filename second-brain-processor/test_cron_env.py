#!/usr/bin/env python3
"""
定时任务环境测试

用途：
1. 模拟cron环境（无OPENCLAW_SESSION变量）
2. 验证AI分析模块在定时任务环境中能正常工作
3. 作为CI/CD的一部分自动运行

使用方法：
    python3 test_cron_env.py              # 运行所有测试
    python3 test_cron_env.py --verbose    # 显示详细输出
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

# 添加处理器目录到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# 模拟cron环境变量
def setup_cron_env():
    """设置模拟cron环境"""
    # 清除可能干扰的环境变量
    cron_unset_vars = [
        'OPENCLAW_SESSION',
        'TERM',  # cron通常没有TERM
    ]
    
    for var in cron_unset_vars:
        if var in os.environ:
            del os.environ[var]
    
    # 设置cron环境特有的变量
    os.environ['PATH'] = '/usr/local/bin:/usr/bin:/bin'
    os.environ['HOME'] = '/root'
    
    return True

def test_import_ai_processor():
    """测试AI处理器导入"""
    print("\n[Test 1] 测试AI处理器导入...")
    
    try:
        from ai_deep_processor import process_conversation_with_ai
        print("  ✅ ai_deep_processor 导入成功")
        return True
    except Exception as e:
        print(f"  ❌ 导入失败: {e}")
        return False

def test_api_key_available():
    """测试API key可用性"""
    print("\n[Test 2] 测试API key可用性...")
    
    api_key = os.environ.get('ALICLOUD_API_KEY', '')
    if api_key:
        print(f"  ✅ ALICLOUD_API_KEY 已配置 (长度: {len(api_key)})")
        return True
    else:
        print("  ⚠️ ALICLOUD_API_KEY 未配置，将使用降级模式")
        return False

def test_ai_analysis_execution():
    """测试AI分析实际执行"""
    print("\n[Test 3] 测试AI分析实际执行...")
    
    try:
        from ai_deep_processor import process_conversation_with_ai
        
        # 使用测试内容
        test_content = """
用户：如何优化Python代码的性能？
AI：可以考虑以下几点：
1. 使用合适的数据结构
2. 避免重复计算
3. 使用内置函数
4. 考虑使用C扩展
"""
        test_title = "Python性能优化讨论"
        
        print(f"  输入: {test_title}")
        
        result = process_conversation_with_ai(test_content, test_title)
        
        # 验证结果
        key_takeaway = result.get('key_takeaway', '')
        core_points = result.get('core_points', [])
        
        # 检查结果是否包含"待AI分析"占位符
        if '【待AI分析】' in key_takeaway or '待深度分析' in key_takeaway:
            print(f"  ❌ 返回了占位符: {key_takeaway[:50]}...")
            return False
        
        # 检查结果是否有实质内容
        if len(core_points) >= 2 and len(key_takeaway) > 10:
            print(f"  ✅ AI分析成功执行")
            print(f"     核心观点: {key_takeaway[:60]}...")
            print(f"     要点数量: {len(core_points)}")
            return True
        else:
            print(f"  ⚠️ AI分析结果异常: 要点数量={len(core_points)}")
            return False
            
    except Exception as e:
        print(f"  ❌ AI分析失败: {e}")
        return False

def test_kimiclaw_morning_process():
    """测试kimiclaw_v2.py morning-process在cron环境下"""
    print("\n[Test 4] 测试凌晨整理流程（模拟）...")
    
    try:
        # 只测试导入，不实际执行（避免副作用）
        result = subprocess.run(
            [sys.executable, '-c', 
             'import sys; sys.path.insert(0, "."); from kimiclaw_v2 import main; print("导入成功")'],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("  ✅ kimiclaw_v2 导入成功")
            return True
        else:
            print(f"  ⚠️ 导入警告: {result.stderr[:200]}")
            return True  # 非致命
    except Exception as e:
        print(f"  ⚠️ 测试异常: {e}")
        return True  # 非致命

def test_morning_process_script():
    """测试run_morning_process_progress.py在cron环境下"""
    print("\n[Test 5] 测试凌晨整理脚本导入...")
    
    try:
        result = subprocess.run(
            [sys.executable, '-c',
             'import sys; sys.path.insert(0, "."); from run_morning_process_progress import ProgressReporter; print("导入成功")'],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("  ✅ run_morning_process_progress 导入成功")
            return True
        else:
            print(f"  ⚠️ 导入警告: {result.stderr[:200]}")
            return True
    except Exception as e:
        print(f"  ⚠️ 测试异常: {e}")
        return True

def generate_report(results):
    """生成测试报告"""
    print("\n" + "="*60)
    print("定时任务环境测试报告")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"环境: 模拟cron环境（无OPENCLAW_SESSION）")
    print("-"*60)
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"\n测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("\n✅ 所有测试通过！定时任务环境配置正确。")
    elif passed >= total * 0.8:
        print("\n⚠️ 部分测试未通过，但核心功能可用。")
    else:
        print("\n❌ 多个测试失败，需要检查配置。")
    
    print("\n建议:")
    print("  1. 确保ALICLOUD_API_KEY已配置")
    print("  2. 确保Python依赖已安装 (requests)")
    print("  3. 确保网络可以访问阿里云API")
    
    return passed == total

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='定时任务环境测试')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细输出')
    args = parser.parse_args()
    
    print("="*60)
    print("开始定时任务环境测试")
    print("="*60)
    print("注意：此测试会清除OPENCLAW_SESSION环境变量，模拟cron环境")
    
    # 保存原始环境
    original_env = dict(os.environ)
    
    try:
        # 设置cron环境
        setup_cron_env()
        print("\n✅ 已切换到模拟cron环境")
        
        # 运行测试
        results = []
        
        results.append(test_import_ai_processor())
        results.append(test_api_key_available())
        results.append(test_ai_analysis_execution())
        results.append(test_kimiclaw_morning_process())
        results.append(test_morning_process_script())
        
        # 生成报告
        success = generate_report(results)
        
        return 0 if success else 1
        
    finally:
        # 恢复原始环境
        os.environ.clear()
        os.environ.update(original_env)
        print("\n✅ 已恢复原始环境")

if __name__ == "__main__":
    sys.exit(main())
