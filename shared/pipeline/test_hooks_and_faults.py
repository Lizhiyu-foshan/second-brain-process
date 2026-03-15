#!/usr/bin/env python3
"""
测试钩子系统和故障注入器测试
验证 hooks 和 fault injection 功能正常工作
"""
import sys
import os
import time
import threading
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.test_hooks import TestHooks, HookPoint, hooks
from shared.fault_injection import FaultInjector, FaultType, FaultContext, injector
from layer1.lock_manager import LockManager
from layer1.task_queue import TaskQueue
from layer2.orchestrator import Orchestrator
from shared.models import Task


def test_hooks_registration():
    """测试钩子注册"""
    print("\n=== Test 1: Hooks Registration ===")
    
    hooks.clear_history()
    hooks.unregister_all()
    
    triggered = []
    
    def callback(context):
        triggered.append(context.hook_point.value)
        print(f"  Hook triggered: {context.hook_point.value}")
    
    # 注册钩子
    hooks.register(HookPoint.LOCK_BEFORE_ACQUIRE, callback)
    hooks.register(HookPoint.LOCK_AFTER_ACQUIRE, callback)
    
    # 触发钩子
    hooks.trigger(HookPoint.LOCK_BEFORE_ACQUIRE, role_id="test_role")
    hooks.trigger(HookPoint.LOCK_AFTER_ACQUIRE, role_id="test_role", success=True)
    
    # 验证
    assert len(triggered) == 2, f"Expected 2 triggers, got {len(triggered)}"
    assert "lock:before_acquire" in triggered
    assert "lock:after_acquire" in triggered
    
    print("  ✅ Hooks registration test passed")
    return True


def test_hooks_history():
    """测试钩子历史记录"""
    print("\n=== Test 2: Hooks History ===")
    
    hooks.clear_history()
    hooks.unregister_all()
    
    def callback(ctx):
        pass
    
    hooks.register(HookPoint.TASK_BEFORE_SUBMIT, callback)
    
    # 触发多次
    for i in range(5):
        hooks.trigger(HookPoint.TASK_BEFORE_SUBMIT, task_id=f"task_{i}")
    
    history = hooks.get_call_history()
    assert len(history) == 5, f"Expected 5 history entries, got {len(history)}"
    
    # 测试特定点的历史
    task_history = hooks.get_call_history(HookPoint.TASK_BEFORE_SUBMIT)
    assert len(task_history) == 5
    
    print("  ✅ Hooks history test passed")
    return True


def test_fault_injection_crash():
    """测试故障注入：崩溃"""
    print("\n=== Test 3: Fault Injection - Crash ===")
    
    injector.clear()
    
    # 注入崩溃故障
    injector.inject(
        FaultType.CRASH,
        "test.component",
        probability=1.0,
        exception_type=RuntimeError,
        error_message="Injected crash fault"
    )
    
    injector.enable()
    
    try:
        fault_config = injector.try_inject("test.component")
        if fault_config:
            injector.apply_fault(fault_config)
        assert False, "Should have raised exception"
    except RuntimeError as e:
        assert "Injected crash fault" in str(e)
        print(f"  ✅ Crash fault caught: {e}")
    finally:
        injector.disable()
    
    return True


def test_fault_injection_delay():
    """测试故障注入：延迟"""
    print("\n=== Test 4: Fault Injection - Delay ===")
    
    injector.clear()
    
    # 注入延迟故障
    injector.inject(
        FaultType.DELAY,
        "test.component",
        probability=1.0,
        duration_ms=500  # 500ms 延迟
    )
    
    injector.enable()
    
    start = time.time()
    fault_config = injector.try_inject("test.component")
    if fault_config:
        injector.apply_fault(fault_config)
    elapsed = time.time() - start
    
    injector.disable()
    
    assert elapsed >= 0.5, f"Expected delay >= 0.5s, got {elapsed}s"
    print(f"  ✅ Delay fault applied: {elapsed:.3f}s")
    
    return True


def test_fault_injection_probability():
    """测试故障注入概率"""
    print("\n=== Test 5: Fault Injection - Probability ===")
    
    injector.clear()
    
    # 注入 50% 概率故障
    injector.inject(
        FaultType.ERROR,
        "test.component",
        probability=0.5
    )
    
    injector.enable()
    
    triggered = 0
    total = 100
    
    for _ in range(total):
        fault_config = injector.try_inject("test.component")
        if fault_config:
            triggered += 1
    
    injector.disable()
    
    # 50% 概率，100次应该触发约 50 次（允许较大误差范围）
    assert 30 <= triggered <= 70, f"Expected ~50 triggers, got {triggered}"
    print(f"  ✅ Probability test: {triggered}/{total} triggered (~{triggered}%)")
    
    return True


def test_fault_context():
    """测试故障注入上下文管理器"""
    print("\n=== Test 6: Fault Context Manager ===")
    
    # 使用上下文管理器
    with FaultContext() as fc:
        fc.inject(FaultType.DELAY, "test.context", duration_ms=100)
        
        # 验证已启用
        assert injector.is_enabled()
        
        fault_config = injector.try_inject("test.context")
        assert fault_config is not None
        print("  ✅ Fault context active")
    
    # 验证已禁用
    assert not injector.is_enabled()
    print("  ✅ Fault context auto-disabled")
    
    return True


def test_lock_manager_hooks():
    """测试 LockManager 钩子触发"""
    print("\n=== Test 7: LockManager Hooks ===")
    
    hooks.clear_history()
    hooks.unregister_all()
    
    triggered = []
    
    def on_acquire(ctx):
        triggered.append("acquire")
    
    def on_release(ctx):
        triggered.append("release")
    
    hooks.register(HookPoint.LOCK_AFTER_ACQUIRE, on_acquire)
    hooks.register(HookPoint.LOCK_AFTER_RELEASE, on_release)
    
    # 创建锁管理器并操作
    lock_mgr = LockManager(lock_dir="/tmp/test_locks")
    
    # 获取锁
    result = lock_mgr.acquire("test_role", "task_001")
    assert result, "Lock acquire should succeed"
    
    # 释放锁
    lock_mgr.release("test_role")
    
    # 验证钩子触发
    assert "acquire" in triggered, f"Expected 'acquire' in {triggered}"
    assert "release" in triggered, f"Expected 'release' in {triggered}"
    
    print("  ✅ LockManager hooks test passed")
    return True


def test_task_queue_hooks():
    """测试 TaskQueue 钩子触发"""
    print("\n=== Test 8: TaskQueue Hooks ===")
    
    hooks.clear_history()
    hooks.unregister_all()
    
    triggered = []
    
    def on_submit(ctx):
        triggered.append("submit")
    
    def on_complete(ctx):
        triggered.append("complete")
    
    hooks.register(HookPoint.TASK_AFTER_SUBMIT, on_submit)
    hooks.register(HookPoint.TASK_AFTER_COMPLETE, on_complete)
    
    # 创建任务队列
    task_queue = TaskQueue(state_file="/tmp/test_tasks.json")
    
    # 提交任务
    task = Task(
        id="test_task_001",
        project_id="proj_001",
        role_id="developer",
        name="Test Task",
        description="Test task for hooks"
    )
    task_queue.submit(task)
    
    # 完成任务
    task_queue.update_status("test_task_001", "completed", {"result": "ok"})
    
    # 验证钩子触发
    assert "submit" in triggered, f"Expected 'submit' in {triggered}"
    assert "complete" in triggered, f"Expected 'complete' in {triggered}"
    
    print("  ✅ TaskQueue hooks test passed")
    return True


def test_lock_manager_fault_injection():
    """测试 LockManager 故障注入"""
    print("\n=== Test 9: LockManager Fault Injection ===")
    
    injector.clear()
    
    lock_mgr = LockManager(lock_dir="/tmp/test_locks_fault")
    
    # 注入延迟故障
    injector.inject(
        FaultType.DELAY,
        "lock_manager.acquire",
        probability=1.0,
        duration_ms=200
    )
    
    injector.enable()
    
    start = time.time()
    result = lock_mgr.acquire("test_role", "task_002")
    elapsed = time.time() - start
    
    injector.disable()
    lock_mgr.release("test_role")
    
    # 应该成功，但有延迟
    assert result, "Lock should be acquired despite delay"
    assert elapsed >= 0.2, f"Expected delay >= 0.2s, got {elapsed}s"
    
    print(f"  ✅ LockManager fault injection: {elapsed:.3f}s delay")
    return True


def test_concurrent_hooks():
    """测试并发钩子触发"""
    print("\n=== Test 10: Concurrent Hooks ===")
    
    hooks.clear_history()
    hooks.unregister_all()
    
    counter = [0]
    lock = threading.Lock()
    
    def increment(ctx):
        with lock:
            counter[0] += 1
    
    hooks.register(HookPoint.LOCK_BEFORE_ACQUIRE, increment)
    
    # 并发触发
    threads = []
    for i in range(10):
        t = threading.Thread(target=lambda: hooks.trigger(
            HookPoint.LOCK_BEFORE_ACQUIRE, role_id=f"role_{i}"))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    assert counter[0] == 10, f"Expected 10 triggers, got {counter[0]}"
    print(f"  ✅ Concurrent hooks: {counter[0]} triggers")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("🧪 测试钩子系统与故障注入器测试套件")
    print("=" * 70)
    
    tests = [
        ("Hooks Registration", test_hooks_registration),
        ("Hooks History", test_hooks_history),
        ("Fault Injection - Crash", test_fault_injection_crash),
        ("Fault Injection - Delay", test_fault_injection_delay),
        ("Fault Injection - Probability", test_fault_injection_probability),
        ("Fault Context Manager", test_fault_context),
        ("LockManager Hooks", test_lock_manager_hooks),
        ("TaskQueue Hooks", test_task_queue_hooks),
        ("LockManager Fault Injection", test_lock_manager_fault_injection),
        ("Concurrent Hooks", test_concurrent_hooks),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"  ❌ Test '{name}' failed: {e}")
    
    print("\n" + "=" * 70)
    print(f"📊 测试结果: {passed}/{len(tests)} 通过, {failed} 失败")
    print("=" * 70)
    
    # 清理
    hooks.unregister_all()
    hooks.clear_history()
    injector.clear()
    injector.disable()
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
