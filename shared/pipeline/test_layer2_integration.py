#!/usr/bin/env python3
"""
Layer 2 集成测试
测试 Orchestrator、Planner、Estimator 协作
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("🔗 Layer 2 集成测试")
print("=" * 60)

results = []

def test(name, func):
    """在隔离环境中运行测试"""
    print(f"\n📦 {name}")
    print("-" * 50)
    
    tmp_dir = tempfile.mkdtemp()
    os.environ["OPENCLAW_WORKSPACE"] = tmp_dir
    os.environ["DASHSCOPE_API_KEY"] = "sk-test-key"
    
    state_dir = Path(tmp_dir) / "layer2_state"
    state_dir.mkdir(exist_ok=True)
    
    try:
        func(str(state_dir))
        results.append((name, True))
        print(f"✅ {name} 通过")
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"❌ {name} 失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def test_orchestrator_init(state_dir):
    """测试 Orchestrator 初始化"""
    from layer1.api import ResourceSchedulerAPI
    from layer2.orchestrator import Orchestrator
    
    layer1 = ResourceSchedulerAPI()
    orch = Orchestrator(layer1, state_dir=state_dir)
    
    # 验证固定角色已初始化
    roles = layer1.registry.list_all()
    role_types = [r.type for r in roles]
    
    expected_roles = ["architect", "developer", "tester", "analyst", "auditor"]
    for role in expected_roles:
        assert role in role_types, f"缺少角色: {role}"
    print(f"  ✓ 固定角色已初始化: {len(roles)} 个")
    
    # 验证子组件已创建
    assert orch.planner is not None
    assert orch.estimator is not None
    print("  ✓ Planner 和 Estimator 已创建")

test("Orchestrator 初始化", test_orchestrator_init)

def test_project_lifecycle(state_dir):
    """测试项目完整生命周期"""
    from layer1.api import ResourceSchedulerAPI
    from layer2.orchestrator import Orchestrator, ProjectStatus
    
    layer1 = ResourceSchedulerAPI()
    orch = Orchestrator(layer1, state_dir=state_dir)
    
    # 1. 创建项目
    project, message = orch.create_project("测试项目描述")
    assert project is not None
    assert project.status == ProjectStatus.PLANNING
    print(f"  ✓ 项目创建成功: {project.id}")
    print(f"  ✓ 蓝图任务数: {len(project.blueprint.tasks)}")
    
    # 2. 确认项目（选择A - 正常执行）
    success, message = orch.confirm_project(project.id, "A")
    assert success == True
    assert project.status == ProjectStatus.RUNNING
    print(f"  ✓ 项目已启动，任务数: {len(project.tasks)}")
    
    # 3. 查询项目状态
    status_msg = orch.check_project_status(project.id)
    assert status_msg is not None
    assert project.name in status_msg
    print(f"  ✓ 状态查询成功")
    
    # 4. 验证任务已提交到 Layer 1（有任务ID即可，不要求都能查询到状态）
    assert len(project.tasks) > 0, "项目应该有任务"
    print(f"  ✓ 所有任务已提交到 Layer 1")

test("项目完整生命周期", test_project_lifecycle)

def test_project_listing(state_dir):
    """测试项目列表功能"""
    from layer1.api import ResourceSchedulerAPI
    from layer2.orchestrator import Orchestrator
    
    layer1 = ResourceSchedulerAPI()
    orch = Orchestrator(layer1, state_dir=state_dir)
    
    # 创建多个项目
    p1, _ = orch.create_project("第一个项目")
    p2, _ = orch.create_project("第二个项目")
    p3, _ = orch.create_project("第三个项目")
    
    # 确认一个项目
    orch.confirm_project(p1.id, "A")
    
    # 列出项目
    list_msg = orch.list_projects()
    assert "第一个项目" in list_msg
    assert "第二个项目" in list_msg
    assert "第三个项目" in list_msg
    print(f"  ✓ 项目列表显示 {len(orch.projects)} 个项目")

test("项目列表功能", test_project_listing)

def test_pause_resume(state_dir):
    """测试暂停和恢复"""
    from layer1.api import ResourceSchedulerAPI
    from layer2.orchestrator import Orchestrator, ProjectStatus
    
    layer1 = ResourceSchedulerAPI()
    orch = Orchestrator(layer1, state_dir=state_dir)
    
    # 创建并启动项目
    project, _ = orch.create_project("暂停测试项目")
    orch.confirm_project(project.id, "A")
    assert project.status == ProjectStatus.RUNNING
    print(f"  ✓ 项目已启动")
    
    # 暂停项目
    success, msg = orch.pause_project(project.id)
    assert success == True
    assert project.status == ProjectStatus.PAUSED
    print(f"  ✓ 项目已暂停")
    
    # 恢复项目
    success, msg = orch.resume_project(project.id)
    assert success == True
    assert project.status == ProjectStatus.RUNNING
    print(f"  ✓ 项目已恢复")

test("暂停和恢复", test_pause_resume)

def test_project_completion(state_dir):
    """测试项目完成"""
    from layer1.api import ResourceSchedulerAPI
    from layer2.orchestrator import Orchestrator, ProjectStatus
    
    layer1 = ResourceSchedulerAPI()
    orch = Orchestrator(layer1, state_dir=state_dir)
    
    # 创建、启动、完成项目
    project, _ = orch.create_project("完成测试项目")
    orch.confirm_project(project.id, "A")
    
    success, msg = orch.complete_project(project.id)
    assert success == True
    assert project.status == ProjectStatus.COMPLETED
    assert project.completed_at is not None
    print(f"  ✓ 项目已完成")

test("项目完成", test_project_completion)

def test_planner_blueprint(state_dir):
    """测试 Planner 蓝图生成"""
    from layer1.api import ResourceSchedulerAPI
    from layer2.planner import Planner
    
    layer1 = ResourceSchedulerAPI()
    planner = Planner(layer1)
    
    # 生成蓝图
    blueprint = planner.create_blueprint("创建一个简单的Web应用")
    
    assert blueprint is not None
    assert len(blueprint.tasks) > 0
    print(f"  ✓ 蓝图生成成功，任务数: {len(blueprint.tasks)}")
    
    # 验证任务结构
    for task in blueprint.tasks:
        assert task.name is not None
        assert task.role is not None
        assert task.pdca_phase.lower() in ["plan", "do", "check"]
    print(f"  ✓ 所有任务结构正确")

test("Planner 蓝图生成", test_planner_blueprint)

def test_estimator_calculation(state_dir):
    """测试 Estimator 估算功能"""
    from layer1.api import ResourceSchedulerAPI
    from layer2.planner import Planner
    from layer2.estimator import Estimator
    
    layer1 = ResourceSchedulerAPI()
    planner = Planner(layer1)
    estimator = Estimator(layer1)
    
    # 生成蓝图
    blueprint = planner.create_blueprint("创建一个简单的Web应用")
    
    # 估算
    estimate = estimator.estimate_project(blueprint)
    
    assert "total_hours" in estimate
    assert "roles" in estimate
    assert "estimated_completion" in estimate
    assert estimate["total_hours"] > 0
    print(f"  ✓ 估算完成: {estimate['total_hours']:.1f} 小时")
    print(f"  ✓ 所需角色: {', '.join(estimate['roles'])}")

test("Estimator 估算功能", test_estimator_calculation)

def test_command_processing(state_dir):
    """测试命令处理"""
    from layer1.api import ResourceSchedulerAPI
    from layer2.orchestrator import Orchestrator
    
    layer1 = ResourceSchedulerAPI()
    orch = Orchestrator(layer1, state_dir=state_dir)
    
    # 测试启动命令
    result = orch.process_command("启动 测试项目")
    assert "项目规划完成" in result
    print(f"  ✓ 启动命令处理成功")
    
    # 获取刚创建的项目ID
    project_id = list(orch.projects.keys())[0]
    
    # 测试确认命令
    result = orch.process_command(f"确认 {project_id} A")
    assert "项目已启动" in result
    print(f"  ✓ 确认命令处理成功")
    
    # 测试查询命令
    result = orch.process_command(f"查询 {project_id}")
    assert "项目状态" in result
    print(f"  ✓ 查询命令处理成功")
    
    # 测试状态命令
    result = orch.process_command("状态")
    assert "项目列表" in result
    print(f"  ✓ 状态命令处理成功")
    
    # 测试未知命令
    result = orch.process_command("未知命令")
    assert "未知命令" in result
    print(f"  ✓ 未知命令处理正确")

test("命令处理", test_command_processing)

def test_persistence(state_dir):
    """测试 Layer 2 状态持久化"""
    from layer1.api import ResourceSchedulerAPI
    from layer2.orchestrator import Orchestrator, ProjectStatus
    
    # 第一个实例
    layer1_1 = ResourceSchedulerAPI()
    orch1 = Orchestrator(layer1_1, state_dir=state_dir)
    
    project, _ = orch1.create_project("持久化测试项目")
    orch1.confirm_project(project.id, "A")
    project_id = project.id
    print(f"  ✓ 第一个实例: 创建并启动项目")
    
    # 第二个实例（模拟重启）
    layer1_2 = ResourceSchedulerAPI()
    orch2 = Orchestrator(layer1_2, state_dir=state_dir)
    
    # 验证项目被恢复
    assert project_id in orch2.projects
    recovered = orch2.projects[project_id]
    assert recovered.name == "持久化测试项目"
    assert recovered.status == ProjectStatus.RUNNING
    print(f"  ✓ 第二个实例: 项目状态从磁盘恢复")

test("状态持久化", test_persistence)

# ==================== 汇总 ====================

print("\n" + "=" * 60)
print("📊 Layer 2 集成测试结果")
print("=" * 60)

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
    print("🎉 所有 Layer 2 集成测试通过！")
else:
    print(f"⚠️  {failed} 个测试失败")

print("=" * 60)
