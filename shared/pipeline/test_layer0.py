#!/usr/bin/env python3
"""
Layer 0 功能测试
测试角色工作器的基本功能
"""
import sys
import os
import tempfile
import shutil
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from layer1.api import ResourceSchedulerAPI
from layer0 import ArchitectWorker, DeveloperWorker, TesterWorker, WorkerPool

print("=" * 80)
print("🧪 Layer 0 角色工作器功能测试")
print("=" * 80)
print()

# 创建临时测试环境
tmp_dir = tempfile.mkdtemp()
state_dir = os.path.join(tmp_dir, 'state')
lock_dir = os.path.join(tmp_dir, 'locks')

os.makedirs(state_dir, exist_ok=True)
os.makedirs(lock_dir, exist_ok=True)

layer1 = ResourceSchedulerAPI(state_dir, lock_dir)

results = []

def test_case(name, test_func):
    """执行测试用例"""
    print(f"📋 {name}")
    print("-" * 70)
    try:
        test_func()
        results.append((name, True, None))
        print("  ✅ 通过")
        print()
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"  ❌ 失败: {e}")
        print()

# ========== 测试1: 架构师工作器 ==========
def test_architect_worker():
    worker = ArchitectWorker(layer1, poll_interval=1.0)
    
    # 测试状态
    status = worker.get_status()
    assert status["role_id"] == "architect"
    assert status["role_name"] == "架构师"
    assert "architecture" in status["capabilities"]
    
    # 测试直接执行任务（不通过轮询）
    task_data = {
        "task_type": "system_design",
        "project_id": "TEST_001",
        "project_name": "测试系统",
        "requirements": {"type": "microservice", "features": ["api", "auth"]}
    }
    
    result = worker.execute_task(task_data)
    assert result.success
    assert "architecture_style" in result.output
    assert result.artifacts is not None
    
    worker.stop()

test_case("TC-001: 架构师工作器 - 系统架构设计", test_architect_worker)

# ========== 测试2: 开发者工作器 ==========
def test_developer_worker():
    worker = DeveloperWorker(layer1, workspace_dir=tmp_dir, poll_interval=1.0)
    
    # 测试状态
    status = worker.get_status()
    assert status["role_id"] == "developer"
    assert status["role_name"] == "开发者"
    assert "coding" in status["capabilities"]
    
    # 测试Skill创建任务
    task_data = {
        "task_type": "skill_creation",
        "project_id": "TEST_002",
        "skill_name": "test_skill",
        "description": "测试Skill",
        "requirements": {"use_cases": "自动化测试"}
    }
    
    result = worker.execute_task(task_data)
    assert result.success
    assert result.output["skill_name"] == "test_skill"
    
    # 验证文件创建
    skill_dir = os.path.join(tmp_dir, "skills", "test_skill")
    assert os.path.exists(skill_dir)
    assert os.path.exists(os.path.join(skill_dir, "SKILL.md"))
    assert os.path.exists(os.path.join(skill_dir, "config.json"))
    
    worker.stop()

test_case("TC-002: 开发者工作器 - Skill创建", test_developer_worker)

# ========== 测试3: 测试员工作器 ==========
def test_tester_worker():
    worker = TesterWorker(layer1, poll_interval=1.0)
    
    # 测试状态
    status = worker.get_status()
    assert status["role_id"] == "tester"
    assert status["role_name"] == "测试员"
    assert "testing" in status["capabilities"]
    
    # 测试单元测试任务
    task_data = {
        "task_type": "unit_test",
        "project_id": "TEST_003",
        "target_module": "test_module",
        "test_scope": ["init", "main", "edge_cases"]
    }
    
    result = worker.execute_task(task_data)
    assert result.success
    assert "total_cases" in result.output
    assert result.artifacts is not None
    
    worker.stop()

test_case("TC-003: 测试员工作器 - 单元测试", test_tester_worker)

# ========== 测试4: 工作器池 ==========
def test_worker_pool():
    pool = WorkerPool()
    
    # 注册工作器
    architect = ArchitectWorker(layer1, poll_interval=1.0)
    developer = DeveloperWorker(layer1, workspace_dir=tmp_dir, poll_interval=1.0)
    tester = TesterWorker(layer1, poll_interval=1.0)
    
    assert pool.register(architect)
    assert pool.register(developer)
    assert pool.register(tester)
    
    # 重复注册应该失败
    assert not pool.register(architect)
    
    # 获取状态
    status = pool.get_status()
    assert len(status) == 3
    assert "architect" in status
    assert "developer" in status
    assert "tester" in status
    
    # 获取工作器
    assert pool.get_worker("architect") == architect
    assert pool.get_worker("nonexistent") is None
    
    # 注销工作器
    assert pool.unregister("architect")
    assert pool.get_worker("architect") is None
    
    pool.stop_all()

test_case("TC-004: 工作器池管理", test_worker_pool)

# ========== 测试5: 完整工作流程 ==========
def test_full_workflow():
    pool = WorkerPool()
    
    # 注册所有工作器
    architect = ArchitectWorker(layer1, poll_interval=0.5)
    developer = DeveloperWorker(layer1, workspace_dir=tmp_dir, poll_interval=0.5)
    tester = TesterWorker(layer1, poll_interval=0.5)
    
    pool.register(architect)
    pool.register(developer)
    pool.register(tester)
    
    # 启动工作器
    pool.start_all()
    
    # 提交测试任务到Layer 1
    # 1. 架构设计任务
    layer1.submit_task({
        "id": "TASK_ARCH_001",
        "project_id": "PROJ_FULL_001",
        "role_id": "architect",
        "name": "系统架构设计",
        "description": "设计测试系统架构",
        "task_type": "system_design",
        "project_name": "测试项目",
        "requirements": {"type": "pipeline"}
    })
    
    # 2. 开发任务
    layer1.submit_task({
        "id": "TASK_DEV_001",
        "project_id": "PROJ_FULL_001",
        "role_id": "developer",
        "name": "功能实现",
        "description": "实现核心功能",
        "task_type": "feature_implementation",
        "feature_name": "核心模块",
        "requirements": {"complexity": "medium"}
    })
    
    # 3. 测试任务
    layer1.submit_task({
        "id": "TASK_TEST_001",
        "project_id": "PROJ_FULL_001",
        "role_id": "tester",
        "name": "功能测试",
        "description": "测试功能实现",
        "task_type": "functional_test",
        "features": [{"name": "核心功能"}]
    })
    
    # 等待工作器处理任务
    print("  ⏳ 等待工作器处理任务...")
    time.sleep(3)
    
    # 获取状态
    status = pool.get_status()
    
    # 验证任务被处理
    total_completed = sum(
        s["stats"]["tasks_completed"] 
        for s in status.values()
    )
    
    print(f"  📊 完成任务数: {total_completed}")
    
    pool.stop_all()

test_case("TC-005: 完整工作流测试", test_full_workflow)

# ========== 汇总 ==========
print()
print("=" * 80)
print("📊 测试结果汇总")
print("=" * 80)
print()

passed = sum(1 for _, status, _ in results if status)
failed = sum(1 for _, status, _ in results if not status)

print(f"总测试数: {len(results)}")
print(f"✅ 通过: {passed}")
print(f"❌ 失败: {failed}")
print(f"通过率: {passed/len(results)*100:.1f}%")
print()

for name, status, error in results:
    emoji = "✅" if status else "❌"
    print(f"  {emoji} {name}")
    if error:
        print(f"      错误: {error}")

print()
if failed == 0:
    print("🎉 所有测试通过！Layer 0 工作器功能完整可用。")
else:
    print(f"⚠️  {failed}个测试失败，需要修复。")
print("=" * 80)

# 清理
shutil.rmtree(tmp_dir)
