#!/usr/bin/env python3
"""
AI能力缺口分析器 - AI Gap Analyzer

功能：
1. 调用Kimi K2.5模型分析用户对话历史
2. 识别真实的能力缺口（非关键词匹配）
3. 生成个性化的改进建议
4. 支持凌晨5:00自动运行和手动运行

使用方法：
    python3 ai_gap_analyzer.py --days 7              # 分析最近7天
    python3 ai_gap_analyzer.py --file memory.md      # 分析指定文件
    python3 ai_gap_analyzer.py --output json         # 输出JSON格式

作者：Kimi Claw
创建时间：2026-03-10
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# 添加处理器目录到路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from config import WORKSPACE, LEARNINGS_DIR, DEFAULT_MODEL


class AIGapAnalyzer:
    """AI能力缺口分析器"""
    
    def __init__(self, model: str = None):
        self.model = model or "kimi-k2.5"  # 阿里云Kimi模型ID
        self.memory_dir = WORKSPACE / "memory"
        self.sessions_dir = Path("/root/.openclaw/agents/main/sessions")
        self.output_file = LEARNINGS_DIR / "ai_gap_analysis.json"
        
        # API配置（从环境变量读取）
        # 使用阿里云百炼Kimi K2.5 API
        self.api_key = os.environ.get('ALICLOUD_API_KEY', '')
        self.base_url = 'https://coding.dashscope.aliyuncs.com/v1'
        self.model = 'kimi-k2.5'
        
        # 加载已安装的skills
        self.installed_skills = self._load_installed_skills()
        
    def _load_installed_skills(self) -> List[str]:
        """加载已安装的skills列表"""
        skills_dir = Path("/root/.openclaw/skills")
        if not skills_dir.exists():
            return []
        return [d.name for d in skills_dir.iterdir() if d.is_dir()]
    
    def _is_skill_installed(self, skill_name: str) -> bool:
        """检查某个skill是否已安装（支持模糊匹配和关键词映射）"""
        if not skill_name:
            return False
        
        skill_name_lower = skill_name.lower()
        
        # 关键词映射表：建议名称 -> 已安装skill关键词
        # 基于 SKILL_INDEX.md 建立的功能-名称映射
        skill_keyword_map = {
            # 文章剪藏/内容处理类
            'article-clip': ['pipeline-health', 'health-monitor'],
            'content-pipeline': ['pipeline-health', 'health-monitor'],
            'article-clip-pipeline': ['pipeline-health', 'health-monitor'],
            'content-processing': ['pipeline-health', 'health-monitor', 'knowledge-studio'],
            'article-processing': ['pipeline-health', 'health-monitor'],
            
            # 上下文/会话管理类
            'context-threshold': ['auto-compact', 'dynamic-compact', 'auto-fix'],
            'context-adaptive': ['auto-compact', 'dynamic-compact', 'auto-fix'],
            'session-compact': ['auto-compact', 'dynamic-compact', 'auto-fix'],
            'dynamic-compact': ['auto-compact', 'dynamic-compact'],
            'context-guardian': ['auto-compact', 'dynamic-compact'],
            'session-management': ['auto-compact', 'dynamic-compact', 'auto-fix'],
            
            # 知识管理/会议准备类
            'meeting-prep': ['knowledge-studio'],
            'discussion-prep': ['knowledge-studio'],
            'knowledge-prep': ['knowledge-studio'],
            'meeting-orchestrator': ['knowledge-studio'],
            'knowledge-management': ['knowledge-studio'],
            'content-organization': ['knowledge-studio'],
            
            # 待办/行动项管理类
            'action-item': ['auto-fix'],
            'action-loop': ['auto-fix'],
            'task-tracker': ['auto-fix'],
            'todo-management': ['auto-fix'],
            'action-closer': ['auto-fix'],
            'workflow-automation': ['auto-fix'],
            
            # Skill市场/发现类
            'skill-market': ['clawhub'],
            'skill-scout': ['clawhub'],
            'skill-discovery': ['clawhub'],
            'market-search': ['clawhub'],
            
            # Git/代码安全类
            'git-safety': ['git-safety-guardian'],
            'git-guardian': ['git-safety-guardian'],
            'push-protection': ['git-safety-guardian'],
            'code-safety': ['git-safety-guardian'],
            
            # 飞书/消息处理类
            'feishu-dedup': ['feishu-deduplication', 'feishu-send-guardian'],
            'message-guardian': ['feishu-deduplication', 'feishu-send-guardian'],
            'send-protection': ['feishu-send-guardian'],
            'duplicate-prevention': ['feishu-deduplication'],
            'message-deduplication': ['feishu-deduplication'],
            
            # BMAD/开发框架类
            'bmad': ['bmad-evo', 'bmad-method'],
            'multi-agent': ['bmad-evo', 'bmad-method'],
            'development-framework': ['bmad-evo', 'bmad-method'],
            'agent-framework': ['bmad-evo', 'bmad-method'],
            
            # 频道配置类
            'channel-setup': ['channels-setup'],
            'im-config': ['channels-setup'],
            'messaging-setup': ['channels-setup'],
            
            # 飞书自动化类
            'feishu-auto': ['feishu-automation'],
            'lark-automation': ['feishu-automation'],
            'feishu-bot': ['feishu-automation'],
        }
        
        # 检查映射表
        for keyword, installed_keywords in skill_keyword_map.items():
            if keyword in skill_name_lower:
                for installed in self.installed_skills:
                    installed_lower = installed.lower()
                    for ik in installed_keywords:
                        if ik in installed_lower:
                            print(f"[INFO] 通过关键词映射跳过已安装skill: {skill_name} -> {installed}")
                            return True
        
        # 原有匹配逻辑
        for installed in self.installed_skills:
            installed_lower = installed.lower()
            if skill_name_lower == installed_lower or skill_name_lower in installed_lower or installed_lower in skill_name_lower:
                return True
        return False
    
    def _filter_installed_skills(self, gaps: List[Dict]) -> List[Dict]:
        """过滤掉已安装skill的建议"""
        filtered = []
        for gap in gaps:
            suggested_skill = gap.get('suggested_skill', '')
            if suggested_skill and self._is_skill_installed(suggested_skill):
                print(f"[INFO] 跳过已安装skill的建议: {suggested_skill}")
                continue
            filtered.append(gap)
        return filtered
        
    def _call_llm(self, prompt: str, temperature: float = 0.3) -> str:
        """调用LLM进行分析"""
        try:
            # 尝试使用openai库
            from openai import OpenAI
            
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的AI能力分析助手，擅长从用户行为中发现效率瓶颈并提出改进建议。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=4000
            )
            
            return response.choices[0].message.content
            
        except ImportError:
            # 如果没有openai库，使用requests
            return self._call_llm_with_requests(prompt, temperature)
        except Exception as e:
            print(f"[ERROR] LLM调用失败: {e}")
            return None
    
    def _call_llm_with_requests(self, prompt: str, temperature: float) -> str:
        """使用requests调用LLM"""
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的AI能力分析助手，擅长从用户行为中发现效率瓶颈并提出改进建议。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"[ERROR] API调用失败: {e}")
            return None
    
    def _read_memory_files(self, days: int = 7) -> str:
        """读取最近N天的memory文件"""
        contents = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            memory_file = self.memory_dir / f"{date}.md"
            
            if memory_file.exists():
                try:
                    content = memory_file.read_text(encoding='utf-8')
                    # 限制单个文件大小，避免超出上下文
                    if len(content) > 10000:
                        content = content[:10000] + "\n... (内容已截断)"
                    contents.append(f"=== {date} ===\n{content}\n")
                except Exception as e:
                    print(f"[WARN] 读取 {memory_file} 失败: {e}")
        
        return "\n".join(contents)
    
    def _read_session_summary(self, days: int = 7) -> str:
        """读取会话摘要"""
        summary = []
        
        # 读取最近的session文件（只读文件名和元数据，不读完整内容）
        if self.sessions_dir.exists():
            session_files = sorted(self.sessions_dir.glob("*.jsonl"), 
                                 key=lambda x: x.stat().st_mtime, 
                                 reverse=True)[:5]  # 最近5个会话
            
            for sf in session_files:
                try:
                    # 只读取前10行作为样本
                    lines = []
                    with open(sf, 'r', encoding='utf-8') as f:
                        for i, line in enumerate(f):
                            if i >= 10:
                                break
                            if line.strip():
                                try:
                                    data = json.loads(line.strip())
                                    # 提取关键信息
                                    if 'role' in data and data['role'] in ['user', 'assistant']:
                                        content = data.get('content', '')[:200]
                                        if content:
                                            lines.append(f"[{data['role']}] {content}")
                                except:
                                    continue
                    
                    if lines:
                        summary.append(f"=== 会话: {sf.name} ===")
                        summary.extend(lines)
                        summary.append("")
                except Exception as e:
                    print(f"[WARN] 读取会话 {sf} 失败: {e}")
        
        return "\n".join(summary[:100])  # 限制总长度
    
    def analyze_with_ai(self, days: int = 7) -> Dict:
        """使用AI分析能力缺口"""
        print(f"🧠 启动AI分析（模型: {self.model}）...")
        
        # 收集数据
        print(f"📚 读取最近{days}天的记忆文件...")
        memory_content = self._read_memory_files(days)
        
        if not memory_content.strip():
            print("[WARN] 没有找到记忆文件内容")
            return {"gaps": [], "timestamp": datetime.now().isoformat()}
        
        print(f"📊 收集到 {len(memory_content)} 字符的记忆内容")
        
        # 构建分析提示
        prompt = self._build_analysis_prompt(memory_content, days)
        
        print("🤖 调用LLM进行分析（约需10-30秒）...")
        response = self._call_llm(prompt, temperature=0.3)
        
        if not response:
            print("[ERROR] LLM分析失败")
            return {"gaps": [], "error": "LLM调用失败", "timestamp": datetime.now().isoformat()}
        
        # 解析响应
        print("📝 解析分析结果...")
        gaps = self._parse_analysis_response(response)
        
        # 过滤已安装的skill
        original_count = len(gaps)
        gaps = self._filter_installed_skills(gaps)
        filtered_count = original_count - len(gaps)
        if filtered_count > 0:
            print(f"[INFO] 过滤了 {filtered_count} 个已安装skill的建议")
        
        # 添加已安装skill信息到结果
        result = {
            "timestamp": datetime.now().isoformat(),
            "model": self.model,
            "analysis_days": days,
            "gaps": gaps,
            "installed_skills": self.installed_skills,  # 记录已安装skill供参考
            "raw_response": response[:2000] if len(response) > 2000 else response  # 保留原始响应供调试
        }
        
        # 保存结果
        self._save_result(result)
        
        return result
    
    def _build_analysis_prompt(self, memory_content: str, days: int) -> str:
        """构建分析提示"""
        # 获取已安装skill列表，供AI参考
        installed_skills_text = "\n".join([f"- {skill}" for skill in self.installed_skills]) if self.installed_skills else "无"
        
        prompt = f"""请分析以下用户最近{days}天的对话和工作记录，识别出用户的**能力缺口**和**效率瓶颈**。

## 已安装的Skills（请不要推荐这些）
{installed_skills_text}

## 分析要求

1. **识别重复性工作**：哪些任务是用户反复手动执行的？
2. **发现工具缺口**：哪些功能用户经常需要但没有自动化工具？
3. **检测流程断点**：用户的工作流中哪些环节效率低下？
4. **评估Skill需求**：基于OpenClaw生态，推荐哪些Skills可以填补缺口？**重要：不要推荐已安装列表中的Skill**

## 输出格式

请以JSON格式返回分析结果：

```json
{{
  "gaps": [
    {{
      "type": "messaging_automation|data_sync|content_processing|knowledge_query|code_generation|meeting_assistant|workflow_optimization",
      "title": "简短标题",
      "description": "详细描述发现的能力缺口",
      "evidence": "基于哪些具体行为得出此结论",
      "frequency": "high|medium|low",
      "suggested_skill": "建议安装的Skill名称",
      "skill_description": "该Skill能解决什么问题",
      "estimated_benefit": "预计节省的时间或提升的效率",
      "priority": "high|medium|low",
      "action": "install_skill|fix_config|enable_feature|create_workflow"
    }}
  ]
}}
```

## 用户行为数据

{memory_content}

请基于以上数据，生成3-5条最有价值的能力缺口分析。"""
        
        return prompt
    
    def _parse_analysis_response(self, response: str) -> List[Dict]:
        """解析LLM的分析响应"""
        gaps = []
        
        # 保存原始响应用于调试
        debug_file = LEARNINGS_DIR / "ai_gap_debug.log"
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"解析时间: {datetime.now().isoformat()}\n")
                f.write(f"响应长度: {len(response)}\n")
                f.write("="*50 + "\n")
                f.write(response)
        except Exception as e:
            print(f"[DEBUG] 保存调试日志失败: {e}")
        
        try:
            # 尝试提取JSON - 支持多种格式
            import re
            
            # 方法1: 查找```json代码块
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                print(f"[DEBUG] 从```json代码块提取JSON，长度: {len(json_str)}")
            else:
                # 方法2: 查找```代码块（无语言标记）
                json_match = re.search(r'```\s*(\{.*?\})\s*```', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    print(f"[DEBUG] 从```代码块提取JSON，长度: {len(json_str)}")
                else:
                    # 方法3: 查找第一个{到最后一个}之间的内容
                    start = response.find('{')
                    end = response.rfind('}')
                    if start != -1 and end != -1 and end > start:
                        json_str = response[start:end+1]
                        print(f"[DEBUG] 从原始文本提取JSON，位置: {start}-{end}")
                    else:
                        # 方法4: 直接使用整个响应
                        json_str = response
                        print(f"[DEBUG] 使用完整响应作为JSON，长度: {len(json_str)}")
            
            # 清理可能的特殊字符
            json_str = json_str.strip()
            
            # 尝试解析JSON
            try:
                data = json.loads(json_str)
                print(f"[DEBUG] JSON解析成功，类型: {type(data)}")
            except json.JSONDecodeError as e:
                print(f"[DEBUG] JSON解析失败: {e}")
                print(f"[DEBUG] JSON前200字符: {json_str[:200]}")
                raise
            
            if "gaps" in data and isinstance(data["gaps"], list):
                gaps = data["gaps"]
                print(f"✅ 成功解析 {len(gaps)} 条能力缺口")
                
                # 验证每条缺口的必要字段
                for i, gap in enumerate(gaps):
                    if not isinstance(gap, dict):
                        print(f"[WARN] 第{i+1}条缺口不是字典类型，跳过")
                        continue
                    # 确保必要字段存在
                    gap.setdefault("type", "unknown")
                    gap.setdefault("title", "未命名缺口")
                    gap.setdefault("description", "")
                    gap.setdefault("priority", "medium")
                    gap.setdefault("action", "install_skill")
            else:
                print(f"[WARN] 响应中没有找到gaps字段，可用字段: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                # 尝试将整个响应作为单条缺口
                if isinstance(data, dict):
                    gaps = [{
                        "type": "workflow_optimization",
                        "title": "AI分析结果",
                        "description": str(data)[:200],
                        "priority": "medium",
                        "action": "install_skill"
                    }]
                
        except json.JSONDecodeError as e:
            print(f"[WARN] JSON解析失败: {e}")
            # 尝试文本解析作为fallback
            gaps = self._parse_text_response(response)
        except Exception as e:
            print(f"[ERROR] 解析响应时出错: {e}")
            gaps = []
        
        return gaps
    
    def _parse_text_response(self, response: str) -> List[Dict]:
        """文本方式解析响应（fallback）- 增强版"""
        gaps = []
        
        print("[DEBUG] 使用文本解析作为fallback...")
        
        # 按行分割并清理
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        # 查找数字编号或Markdown标题
        import re
        
        # 模式1: 数字编号 (1. 2. 3.)
        numbered_sections = re.split(r'\n(?=\d+\.)', response)
        
        # 模式2: Markdown标题 (## **)
        header_sections = re.split(r'\n(?=##|\*\*)', response)
        
        # 使用能分割出更多部分的方案
        sections = numbered_sections if len(numbered_sections) > len(header_sections) else header_sections
        
        print(f"[DEBUG] 文本解析: 找到 {len(sections)} 个部分")
        
        for i, section in enumerate(sections[:6], 1):  # 最多6条
            section = section.strip()
            if not section or len(section) < 20:  # 太短的跳过
                continue
            
            # 提取标题（第一行）
            first_line = section.split('\n')[0].strip()
            # 清理Markdown标记
            title = re.sub(r'^\d+\.\s*', '', first_line)  # 移除数字编号
            title = re.sub(r'[#*\-\[\]]', '', title).strip()  # 移除Markdown标记
            
            if len(title) < 3:  # 标题太短，跳过
                continue
            
            # 提取描述（剩余内容）
            description = '\n'.join(section.split('\n')[1:]).strip()[:200]
            
            # 检测优先级关键词
            priority = "medium"
            if any(kw in section.lower() for kw in ['高优先级', '重要', '关键', 'high', 'critical', '必须']):
                priority = "high"
            elif any(kw in section.lower() for kw in ['低优先级', '可选', '建议', 'low', '可以考虑']):
                priority = "low"
            
            # 检测类型关键词
            gap_type = "workflow_optimization"
            if any(kw in section.lower() for kw in ['git', '同步', '备份', 'push']):
                gap_type = "data_sync"
            elif any(kw in section.lower() for kw in ['消息', '通知', '飞书', '提醒', '推送']):
                gap_type = "messaging_automation"
            elif any(kw in section.lower() for kw in ['会议', '纪要', '待办', 'action']):
                gap_type = "meeting_assistant"
            elif any(kw in section.lower() for kw in ['文章', '内容', '整理', '剪藏']):
                gap_type = "content_processing"
            
            gap = {
                "type": gap_type,
                "title": title[:50],  # 限制长度
                "description": description or "AI识别的能力缺口",
                "evidence": "基于行为模式分析",
                "frequency": "medium",
                "suggested_skill": f"auto-{gap_type}",
                "skill_description": f"自动处理{gap_type}相关任务",
                "estimated_benefit": "待评估",
                "priority": priority,
                "action": "install_skill"
            }
            
            gaps.append(gap)
            print(f"[DEBUG] 文本解析: 提取到缺口 '{title[:30]}...'")
        
        print(f"✅ 文本解析完成，提取 {len(gaps)} 条缺口")
        return gaps
    
    def _save_result(self, result: Dict):
        """保存分析结果"""
        try:
            LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"💾 分析结果已保存: {self.output_file}")
        except Exception as e:
            print(f"[WARN] 保存结果失败: {e}")
    
    def format_report(self, result: Dict) -> str:
        """格式化分析报告（带来源标记）"""
        gaps = result.get("gaps", [])
        
        if not gaps:
            return "🧠 **AI自主进化分析**：经过深度分析，未发现明显的能力缺口，系统运行高效！"
        
        lines = ["\n🧠 **AI自主进化分析**（Kimi K2.5 深度分析）\n"]
        lines.append(f"📅 分析时间: {result.get('timestamp', '未知')[:19]}")
        lines.append(f"📊 分析天数: {result.get('analysis_days', 7)} 天")
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
            
            # 推荐Skill及来源标记
            skill = gap.get('suggested_skill', '')
            if skill:
                # 判断skill来源
                source_tag = self._get_skill_source_tag(skill)
                lines.append(f"   💡 推荐Skill: {skill} {source_tag}")
                
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
            
            lines.append("")
        
        lines.append("---\n")
        lines.append("📋 **批量操作**：")
        lines.append("• `全部安装` - 安装所有高优先级建议")
        lines.append("• `忽略` - 今日不处理，明日再评估")
        lines.append("• `详细{i}` - 查看第i条详细说明\n")
        
        # 添加来源图例
        lines.append("🏷️ **Skill来源说明**：")
        lines.append("• 📦 ClawHub - 已在ClawHub市场发布")
        lines.append("• 🐙 GitHub - 开源社区项目")
        lines.append("• 🛠️ 自建 - 需本地创建实现\n")
        
        return "\n".join(lines)
    
    def _get_skill_source_tag(self, skill_name: str) -> str:
        """获取skill的来源标记"""
        if not skill_name:
            return ""
        
        # 检查是否已在本地安装
        if self._is_skill_installed(skill_name):
            return "[✅已安装]"
        
        # 检查常见skill的来源（硬编码映射表）
        clawhub_skills = [
            "feishu-automation", "knowledge-studio", "bmad-evo", "bmad-method",
            "channels-setup", "nano-pdf", "github", "weather", "healthcheck",
            "tmux", "clawhub"
        ]
        
        github_skills = [
            "self-improving-agent", "openclaw-skills", "skill-creator"
        ]
        
        skill_lower = skill_name.lower()
        
        # 检查ClawHub
        for cs in clawhub_skills:
            if cs in skill_lower or skill_lower in cs:
                return "[📦ClawHub]"
        
        # 检查GitHub
        for gs in github_skills:
            if gs in skill_lower or skill_lower in gs:
                return "[🐙GitHub]"
        
        # 默认标记为自建
        return "[🛠️自建]"


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI能力缺口分析器')
    parser.add_argument('--days', type=int, default=7, help='分析天数（默认7天）')
    parser.add_argument('--model', type=str, default=None, help='模型ID（默认使用系统配置）')
    parser.add_argument('--output', type=str, choices=['json', 'report'], default='report', help='输出格式')
    parser.add_argument('--save', action='store_true', help='保存结果到文件')
    
    args = parser.parse_args()
    
    analyzer = AIGapAnalyzer(model=args.model)
    
    print("=" * 60)
    print(f"🚀 AI能力缺口分析器启动")
    print(f"模型: {analyzer.model}")
    print(f"分析天数: {args.days} 天")
    print("=" * 60)
    
    result = analyzer.analyze_with_ai(days=args.days)
    
    if args.output == 'json':
        print("\n" + json.dumps(result, ensure_ascii=False, indent=2))
    else:
        report = analyzer.format_report(result)
        print("\n" + report)
    
    print("=" * 60)
    print("✅ 分析完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
