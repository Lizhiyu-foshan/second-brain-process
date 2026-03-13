#!/usr/bin/env python3
"""
BMAD-EVO 流程模拟
演示完整的约束驱动开发流程
"""

import json
from datetime import datetime, timedelta

# ============ 模拟数据 ============

# 1. 项目启动 - 创建项目章程
project_charter = {
    "project": {
        "name": "用户评论系统",
        "vision": "让用户可以方便地对文章进行评论和互动",
        "success_criteria": [
            "日活用户使用率 > 30%",
            "评论加载时间 < 100ms",
            "垃圾评论率 < 5%"
        ]
    },
    "constraints": {
        "hard": {
            "time": {
                "deadline": "2026-03-15",
                "milestones": [
                    "原型: 2026-03-05",
                    "测试: 2026-03-12",
                    "上线: 2026-03-15"
                ]
            },
            "budget": {
                "max_cost": 5000,
                "resources": ["2台服务器", "1个开发"]
            },
            "compliance": [
                "符合网络安全法",
                "用户数据加密存储"
            ]
        },
        "soft": {
            "tech_stack": {
                "prefer": ["PostgreSQL", "Redis", "Node.js"],
                "avoid": ["MongoDB", "微服务架构"]
            },
            "quality": {
                "test_coverage": "> 80%",
                "code_review": True,
                "doc_required": True
            }
        }
    },
    "risks": [
        {
            "id": "R1",
            "desc": "数据量增长超预期",
            "probability": "中",
            "impact": "高",
            "mitigation": "预留分库分表扩展点"
        },
        {
            "id": "R2",
            "desc": "垃圾评论泛滥",
            "probability": "高",
            "impact": "中",
            "mitigation": "接入第三方审核API"
        }
    ]
}

# 2. 模拟各阶段输出
def simulate_stage(stage_name, agent, output, constraints_check, decisions=None):
    """模拟一个阶段的执行"""
    print(f"\n{'='*60}")
    print(f"🔄 阶段：{stage_name}")
    print(f"👤 Agent：{agent}")
    print(f"{'='*60}")
    
    # 阶段输出
    print(f"\n📄 输出：{output['title']}")
    print(f"   {output['content'][:200]}...")
    
    # 约束检查
    print(f"\n🔍 约束检查：")
    for check in constraints_check:
        status = "✅" if check['pass'] else "⚠️"
        print(f"   {status} {check['name']}: {check['message']}")
    
    # 决策记录
    if decisions:
        print(f"\n📝 决策记录：")
        for d in decisions:
            print(f"   - {d['title']}: {d['reason']}")
    
    return {
        "stage": stage_name,
        "agent": agent,
        "output": output,
        "checks": constraints_check,
        "decisions": decisions or []
    }

# ============ 模拟执行 ============

print("🚀 BMAD-EVO 流程模拟开始")
print(f"项目：{project_charter['project']['name']}")
print(f"愿景：{project_charter['project']['vision']}")
print(f"时间约束：{project_charter['constraints']['hard']['time']['deadline']}")

# 阶段1：分析师
stage1 = simulate_stage(
    stage_name="需求分析",
    agent="业务分析师 Mary",
    output={
        "title": "需求简报.md",
        "content": "用户评论系统需求分析...\n- 功能：发表评论、回复、点赞\n- 用户：注册用户可评论，游客可查看\n- 数据：评论内容、作者、时间、点赞数"
    },
    constraints_check=[
        {"name": "时间约束", "pass": True, "message": "预计2天完成，符合里程碑"},
        {"name": "需求清晰度", "pass": True, "message": "需求可测，覆盖核心场景"}
    ],
    decisions=[
        {"title": "支持嵌套回复", "reason": "提升互动深度，但控制最多3层"}
    ]
)

# 阶段2：产品经理
stage2 = simulate_stage(
    stage_name="产品设计",
    agent="产品经理 Bob",
    output={
        "title": "PRD文档.md",
        "content": "产品需求文档...\n- 评论列表页\n- 评论详情页\n- 评论输入框\n- 点赞/回复按钮"
    },
    constraints_check=[
        {"name": "技术选型", "pass": True, "message": "PostgreSQL 符合 prefer 列表"},
        {"name": "时间约束", "pass": True, "message": "PRD 2天内完成"}
    ],
    decisions=[
        {"title": "评论排序", "reason": "默认按时间倒序，可选按热度"}
    ]
)

# 阶段3：架构师（触发约束违反）
print(f"\n{'='*60}")
print(f"🔄 阶段：架构设计")
print(f"👤 Agent：架构师 Alex")
print(f"{'='*60}")

print(f"\n📄 输出：技术方案.md")
print(f"   技术选型：PostgreSQL + Node.js + Express")
print(f"   API 设计：GET /comments, POST /comments...")
print(f"   预计性能：API 响应时间 150ms")

print(f"\n🔍 约束检查：")
print(f"   ❌ 性能约束：预计 150ms > 100ms 目标")

print(f"\n🤔 自反思：")
print(f"   问题：响应时间超出约束")
print(f"   方案1：引入 Redis 缓存 → 预计 80ms ✅")
print(f"   方案2：优化查询 → 预计 120ms ❌")
print(f"   方案3：异步加载 → 影响体验 ❌")

print(f"\n✅ 自动选择：引入 Redis 缓存")

print(f"\n📝 决策记录：")
print(f"   - 引入 Redis 缓存：满足性能约束，+0.5天开发时间")

stage3 = {
    "stage": "架构设计",
    "agent": "架构师 Alex",
    "output": {"title": "技术方案.md", "content": "..."},
    "checks": [
        {"name": "性能约束", "pass": True, "message": "引入 Redis 后预计 80ms"},
        {"name": "技术选型", "pass": True, "message": "PostgreSQL + Redis 符合 prefer"}
    ],
    "decisions": [
        {"title": "引入 Redis 缓存", "reason": "满足 <100ms 性能约束"}
    ]
}

# 阶段4：开发
stage4 = simulate_stage(
    stage_name="开发实现",
    agent="开发者 David",
    output={
        "title": "代码实现",
        "content": "src/\n- controllers/comment.js\n- models/comment.js\n- services/comment.js\n测试覆盖率：75%"
    },
    constraints_check=[
        {"name": "功能完成", "pass": True, "message": "核心功能已实现"},
        {"name": "测试覆盖", "pass": False, "message": "75% < 80% 目标"}
    ],
    decisions=[]
)

# 自反思：测试覆盖不足
print(f"\n🤔 自反思：")
print(f"   问题：测试覆盖率 75% < 80%")
print(f"   方案1：补充边界测试 → +0.3天 ✅")
print(f"   方案2：降低要求 → 违反约束 ❌")
print(f"\n✅ 自动选择：补充边界测试")

# 阶段5：QA
stage5 = simulate_stage(
    stage_name="测试验收",
    agent="QA 工程师 Emily",
    output={
        "title": "测试报告",
        "content": "测试完成...\n- 功能测试：通过\n- 性能测试：85ms < 100ms ✅\n- 安全测试：通过"
    },
    constraints_check=[
        {"name": "功能测试", "pass": True, "message": "全部通过"},
        {"name": "性能测试", "pass": True, "message": "85ms < 100ms"},
        {"name": "安全测试", "pass": True, "message": "无漏洞"}
    ],
    decisions=[]
)

# ============ 项目复盘 ============

print(f"\n{'='*60}")
print(f"📊 项目复盘")
print(f"{'='*60}")

print(f"\n项目：用户评论系统")
print(f"周期：2026-02-20 至 2026-03-14（提前1天）")
print(f"状态：✅ 成功上线")

print(f"\n约束达成情况：")
print(f"  ✅ 时间：14天 / 15天")
print(f"  ✅ 预算：4800元 / 5000元")
print(f"  ✅ 性能：85ms < 100ms")
print(f"  ✅ 测试覆盖：82% > 80%")
print(f"  ✅ 安全合规：100%")

print(f"\n关键决策：")
print(f"  1. 引入 Redis 缓存：满足性能约束")
print(f"  2. 补充边界测试：满足质量约束")

print(f"\n形成模式：")
print(f"  已保存到：patterns/comment-system-v1.md")

print(f"\n🎉 BMAD-EVO 流程模拟完成！")
