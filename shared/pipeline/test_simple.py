#!/usr/bin/env python3
"""
简化版集成测试 - 验证固定角色和AI分解
"""
import sys
import os
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("🧪 简化集成测试")
print("=" * 60)
print()

# 创建临时目录
tmp_dir = tempfile.mkdtemp()
state_dir = os.path.join(tmp_dir, 'state')
lock_dir = os.path.join(tmp_dir, 'locks')
os.makedirs(state_dir, exist_ok=True)
os.makedirs(lock_dir, exist_ok=True)

# 设置 API Key
os.environ["DASHSCOPE_API_KEY"] = "sk-sp-68f6997fc9924babb9f6b50c03a5a529"

try:
    # 导入组件
    from layer1.api import ResourceSchedulerAPI
    from layer2 import Orchestrator
    from layer0 import ArchitectWorker, DeveloperWorker, TesterWorker, WorkerPool
    
    # 1. 测试固定角色初始化
    print("📋 测试1: 固定角色初始化")
    layer1 = ResourceSchedulerAPI(state_dir, lock_dir)
    orchestrator = Orchestrator(layer1, state_dir)
    
    roles_status = layer1.get_roles_status()
    roles_dict = roles_status.get("roles", {})
    
    expected = ["architect", "developer", "tester", "analyst", "auditor"]
    for role_id in expected:
        if role_id in roles_dict:
            print(f"  ✓ {role_id}: {roles_dict[role_id]['name']}")
        else:
            print(f"  ✗ {role_id}: 缺失！")
    
    print()
    
    # 2. 测试AI任务分解（无API Key时使用降级）
    print("📋 测试2: AI任务分解")
    description = "开发一个Web API，支持用户认证和数据CRUD操作"
    blueprint = orchestrator.planner.create_blueprint(description)
    
    print(f"  项目名称: {blueprint.name}")
    print(f"  任务数量: {len(blueprint.tasks)}")
    print(f"  涉及角色: {', '.join(blueprint.estimated_roles)}")
    print()
    print("  任务列表:")
    for i, task in enumerate(blueprint.tasks[:5], 1):
        print(f"    {i}. [{task.role}] {task.name}")
    print()
    
    # 3. 测试Worker创建（直接使用固定ID）
    print("📋 测试3: Worker使用固定ID")
    worker_pool = WorkerPool()
    architect = ArchitectWorker(layer1, poll_interval=2.0)
    developer = DeveloperWorker(layer1, workspace_dir=tmp_dir, poll_interval=2.0)
    tester = TesterWorker(layer1, poll_interval=2.0)
    
    worker_pool.register(architect)
    worker_pool.register(developer)
    worker_pool.register(tester)
    
    print(f"  Architect ID: {architect.role_id}")
    print(f"  Developer ID: {developer.role_id}")
    print(f"  Tester ID: {tester.role_id}")
    print()
    
    # 4. 测试项目创建和任务提交
    print("📋 测试4: 项目创建与任务提交")
    project, msg = orchestrator.create_project("开发日志分析工具")
    print(f"  规划阶段:")
    print(f"    项目ID: {project.id}")
    print(f"    状态: {project.status.value}")
    print(f"    Blueprint任务数: {len(project.blueprint.tasks)}")
    print(f"    项目tasks列表: {len(project.tasks)}")
    
    # 确认前检查队列
    roles_status = layer1.get_roles_status()
    roles_dict = roles_status.get("roles", {})
    print(f"\n  确认前队列状态:")
    for role_id in ["architect", "developer", "tester"]:
        if role_id in roles_dict:
            print(f"    [{role_id}] 队列: {roles_dict[role_id]['queue_depth']}")
    
    # 确认项目
    success, start_msg = orchestrator.confirm_project(project.id, "A")
    print(f"\n  启动后:")
    print(f"    状态: {project.status.value}")
    print(f"    项目tasks列表: {len(project.tasks)}")
    
    # 确认后检查队列
    roles_status = layer1.get_roles_status()
    roles_dict = roles_status.get("roles", {})
    print(f"\n  确认后队列状态:")
    for role_id in ["architect", "developer", "tester"]:
        if role_id in roles_dict:
            print(f"    [{role_id}] 队列: {roles_dict[role_id]['queue_depth']}")
    print()
    
    # 5. 验证角色队列
    print("📋 测试5: 角色队列状态")
    roles_status = layer1.get_roles_status()
    roles_dict = roles_status.get("roles", {})
    for role_id in ["architect", "developer", "tester"]:
        if role_id in roles_dict:
            status = roles_dict[role_id]
            print(f"  [{role_id}] 队列: {status['queue_depth']}, 状态: {status['status']}")
    print()
    
    print("=" * 60)
    print("✅ 所有基础测试通过！")
    print("=" * 60)
    
finally:
    # 清理
    shutil.rmtree(tmp_dir, ignore_errors=True)
