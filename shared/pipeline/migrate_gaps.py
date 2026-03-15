#!/usr/bin/env python3
"""
GAP 任务迁移脚本
将 GAP02~GAP04 迁移到 Pipeline 框架
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from layer1.api import ResourceSchedulerAPI
from layer2.orchestrator import Orchestrator
from shared.models import Task

# 初始化系统
layer1 = ResourceSchedulerAPI()
orchestrator = Orchestrator(layer1, state_dir="./gap_state")

print("=" * 70)
print("🔄 GAP 任务迁移到 Pipeline 框架")
print("=" * 70)

# GAP 定义
GAPS = {
    "GAP02": {
        "title": "跨系统定时任务状态监控缺失",
        "description": "OpenClaw 2026.2.13版本更新导致isolated+agentTurn模式失效，所有定时任务停止执行但系统显示'成功'。缺乏统一的任务执行健康度仪表盘。",
        "skill_name": "cron-health-dashboard",
        "priority": "P0",  # 高优先级
        "role": "developer",
        "estimated_hours": 8,
        "pdca_phase": "Do"
    },
    "GAP03": {
        "title": "Skill名称语义匹配失效导致重复推荐",
        "description": "AI分析器推荐的skill名称与实际安装的skill名称存在语义鸿沟，导致已安装功能被误判为缺口。缺乏skill功能语义索引而非字符串匹配。",
        "skill_name": "skill-semantic-index",
        "priority": "P1",
        "role": "architect",
        "estimated_hours": 6,
        "pdca_phase": "Plan"
    },
    "GAP04": {
        "title": "讨论准备与知识预加载依赖人工触发",
        "description": "用户需主动输入'主题讨论'或等待14:00定时检查才能启动知识预加载，缺乏基于日程的智能预判。",
        "skill_name": "calendar-aware-prep",
        "priority": "P2",
        "role": "analyst",
        "estimated_hours": 4,
        "pdca_phase": "Check"
    }
}

# 创建项目
def create_gap_project():
    """创建 GAP 迁移项目"""
    project_desc = """迁移 GAP02~GAP04 到 Pipeline 框架：
- GAP02: cron-health-dashboard (高优先级，今晚完成)
- GAP03: skill-semantic-index (中优先级)
- GAP04: calendar-aware-prep (低优先级)
"""
    
    project, message = orchestrator.create_project(project_desc)
    print(f"✅ 项目创建成功: {project.id}")
    print(f"   项目名称: {project.name}")
    
    # 确认项目
    success, confirm_msg = orchestrator.confirm_project(project.id, "A")
    print(f"✅ 项目已启动")
    
    return project

# 手动添加 GAP 任务（因为蓝图生成可能不完整）
def add_gap_tasks(project_id):
    """为项目添加 GAP 任务"""
    print("\n📋 添加 GAP 任务到项目:")
    
    for gap_id, gap_info in GAPS.items():
        task_data = {
            "project_id": project_id,
            "role_id": gap_info["role"],
            "name": f"[{gap_id}] {gap_info['title']}",
            "description": gap_info["description"],
            "priority": gap_info["priority"],
            "metadata": {
                "gap_id": gap_id,
                "skill_name": gap_info["skill_name"],
                "estimated_hours": gap_info["estimated_hours"],
                "pdca_phase": gap_info["pdca_phase"]
            }
        }
        
        result = layer1.submit_task(task_data)
        if result["success"]:
            print(f"   ✅ {gap_id}: {gap_info['skill_name']} ({gap_info['priority']})")
        else:
            print(f"   ❌ {gap_id}: 提交失败 - {result.get('message')}")

# 主流程
if __name__ == "__main__":
    print(f"\n🎯 迁移目标:")
    for gap_id, info in GAPS.items():
        print(f"   {gap_id}: {info['skill_name']} ({info['priority']})")
    
    print(f"\n🚀 开始迁移...")
    project = create_gap_project()
    add_gap_tasks(project.id)
    
    print(f"\n" + "=" * 70)
    print(f"✅ GAP02~GAP04 已迁移到 Pipeline 项目: {project.id}")
    print(f"\n下一步:")
    print(f"   1. 设置 GAP02 (cron-health-dashboard) 今晚 20:00 定时任务")
    print(f"   2. 开始 GAP02 分析、开发、测试")
    print("=" * 70)
