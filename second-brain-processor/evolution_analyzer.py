#!/usr/bin/env python3
"""
自主进化分析器 - Evolution Analyzer

功能：
1. 分析用户使用模式，发现重复手动操作
2. 基于对话历史识别能力缺口
3. 生成改进建议列表
4. 输出给每日报告供用户选择

改进：加入 ClawHub + GitHub 双重搜索验证

作者：Kimi Claw
创建时间：2026-03-10
更新时间：2026-03-11
"""

import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class EvolutionAnalyzer:
    """自主进化分析器"""
    
    def __init__(self, workspace: Path = None):
        self.workspace = workspace or Path("/root/.openclaw/workspace")
        self.sessions_dir = Path("/root/.openclaw/agents/main/sessions")
        self.memory_dir = self.workspace / "memory"
        self.obsidian_vault = self.workspace / "obsidian-vault"
        self.suggestions_file = self.workspace / "second-brain-processor" / "evolution_suggestions.json"
        self.learnings_dir = self.workspace / "second-brain-processor" / ".learnings"
        
        # 能力缺口模式定义（带 skill 映射）
        self.gap_patterns = {
            "messaging_automation": {
                "patterns": ["发送飞书", "发消息", "提醒", "通知", "推送"],
                "suggestion": "安装 feishu-automation skill，实现定时/触发式消息推送",
                "priority": "high",
                "estimated_time_save": "30分钟/天",
                "skill_keywords": ["feishu-automation", "message", "notification"]
            },
            "data_sync": {
                "patterns": ["同步到GitHub", "推送", "备份", "上传"],
                "suggestion": "配置 auto-git-sync trigger，文件变更自动推送",
                "priority": "medium",
                "estimated_time_save": "10分钟/天",
                "skill_keywords": ["auto-git-sync", "git-sync", "backup"]
            },
            "content_processing": {
                "patterns": ["整理文章", "总结", "提取要点", "剪藏"],
                "suggestion": "启用 auto-content-processor，自动分析剪藏文章",
                "priority": "medium",
                "estimated_time_save": "20分钟/天",
                "skill_keywords": ["auto-content", "content-processor", "article"]
            },
            "knowledge_query": {
                "patterns": ["查找", "搜索", "我记得", "之前说过"],
                "suggestion": "安装 knowledge-retrieval skill，增强记忆搜索能力",
                "priority": "low",
                "estimated_time_save": "5分钟/天",
                "skill_keywords": ["knowledge-retrieval", "search", "memory"]
            },
            "code_generation": {
                "patterns": ["写脚本", "生成代码", "自动化", "批量处理"],
                "suggestion": "启用 skill-creator，基于自然语言自动生成工具",
                "priority": "high",
                "estimated_time_save": "1小时/任务",
                "skill_keywords": ["skill-creator", "code-gen", "generator"]
            },
            "meeting_assistant": {
                "patterns": ["会议纪要", "会议记录", "待办", "action item"],
                "suggestion": "安装 meeting-minutes skill，自动提取会议要点和待办",
                "priority": "medium",
                "estimated_time_save": "15分钟/会议",
                "skill_keywords": ["meeting-minutes", "meeting", "minutes"]
            },
            "calendar_sync": {
                "patterns": ["日历", "日程", "会议安排", "提醒事项"],
                "suggestion": "安装 calendar-sync skill，同步日历和自动提醒",
                "priority": "medium",
                "estimated_time_save": "10分钟/天",
                "skill_keywords": ["calendar-sync", "calendar", "schedule"]
            },
            "email_management": {
                "patterns": ["邮件", "收件箱", "email", "gmail"],
                "suggestion": "安装 email-assistant skill，自动分类和处理邮件",
                "priority": "low",
                "estimated_time_save": "15分钟/天",
                "skill_keywords": ["email-assistant", "email", "mail"]
            }
        }
        
        # 已安装技能清单（从目录读取）
        self.installed_skills = self._load_installed_skills()
        
        # 缓存搜索结果避免重复请求
        self._search_cache = {}
        
    def _load_installed_skills(self) -> List[str]:
        """加载已安装的skills"""
        skills_dir = Path("/root/.openclaw/skills")
        if not skills_dir.exists():
            return []
        return [d.name for d in skills_dir.iterdir() if d.is_dir()]
    
    def _search_clawhub(self, keyword: str) -> Tuple[bool, Optional[str]]:
        """
        搜索 ClawHub 是否有对应 skill
        
        Returns: (found, skill_name_or_none)
        """
        # 检查缓存
        if keyword in self._search_cache:
            return self._search_cache[keyword]
        
        try:
            result = subprocess.run(
                ["clawhub", "search", keyword],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                # 解析输出，查找匹配的 skill
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    # 简单匹配：如果关键词在输出行中
                    if keyword.lower() in line.lower():
                        self._search_cache[keyword] = (True, keyword)
                        return True, keyword
                        
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"[WARN] ClawHub 搜索失败 ({keyword}): {e}")
        
        self._search_cache[keyword] = (False, None)
        return False, None
    
    def _search_github(self, keyword: str) -> Tuple[bool, Optional[str]]:
        """
        搜索 GitHub 是否有对应 skill
        
        Returns: (found, repo_full_name_or_none)
        """
        # 检查缓存
        cache_key = f"github:{keyword}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]
        
        try:
            # 使用 gh CLI 搜索
            result = subprocess.run(
                ["gh", "search", "repos", f"{keyword} skill", "--limit", "5", "--json", "fullName,name"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout:
                repos = json.loads(result.stdout)
                for repo in repos:
                    repo_name = repo.get('name', '').lower()
                    # 匹配规则：仓库名包含关键词或 skill
                    if keyword.lower() in repo_name or 'skill' in repo_name:
                        full_name = repo.get('fullName')
                        self._search_cache[cache_key] = (True, full_name)
                        return True, full_name
                        
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[WARN] GitHub 搜索失败 ({keyword}): {e}")
        
        self._search_cache[cache_key] = (False, None)
        return False, None
    
    def _find_best_skill_match(self, gap_type: str) -> Tuple[bool, Optional[str], str]:
        """
        为能力缺口寻找最佳 skill 匹配
        
        搜索策略：
        1. 先搜索 ClawHub
        2. 如果失败，搜索 GitHub
        3. 返回最佳匹配结果
        
        Returns: (found, skill_name, source)
                 source: "clawhub" | "github" | "none"
        """
        config = self.gap_patterns.get(gap_type, {})
        keywords = config.get("skill_keywords", [gap_type])
        
        # 1. 先尝试 ClawHub
        for keyword in keywords:
            found, skill = self._search_clawhub(keyword)
            if found:
                print(f"[INFO] 在 ClawHub 找到匹配: {skill}")
                return True, skill, "clawhub"
        
        # 2. 尝试 GitHub
        for keyword in keywords:
            found, repo = self._search_github(keyword)
            if found:
                print(f"[INFO] 在 GitHub 找到匹配: {repo}")
                return True, repo, "github"
        
        # 3. 都没找到
        return False, None, "none"
    
    def analyze_conversation_patterns(self, days: int = 7) -> Dict:
        """分析对话模式，发现重复操作"""
        patterns_found = {}
        
        # 读取最近7天的memory文件
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            memory_file = self.memory_dir / f"{date}.md"
            
            if memory_file.exists():
                content = memory_file.read_text(encoding='utf-8')
                
                for gap_type, config in self.gap_patterns.items():
                    # 检查是否已安装对应skill
                    if self._is_skill_installed(gap_type):
                        continue
                    
                    # 统计匹配次数
                    match_count = 0
                    for pattern in config["patterns"]:
                        match_count += len(re.findall(pattern, content))
                    
                    if match_count > 0:
                        if gap_type not in patterns_found:
                            patterns_found[gap_type] = {
                                "count": 0,
                                "config": config,
                                "last_mentioned": date
                            }
                        patterns_found[gap_type]["count"] += match_count
        
        return patterns_found
    
    def _is_skill_installed(self, gap_type: str) -> bool:
        """检查某类能力是否已安装对应skill"""
        skill_mapping = {
            "messaging_automation": ["feishu", "messaging", "notification"],
            "data_sync": ["git", "sync", "backup"],
            "content_processing": ["content", "article", "processor"],
            "knowledge_query": ["knowledge", "retrieval", "search"],
            "code_generation": ["skill-creator", "code-gen"],
            "meeting_assistant": ["meeting", "minutes"]
        }
        
        keywords = skill_mapping.get(gap_type, [])
        for skill in self.installed_skills:
            for keyword in keywords:
                if keyword.lower() in skill.lower():
                    return True
        return False
    
    def analyze_error_patterns(self) -> List[Dict]:
        """分析错误模式，发现系统性问题"""
        errors = []
        
        # 读取错误日志
        error_log = self.workspace / "second-brain-processor" / ".learnings" / "ERRORS.md"
        if error_log.exists():
            content = error_log.read_text(encoding='utf-8')
            
            # 统计错误类型
            error_types = {
                "git_push_failed": (r"git.*push.*failed|git.*timeout", "Git推送失败", "优化Git流程或检查网络"),
                "api_rate_limit": (r"rate.*limit|429|too.*many.*requests", "API限流", "增加请求间隔或升级套餐"),
                "file_too_large": (r"file.*too.*large|size.*exceed", "文件过大", "增加文件分割或压缩机制"),
                "timeout": (r"timeout|timed.*out", "超时", "增加超时时间或优化性能")
            }
            
            for error_type, (pattern, name, suggestion) in error_types.items():
                count = len(re.findall(pattern, content, re.IGNORECASE))
                if count >= 2:  # 重复出现2次以上
                    errors.append({
                        "type": error_type,
                        "name": name,
                        "count": count,
                        "suggestion": suggestion,
                        "priority": "high" if count >= 5 else "medium"
                    })
        
        return errors
    
    def generate_improvement_suggestions(self) -> Dict:
        """生成完整的改进建议（带 ClawHub + GitHub 双重验证）"""
        suggestions = {
            "generated_at": datetime.now().isoformat(),
            "from_evolution_analyzer": True,
            "patterns": [],
            "errors": [],
            "new_skills": [],
            "workflow_optimizations": [],
            "search_stats": {
                "clawhub_searches": 0,
                "github_searches": 0,
                "found_on_clawhub": 0,
                "found_on_github": 0
            }
        }
        
        # 1. 分析使用模式
        patterns = self.analyze_conversation_patterns(days=7)
        for gap_type, data in patterns.items():
            if data["count"] >= 3:  # 一周内出现3次以上
                print(f"[INFO] 发现模式 '{gap_type}'，验证 skill 可用性...")
                
                # 验证 skill 是否真实存在
                found, skill_name, source = self._find_best_skill_match(gap_type)
                
                # 更新统计
                suggestions["search_stats"]["clawhub_searches"] += len(data["config"].get("skill_keywords", []))
                if source == "clawhub":
                    suggestions["search_stats"]["found_on_clawhub"] += 1
                elif source == "github":
                    suggestions["search_stats"]["found_on_github"] += 1
                
                # 只在找到可用 skill 时才推荐
                if found:
                    suggestions["patterns"].append({
                        "type": gap_type,
                        "frequency": data["count"],
                        "description": f"检测到 '{gap_type}' 模式，本周出现 {data['count']} 次",
                        "suggestion": data["config"]["suggestion"],
                        "priority": data["config"]["priority"],
                        "estimated_benefit": data["config"]["estimated_time_save"],
                        "action": "install_skill",
                        "skill_name": skill_name,
                        "skill_source": source,
                        "verified": True
                    })
                else:
                    # skill 未找到，记录为潜在需求但不推荐安装
                    print(f"[INFO] 未找到 '{gap_type}' 的可用 skill，跳过推荐")
                    self._record_potential_need(gap_type, data)
        
        # 2. 分析错误模式
        errors = self.analyze_error_patterns()
        for error in errors:
            suggestions["errors"].append({
                "type": error["type"],
                "description": f"'{error['name']}' 重复出现 {error['count']} 次",
                "suggestion": error["suggestion"],
                "priority": error["priority"],
                "action": "fix_config"
            })
        
        # 3. 检查Obsidian Vault使用模式
        vault_suggestions = self._analyze_vault_usage()
        suggestions["workflow_optimizations"].extend(vault_suggestions)
        
        # 4. 基于已有技能推荐组合
        combo_suggestions = self._suggest_skill_combinations()
        suggestions["new_skills"].extend(combo_suggestions)
        
        # 保存建议到文件
        self._save_suggestions(suggestions)
        
        return suggestions
    
    def _analyze_vault_usage(self) -> List[Dict]:
        """分析Obsidian Vault使用模式"""
        suggestions = []
        
        articles_dir = self.obsidian_vault / "03-Articles"
        if articles_dir.exists():
            article_count = len(list(articles_dir.rglob("*.md")))
            
            if article_count > 50:
                suggestions.append({
                    "type": "vault_organization",
                    "description": f"知识库已有 {article_count} 篇文章，建议启用自动标签和链接系统",
                    "suggestion": "配置 auto-tagging 和知识图谱生成",
                    "priority": "medium",
                    "action": "enable_feature",
                    "feature": "auto-tagging"
                })
        
        return suggestions
    
    def _suggest_skill_combinations(self) -> List[Dict]:
        """基于已有技能推荐组合"""
        suggestions = []
        
        # 检查已安装技能
        has_bmad = any("bmad" in s for s in self.installed_skills)
        has_knowledge = any("knowledge" in s for s in self.installed_skills)
        
        # 如果同时有BMAD和Knowledge Studio，建议组合工作流
        if has_bmad and has_knowledge:
            suggestions.append({
                "type": "skill_combination",
                "description": "BMAD框架 + Knowledge Studio 可以组合为项目知识管理工作流",
                "suggestion": "创建 project-knowledge-bridge，自动将项目文档同步到知识库",
                "priority": "low",
                "action": "create_workflow",
                "workflow_name": "project-knowledge-bridge"
            })
        
        return suggestions
    
    def _record_potential_need(self, gap_type: str, data: Dict):
        """记录潜在需求（未找到对应 skill 的模式）"""
        needs_file = self.learnings_dir / "potential_needs.json"
        self.learnings_dir.mkdir(parents=True, exist_ok=True)
        
        needs = []
        if needs_file.exists():
            try:
                with open(needs_file, 'r', encoding='utf-8') as f:
                    needs = json.load(f)
            except:
                needs = []
        
        # 检查是否已记录
        existing = [n for n in needs if n.get("gap_type") == gap_type]
        if existing:
            # 更新频率
            existing[0]["frequency"] = data["count"]
            existing[0]["last_seen"] = datetime.now().isoformat()
        else:
            needs.append({
                "gap_type": gap_type,
                "description": data["config"]["suggestion"],
                "frequency": data["count"],
                "keywords": data["config"].get("skill_keywords", []),
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "status": "pending"  # pending | researching | implemented | rejected
            })
        
        with open(needs_file, 'w', encoding='utf-8') as f:
            json.dump(needs, f, ensure_ascii=False, indent=2)
    
    def _save_suggestions(self, suggestions: Dict):
        """保存建议到文件"""
        self.suggestions_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.suggestions_file, 'w', encoding='utf-8') as f:
            json.dump(suggestions, f, ensure_ascii=False, indent=2)
    
    def get_pending_suggestions(self) -> List[Dict]:
        """获取待处理的建议（用于8:30报告）"""
        if not self.suggestions_file.exists():
            return []
        
        with open(self.suggestions_file, 'r', encoding='utf-8') as f:
            suggestions = json.load(f)
        
        # 合并所有建议并按优先级排序
        all_suggestions = []
        all_suggestions.extend(suggestions.get("patterns", []))
        all_suggestions.extend(suggestions.get("errors", []))
        all_suggestions.extend(suggestions.get("new_skills", []))
        all_suggestions.extend(suggestions.get("workflow_optimizations", []))
        
        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        all_suggestions.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))
        
        return all_suggestions
    
    def format_suggestions_for_report(self) -> str:
        """格式化建议为报告文本（显示来源）"""
        suggestions = self.get_pending_suggestions()
        
        if not suggestions:
            return "🎯 **自主进化分析**：今日未发现明显的能力缺口，系统运行良好！"
        
        lines = ["\n🎯 **自主进化分析**（基于7天使用模式）\n"]
        lines.append("检测到以下可优化项，回复对应指令执行：\n")
        
        for i, s in enumerate(suggestions[:5], 1):  # 最多显示5条
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(s.get("priority", "low"), "⚪")
            
            # 显示来源
            source = s.get("skill_source", "")
            source_tag = ""
            if source == "clawhub":
                source_tag = " [📦ClawHub]"
            elif source == "github":
                source_tag = " [🐙GitHub]"
            
            lines.append(f"{i}. {priority_emoji} **{s['description']}**{source_tag}")
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
        lines.append("• `详细{i}` - 查看第i条详细说明\n")
        
        return "\n".join(lines)


def main():
    """主函数 - 用于命令行调用"""
    analyzer = EvolutionAnalyzer()
    
    # 生成建议
    suggestions = analyzer.generate_improvement_suggestions()
    
    # 输出统计
    total = (
        len(suggestions.get("patterns", [])) +
        len(suggestions.get("errors", [])) +
        len(suggestions.get("new_skills", [])) +
        len(suggestions.get("workflow_optimizations", []))
    )
    
    print(f"✅ 进化分析完成，发现 {total} 个改进建议")
    print(f"   已保存到: {analyzer.suggestions_file}")
    
    return suggestions


if __name__ == "__main__":
    main()
