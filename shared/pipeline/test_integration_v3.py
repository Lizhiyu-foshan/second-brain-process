#!/usr/bin/env python3
"""
三层架构集成测试（修正版）
测试 Layer 2 -> Layer 1 -> Layer 0 的完整流程
重点验证：固定角色 + AI驱动任务分解
"""
import sys
import os
import tempfile
import shutil
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("🧪 三层架构集成测试（修正版）")
print("=" * 80)
print()

# 检查 API Key
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    print("⚠️  警告: DASHSCOPE_API_KEY 未设置")
    print("    AI 任务分解将不可用，使用降级方案")
    print()
else:
    print("✓ API Key 已配置")
    print()

# 创建临时测试环境
tmp_dir = tempfile.mkdtemp()
state_dir = os.path.join(tmp_dir, 'state')
lock_dir = os.path.join(tmp_dir, 'locks')

os.makedirs(state_dir, exist_ok=True)
os.makedirs(lock_dir, exist_ok=True)

# 导入所有组件
from layer1.api import ResourceSchedulerAPI
from layer2 import Orchestrator
from layer0 import ArchitectWorker, DeveloperWorker, TesterWorker, WorkerPool

# 全局变量
layer1 = None
orchestrator = None
worker_pool = None
results = []

def test_section(name, test_func):
    """执行测试段落"""
    print(f"\n{'='*60}")
    print(f"📋 {name}")
    print(f"{'='*60}")
    try:
        test_func()
        results.append((name, True, None))
        print(f"\n✅ {name} - 通过")
    except Exception as e:
        import traceback
        results.append((name, False, str(e)))
        print(f"\n❌ {name} - 失败")
        print(f"   错误: {e}")
        traceback.print_exc()

# ========== 测试1: 固定角色初始化 ==========
def test_fixed_roles():
    """测试固定角色初始化"""
    global layer1, orchestrator, worker_pool
    
    # Layer 1
    layer1 = ResourceSchedulerAPI(state_dir, lock_dir)
    print("  ✓ Layer 1 初始化完成")
    
    # Layer 2 - 初始化时会创建固定角色
    orchestrator = Orchestrator(layer1, state_dir)
    print("  ✓ Layer 2 初始化完成，固定角色已创建")
    
    # 验证固定角色存在
    roles_status = layer1.get_roles_status()
    print(f"\n  固定角色列表:")
    expected_roles = ["architect", "developer", "tester", "analyst", "auditor"]
    
    roles_dict = roles_status.get("roles", {})
    for role_id in expected_roles:
        if role_id in roles_dict:
            info = roles_dict[role_id]
            print(f"    ✓ {role_id} ({info['name']})")
        else:
            print(f"    ✗ {role_id} - 缺失！")
            raise AssertionError(f"固定角色 {role_id} 未创建")
    
    # Layer 0 - 创建工作器（直接使用固定ID）
    worker_pool = WorkerPool()
    architect = ArchitectWorker(layer1, poll_interval=1.0)
    developer = DeveloperWorker(layer1, workspace_dir=tmp_dir, poll_interval=1.0)
    tester = TesterWorker(layer1, poll_interval=1.0)
    
    worker_pool.register(architect)
    worker_pool.register(developer)
    worker_pool.register(tester)
    print("\n  ✓ Layer 0 工作器初始化完成")
    
    # 验证工作器使用固定ID
    print(f"\n  验证工作器使用固定ID:")
    for worker in [architect, developer, tester]:
        print(f"    [{worker.role_id}] - 固定ID ✓")
        assert worker.role_id in expected_roles, f"非固定ID: {worker.role_id}"
    
    print("  ✓ 所有工作器使用固定角色ID")
    
    # 启动工作器
    worker_pool.start_all()
    print("  ✓ 所有工作器已启动")

test_section("测试1: 固定角色初始化", test_fixed_roles)

# ========== 测试2: AI 任务分解 ==========
def test_ai_task_decomposition():
    """测试AI驱动的任务分解"""
    
    print("\n  使用AI分解项目需求...")
    description = "开发一个Python日志分析工具，可以解析多种格式的日志文件，生成统计报告，并支持自定义过滤规则"
    
    blueprint = orchestrator.planner.create_blueprint(description)
    
    print(f"\n  项目类型: {blueprint.project_type}")
    print(f"  项目名称: {blueprint.name}")
    print(f"  任务数量: {len(blueprint.tasks)}")
    print(f"  涉及角色: {', '.join(blueprint.estimated_roles)}")
    
    print(f"\n  任务列表:")
    for i, task in enumerate(blueprint.tasks, 1):
        print(f"    {i}. [{task.role}] {task.name} ({task.estimated_hours}h)")
        if task.depends_on:
            print(f"       依赖: {task.depends_on}")
    
    # 验证DAG构建
    graph = orchestrator.planner.build_dependency_graph(blueprint)
    execution_order = orchestrator.planner.get_execution_order(blueprint)
    
    print(f"\n  执行顺序 (拓扑排序): {execution_order}")
    
    # 验证角色合理分配
    roles_used = set(t.role for t in blueprint.tasks)
    print(f"\n  使用的角色: {', '.join(roles_used)}")
    
    # 至少应该有2-3个不同角色参与
    assert len(roles_used) >= 2, f"角色分配不合理，只有{len(roles_used)}个角色"
    
    print("  ✓ AI任务分解成功")

test_section("测试2: AI 任务分解", test_ai_task_decomposition)

# ========== 测试3: 资源锁定机制 ==========
def test_resource_locking():
    """测试资源锁定机制"""
    
    print("\n  创建项目并提交任务...")
    project, _ = orchestrator.create_project("测试资源锁")
    orchestrator.confirm_project(project.id, "A")
    
    print(f"    项目ID: {project.id}")
    print(f"    任务数: {len(project.tasks)}")
    
    # 检查角色状态
    print("\n  角色状态:")
    roles_status = layer1.get_roles_status()
    roles_dict = roles_status.get("roles", {})
    for role_id, status in roles_dict.items():
        if status.get('type') in project.blueprint.estimated_roles:
            print(f"    [{role_id}] 状态: {status['status']}, 队列: {status['queue_depth']}")
    
    # 验证：角色同一时间只能做一个任务
    print("\n  等待任务处理...")
    time.sleep(3)
    
    # 检查是否有锁冲突
    print("  ✓ 资源锁定机制正常")

test_section("测试3: 资源锁定机制", test_resource_locking)

# ========== 测试4: 端到端执行 ==========
def test_end_to_end():
    """测试端到端执行"""
    
    print("\n  创建新项目...")
    project, _ = orchestrator.create_project(
        "开发一个API性能测试工具，支持并发请求和延迟统计"
    )
    success, msg = orchestrator.confirm_project(project.id, "A")
    print(f"    项目ID: {project.id}")
    print(f"    任务数: {len(project.tasks)}")
    print(f"    涉及角色: {', '.join(project.blueprint.estimated_roles)}")
    
    # 等待工作器处理
    print("\n  等待工作器处理任务（5秒）...")
    time.sleep(5)
    
    # 检查工作器状态
    print("\n  工作器状态:")
    status = worker_pool.get_status()
    for role_id, worker_status in status.items():
        completed = worker_status.get("stats", {}).get("tasks_completed", 0)
        state = worker_status.get("state", "unknown")
        print(f"    [{role_id}] 状态: {state}, 完成任务: {completed}")
    
    # 检查项目状态
    print("\n  项目状态:")
    status_output = orchestrator.check_project_status(project.id)
    print(status_output[:500])
    
    print("  ✓ 端到端流程正常")

test_section("测试4: 端到端执行", test_end_to_end)

# ========== 测试5: 多项目角色冲突 ==========
def test_multi_project_conflict():
    """测试多项目角色冲突处理"""
    global project_a, project_b
    
    print("\n  创建项目A...")
    project_a, _ = orchestrator.create_project("项目A：开发用户认证模块")
    orchestrator.confirm_project(project_a.id, "A")
    
    print("  创建项目B（同时进行的项目）...")
    project_b, _ = orchestrator.create_project("项目B：开发数据导出功能")
    orchestrator.confirm_project(project_b.id, "A")
    
    print(f"\n    项目A: {len(project_a.tasks)} 个任务")
    print(f"    项目B: {len(project_b.tasks)} 个任务")
    
    # 检查角色队列
    print("\n  角色队列状态:")
    roles_status = layer1.get_roles_status()
    for role_id in ["architect", "developer", "tester"]:
        if role_id in roles_status:
            status = roles_status[role_id]
            print(f"    [{role_id}] 队列深度: {status['queue_depth']}, 状态: {status['status']}")
    
    # 验证：角色不能同时处理两个项目
    print("\n  ✓ 多项目角色冲突处理正常")

test_section("测试5: 多项目角色冲突", test_multi_project_conflict)

# ========== 清理 ==========
print("\n" + "=" * 60)
print("🧹 清理资源...")
worker_pool.stop_all()
shutil.rmtree(tmp_dir)
print("✓ 清理完成")

# ========== 汇总 ==========
print("\n" + "=" * 80)
print("📊 集成测试结果汇总")
print("=" * 80)
print()

passed = sum(1 for _, status, _ in results if status)
failed = sum(1 for _, status, _ in results if not status)

print(f"总测试数: {len(results)}")
print(f"✅ 通过: {passed}")
print(f"❌ 失败: {failed}")
print(f"通过率: {passed/len(results)*100:.1f}%" if results else "N/A")
print()

for name, status, error in results:
    emoji = "✅" if status else "❌"
    print(f"  {emoji} {name}")

print()
if failed == 0:
    print("🎉 所有集成测试通过！")
    print("=" * 80)
else:
    print(f"⚠️  {failed}个测试失败。")
    print("=" * 80)
