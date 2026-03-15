#!/usr/bin/env python3
"""
Layer 1 单元测试
验证核心组件功能
"""
import sys
import os
import tempfile
import shutil
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, '/root/.openclaw/workspace/shared/pipeline')

from layer1.role_registry import RoleRegistry
from layer1.lock_manager import LockManager
from layer1.task_queue import TaskQueue
from layer1.conflict_detector import ConflictDetector
from layer1.priority_manager import PriorityManager
from layer1.api import ResourceSchedulerAPI
from shared.models import Task, RoleConfig


def test_role_registry():
    """测试角色注册表"""
    print("\n=== Testing RoleRegistry ===")
    
    # 创建临时目录
    tmp_dir = tempfile.mkdtemp()
    state_file = os.path.join(tmp_dir, "roles.json")
    
    try:
        registry = RoleRegistry(state_file)
        
        # 测试注册
        role_id = registry.register(
            role_type="architect",
            name="系统架构师",
            capabilities=["gap_analysis", "solution_design"],
            config=RoleConfig(poll_interval_minutes=10)
        )
        print(f"✓ Registered role: {role_id}")
        
        # 测试获取
        role = registry.get(role_id)
        assert role is not None
        assert role.type == "architect"
        print(f"✓ Retrieved role: {role.name}")
        
        # 测试状态查询
        status = registry.get_status()
        assert role_id in status
        print(f"✓ Status query: {len(status)} roles")
        
        # 测试按类型查询
        architects = registry.get_by_type("architect")
        assert len(architects) == 1
        print(f"✓ Query by type: {len(architects)} architects")
        
        print("✅ RoleRegistry tests passed!")
        
    finally:
        shutil.rmtree(tmp_dir)


def test_lock_manager():
    """测试锁管理器"""
    print("\n=== Testing LockManager ===")
    
    tmp_dir = tempfile.mkdtemp()
    
    try:
        lock_mgr = LockManager(tmp_dir, default_timeout_ms=5000)  # 5秒超时
        
        # 测试获取锁
        acquired = lock_mgr.acquire("role_001", "task_001")
        assert acquired is True
        print("✓ Lock acquired")
        
        # 测试重复获取（应失败）
        acquired2 = lock_mgr.acquire("role_001", "task_002")
        assert acquired2 is False
        print("✓ Duplicate lock rejected")
        
        # 测试锁信息查询
        lock_info = lock_mgr.get_lock_info("role_001")
        assert lock_info is not None
        assert lock_info.role_id == "role_001"
        print("✓ Lock info retrieved")
        
        # 测试释放锁
        released = lock_mgr.release("role_001")
        assert released is True
        print("✓ Lock released")
        
        # 测试超时清理
        lock_mgr.acquire("role_002", "task_003", timeout_ms=1)  # 1ms超时
        import time
        time.sleep(0.1)  # 等待超时
        cleaned = lock_mgr.cleanup_expired()
        assert cleaned == 1
        print(f"✓ Expired locks cleaned: {cleaned}")
        
        print("✅ LockManager tests passed!")
        
    finally:
        shutil.rmtree(tmp_dir)


def test_task_queue():
    """测试任务队列"""
    print("\n=== Testing TaskQueue ===")
    
    tmp_dir = tempfile.mkdtemp()
    state_file = os.path.join(tmp_dir, "tasks.json")
    
    try:
        queue = TaskQueue(state_file)
        
        # 测试提交任务
        task = Task(
            project_id="proj_001",
            role_id="role_001",
            name="测试任务",
            description="这是一个测试任务",
            priority="P1"
        )
        task_id = queue.submit(task)
        print(f"✓ Task submitted: {task_id}")
        
        # 测试获取任务
        retrieved = queue.get(task_id)
        assert retrieved is not None
        assert retrieved.name == "测试任务"
        print("✓ Task retrieved")
        
        # 测试状态更新
        queue.update_status(task_id, "processing")
        retrieved = queue.get(task_id)
        assert retrieved.status == "processing"
        assert retrieved.started_at is not None
        print("✓ Status updated")
        
        # 测试完成任务
        queue.update_status(task_id, "completed", {"output": "done"})
        retrieved = queue.get(task_id)
        assert retrieved.status == "completed"
        assert retrieved.result.get("output") == "done"
        print("✓ Task completed")
        
        # 测试统计
        stats = queue.get_statistics()
        assert stats.get("completed", 0) == 1
        print(f"✓ Statistics: {stats}")
        
        print("✅ TaskQueue tests passed!")
        
    finally:
        shutil.rmtree(tmp_dir)


def test_conflict_detector():
    """测试冲突检测器"""
    print("\n=== Testing ConflictDetector ===")
    
    tmp_dir = tempfile.mkdtemp()
    
    try:
        registry = RoleRegistry(os.path.join(tmp_dir, "roles.json"))
        queue = TaskQueue(os.path.join(tmp_dir, "tasks.json"))
        detector = ConflictDetector(queue, registry)
        
        # 注册角色
        role_id = registry.register("developer", "开发者", ["coding"])
        
        # 测试角色过载检测
        # 让角色处于忙碌状态
        registry.update_status(role_id, "busy", "some_task")
        # 添加多个排队任务
        for i in range(3):
            registry.add_to_queue(role_id, f"task_{i}")
        
        task = Task(
            role_id=role_id,
            name="新任务",
            description="测试过载检测"
        )
        
        conflicts = detector.check_task_submit(task)
        overload_conflicts = [c for c in conflicts if c.type == "ROLE_OVERLOAD"]
        assert len(overload_conflicts) > 0
        print(f"✓ Overload detected: {len(overload_conflicts)} conflicts")
        
        # 测试依赖冲突
        task2 = Task(
            role_id=role_id,
            name="依赖任务",
            depends_on=["nonexistent_task"]
        )
        
        conflicts2 = detector.check_task_submit(task2)
        dep_conflicts = [c for c in conflicts2 if c.type == "MISSING_DEPENDENCY"]
        assert len(dep_conflicts) == 1
        print("✓ Missing dependency detected")
        
        print("✅ ConflictDetector tests passed!")
        
    finally:
        shutil.rmtree(tmp_dir)


def test_priority_manager():
    """测试优先级管理器"""
    print("\n=== Testing PriorityManager ===")
    
    pm = PriorityManager()
    
    # 测试优先级分数计算
    task_p0 = Task(priority="P0")
    task_p0.created_at = datetime.now() - timedelta(hours=2)  # 等待2小时
    
    score_p0 = pm.calculate_priority_score(task_p0)
    assert score_p0 > 100  # P0基础权重100 + 等待加成
    print(f"✓ P0 score: {score_p0}")
    
    task_p2 = Task(priority="P2")
    task_p2.created_at = datetime.now()
    
    score_p2 = pm.calculate_priority_score(task_p2)
    assert score_p2 == 10  # P2基础权重10，无等待
    print(f"✓ P2 score: {score_p2}")
    
    # 测试队列排序
    tasks = [task_p2, task_p0]
    sorted_tasks = pm.sort_queue(tasks)
    assert sorted_tasks[0].priority == "P0"
    print("✓ Queue sorted by priority")
    
    # 测试抢占
    new_task = Task(priority="P0")
    current_task = Task(priority="P1")
    should_preempt = pm.should_preempt(new_task, current_task)
    assert should_preempt is True
    print("✓ Preemption check passed")
    
    print("✅ PriorityManager tests passed!")


def test_resource_scheduler_api():
    """测试资源调度API整合"""
    print("\n=== Testing ResourceSchedulerAPI ===")
    
    tmp_dir = tempfile.mkdtemp()
    state_dir = os.path.join(tmp_dir, "state")
    lock_dir = os.path.join(tmp_dir, "locks")
    
    try:
        api = ResourceSchedulerAPI(state_dir, lock_dir)
        
        # 注册角色
        role_id = api.registry.register("tester", "测试员", ["testing"])
        print(f"✓ Role registered via API: {role_id}")
        
        # 查询状态
        status = api.get_roles_status()
        assert "roles" in status
        print(f"✓ Status queried: {len(status['roles'])} roles")
        
        # 提交任务
        result = api.submit_task({
            "project_id": "proj_001",
            "role_id": role_id,
            "name": "API测试任务",
            "description": "测试API",
            "priority": "P1"
        })
        assert result["success"] is True
        task_id = result["task_id"]
        print(f"✓ Task submitted via API: {task_id}")
        
        # 获取任务状态
        task_status = api.get_task_status(task_id)
        assert task_status is not None
        assert task_status["status"] == "pending"
        print("✓ Task status retrieved")
        
        # 申请锁
        lock_result = api.acquire_lock(role_id, task_id)
        assert lock_result["acquired"] is True
        print("✓ Lock acquired via API")
        
        # 完成任务
        complete_result = api.complete_task(task_id, True, {"result": "success"})
        assert complete_result["status"] == "completed"
        print("✓ Task completed via API")
        
        # 获取统计
        stats = api.get_statistics()
        assert "roles" in stats
        assert "tasks" in stats
        print(f"✓ Statistics: {stats['tasks']}")
        
        print("✅ ResourceSchedulerAPI tests passed!")
        
    finally:
        shutil.rmtree(tmp_dir)


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Layer 1 Unit Tests")
    print("=" * 60)
    
    try:
        test_role_registry()
        test_lock_manager()
        test_task_queue()
        test_conflict_detector()
        test_priority_manager()
        test_resource_scheduler_api()
        
        print("\n" + "=" * 60)
        print("✅ All Layer 1 tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
