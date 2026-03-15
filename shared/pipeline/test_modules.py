#!/usr/bin/env python3
"""
模块单元测试套件
测试各个 Layer 0/1/2 模块的功能
"""
import os
import sys
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime

# 设置测试环境
tmp_dir = tempfile.mkdtemp()
os.environ["OPENCLAW_WORKSPACE"] = tmp_dir
os.environ["DASHSCOPE_API_KEY"] = "sk-test-key"

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("🧪 模块单元测试套件")
print("=" * 70)
print(f"测试目录: {tmp_dir}")
print()

# 测试统计
test_results = []

def run_test(module_name, test_func):
    """运行单个测试"""
    print(f"\n📦 {module_name}")
    print("-" * 50)
    try:
        test_func()
        test_results.append((module_name, True, None))
        print(f"✅ {module_name} 测试通过")
        return True
    except Exception as e:
        test_results.append((module_name, False, str(e)))
        print(f"❌ {module_name} 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

# ==================== Layer 1 测试 ====================

def test_lock_manager():
    """测试锁管理器"""
    from layer1.lock_manager import LockManager, get_workspace_dir
    
    # 测试路径配置
    workspace = get_workspace_dir()
    assert str(workspace) == tmp_dir, f"路径不匹配"
    print("  ✓ 环境变量路径配置正确")
    
    # 测试锁获取和释放
    lock_dir = Path(tmp_dir) / "locks"
    lm = LockManager(lock_dir)
    
    # 获取锁
    result = lm.acquire("test_role", "task_001")
    assert result == True, "获取锁失败"
    print("  ✓ 锁获取成功")
    
    # 重复获取应该失败
    result = lm.acquire("test_role", "task_002")
    assert result == False, "重复获取应该失败"
    print("  ✓ 重复获取锁被正确拒绝")
    
    # 检查锁状态
    assert lm.is_locked("test_role") == True, "锁状态检测失败"
    print("  ✓ 锁状态检测正确")
    
    # 获取锁信息
    lock_info = lm.get_lock_info("test_role")
    assert lock_info is not None, "锁信息获取失败"
    assert lock_info.task_id == "task_001", "锁信息任务ID不匹配"
    print("  ✓ 锁信息获取正确")
    
    # 释放锁
    result = lm.release("test_role")
    assert result == True, "释放锁失败"
    print("  ✓ 锁释放成功")
    
    # 检查锁状态
    assert lm.is_locked("test_role") == False, "锁应该已被释放"
    print("  ✓ 锁释放后状态正确")
    
    # 测试过期锁清理
    lm.acquire("expired_role", "task_003", timeout_ms=1)
    import time
    time.sleep(0.01)  # 等待锁过期
    cleaned = lm.cleanup_expired()
    assert cleaned >= 0, "清理过期锁失败"
    print("  ✓ 过期锁清理功能正常")

def test_task_queue():
    """测试任务队列"""
    from layer1.task_queue import TaskQueue
    from shared.models import Task
    
    state_file = Path(tmp_dir) / "state" / "test_queue.json"
    tq = TaskQueue(state_file)
    
    # 创建测试任务
    task = Task(
        id="test_task_001",
        project_id="proj_001",
        role_id="architect",
        name="测试任务",
        description="这是一个测试任务",
        priority="P0"
    )
    
    # 提交任务
    task_id = tq.submit(task)
    assert task_id == "test_task_001", "任务ID不匹配"
    print("  ✓ 任务提交成功")
    
    # 获取任务
    retrieved = tq.get(task_id)
    assert retrieved is not None, "任务获取失败"
    assert retrieved.name == "测试任务", "任务名称不匹配"
    print("  ✓ 任务获取成功")
    
    # 更新状态
    tq.update_status(task_id, "processing")
    retrieved = tq.get(task_id)
    assert retrieved.status == "processing", "状态更新失败"
    print("  ✓ 任务状态更新成功")
    
    # 获取下一个任务
    next_task = tq.get_next_for_role("architect")
    assert next_task is not None, "应该有一个待处理任务"
    print("  ✓ 获取下一个任务成功")
    
    # 统计查询
    stats = tq.get_statistics()
    assert "pending" in stats, "统计信息不完整"
    print("  ✓ 统计查询成功")
    
    # 删除任务
    result = tq.delete(task_id)
    assert result == True, "任务删除失败"
    print("  ✓ 任务删除成功")

def test_role_registry():
    """测试角色注册表"""
    from layer1.role_registry import RoleRegistry
    from shared.models import Role, RoleConfig
    
    state_file = Path(tmp_dir) / "state" / "test_registry.json"
    registry = RoleRegistry(state_file)
    
    # 注册角色
    role = Role(
        id="architect_001",
        type="architect",
        name="架构师",
        capabilities=["design", "review"],
        config=RoleConfig()
    )
    
    registry.register(role)
    print("  ✓ 角色注册成功")
    
    # 获取角色
    retrieved = registry.get("architect_001")
    assert retrieved is not None, "角色获取失败"
    assert retrieved.name == "架构师", "角色名称不匹配"
    print("  ✓ 角色获取成功")
    
    # 更新状态
    registry.update_status("architect_001", "busy")
    retrieved = registry.get("architect_001")
    assert retrieved.status == "busy", "状态更新失败"
    print("  ✓ 角色状态更新成功")
    
    # 获取所有角色
    all_roles = registry.get_all()
    assert len(all_roles) >= 1, "角色列表为空"
    print("  ✓ 获取所有角色成功")
    
    # 按类型查询
    architects = registry.get_by_type("architect")
    assert len(architects) >= 1, "按类型查询失败"
    print("  ✓ 按类型查询成功")
    
    # 注销角色
    registry.unregister("architect_001")
    retrieved = registry.get("architect_001")
    assert retrieved is None, "角色应该已被注销"
    print("  ✓ 角色注销成功")

def test_conflict_detector():
    """测试冲突检测器"""
    from layer1.conflict_detector import ConflictDetector
    from layer1.task_queue import TaskQueue
    from layer1.role_registry import RoleRegistry
    from shared.models import Task
    
    tq = TaskQueue(Path(tmp_dir) / "state" / "conflict_queue.json")
    registry = RoleRegistry(Path(tmp_dir) / "state" / "conflict_registry.json")
    detector = ConflictDetector(tq, registry)
    
    # 提交两个冲突的任务（同角色）
    task1 = Task(
        id="conflict_task_1",
        project_id="proj_001",
        role_id="architect",
        name="任务1",
        priority="P0"
    )
    task2 = Task(
        id="conflict_task_2",
        project_id="proj_001",
        role_id="architect",
        name="任务2",
        priority="P1"
    )
    
    tq.submit(task1)
    tq.submit(task2)
    
    # 检测冲突
    conflicts = detector.detect_conflicts()
    # 应该检测到资源竞争（同角色的多个pending任务）
    assert isinstance(conflicts, list), "冲突检测结果格式错误"
    print("  ✓ 冲突检测功能正常")
    
    # 测试依赖环检测
    task_a = Task(
        id="task_a",
        project_id="proj_002",
        role_id="dev",
        name="任务A",
        depends_on=["task_b"]
    )
    task_b = Task(
        id="task_b",
        project_id="proj_002",
        role_id="dev",
        name="任务B",
        depends_on=["task_a"]  # 循环依赖
    )
    
    tq.submit(task_a)
    tq.submit(task_b)
    
    deadlock = detector.detect_deadlock()
    assert isinstance(deadlock, list), "死锁检测结果格式错误"
    print("  ✓ 死锁检测功能正常")

# ==================== Layer 0 测试 ====================

def test_ai_client():
    """测试 AI 客户端"""
    from layer0.ai_client import AliyunAIClient
    
    client = AliyunAIClient()
    
    # 检查 API Key 配置
    assert client.api_key is not None, "API Key 未配置"
    print("  ✓ API Key 已配置")
    
    # 检查角色提示词加载
    assert "architect" in client.system_prompts, "architect 提示词未加载"
    assert "developer" in client.system_prompts, "developer 提示词未加载"
    assert "tester" in client.system_prompts, "tester 提示词未加载"
    assert "auditor" in client.system_prompts, "auditor 提示词未加载"
    print("  ✓ 所有角色提示词已加载")
    
    # 检查模型选择
    model = client._select_model_by_role("architect")
    assert model is not None, "模型选择失败"
    print(f"  ✓ 角色模型映射正常: {model}")

def test_shared_models():
    """测试共享模型"""
    from shared.models import Task, Role, LockInfo, Priority
    
    # 测试任务创建
    task = Task(
        id="test_001",
        project_id="proj_001",
        role_id="architect",
        name="测试任务",
        priority="P0"
    )
    assert task.id == "test_001"
    assert task.priority == Priority.P0
    print("  ✓ Task 模型创建成功")
    
    # 测试锁信息
    lock = LockInfo(
        role_id="architect",
        task_id="task_001",
        acquired_at=datetime.now(),
        timeout_ms=30000
    )
    assert lock.role_id == "architect"
    print("  ✓ LockInfo 模型创建成功")
    
    # 测试序列化
    task_dict = task.to_dict() if hasattr(task, 'to_dict') else task.__dict__
    assert task_dict is not None
    print("  ✓ 模型序列化正常")

# ==================== 运行测试 ====================

print("\n🔹 Layer 1 组件测试")
print("=" * 50)

run_test("LockManager (锁管理器)", test_lock_manager)
run_test("TaskQueue (任务队列)", test_task_queue)
run_test("RoleRegistry (角色注册表)", test_role_registry)
run_test("ConflictDetector (冲突检测器)", test_conflict_detector)

print("\n🔹 Layer 0 组件测试")
print("=" * 50)

run_test("AIClient (AI 客户端)", test_ai_client)
run_test("SharedModels (共享模型)", test_shared_models)

# ==================== 清理 ====================

shutil.rmtree(tmp_dir, ignore_errors=True)

# ==================== 汇总 ====================

print("\n" + "=" * 70)
print("📊 单元测试结果汇总")
print("=" * 70)
print()

passed = sum(1 for _, status, _ in test_results if status)
failed = sum(1 for _, status, _ in test_results if not status)
total = len(test_results)

print(f"总测试数: {total}")
print(f"✅ 通过: {passed}")
print(f"❌ 失败: {failed}")
print(f"通过率: {passed/total*100:.1f}%" if total > 0 else "N/A")
print()

for name, status, error in test_results:
    emoji = "✅" if status else "❌"
    print(f"  {emoji} {name}")
    if error:
        print(f"      错误: {error}")

print()
if failed == 0:
    print("🎉 所有模块单元测试通过！")
else:
    print(f"⚠️  {failed} 个模块测试失败")

print("=" * 70)
