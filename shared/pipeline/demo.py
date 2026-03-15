#!/usr/bin/env python3
"""
双层任务编排系统 - 功能演示
展示完整的工作流程
"""
import sys
import os
import tempfile
import shutil

sys.path.insert(0, '/root/.openclaw/workspace/shared/pipeline')

from layer1.api import ResourceSchedulerAPI
from workers.architect import ArchitectWorker
from workers.developer import DeveloperWorker
from workers.tester import TesterWorker
import threading
import time


def demo_full_workflow():
    """演示完整工作流程"""
    print("=" * 70)
    print("双层任务编排系统 - 功能演示")
    print("=" * 70)
    
    # 创建临时目录
    tmp_dir = tempfile.mkdtemp()
    state_dir = os.path.join(tmp_dir, "state")
    lock_dir = os.path.join(tmp_dir, "locks")
    
    try:
        # 初始化API
        api = ResourceSchedulerAPI(state_dir, lock_dir)
        print("\n✅ Layer 1 API 初始化完成")
        
        # 1. 注册角色
        print("\n--- Step 1: 注册角色 ---")
        architect_id = api.registry.register(
            "architect", "系统架构师", 
            ["gap_analysis", "solution_design", "architecture"]
        )
        developer_id = api.registry.register(
            "developer", "Skill开发者",
            ["skill_creation", "code_implementation", "programming"]
        )
        tester_id = api.registry.register(
            "tester", "质量验证员",
            ["testing", "validation", "quality_assurance"]
        )
        print(f"✅ 角色注册完成:")
        print(f"   - 架构师: {architect_id}")
        print(f"   - 开发者: {developer_id}")
        print(f"   - 测试员: {tester_id}")
        
        # 2. 提交任务
        print("\n--- Step 2: 提交任务 ---")
        
        # 架构任务
        arch_result = api.submit_task({
            "project_id": "PROJ_001",
            "role_id": architect_id,
            "name": "GAP-002 架构设计",
            "description": "设计skill-factory的架构方案",
            "priority": "P1"
        })
        arch_task_id = arch_result["task_id"]
        print(f"✅ 架构任务提交: {arch_task_id}")
        
        # 开发任务（依赖架构）
        dev_result = api.submit_task({
            "project_id": "PROJ_001",
            "role_id": developer_id,
            "name": "GAP-002 开发实现",
            "description": "实现skill-factory核心功能",
            "priority": "P1",
            "depends_on": [arch_task_id]
        })
        dev_task_id = dev_result["task_id"]
        print(f"✅ 开发任务提交: {dev_task_id}")
        
        # 测试任务（依赖开发）
        test_result = api.submit_task({
            "project_id": "PROJ_001",
            "role_id": tester_id,
            "name": "GAP-002 测试验证",
            "description": "验证skill-factory功能正确性",
            "priority": "P1",
            "depends_on": [dev_task_id]
        })
        test_task_id = test_result["task_id"]
        print(f"✅ 测试任务提交: {test_task_id}")
        
        # 3. 显示任务依赖链
        print("\n--- Step 3: 任务依赖链 ---")
        print(f"   {arch_task_id} (架构)")
        print(f"      ↓")
        print(f"   {dev_task_id} (开发)")
        print(f"      ↓")
        print(f"   {test_task_id} (测试)")
        
        # 4. 模拟工作器执行
        print("\n--- Step 4: 角色工作器执行 ---")
        
        # 架构师获取任务
        arch_task = api.poll_task(architect_id)
        if arch_task is None:
            # 先获取锁
            api.acquire_lock(architect_id, arch_task_id)
            arch_task = api.poll_task(architect_id)
        
        if arch_task:
            print(f"🔄 架构师执行任务: {arch_task['name']}")
            time.sleep(0.5)  # 模拟执行
            api.complete_task(arch_task_id, True, {
                "output": "架构设计完成",
                "artifacts": ["design.md"]
            })
            api.release_lock(architect_id)
            print(f"✅ 架构任务完成")
        
        # 开发者获取任务（现在应该可以获取了，因为架构完成）
        time.sleep(0.1)  # 确保状态更新
        dev_task = api.poll_task(developer_id)
        if dev_task is None:
            api.acquire_lock(developer_id, dev_task_id)
            dev_task = api.poll_task(developer_id)
        
        if dev_task:
            print(f"🔄 开发者执行任务: {dev_task['name']}")
            time.sleep(0.5)
            api.complete_task(dev_task_id, True, {
                "output": "开发完成",
                "artifacts": ["skill.py"]
            })
            api.release_lock(developer_id)
            print(f"✅ 开发任务完成")
        
        # 测试员获取任务
        time.sleep(0.1)
        test_task = api.poll_task(tester_id)
        if test_task is None:
            api.acquire_lock(tester_id, test_task_id)
            test_task = api.poll_task(tester_id)
        
        if test_task:
            print(f"🔄 测试员执行任务: {test_task['name']}")
            time.sleep(0.5)
            api.complete_task(test_task_id, True, {
                "output": "测试通过",
                "artifacts": ["test_report.md"],
                "user_decision_required": True
            })
            api.release_lock(tester_id)
            print(f"✅ 测试任务完成")
        
        # 5. 显示最终统计
        print("\n--- Step 5: 最终统计 ---")
        stats = api.get_statistics()
        
        print(f"\n📊 角色状态:")
        for role_id, role_info in api.registry.get_status().items():
            emoji = "🟢" if role_info["status"] == "idle" else "🟡"
            print(f"   {emoji} {role_info['name']}: {role_info['status']}")
        
        print(f"\n📋 任务统计:")
        for status, count in stats['tasks'].items():
            emoji = {"completed": "✅", "failed": "❌", "pending": "⏳", "processing": "🔄"}.get(status, "⭕")
            print(f"   {emoji} {status}: {count}")
        
        print(f"\n🔒 活跃锁: {stats['locks']['active']}")
        
        # 6. 冲突检测
        print("\n--- Step 6: 冲突检测 ---")
        deadlock = api.conflict_detector.detect_deadlock()
        if deadlock:
            print(f"⚠️  检测到死锁: {deadlock}")
        else:
            print("✅ 无死锁")
        
        conflict_summary = api.conflict_detector.get_conflict_summary()
        print(f"   历史冲突总数: {conflict_summary['total']}")
        
        print("\n" + "=" * 70)
        print("✅ 演示完成！")
        print("=" * 70)
        
    finally:
        shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    demo_full_workflow()
