#!/usr/bin/env python3
"""
集成测试 - 修复版（测试隔离）
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("🔗 集成测试 - 双层任务编排系统")
print("=" * 70)

results = []

def test(name, func):
    """在隔离环境中运行测试"""
    print(f"\n📦 {name}")
    print("-" * 50)
    
    # 创建独立测试目录
    tmp_dir = tempfile.mkdtemp()
    os.environ["OPENCLAW_WORKSPACE"] = tmp_dir
    os.environ["DASHSCOPE_API_KEY"] = "sk-test-key"
    
    try:
        func()
        results.append((name, True))
        print(f"✅ {name} 通过")
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"❌ {name} 失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

# ==================== 集成测试场景 ====================

def test_layer1_api_integration():
    """测试 Layer 1 API 整合"""
    from layer1.api import ResourceSchedulerAPI
    from shared.models import Task
    
    api = ResourceSchedulerAPI()
    print("  ✓ Layer 1 API 初始化成功")
    
    # 先注册角色
    api.registry.register("architect", "架构师", ["design"])
    print("  ✓ 角色注册成功")
    
    # 测试任务提交
    task = Task(
        id="integration_task_1",
        project_id="proj_001",
        role_id="architect",
        name="集成测试任务",
        priority="P0"
    )
    result = api.submit_task(task)
    assert result["success"] == True, f"任务提交失败: {result.get('message')}"
    assert result["task_id"] == "integration_task_1"
    print("  ✓ submit_task 工作正常")
    
    # 测试锁获取/释放
    lock_result = api.acquire_lock("architect", "integration_task_1")
    assert lock_result["acquired"] == True, "锁获取失败"
    print("  ✓ acquire_lock 工作正常")
    
    result = api.release_lock("architect")
    assert result["released"] == True, "锁释放失败"
    print("  ✓ release_lock 工作正常")
    
    # 测试完成任务
    api.complete_task("integration_task_1", success=True, result={"output": "done"})
    completed_task = api.task_queue.get("integration_task_1")
    assert completed_task.status == "completed"
    print("  ✓ complete_task 工作正常")

test("Layer 1 API 整合", test_layer1_api_integration)

def test_multi_role_coordination():
    """测试多角色协调"""
    from layer1.api import ResourceSchedulerAPI
    from shared.models import Task
    
    api = ResourceSchedulerAPI()
    
    # 注册多个角色
    api.registry.register("architect", "架构师", ["design"])
    api.registry.register("developer", "开发者", ["code"])
    api.registry.register("tester", "测试员", ["test"])
    print("  ✓ 多个角色注册成功")
    
    # 为不同角色提交任务
    tasks = [
        Task(id="arch_task", project_id="p1", role_id="architect", name="设计任务", priority="P0"),
        Task(id="dev_task", project_id="p1", role_id="developer", name="开发任务", priority="P1"),
        Task(id="test_task", project_id="p1", role_id="tester", name="测试任务", priority="P2"),
    ]
    
    for task in tasks:
        result = api.submit_task(task)
        assert result["success"] == True, f"任务提交失败: {result.get('message')}"
    print("  ✓ 多角色任务提交成功")
    
    # 验证各角色能获取自己的任务
    arch_next = api.task_queue.get_next_for_role("architect")
    assert arch_next.id == "arch_task"
    
    dev_next = api.task_queue.get_next_for_role("developer")
    assert dev_next.id == "dev_task"
    
    test_next = api.task_queue.get_next_for_role("tester")
    assert test_next.id == "test_task"
    print("  ✓ 各角色任务隔离正确")

test("多角色协调", test_multi_role_coordination)

def test_lock_with_task_execution():
    """测试锁与任务执行协作"""
    from layer1.api import ResourceSchedulerAPI
    from shared.models import Task
    
    api = ResourceSchedulerAPI()
    
    # 注册角色
    api.registry.register("architect", "架构师", ["design"])
    
    # 提交任务
    task = Task(
        id="locked_task",
        project_id="p1",
        role_id="architect",
        name="需要锁的任务",
        priority="P0"
    )
    result = api.submit_task(task)
    assert result["success"] == True
    print("  ✓ 任务提交成功")
    
    # 模拟执行流程
    # 1. 获取锁
    lock_result = api.acquire_lock("architect", "locked_task")
    assert lock_result["acquired"] == True
    print("  ✓ 执行前获取锁成功")
    
    # 2. 更新任务状态为处理中
    api.task_queue.update_status("locked_task", "processing")
    assert api.task_queue.get("locked_task").status == "processing"
    print("  ✓ 任务状态更新为 processing")
    
    # 3. 完成任务
    api.complete_task("locked_task", success=True, result={"files": ["a.py"]})
    completed = api.task_queue.get("locked_task")
    assert completed.status == "completed"
    print("  ✓ 任务完成")
    
    # 4. 释放锁
    api.release_lock("architect")
    assert api.lock_manager.is_locked("architect") == False
    print("  ✓ 执行后释放锁成功")

test("锁与任务执行协作", test_lock_with_task_execution)

def test_task_dependencies():
    """测试任务依赖链"""
    from layer1.api import ResourceSchedulerAPI
    from shared.models import Task
    
    api = ResourceSchedulerAPI()
    
    # 注册角色
    api.registry.register("architect", "架构师", ["design"])
    
    # 创建依赖链: task_c -> task_b -> task_a
    task_a = Task(
        id="task_a",
        project_id="p1",
        role_id="architect",
        name="基础任务",
        priority="P0"
    )
    task_b = Task(
        id="task_b",
        project_id="p1",
        role_id="architect",
        name="依赖A的任务",
        priority="P0",
        depends_on=["task_a"]
    )
    task_c = Task(
        id="task_c",
        project_id="p1",
        role_id="architect",
        name="依赖B的任务",
        priority="P0",
        depends_on=["task_b"]
    )
    
    for task in [task_a, task_b, task_c]:
        result = api.submit_task(task)
        assert result["success"] == True, f"任务提交失败: {result.get('message')}"
    print("  ✓ 依赖链任务提交成功")
    
    # 只有 task_a 应该能被获取（没有未完成的依赖）
    next_task = api.task_queue.get_next_for_role("architect")
    assert next_task.id == "task_a", f"期望 task_a, 得到 {next_task.id}"
    print("  ✓ 正确识别可执行任务: task_a")
    
    # 完成 task_a
    api.task_queue.update_status("task_a", "completed")
    
    # 现在 task_b 应该可以执行
    next_task = api.task_queue.get_next_for_role("architect")
    assert next_task.id == "task_b"
    print("  ✓ 依赖满足后 task_b 可执行")
    
    # 获取依赖链
    chain = api.task_queue.get_dependency_chain("task_c")
    assert "task_a" in chain and "task_b" in chain
    print("  ✓ 依赖链查询正确")

test("任务依赖链", test_task_dependencies)

def test_persistence():
    """测试数据持久化"""
    from layer1.api import ResourceSchedulerAPI
    from shared.models import Task
    
    # 第一个 API 实例
    api1 = ResourceSchedulerAPI()
    
    # 注册角色
    api1.registry.register("architect", "架构师", ["design"])
    
    task = Task(
        id="persistent_task",
        project_id="p1",
        role_id="architect",
        name="持久化测试任务",
        priority="P0"
    )
    result = api1.submit_task(task)
    assert result["success"] == True
    
    lock_result = api1.acquire_lock("architect", "persistent_task")
    assert lock_result["acquired"] == True
    print("  ✓ 第一个实例: 提交任务并获取锁")
    
    # 创建新的 API 实例（模拟重启）
    api2 = ResourceSchedulerAPI()
    
    # 验证任务被持久化
    retrieved = api2.task_queue.get("persistent_task")
    assert retrieved is not None, "任务应该被持久化"
    assert retrieved.name == "持久化测试任务"
    print("  ✓ 第二个实例: 任务从磁盘恢复")
    
    # 验证锁也被持久化
    lock_info = api2.lock_manager.get_lock_info("architect")
    assert lock_info is not None, "锁应该被持久化"
    assert lock_info.task_id == "persistent_task"
    print("  ✓ 第二个实例: 锁状态从磁盘恢复")

test("数据持久化", test_persistence)

def test_error_handling():
    """测试错误处理"""
    from layer1.api import ResourceSchedulerAPI
    from shared.models import Task
    
    api = ResourceSchedulerAPI()
    
    # 测试获取不存在的任务
    non_existent = api.task_queue.get("not_exist")
    assert non_existent is None
    print("  ✓ 获取不存在的任务返回 None")
    
    # 测试释放不存在的锁
    result = api.release_lock("non_existent_role")
    assert result["released"] == True  # 应该成功（幂等）
    print("  ✓ 释放不存在的锁成功（幂等）")
    
    # 测试重复注册角色
    api.registry.register("test_role", "测试角色", ["test"])
    # 再次注册应该返回已存在的ID
    role_id = api.registry.register("test_role", "测试角色2", ["test2"])
    assert role_id == "test_role"  # ID 不变
    retrieved = api.registry.get("test_role")
    assert retrieved.name == "测试角色"  # 名称不变
    print("  ✓ 重复注册处理正确（幂等）")
    
    # 测试向不存在的角色提交任务
    bad_task = Task(id="bad", project_id="p1", role_id="non_existent", name="错误任务")
    result = api.submit_task(bad_task)
    assert result["success"] == False
    assert "不存在" in result["message"]
    print("  ✓ 向不存在角色提交任务返回错误")

test("错误处理", test_error_handling)

# ==================== 汇总 ====================

print("\n" + "=" * 70)
print("📊 集成测试结果汇总")
print("=" * 70)

passed = sum(1 for r in results if len(r) == 2)
failed = sum(1 for r in results if len(r) == 3)

print(f"总测试: {len(results)}")
print(f"✅ 通过: {passed}")
print(f"❌ 失败: {failed}")
print()

for r in results:
    emoji = "✅" if len(r) == 2 else "❌"
    print(f"  {emoji} {r[0]}")
    if len(r) == 3:
        print(f"      错误: {r[2]}")

print()
if failed == 0:
    print("🎉 所有集成测试通过！系统运行正常。")
else:
    print(f"⚠️  {failed} 个集成测试失败，需要检查。")

print("=" * 70)
