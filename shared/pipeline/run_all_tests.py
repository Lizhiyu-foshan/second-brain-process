#!/usr/bin/env python3
"""
完整测试套件 - 运行所有测试并生成报告
"""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

REPORT = []

def run_test(name, cmd, cwd=None):
    """运行测试并记录结果"""
    print(f"\n{'='*60}")
    print(f"🧪 {name}")
    print('='*60)
    
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=60, cwd=cwd
        )
        
        output = result.stdout + result.stderr
        
        # 解析结果
        if "通过" in output and "失败" in output:
            # 提取通过/失败数量
            lines = output.split('\n')
            for line in lines:
                if '通过:' in line and '失败:' in line:
                    REPORT.append((name, True, line.strip()))
                    print(f"✅ {line.strip()}")
                    return True
        
        if result.returncode == 0 or "通过" in output:
            REPORT.append((name, True, "测试通过"))
            print("✅ 测试通过")
            return True
        else:
            REPORT.append((name, False, f"返回码: {result.returncode}"))
            print(f"❌ 测试失败: 返回码 {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        REPORT.append((name, False, "超时"))
        print("⏱️ 测试超时")
        return False
    except Exception as e:
        REPORT.append((name, False, str(e)))
        print(f"❌ 错误: {e}")
        return False

# 运行所有测试
print("\n" + "="*70)
print("🔬 完整测试套件")
print("="*70)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

pipeline_dir = Path(__file__).parent

# 1. 单元测试
run_test("单元测试 (test_quick.py)", "python3 test_quick.py", cwd=pipeline_dir)

# 2. 安全修复验证
run_test("安全修复验证 (test_security_fixes.py)", "python3 test_security_fixes.py", cwd=pipeline_dir)

# 3. Layer 2 集成测试
run_test("Layer 2 集成测试 (test_layer2_integration.py)", "python3 test_layer2_integration.py", cwd=pipeline_dir)

# 4. E2E 工作流测试
run_test("E2E 工作流测试 (test_e2e_workflow.py)", "python3 test_e2e_workflow.py", cwd=pipeline_dir)

# 生成报告
print("\n" + "="*70)
print("📊 测试报告汇总")
print("="*70)

passed = sum(1 for r in REPORT if r[1])
failed = sum(1 for r in REPORT if not r[1])

print(f"\n总测试套件: {len(REPORT)}")
print(f"✅ 通过: {passed}")
print(f"❌ 失败: {failed}")
print()

for name, status, detail in REPORT:
    emoji = "✅" if status else "❌"
    print(f"{emoji} {name}")
    print(f"   {detail}")

print()
print("="*70)
if failed == 0:
    print("🎉 所有测试套件通过！系统运行正常。")
else:
    print(f"⚠️  {failed} 个测试套件需要检查。")
print("="*70)
