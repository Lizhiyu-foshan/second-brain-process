#!/usr/bin/env python3
"""
自我进化系统 - 改进实施器

将AI发现的Gap转化为具体可执行的改进任务
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
LEARNINGS_DIR = WORKSPACE / ".learnings"

# 加载AI分析结果
AI_RESULT_FILE = LEARNINGS_DIR / "ai_gap_analysis.json"

def load_gaps():
    """加载AI分析的Gap"""
    if not AI_RESULT_FILE.exists():
        print("❌ 未找到AI分析结果")
        return []
    
    try:
        with open(AI_RESULT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查是否是今天的
        timestamp = data.get('timestamp', '')
        today = datetime.now().strftime('%Y-%m-%d')
        
        if not timestamp.startswith(today):
            print(f"⚠️ AI分析结果不是今天的（{timestamp[:10]}）")
            return []
        
        gaps = data.get('gaps', [])
        print(f"✅ 找到 {len(gaps)} 个Gap（分析时间：{timestamp[:19]}）")
        return gaps
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        return []
    except Exception as e:
        print(f"❌ 读取失败: {e}")
        return []

def execute_gap_fix(gap, index):
    """执行单个Gap的修复"""
    title = gap.get('title', '未命名')
    action = gap.get('action', 'unknown')
    priority = gap.get('priority', 'medium')
    skill = gap.get('suggested_skill', '')
    
    print(f"\n{'='*60}")
    print(f"[{index}] {title}")
    print(f"    优先级: {priority} | 动作: {action} | 建议Skill: {skill}")
    print(f"{'='*60}")
    
    if action == 'install_skill':
        # 检查Skill是否已存在
        skill_path = WORKSPACE / "skills" / skill
        if skill_path.exists():
            print(f"    ⚠️ Skill '{skill}' 已存在，跳过安装")
            return True
        
        print(f"    💡 建议创建Skill: {skill}")
        print(f"    📝 描述: {gap.get('skill_description', '无')[:80]}...")
        print(f"    ⏱️ 预计收益: {gap.get('estimated_benefit', '未知')}")
        print(f"    ⚡ 需要手动执行: 回复'创建{index}'来创建此Skill")
        return False  # 需要手动确认
    
    elif action == 'fix_config':
        print(f"    🔧 需要修复配置")
        print(f"    ⚡ 需要手动执行: 回复'修复{index}'来修复")
        return False
    
    elif action == 'enable_feature':
        print(f"    🚀 需要启用功能")
        print(f"    ⚡ 需要手动执行: 回复'启用{index}'来启用")
        return False
    
    else:
        print(f"    ⚠️ 未知动作类型: {action}")
        return False

def generate_action_plan(gaps):
    """生成行动计划"""
    plan_file = LEARNINGS_DIR / "evolution_action_plan.md"
    
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    lines = [
        f"# 自我进化行动计划 - {today}",
        "",
        f"发现 {len(gaps)} 个系统能力缺口，需要改进实施。",
        "",
        "## 高优先级（立即处理）",
        ""
    ]
    
    for i, gap in enumerate(gaps, 1):
        if gap.get('priority') == 'high':
            lines.append(f"{i}. **{gap.get('title')}**")
            lines.append(f"   - 类型: {gap.get('type')}")
            lines.append(f"   - 建议Skill: `{gap.get('suggested_skill', 'N/A')}`")
            lines.append(f"   - 操作: 回复 `创建{i}` 执行")
            lines.append("")
    
    lines.extend([
        "## 中优先级（本周处理）",
        ""
    ])
    
    for i, gap in enumerate(gaps, 1):
        if gap.get('priority') == 'medium':
            lines.append(f"{i}. **{gap.get('title')}**")
            lines.append(f"   - 建议Skill: `{gap.get('suggested_skill', 'N/A')}`")
            lines.append("")
    
    lines.extend([
        "## 改进统计",
        f"- 高优先级: {sum(1 for g in gaps if g.get('priority') == 'high')} 个",
        f"- 中优先级: {sum(1 for g in gaps if g.get('priority') == 'medium')} 个",
        f"- 低优先级: {sum(1 for g in gaps if g.get('priority') == 'low')} 个",
        "",
        "---",
        "*由自我进化系统自动生成*"
    ])
    
    plan_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n📋 行动计划已保存: {plan_file}")

def main():
    print("=" * 70)
    print("自我进化系统 - 改进实施")
    print("=" * 70)
    print()
    
    # 加载Gap
    gaps = load_gaps()
    if not gaps:
        print("\n✅ 未发现需要改进的Gap，系统运行良好！")
        return
    
    print()
    
    # 执行每个Gap的修复
    executed = 0
    pending = 0
    
    for i, gap in enumerate(gaps, 1):
        result = execute_gap_fix(gap, i)
        if result:
            executed += 1
        else:
            pending += 1
    
    # 生成行动计划
    generate_action_plan(gaps)
    
    # 总结
    print()
    print("=" * 70)
    print("改进实施总结")
    print("=" * 70)
    print(f"总Gap数: {len(gaps)}")
    print(f"自动执行: {executed} 个")
    print(f"需手动确认: {pending} 个")
    print()
    print("💡 提示: 回复对应的指令（如'创建1'、'修复2'）来执行改进")

if __name__ == "__main__":
    main()
