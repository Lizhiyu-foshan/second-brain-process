#!/usr/bin/env python3
"""
每日复盘报告 - Python版（带实时进度反馈）

特性：
1. 每个关键步骤发送进度更新
2. 完成后发送详细报告到飞书
"""

import subprocess
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# 路径配置
WORKSPACE = Path("/root/.openclaw/workspace")
SCRIPT_DIR = WORKSPACE / "second-brain-processor"
VAULT_DIR = WORKSPACE / "obsidian-vault"
LEARNINGS_DIR = WORKSPACE / ".learnings"  # 修正：使用workspace级别的.learnings
FEISHU_USER = "ou_363105a68ee112f714ed44e12c802051"


class ProgressReporter:
    """进度报告器"""
    
    def __init__(self, total_steps: int, task_name: str):
        self.total_steps = total_steps
        self.current_step = 0
        self.task_name = task_name
        self.start_time = datetime.now()
        
    def start_step(self, step_name: str, estimated_seconds: int = 30):
        """开始新步骤"""
        self.current_step += 1
        self.step_start_time = datetime.now()
        self.current_step_name = step_name
        self.estimated_seconds = estimated_seconds
        
        percent = int((self.current_step - 1) / self.total_steps * 100)
        self._report(f"步骤 {self.current_step}/{self.total_steps}", step_name, percent, f"~{estimated_seconds}秒")
        
    def update(self, message: str, percent_in_step: int = 50):
        """更新当前步骤进度"""
        base_percent = int((self.current_step - 1) / self.total_steps * 100)
        step_percent = int(percent_in_step / self.total_steps)
        total_percent = min(base_percent + step_percent, 99)
        
        # 计算剩余时间
        elapsed = (datetime.now() - self.step_start_time).total_seconds()
        if elapsed > 0 and percent_in_step > 0:
            total_estimated = elapsed / (percent_in_step / 100)
            remaining = max(0, total_estimated - elapsed)
            eta = f"~{int(remaining)}秒"
        else:
            eta = f"~{self.estimated_seconds}秒"
        
        self._report(f"步骤 {self.current_step}/{self.total_steps}", message, total_percent, eta)
        
    def complete_step(self, message: str = "完成"):
        """完成当前步骤"""
        percent = int(self.current_step / self.total_steps * 100)
        self._report(f"步骤 {self.current_step}/{self.total_steps}", message, percent, "下一步")
        
    def complete(self, message: str = "全部完成"):
        """任务完成"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        self._report("完成", message, 100, f"总耗时{int(total_time)}秒")
        
    def _report(self, step: str, message: str, percent: int, eta: str):
        """发送进度报告"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        progress_line = f"[{timestamp}] 📊 {self.task_name} | {step}: {message} ({percent}%) ETA: {eta}"
        print(progress_line)


def get_vault_stats():
    """获取知识库统计"""
    stats = {'conversations': 0, 'articles': 0, 'total': 0}
    
    if not VAULT_DIR.exists():
        return stats
    
    conv_dir = VAULT_DIR / '02-Conversations'
    if conv_dir.exists():
        stats['conversations'] = len(list(conv_dir.glob('*.md')))
    
    art_dir = VAULT_DIR / '03-Articles'
    if art_dir.exists():
        stats['articles'] = len(list(art_dir.rglob('*.md')))
    
    stats['total'] = stats['conversations'] + stats['articles']
    return stats


def get_health_status() -> str:
    """获取文章剪藏链路健康状态"""
    try:
        # 检查健康检查报告
        health_file = LEARNINGS_DIR / "health_check_report.json"
        if health_file.exists():
            with open(health_file, 'r', encoding='utf-8') as f:
                health = json.load(f)
            
            overall = health.get('overall_status', 'unknown')
            checks = health.get('checks', {})
            issues = health.get('issues', [])
            
            lines = ["\n🏥 **系统健康状态**"]
            
            # 总体状态
            if overall == 'healthy':
                lines.append("✅ 所有系统运行正常")
            else:
                lines.append(f"⚠️ 发现 {len(issues)} 个问题")
            
            # 详细检查项
            for name, check in checks.items():
                emoji = "✅" if check.get('healthy') else "⚠️"
                msg = check.get('message', '')
                lines.append(f"   {emoji} {name}: {msg}")
            
            # 如果有建议，显示第一条
            recommendations = health.get('recommendations', [])
            if recommendations:
                rec = recommendations[0]
                lines.append(f"\n   💡 建议: {rec.get('action', '')}")
            
            return "\n".join(lines)
        
        # 如果没有健康报告，检查队列状态
        queue_file = SCRIPT_DIR / "message_queue.json"
        if queue_file.exists():
            with open(queue_file, 'r', encoding='utf-8') as f:
                queue = json.load(f)
            pending = len(queue.get('messages', []))
            if pending > 0:
                return f"\n🏥 **系统健康状态**\n   📝 待处理队列: {pending} 条消息"
        
        return "\n🏥 **系统健康状态**\n   ✅ 文章剪藏链路运行正常"
        
    except Exception as e:
        return f"\n🏥 **系统健康状态**\n   ⚠️ 检查失败: {str(e)[:50]}"


def generate_report():
    """生成复盘报告（包含进化建议）"""
    stats = get_vault_stats()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 获取进化建议
    evolution_section = _get_evolution_suggestions()
    
    # 获取健康状态
    health_section = get_health_status()
    
    report = f"""📊 每日复盘报告（{today}）

📅 昨日概况（{yesterday}）
• 新增对话记录：已自动归档
• 知识库总篇数：{stats['total']} 篇
  - 对话记录：{stats['conversations']} 篇
  - 文章剪藏：{stats['articles']} 篇
{health_section}

{evolution_section}

💡 其他功能
• 待处理链接请回复"队列"查看
• 发送链接给我，自动添加到待处理队列

⏰ 报告生成时间：{datetime.now().strftime('%H:%M')}
"""
    return report


def _get_evolution_suggestions() -> str:
    """获取进化建议部分 - 优先使用AI分析，失败则回退到基础分析"""
    
    # 首先尝试读取AI分析结果
    ai_result_file = LEARNINGS_DIR / "ai_gap_analysis.json"
    
    if ai_result_file.exists():
        try:
            import json
            with open(ai_result_file, 'r', encoding='utf-8') as f:
                ai_result = json.load(f)
            
            # 检查是否是今天的分析结果
            result_time = ai_result.get('timestamp', '')
            if result_time:
                result_date = result_time[:10]  # 提取日期部分 YYYY-MM-DD
                today = datetime.now().strftime('%Y-%m-%d')
                
                if result_date == today and ai_result.get('gaps'):
                    print(f"[INFO] 使用今日AI分析结果（{len(ai_result['gaps'])}条缺口）")
                    return _format_ai_suggestions(ai_result)
                else:
                    print(f"[INFO] AI分析结果日期: {result_date}，今日: {today}，使用备用方案")
        except Exception as e:
            print(f"[WARN] 读取AI分析结果失败: {e}")
    
    # 回退到基础分析器
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from evolution_analyzer import EvolutionAnalyzer
        
        analyzer = EvolutionAnalyzer()
        suggestions = analyzer.get_pending_suggestions()
        
        if not suggestions:
            return "🎯 **自主进化分析**：今日未发现明显的能力缺口，系统运行良好！"
        
        lines = ["🎯 **自主进化分析**（基于7天使用模式）\n"]
        lines.append("检测到以下可优化项，回复对应指令执行：\n")
        
        for i, s in enumerate(suggestions[:5], 1):
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(s.get("priority", "low"), "⚪")
            lines.append(f"{i}. {priority_emoji} **{s['description']}**")
            lines.append(f"   💡 建议：{s['suggestion']}")
            
            if "estimated_benefit" in s:
                lines.append(f"   ⏱️ 预计收益：{s['estimated_benefit']}")
            
            action_type = s.get("action", "unknown")
            if action_type == "install_skill":
                lines.append(f"   👉 回复 `安装{i}` 执行")
            elif action_type == "fix_config":
                lines.append(f"   👉 回复 `修复{i}` 执行")
            elif action_type == "enable_feature":
                lines.append(f"   👉 回复 `启用{i}` 执行")
            
            lines.append("")
        
        lines.append("📋 **批量操作**：")
        lines.append("• `全部安装` - 安装所有高优先级建议")
        lines.append("• `忽略` - 今日不处理，明日再评估")
        lines.append("• `详细{i}` - 查看第i条详细说明")
        
        return "\n".join(lines)
        
    except Exception as e:
        print(f"[WARN] 获取进化建议失败: {e}")
        return "🎯 **自主进化分析**：建议获取暂时不可用，系统正常运行中。"


def _format_ai_suggestions(ai_result: dict) -> str:
    """格式化AI分析的建议"""
    gaps = ai_result.get("gaps", [])
    
    if not gaps:
        return "🧠 **AI自主进化分析**：经过深度分析，未发现明显的能力缺口，系统运行高效！"
    
    lines = ["\n🧠 **AI自主进化分析**（Kimi K2.5 深度分析）\n"]
    
    # 添加分析元信息
    analysis_time = ai_result.get('timestamp', '未知')[:19]
    lines.append(f"📅 分析时间: {analysis_time}")
    lines.append(f"📊 分析天数: {ai_result.get('analysis_days', 7)} 天")
    lines.append(f"🔍 发现缺口: {len(gaps)} 个\n")
    lines.append("---\n")
    
    for i, gap in enumerate(gaps[:5], 1):
        priority = gap.get('priority', 'medium')
        emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(priority, '⚪')
        
        lines.append(f"{i}. {emoji} **{gap.get('title', '未命名')}**")
        lines.append(f"   📋 缺口类型: {gap.get('type', 'unknown')}")
        
        # 描述可能较长，限制显示
        description = gap.get('description', '')
        if len(description) > 100:
            description = description[:100] + "..."
        lines.append(f"   📝 描述: {description}")
        
        # 行为证据
        evidence = gap.get('evidence', '')
        if evidence:
            if len(evidence) > 80:
                evidence = evidence[:80] + "..."
            lines.append(f"   📊 行为证据: {evidence}")
        
        # 推荐Skill
        skill = gap.get('suggested_skill', '')
        if skill:
            lines.append(f"   💡 推荐Skill: {skill}")
            skill_desc = gap.get('skill_description', '')
            if skill_desc:
                if len(skill_desc) > 80:
                    skill_desc = skill_desc[:80] + "..."
                lines.append(f"      {skill_desc}")
        
        # 预计收益
        benefit = gap.get('estimated_benefit', '')
        if benefit:
            lines.append(f"   ⏱️ 预计收益: {benefit}")
        
        # 操作指令
        action = gap.get('action', 'install_skill')
        if action == 'install_skill':
            lines.append(f"   👉 回复 `安装{i}` 执行安装")
        elif action == 'fix_config':
            lines.append(f"   👉 回复 `修复{i}` 执行修复")
        elif action == 'enable_feature':
            lines.append(f"   👉 回复 `启用{i}` 启用功能")
        elif action == 'create_workflow':
            lines.append(f"   👉 回复 `创建{i}` 创建工作流")
        
        lines.append("")
    
    lines.append("---\n")
    lines.append("📋 **批量操作**：")
    lines.append("• `全部安装` - 安装所有高优先级建议")
    lines.append("• `忽略` - 今日不处理，明日再评估")
    lines.append("• `详细{i}` - 查看第i条详细说明\n")
    
    return "\n".join(lines)


def send_feishu_report(report: str) -> bool:
    """发送报告到飞书 - 使用严格防重发守护进程"""
    try:
        # 导入守护进程
        sys.path.insert(0, str(SCRIPT_DIR))
        from feishu_guardian import send_feishu_safe
        
        result = send_feishu_safe(
            report, 
            target=FEISHU_USER, 
            msg_type="daily_report",
            max_retries=1
        )
        
        return result["success"]
        
    except Exception as e:
        print(f"[WARN] 飞书发送失败: {e}")
        # 降级到备用方法
        return _send_feishu_fallback(report)


def _send_feishu_fallback(report: str) -> bool:
    """备用发送方法 - 写入文件等待手动发送"""
    try:
        # 将报告保存到文件
        report_file = WORKSPACE / ".learnings" / "pending_daily_report.txt"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(report, encoding='utf-8')
        
        print(f"[INFO] 报告已保存到: {report_file}")
        print("[INFO] 请手动复制内容发送到飞书")
        return False
    except Exception as e:
        print(f"[WARN] 备用保存也失败: {e}")
        return False


def run_with_progress():
    """带进度反馈的主流程"""
    print("=" * 50)
    print(f"每日复盘报告 - {datetime.now()}")
    print("预计总耗时: 15-30秒")
    print("=" * 50)
    
    # 创建进度报告器（2个步骤）
    progress = ProgressReporter(total_steps=2, task_name="每日复盘")
    
    # 步骤1: 统计数据
    progress.start_step("统计知识库数据", estimated_seconds=10)
    progress.update("扫描对话记录...", 30)
    
    stats = get_vault_stats()
    progress.update("统计文章剪藏...", 70)
    
    # 生成报告
    progress.update("生成报告内容...", 90)
    report = generate_report()
    progress.complete_step("统计完成")
    
    # 步骤2: 发送报告
    progress.start_step("发送复盘报告", estimated_seconds=15)
    progress.update("连接飞书...", 30)
    
    if send_feishu_report(report):
        progress.update("发送成功", 100)
        progress.complete_step("发送完成")
        print("\n✅ 复盘报告已发送到飞书")
    else:
        progress.update("发送失败", 50)
        progress.complete_step("发送失败")
        print("\n⚠️ 飞书发送失败，报告内容：")
        print(report)
    
    # 任务完成
    progress.complete()
    print("=" * 50)
    
    return True


if __name__ == "__main__":
    success = run_with_progress()
    sys.exit(0 if success else 1)
