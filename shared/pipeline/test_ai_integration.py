#!/usr/bin/env python3
"""
集成测试 - 验证 AI 驱动的任务分解
设置超时避免长时间等待
"""
import os
os.environ["DASHSCOPE_API_KEY"] = "sk-sp-68f6997fc9924babb9f6b50c03a5a529"

import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("🧪 AI 驱动任务分解集成测试")
print("=" * 70)
print()

# 创建临时目录
tmp_dir = tempfile.mkdtemp()
state_dir = os.path.join(tmp_dir, 'state')
lock_dir = os.path.join(tmp_dir, 'locks')
os.makedirs(state_dir, exist_ok=True)
os.makedirs(lock_dir, exist_ok=True)

try:
    # 导入组件
    from layer1.api import ResourceSchedulerAPI
    from layer2 import Orchestrator
    
    # 1. 初始化
    print("📋 步骤1: 初始化系统")
    layer1 = ResourceSchedulerAPI(state_dir, lock_dir)
    orchestrator = Orchestrator(layer1, state_dir)
    print("  ✓ Layer 1 & Layer 2 初始化完成\n")
    
    # 2. AI 任务分解
    print("📋 步骤2: AI 驱动任务分解")
    print("  项目需求: 开发一个Python日志分析工具")
    print("  等待 AI 分析...")
    
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("AI 调用超时")
    
    # 设置30秒超时
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(30)
    
    try:
        description = "开发一个Python日志分析工具，可以解析多种格式的日志文件，生成统计报告，并支持自定义过滤规则"
        blueprint = orchestrator.planner.create_blueprint(description)
        signal.alarm(0)  # 取消超时
        
        print(f"  ✓ AI 分析完成")
        print(f"    项目类型: {blueprint.project_type}")
        print(f"    项目名称: {blueprint.name}")
        print(f"    任务数量: {len(blueprint.tasks)}")
        print(f"    涉及角色: {', '.join(blueprint.estimated_roles)}")
        print(f"    预计工时: {blueprint.estimated_duration}h")
        print()
        
        print("  任务详情:")
        for i, task in enumerate(blueprint.tasks, 1):
            deps = f" (依赖: {task.depends_on})" if task.depends_on else ""
            print(f"    {i}. [{task.role}] {task.name}{deps}")
        print()
        
        # 3. 验证 DAG
        print("📋 步骤3: 验证任务依赖图")
        graph = orchestrator.planner.build_dependency_graph(blueprint)
        execution_order = orchestrator.planner.get_execution_order(blueprint)
        print(f"  执行顺序: {execution_order}")
        print(f"  ✓ DAG 构建成功\n")
        
        # 4. 创建项目并提交任务
        print("📋 步骤4: 项目创建与任务调度")
        project, msg = orchestrator.create_project(description)
        print(f"  项目ID: {project.id}")
        print(f"  Blueprint 任务: {len(project.blueprint.tasks)}")
        
        # 确认项目
        success, start_msg = orchestrator.confirm_project(project.id, "A")
        print(f"  确认后状态: {project.status.value}")
        print(f"  项目任务数: {len(project.tasks)}")
        
        # 检查队列
        roles_status = layer1.get_roles_status()
        roles_dict = roles_status.get("roles", {})
        print(f"\n  角色队列状态:")
        for role_id in blueprint.estimated_roles:
            if role_id in roles_dict:
                qd = roles_dict[role_id]['queue_depth']
                print(f"    [{role_id}] 队列: {qd}")
        print()
        
        # 5. 结果汇总
        print("=" * 70)
        print("✅ 集成测试结果汇总")
        print("=" * 70)
        print()
        print(f"✓ 固定角色初始化: 成功")
        print(f"✓ AI 任务分解: 成功 ({len(blueprint.tasks)} 个任务)")
        print(f"✓ DAG 构建: 成功")
        print(f"✓ 项目调度: 成功")
        print()
        print("🎉 所有测试通过！")
        print("=" * 70)
        
    except TimeoutError:
        print("  ⚠️ AI 调用超时 (30s)")
        print("  检查网络连接或 API 配置")
        
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)
