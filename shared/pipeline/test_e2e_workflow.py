#!/usr/bin/env python3
"""
端到端（E2E）工作流测试
完整模拟：用户创建项目 → 任务调度 → 角色执行 → PDCA循环
"""
import os
import sys
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime

# 设置测试环境
tmp_dir = tempfile.mkdtemp()
os.environ["OPENCLAW_WORKSPACE"] = tmp_dir
os.environ["DASHSCOPE_API_KEY"] = "sk-test-key"

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("🎭 端到端（E2E）工作流测试")
print("=" * 70)
print(f"测试目录: {tmp_dir}")
print()

# 导入系统组件
from layer1.api import ResourceSchedulerAPI
from layer2.orchestrator import Orchestrator, ProjectStatus
from shared.models import Task

# 初始化系统
layer1 = ResourceSchedulerAPI()
orchestrator = Orchestrator(layer1, state_dir=str(Path(tmp_dir) / "layer2_state"))

print("✅ 系统初始化完成")
print(f"   - 已注册角色: {len(layer1.registry.list_all())} 个")
print()

# ==================== E2E 测试场景 ====================

print("━" * 70)
print("🎬 场景1: 完整项目生命周期")
print("━" * 70)

# Step 1: 用户创建项目
print("\n📋 Step 1: 用户创建项目")
print("-" * 50)

user_input = "创建一个Python CLI工具，用于管理待办事项，支持添加、删除、列出任务"
print(f"用户输入: {user_input[:50]}...")

project, planning_msg = orchestrator.create_project(user_input)
print(f"✅ 项目创建成功: {project.id}")
print(f"   项目名称: {project.name}")
print(f"   初始状态: {project.status.value}")
print(f"   蓝图任务数: {len(project.blueprint.tasks)}")

# 显示生成的任务
print(f"\n📋 生成的任务列表:")
for i, task in enumerate(project.blueprint.tasks, 1):
    print(f"   {i}. [{task.role.upper()}] {task.name} ({task.pdca_phase})")

# Step 2: 用户确认方案
print("\n📋 Step 2: 用户确认方案")
print("-" * 50)

print("用户选择: A (正常执行)")
success, confirm_msg = orchestrator.confirm_project(project.id, "A")
print(f"✅ {confirm_msg.split(chr(10))[0]}")  # 第一行
print(f"   项目状态: {project.status.value}")
print(f"   提交任务数: {len(project.tasks)}")

# Step 3: 模拟角色 Worker 执行任务
print("\n📋 Step 3: 角色 Worker 获取并执行任务")
print("-" * 50)

completed_tasks = []
max_iterations = 20  # 防止无限循环
iteration = 0

while iteration < max_iterations:
    iteration += 1
    
    # 获取所有空闲角色
    idle_roles = layer1.registry.get_idle_roles()
    if not idle_roles:
        print(f"   迭代 {iteration}: 无空闲角色，等待...")
        break
    
    # 尝试为每个空闲角色分配任务
    tasks_executed_this_round = 0
    
    for role in idle_roles:
        # 获取该角色的下一个任务
        next_task = layer1.task_queue.get_next_for_role(role.id)
        if not next_task:
            continue
        
        print(f"   迭代 {iteration}: [{role.id}] 获取任务: {next_task.name}")
        
        # 获取锁
        lock_result = layer1.acquire_lock(role.id, next_task.id)
        if not lock_result["acquired"]:
            print(f"      ⚠️ 获取锁失败，跳过")
            continue
        
        # 模拟任务执行
        print(f"      🔄 执行任务中...")
        time.sleep(0.1)  # 模拟执行时间
        
        # 完成任务
        layer1.complete_task(
            next_task.id, 
            success=True, 
            result={"output": f"由 {role.id} 完成", "files": [f"{next_task.id}.py"]}
        )
        layer1.release_lock(role.id)
        
        completed_tasks.append(next_task.id)
        tasks_executed_this_round += 1
        print(f"      ✅ 任务完成: {next_task.id}")
    
    if tasks_executed_this_round == 0:
        # 检查是否还有未完成的任务
        all_done = True
        for task_id in project.tasks:
            status = layer1.get_task_status(task_id)
            if status and status["status"] not in ["completed", "failed"]:
                all_done = False
                break
        if all_done:
            print(f"   迭代 {iteration}: 所有任务已完成")
            break

print(f"\n✅ 任务执行完成")
print(f"   总迭代次数: {iteration}")
print(f"   完成任务数: {len(completed_tasks)}/{len(project.tasks)}")

# Step 4: 查询项目状态
print("\n📋 Step 4: 查询项目最终状态")
print("-" * 50)

status_msg = orchestrator.check_project_status(project.id)
print(status_msg)

# ==================== 场景2: PDCA 循环 ====================

print("\n" + "━" * 70)
print("🎬 场景2: PDCA 循环测试（含失败和修复）")
print("━" * 70)

# 创建一个新项目，模拟部分任务失败
print("\n📋 Step 1: 创建新项目")
project2, _ = orchestrator.create_project("创建Web API服务")
orchestrator.confirm_project(project2.id, "A")
print(f"✅ 项目启动: {project2.id}")

# 模拟部分任务成功，部分失败
print("\n📋 Step 2: 模拟任务执行（部分失败）")
success_count = 0
fail_count = 0

for i, task_id in enumerate(project2.tasks):
    task = layer1.task_queue.get(task_id)
    if not task:
        continue
        
    if i % 2 == 0:  # 偶数任务成功
        # 先获取锁再完成任务
        layer1.acquire_lock(task.role_id, task_id)
        layer1.complete_task(task_id, success=True, result={"output": "成功"})
        layer1.release_lock(task.role_id)
        success_count += 1
    else:  # 奇数任务失败
        # 先获取锁再标记失败
        layer1.acquire_lock(task.role_id, task_id)
        layer1.complete_task(task_id, success=False, result={"error": "模拟错误"})
        layer1.release_lock(task.role_id)
        fail_count += 1

print(f"   成功: {success_count}, 失败: {fail_count}")

# 触发 PDCA Check
print("\n📋 Step 3: 触发 PDCA Check")
check_msg = orchestrator.handle_pdca_check(project2.id)
print(check_msg.split(chr(10))[0])  # 第一行

# 用户决策：调整（修复失败任务）
print("\n📋 Step 4: 用户决策 - 调整")
print("用户选择: B (调整修复)")
success, decision_msg = orchestrator.handle_pdca_decision(project2.id, "B")
print(f"✅ {decision_msg}")

# 验证修复任务已创建
print("\n📋 Step 5: 验证修复任务")
fix_tasks = [t for t in project2.tasks if layer1.task_queue.get(t) and "[Fix]" in (layer1.task_queue.get(t).name or "")]
print(f"   修复任务数: {len(fix_tasks)}")

# ==================== 场景3: 并发多项目 ====================

print("\n" + "━" * 70)
print("🎬 场景3: 并发多项目管理")
print("━" * 70)

# 创建多个项目
projects = []
for i in range(3):
    proj, _ = orchestrator.create_project(f"并发项目 {i+1}")
    orchestrator.confirm_project(proj.id, "A")
    projects.append(proj)
    print(f"✅ 项目 {i+1} 启动: {proj.id[:20]}...")

# 列出所有项目
print("\n📋 所有项目列表:")
list_msg = orchestrator.list_projects()
print(list_msg.split(chr(10))[0])  # 第一行
print(f"   总计: {len(orchestrator.projects)} 个项目")

# 暂停一个项目
print(f"\n📋 暂停项目: {projects[1].id[:20]}...")
success, pause_msg = orchestrator.pause_project(projects[1].id)
print(f"✅ {pause_msg.split(chr(10))[0]}")

# 完成一个项目
print(f"\n📋 完成项目: {projects[2].id[:20]}...")
success, complete_msg = orchestrator.complete_project(projects[2].id)
print(f"✅ {complete_msg}")

# ==================== 场景4: 系统统计 ====================

print("\n" + "━" * 70)
print("🎬 场景4: 系统统计和监控")
print("━" * 70)

stats = layer1.get_statistics()
print("\n📊 Layer 1 统计:")
print(f"   角色: {stats['roles']['total']} 个 (空闲: {stats['roles']['idle']}, 忙碌: {stats['roles']['busy']})")
print(f"   任务: {stats['tasks']}")
print(f"   活跃锁: {stats['locks']['active']} 个")

# ==================== 汇总 ====================

print("\n" + "=" * 70)
print("📊 E2E 测试总结")
print("=" * 70)

print("\n✅ 完成的测试场景:")
print("   1. 完整项目生命周期（创建→确认→执行→完成）")
print("   2. PDCA 循环（Check → 决策 → 修复）")
print("   3. 并发多项目管理")
print("   4. 系统统计和监控")

print("\n📈 测试统计:")
print(f"   创建项目数: {len(orchestrator.projects)}")
print(f"   总任务数: {sum(len(p.tasks) for p in orchestrator.projects.values())}")
print(f"   完成任务数: {len(completed_tasks)}")

# 清理
shutil.rmtree(tmp_dir, ignore_errors=True)

print("\n🎉 端到端工作流测试完成！")
print("=" * 70)
