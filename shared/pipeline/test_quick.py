#!/usr/bin/env python3
"""
快速模块验证测试
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

tmp_dir = tempfile.mkdtemp()
os.environ["OPENCLAW_WORKSPACE"] = tmp_dir
os.environ["DASHSCOPE_API_KEY"] = "sk-test-key"

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("🧪 快速模块验证测试")
print("=" * 60)
print()

results = []

def test(name, func):
    print(f"\n📋 {name}")
    try:
        func()
        results.append((name, True))
        print(f"  ✅ 通过")
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"  ❌ 失败: {e}")

# 测试1: 路径配置
def test_path():
    from layer1.lock_manager import get_workspace_dir
    workspace = get_workspace_dir()
    assert str(workspace) == tmp_dir
    print(f"  ✓ 路径: {workspace}")
test("环境变量路径配置", test_path)

# 测试2: 锁管理器
def test_lock():
    from layer1.lock_manager import LockManager
    lm = LockManager(Path(tmp_dir) / "locks")
    
    # 获取锁
    assert lm.acquire("role1", "task1") == True
    print(f"  ✓ 锁获取成功")
    
    # 重复获取失败
    assert lm.acquire("role1", "task2") == False
    print(f"  ✓ 重复获取被拒绝")
    
    # 释放锁
    assert lm.release("role1") == True
    print(f"  ✓ 锁释放成功")
    
    # 另一个角色可以获取
    assert lm.acquire("role2", "task3") == True
    lm.release("role2")
    print(f"  ✓ 不同角色互不影响")
test("LockManager 基本功能", test_lock)

# 测试3: 任务队列
def test_task_queue():
    from layer1.task_queue import TaskQueue
    from shared.models import Task
    
    tq = TaskQueue(Path(tmp_dir) / "state" / "queue.json")
    
    task = Task(
        id="t1",
        project_id="p1",
        role_id="architect",
        name="测试任务",
        priority="P0"
    )
    
    task_id = tq.submit(task)
    assert task_id == "t1"
    print(f"  ✓ 任务提交: {task_id}")
    
    retrieved = tq.get("t1")
    assert retrieved.name == "测试任务"
    print(f"  ✓ 任务获取成功")
    
    tq.update_status("t1", "completed")
    assert tq.get("t1").status == "completed"
    print(f"  ✓ 状态更新成功")
test("TaskQueue 基本功能", test_task_queue)

# 测试4: 角色注册表
def test_registry():
    from layer1.role_registry import RoleRegistry
    
    registry = RoleRegistry(Path(tmp_dir) / "state" / "registry.json")
    
    # register 方法参数: role_type, name, capabilities
    role_id = registry.register(
        role_type="architect",
        name="架构师",
        capabilities=["design"]
    )
    print(f"  ✓ 角色注册成功: {role_id}")
    
    retrieved = registry.get(role_id)
    assert retrieved.name == "架构师"
    print(f"  ✓ 角色获取成功")
    
    registry.unregister(role_id)
    assert registry.get(role_id) is None
    print(f"  ✓ 角色注销成功")
test("RoleRegistry 基本功能", test_registry)

# 测试5: 共享模型
def test_models():
    from shared.models import Task, Role, LockInfo
    from datetime import datetime
    
    task = Task(id="t1", project_id="p1", role_id="r1", name="任务", priority="P0")
    assert task.priority == "P0"
    print(f"  ✓ Task 模型正常")
    
    lock = LockInfo(role_id="r1", task_id="t1", acquired_at=datetime.now(), timeout_ms=30000)
    assert lock.role_id == "r1"
    print(f"  ✓ LockInfo 模型正常")
test("共享模型", test_models)

# 测试6: AI 客户端配置
def test_ai_client():
    from layer0.ai_client import AliyunAIClient
    
    client = AliyunAIClient()
    assert "architect" in client.system_prompts
    assert "developer" in client.system_prompts
    assert "tester" in client.system_prompts
    assert "auditor" in client.system_prompts
    print(f"  ✓ 所有角色提示词已加载")
test("AI Client 配置", test_ai_client)

# 清理
shutil.rmtree(tmp_dir, ignore_errors=True)

# 汇总
print("\n" + "=" * 60)
print("📊 测试结果")
print("=" * 60)
passed = sum(1 for r in results if len(r) == 2)
failed = sum(1 for r in results if len(r) == 3)
print(f"通过: {passed}, 失败: {failed}")
for r in results:
    emoji = "✅" if len(r) == 2 else "❌"
    print(f"  {emoji} {r[0]}")
print()
print("🎉 快速验证完成！" if failed == 0 else f"⚠️  {failed} 个失败")
