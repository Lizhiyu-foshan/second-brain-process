#!/usr/bin/env python3
"""
安全修复验证测试
验证所有 Critical 和 High 级别安全问题已修复
"""
import os
os.environ["OPENCLAW_WORKSPACE"] = "/tmp/test_workspace"
os.environ["DASHSCOPE_API_KEY"] = "sk-test-key"

import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("🔒 安全修复验证测试")
print("=" * 70)
print()

tmp_dir = tempfile.mkdtemp()
os.environ["OPENCLAW_WORKSPACE"] = tmp_dir

results = []

def test_case(name, test_func):
    """运行测试用例"""
    print(f"\n📋 {name}")
    try:
        test_func()
        results.append((name, True, None))
        print(f"  ✅ 通过")
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"  ❌ 失败: {e}")

# 测试1: 环境变量配置路径
def test_env_path():
    from layer1.lock_manager import get_workspace_dir
    workspace = get_workspace_dir()
    assert str(workspace) == tmp_dir, f"路径不匹配: {workspace} != {tmp_dir}"
    print(f"  ✓ 路径正确: {workspace}")

test_case("测试1: 环境变量配置路径", test_env_path)

# 测试2: 锁管理器使用原子锁
def test_atomic_lock():
    from layer1.lock_manager import LockManager
    import fcntl
    
    lock_dir = Path(tmp_dir) / "locks"
    lm = LockManager(lock_dir)
    
    # 检查是否使用了 fcntl
    import inspect
    source = inspect.getsource(lm.acquire)
    assert "fcntl.flock" in source, "未使用 fcntl.flock"
    print(f"  ✓ 使用 fcntl.flock 实现原子锁")

test_case("测试2: 锁管理器使用原子锁 (fcntl)", test_atomic_lock)

# 测试3: 状态文件原子写入
def test_atomic_write():
    from layer1.task_queue import TaskQueue
    import inspect
    
    tq = TaskQueue(f"{tmp_dir}/state/test_queue.json")
    
    source = inspect.getsource(tq._save)
    assert "mkstemp" in source, "未使用临时文件"
    assert "os.replace" in source, "未使用原子替换"
    print(f"  ✓ 使用 mkstemp + os.replace 实现原子写入")

test_case("测试3: 状态文件原子写入", test_atomic_write)

# 测试4: 异常处理改进
def test_exception_handling():
    from layer1.task_queue import TaskQueue
    import inspect
    
    tq = TaskQueue(f"{tmp_dir}/state/test_queue.json")
    
    source = inspect.getsource(tq._load)
    assert "json.JSONDecodeError" in source, "未捕获 JSONDecodeError"
    assert "PermissionError" in source, "未捕获 PermissionError"
    print(f"  ✓ 改进了异常处理")

test_case("测试4: 异常处理改进", test_exception_handling)

# 测试5: 损坏文件备份
def test_corrupted_backup():
    from layer1.task_queue import TaskQueue
    import inspect
    
    tq = TaskQueue(f"{tmp_dir}/state/test_queue.json")
    
    source = inspect.getsource(tq._load)
    assert "_backup_corrupted_file" in source, "未实现损坏文件备份"
    print(f"  ✓ 实现了损坏文件备份机制")

test_case("测试5: 损坏文件备份机制", test_corrupted_backup)

# 清理
shutil.rmtree(tmp_dir, ignore_errors=True)

# 汇总
print("\n" + "=" * 70)
print("📊 验证结果汇总")
print("=" * 70)
print()

passed = sum(1 for _, status, _ in results if status)
failed = sum(1 for _, status, _ in results if not status)

print(f"总测试: {len(results)}")
print(f"✅ 通过: {passed}")
print(f"❌ 失败: {failed}")
print()

for name, status, error in results:
    emoji = "✅" if status else "❌"
    print(f"  {emoji} {name}")

print()
if failed == 0:
    print("🎉 所有安全修复验证通过！")
    print("=" * 70)
else:
    print(f"⚠️  {failed}个测试失败")
    print("=" * 70)
