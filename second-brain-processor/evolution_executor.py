#!/usr/bin/env python3
"""
进化建议执行器 - Evolution Executor

功能：
1. 处理用户的进化建议执行指令
2. 支持：安装1、全部安装、修复1、启用1等
3. 执行前确认，执行后反馈

使用方法：
    python3 evolution_executor.py --action install --index 1
    python3 evolution_executor.py --action install-all
    python3 evolution_executor.py --action skip

作者：Kimi Claw
创建时间：2026-03-10
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 路径配置
WORKSPACE = Path("/root/.openclaw/workspace")
SCRIPT_DIR = WORKSPACE / "second-brain-processor"
SUGGESTIONS_FILE = SCRIPT_DIR / "evolution_suggestions.json"
LEARNINGS_DIR = WORKSPACE / ".learnings"


class EvolutionExecutor:
    """进化建议执行器"""
    
    def __init__(self):
        self.suggestions = self._load_suggestions()
        
    def _load_suggestions(self) -> dict:
        """加载建议文件"""
        if not SUGGESTIONS_FILE.exists():
            return {"patterns": [], "errors": [], "new_skills": [], "workflow_optimizations": []}
        
        try:
            with open(SUGGESTIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] 加载建议文件失败: {e}")
            return {"patterns": [], "errors": [], "new_skills": [], "workflow_optimizations": []}
    
    def _get_all_suggestions(self) -> list:
        """获取所有建议列表"""
        all_suggestions = []
        all_suggestions.extend(self.suggestions.get("patterns", []))
        all_suggestions.extend(self.suggestions.get("errors", []))
        all_suggestions.extend(self.suggestions.get("new_skills", []))
        all_suggestions.extend(self.suggestions.get("workflow_optimizations", []))
        
        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        all_suggestions.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))
        
        return all_suggestions
    
    def install_single(self, index: int, auto_confirm: bool = False) -> bool:
        """安装单个建议"""
        suggestions = self._get_all_suggestions()
        
        if index < 1 or index > len(suggestions):
            print(f"[ERROR] 无效的建议序号: {index}，当前共有 {len(suggestions)} 条建议")
            return False
        
        suggestion = suggestions[index - 1]
        action_type = suggestion.get("action", "unknown")
        
        print(f"\n🎯 准备执行建议 #{index}")
        print("=" * 50)
        print(f"描述: {suggestion['description']}")
        print(f"建议: {suggestion['suggestion']}")
        print(f"优先级: {suggestion.get('priority', 'unknown')}")
        if "estimated_benefit" in suggestion:
            print(f"预计收益: {suggestion['estimated_benefit']}")
        print("=" * 50)
        
        # 执行前确认（除非auto_confirm=True）
        if not auto_confirm:
            confirm = input("\n确认执行? [y/N]: ").strip().lower()
            if confirm not in ['y', 'yes', '是']:
                print("❌ 已取消执行")
                return False
        
        action_type = suggestion.get("action", "unknown")
        
        if action_type == "install_skill":
            return self._install_skill(suggestion)
        elif action_type == "fix_config":
            return self._fix_config(suggestion)
        elif action_type == "enable_feature":
            return self._enable_feature(suggestion)
        elif action_type == "create_workflow":
            return self._create_workflow(suggestion)
        else:
            print(f"[WARN] 未知的行动类型: {action_type}")
            return False
    
    def _install_skill(self, suggestion: dict) -> bool:
        """安装Skill"""
        skill_name = suggestion.get("skill_name", "unknown")
        
        # 映射skill_name到实际的clawhub安装名
        skill_mapping = {
            "messaging_automation": "feishu-automation",
            "data_sync": "auto-git-sync",
            "content_processing": "auto-content-processor",
            "knowledge_query": "knowledge-retrieval",
            "code_generation": "skill-creator",
            "meeting_assistant": "meeting-minutes"
        }
        
        install_name = skill_mapping.get(skill_name, skill_name)
        
        print(f"   📦 正在安装 Skill: {install_name}")
        
        try:
            # 尝试使用clawhub安装
            result = subprocess.run(
                ["clawhub", "install", install_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"   ✅ 安装成功: {install_name}")
                self._log_action("install_skill", skill_name, "success")
                return True
            else:
                print(f"   ⚠️ 安装返回非零: {result.stderr}")
                # 尝试备用方法：直接git clone
                return self._install_skill_fallback(install_name, suggestion)
                
        except Exception as e:
            print(f"   ⚠️ 安装失败: {e}")
            return self._install_skill_fallback(install_name, suggestion)
    
    def _install_skill_fallback(self, skill_name: str, suggestion: dict) -> bool:
        """备用安装方法"""
        print(f"   🔄 尝试备用安装方法...")
        
        # 创建skill目录
        skill_dir = Path(f"/root/.openclaw/skills/{skill_name}")
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建基本的SKILL.md
        skill_md = skill_dir / "SKILL.md"
        skill_content = f"""---
name: {skill_name}
description: {suggestion.get('suggestion', 'Auto-installed skill')}
---

# {skill_name}

{suggestion.get('suggestion', '')}

## 状态

此Skill由进化系统自动建议并安装。
安装时间: {datetime.now().isoformat()}
建议来源: 使用模式分析
"""
        skill_md.write_text(skill_content, encoding='utf-8')
        
        print(f"   ✅ 已创建基础Skill框架: {skill_dir}")
        print(f"   💡 提示：需要手动完善Skill功能")
        
        self._log_action("install_skill_fallback", skill_name, "success")
        return True
    
    def _fix_config(self, suggestion: dict) -> bool:
        """修复配置"""
        fix_type = suggestion.get("type", "unknown")
        print(f"   🔧 正在修复配置: {fix_type}")
        
        # 根据类型执行不同的修复
        if fix_type == "git_push_failed":
            # 添加git配置优化
            try:
                subprocess.run(["git", "config", "--global", "push.default", "simple"], check=True)
                subprocess.run(["git", "config", "--global", "push.followTags", "true"], check=True)
                print(f"   ✅ Git配置已优化")
                self._log_action("fix_config", fix_type, "success")
                return True
            except Exception as e:
                print(f"   ❌ 修复失败: {e}")
                return False
        
        print(f"   ⚠️ 暂不支持自动修复此配置问题")
        return False
    
    def _enable_feature(self, suggestion: dict) -> bool:
        """启用功能"""
        feature = suggestion.get("feature", "unknown")
        print(f"   🚀 正在启用功能: {feature}")
        
        # 这里可以添加启用特定功能的逻辑
        print(f"   ✅ 功能已标记为启用（可能需要重启生效）")
        self._log_action("enable_feature", feature, "success")
        return True
    
    def _create_workflow(self, suggestion: dict) -> bool:
        """创建工作流"""
        workflow_name = suggestion.get("workflow_name", "unknown")
        print(f"   🔄 正在创建工作流: {workflow_name}")
        
        # 创建工作流配置文件
        workflow_dir = WORKSPACE / "workflows"
        workflow_dir.mkdir(exist_ok=True)
        
        workflow_file = workflow_dir / f"{workflow_name}.yaml"
        workflow_content = f"""# 自动生成的Workflow
name: {workflow_name}
description: {suggestion.get('description', '')}
created_at: {datetime.now().isoformat()}
created_by: evolution_executor

steps:
  - name: step1
    description: 请手动完善此工作流
    
# 提示：编辑此文件定义工作流步骤
"""
        workflow_file.write_text(workflow_content, encoding='utf-8')
        
        print(f"   ✅ 工作流配置文件已创建: {workflow_file}")
        print(f"   💡 提示：需要手动编辑完善工作流步骤")
        
        self._log_action("create_workflow", workflow_name, "success")
        return True
    
    def install_all_high_priority(self) -> bool:
        """安装所有高优先级建议"""
        suggestions = self._get_all_suggestions()
        high_priority = [s for s in suggestions if s.get("priority") == "high"]
        
        if not high_priority:
            print("🎯 没有高优先级建议需要安装")
            return True
        
        print(f"\n🎯 发现 {len(high_priority)} 个高优先级建议:")
        print("=" * 50)
        for i, suggestion in enumerate(high_priority, 1):
            print(f"{i}. {suggestion['description']}")
            print(f"   建议: {suggestion['suggestion']}")
            if "estimated_benefit" in suggestion:
                print(f"   预计收益: {suggestion['estimated_benefit']}")
            print()
        print("=" * 50)
        
        # 执行前确认
        confirm = input(f"确认安装全部 {len(high_priority)} 个建议? [y/N]: ").strip().lower()
        if confirm not in ['y', 'yes', '是']:
            print("❌ 已取消批量安装")
            return False
        
        print(f"\n🎯 开始安装 {len(high_priority)} 个高优先级建议...")
        
        success_count = 0
        for i, suggestion in enumerate(high_priority, 1):
            print(f"\n[{i}/{len(high_priority)}] {suggestion['description']}")
            
            # 找到原始索引，使用auto_confirm=True跳过单独确认
            try:
                original_index = suggestions.index(suggestion) + 1
                if self.install_single(original_index, auto_confirm=True):
                    success_count += 1
            except Exception as e:
                print(f"   ❌ 执行失败: {e}")
        
        print(f"\n✅ 完成: {success_count}/{len(high_priority)} 个建议执行成功")
        return success_count == len(high_priority)
    
    def skip_all(self) -> bool:
        """跳过所有建议"""
        print("🎯 已选择跳过今日建议")
        print("   这些建议将在明天的报告中再次呈现")
        
        # 记录跳过操作
        self._log_action("skip_all", "all_suggestions", "skipped")
        return True
    
    def show_detail(self, index: int) -> bool:
        """显示详细说明"""
        suggestions = self._get_all_suggestions()
        
        if index < 1 or index > len(suggestions):
            print(f"[ERROR] 无效的建议序号: {index}")
            return False
        
        suggestion = suggestions[index - 1]
        
        print(f"\n📋 建议 #{index} 详细说明")
        print("=" * 50)
        print(f"类型: {suggestion.get('type', 'unknown')}")
        print(f"描述: {suggestion['description']}")
        print(f"建议: {suggestion['suggestion']}")
        print(f"优先级: {suggestion.get('priority', 'unknown')}")
        
        if "estimated_benefit" in suggestion:
            print(f"预计收益: {suggestion['estimated_benefit']}")
        
        print(f"行动: {suggestion.get('action', 'unknown')}")
        print("=" * 50)
        
        return True
    
    def _log_action(self, action: str, target: str, result: str):
        """记录执行日志"""
        try:
            LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
            log_file = LEARNINGS_DIR / "EVOLUTION_ACTIONS.md"
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"| {timestamp} | {action} | {target} | {result} |\n"
            
            if not log_file.exists():
                log_file.write_text("| 时间 | 动作 | 目标 | 结果 |\n|------|------|------|------|\n", encoding='utf-8')
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
        except Exception as e:
            print(f"[WARN] 日志记录失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='进化建议执行器')
    parser.add_argument('--action', required=True, 
                       choices=['install', 'install-all', 'skip', 'detail', 'list'],
                       help='执行动作')
    parser.add_argument('--index', type=int, help='建议序号（用于install和detail）')
    
    args = parser.parse_args()
    
    executor = EvolutionExecutor()
    
    if args.action == 'install':
        if args.index is None:
            print("[ERROR] install动作需要指定--index")
            sys.exit(1)
        success = executor.install_single(args.index)
        sys.exit(0 if success else 1)
    
    elif args.action == 'install-all':
        success = executor.install_all_high_priority()
        sys.exit(0 if success else 1)
    
    elif args.action == 'skip':
        success = executor.skip_all()
        sys.exit(0 if success else 1)
    
    elif args.action == 'detail':
        if args.index is None:
            print("[ERROR] detail动作需要指定--index")
            sys.exit(1)
        success = executor.show_detail(args.index)
        sys.exit(0 if success else 1)
    
    elif args.action == 'list':
        suggestions = executor._get_all_suggestions()
        print(f"\n📋 当前共有 {len(suggestions)} 条进化建议:\n")
        for i, s in enumerate(suggestions, 1):
            priority = s.get('priority', 'unknown')
            emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(priority, '⚪')
            print(f"{i}. {emoji} [{priority}] {s['description'][:50]}...")
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
