#!/usr/bin/env python3
"""
主题讨论激发器 - Topic Discussion Igniter

升级版能力：
1. AI深度分析：读取笔记内容，发现关联，生成洞察
2. 主题发现：自动从近期笔记中提取潜在讨论主题
3. 渐进展现：分阶段抛出，激发思考
4. 交互讨论：根据用户回应深入探索
5. 行动转化：最终形成指引或工具

启动方式：
- 主动：用户发送"主题讨论" → 自动发现主题
- 被动：用户发送相关链接 → 抛出关联指引
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 路径配置
WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
VAULT_DIR = WORKSPACE / "obsidian-vault"
LEARNINGS_DIR = WORKSPACE / ".learnings"
TOPIC_STATE_FILE = LEARNINGS_DIR / "topic_discussion_state.json"
DISCUSSION_HISTORY_FILE = LEARNINGS_DIR / "discussion_history.json"

FEISHU_USER = "ou_363105a68ee112f714ed44e12c802051"


class TopicDiscussionIgniter:
    """主题讨论激发器"""
    
    def __init__(self):
        self.state = self._load_state()
        self.api_key = self._get_api_key()
        self.base_url = self._get_base_url()
        
    def _get_api_key(self) -> str:
        """获取API密钥 - 优先使用Kimi Coding Plan"""
        import os
        # 优先尝试Kimi Coding Plan (KIMI_API_KEY)
        key = os.environ.get('KIMI_API_KEY', '')
        if key:
            return key
        # 回退到AliCloud
        return os.environ.get('ALICLOUD_API_KEY', '')
    
    def _get_base_url(self) -> str:
        """获取API基础URL - 根据key类型选择"""
        import os
        # 如果KIMI_API_KEY存在，使用Moonshot官方API
        if os.environ.get('KIMI_API_KEY', ''):
            return os.environ.get('KIMI_BASE_URL', 'https://api.moonshot.cn/v1')
        # 否则使用AliCloud DashScope
        return os.environ.get('ALICLOUD_BASE_URL', 'https://coding.dashscope.aliyuncs.com/v1')
    
    def _load_state(self) -> Dict:
        """加载讨论状态"""
        if TOPIC_STATE_FILE.exists():
            try:
                with open(TOPIC_STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'current_topic': None,
            'stage': 0,  # 0=未开始, 1=主题引入, 2=深度展开, 3=关联发现, 4=行动转化
            'messages_sent': 0,
            'last_interaction': None,
            'pending_questions': []
        }
    
    def _save_state(self):
        """保存讨论状态"""
        LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(TOPIC_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def discover_topics_from_recent_notes(self, days: int = 3) -> List[Dict]:
        """
        从近期笔记中发现潜在讨论主题
        
        策略：
        1. 找出最近N天的笔记
        2. 识别高频关键词
        3. 发现未完成的思考线索
        4. 找出可以深化为指引/工具的主题
        """
        topics = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 收集近期笔记
        recent_notes = []
        
        # 从memory目录
        if MEMORY_DIR.exists():
            for md_file in MEMORY_DIR.rglob("*.md"):
                try:
                    mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
                    if mtime >= cutoff_date:
                        content = md_file.read_text(encoding='utf-8')
                        recent_notes.append({
                            'file': md_file.name,
                            'path': str(md_file),
                            'mtime': mtime,
                            'content': content
                        })
                except:
                    continue
        
        # 从vault目录
        if VAULT_DIR.exists():
            for md_file in VAULT_DIR.rglob("*.md"):
                try:
                    mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
                    if mtime >= cutoff_date:
                        content = md_file.read_text(encoding='utf-8')
                        recent_notes.append({
                            'file': md_file.name,
                            'path': str(md_file),
                            'mtime': mtime,
                            'content': content
                        })
                except:
                    continue
        
        # 按时间排序
        recent_notes.sort(key=lambda x: x['mtime'], reverse=True)
        
        # 使用简单启发式发现主题（实际应使用AI分析）
        topic_candidates = []
        
        for note in recent_notes[:10]:  # 分析最近10条
            # 提取标题和关键段落
            lines = note['content'].split('\n')
            title = lines[0] if lines else note['file']
            
            # 找出发散思考的标记
            if any(marker in note['content'] for marker in [
                '发散', '联想', '思考', '疑问', '?', '待讨论',
                'TODO', 'FIXME', '待确认', '可以深入'
            ]):
                topic_candidates.append({
                    'title': title.replace('#', '').strip()[:50],
                    'file': note['file'],
                    'indicator': '发现未完成的思考线索',
                    'priority': 'high'
                })
        
        return topic_candidates[:3]  # 返回前3个候选
    
    def analyze_topic_with_ai(self, topic: str, related_notes: List[Dict]) -> Dict:
        """
        AI深度分析主题 - 真正调用Kimi K2.5
        
        分析维度：
        1. 核心洞察提取
        2. 关联性发现（与其他主题的连接）
        3. 潜在价值评估（能否转化为指引/工具）
        4. 讨论路径设计（如何分阶段展开）
        """
        import requests
        import json
        
        # 读取相关笔记内容
        contents = []
        for note in related_notes[:3]:
            try:
                content = Path(note['path']).read_text(encoding='utf-8')
                contents.append(f"=== {note['file']} ===\n{content[:3000]}")
            except:
                continue
        
        combined_content = '\n\n'.join(contents)
        
        # 构建AI分析提示
        prompt = f"""作为主题讨论引导者，请深度分析以下内容，设计一个能激发用户思考的讨论路径。

**主题**: {topic}

**相关材料**:
```
{combined_content[:6000]}
```

请按以下JSON格式输出分析结果:
{{
    "core_insight": "一句话核心洞察（发现了什么价值）",
    "key_questions": [
        "能激发思考的开放式问题1",
        "能激发思考的开放式问题2", 
        "能激发思考的开放式问题3"
    ],
    "connections": [
        "与XX主题的关联：具体联系"
    ],
    "potential_value": "如果能深入讨论，可能产生什么指引或工具？",
    "discussion_path": {{
        "stage1_intro": "如何用一句话引入，引发兴趣？",
        "stage2_deepen": "如何逐步展开核心洞察？",
        "stage3_connect": "如何引导发现关联？",
        "stage4_action": "如何自然过渡到行动转化？"
    }}
}}

要求：
1. 问题要开放式，不能是简单的是/否
2. 要基于材料中的具体内容，不能泛泛而谈
3. 讨论路径要循序渐进，不要一次性抛出所有内容
4. 要激发用户自己的思考，而不是给出标准答案
5. 必须返回合法的JSON格式"""
        
        # 真正调用Kimi K2.5
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "system", "content": "你是一个专业的主题讨论引导者，擅长从用户的笔记中发现有价值的思考线索，设计能激发深度思考的讨论路径。请用中文回复。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_content = result['choices'][0]['message']['content']
                
                # 提取JSON部分
                try:
                    # 尝试直接解析
                    analysis = json.loads(ai_content)
                    return analysis
                except json.JSONDecodeError:
                    # 尝试从markdown代码块提取
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', ai_content, re.DOTALL)
                    if json_match:
                        analysis = json.loads(json_match.group(1))
                        return analysis
                    else:
                        # 返回原始内容包装
                        return {
                            'core_insight': ai_content[:200],
                            'key_questions': ['请继续深入讨论这个主题'],
                            'connections': [],
                            'potential_value': '需要进一步探讨',
                            'discussion_path': {
                                'stage1_intro': ai_content[:100],
                                'stage2_deepen': '请分享更多想法',
                                'stage3_connect': '我们可以建立更多关联',
                                'stage4_action': '最终形成可落地的方案'
                            }
                        }
            else:
                print(f"[ERROR] API调用失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"[ERROR] AI调用失败: {e}")
        
        # 降级到模板（如果API调用失败）
        return {
            'core_insight': f'基于{topic}的材料，发现了可以从XX角度深化',
            'key_questions': [
                '如果从XX视角重新审视，会有什么新发现？',
                '材料中提到的XX和YY之间有什么深层关联？',
                '如果要把这个思考转化为具体行动，第一步应该是什么？'
            ],
            'connections': ['与之前讨论的ZZ主题有潜在关联'],
            'potential_value': '可能形成XX操作指引或YY自动化工具',
            'discussion_path': {
                'stage1_intro': '注意到你最近在关注XX，有一个角度可能值得探讨...',
                'stage2_deepen': '深入看材料中的这一点，其实暗示了...',
                'stage3_connect': '这让我联想到你之前提到的YY...',
                'stage4_action': '基于这些，你觉得是否值得把XX固化成...'
            }
        }
    
    def generate_stage_message(self, topic: str, analysis: Dict, stage: int) -> str:
        """生成当前阶段的讨论消息"""
        path = analysis.get('discussion_path', {})
        
        if stage == 1:
            # 阶段1：引入主题
            return f"""💡 **主题讨论：{topic}**

{path.get('stage1_intro', f'注意到你最近在关注{topic}，想和你一起深入探讨一下。')}

💭 **启动问题**：
{analysis['key_questions'][0] if analysis['key_questions'] else '你对这个主题最关心的是什么？'}

（回复你的想法，我们继续深入）"""
        
        elif stage == 2:
            # 阶段2：深度展开
            return f"""🎯 **继续：{topic}**

{path.get('stage2_deepen', '进一步看这个问题...')}

核心洞察：**{analysis['core_insight']}**

💭 **深入问题**：
{analysis['key_questions'][1] if len(analysis['key_questions']) > 1 else '你觉得这个洞察对你有什么启发？'}

（继续回复，我们一起挖掘更多）"""
        
        elif stage == 3:
            # 阶段3：关联发现
            connections = '\n'.join([f"• {c}" for c in analysis.get('connections', [])])
            return f"""🔗 **关联发现：{topic}**

{path.get('stage3_connect', '这让我想到一些关联...')}

{connections}

💭 **连接问题**：
{analysis['key_questions'][2] if len(analysis['key_questions']) > 2 else '这些关联是否给了你新的视角？'}

（说说你的联想）"""
        
        elif stage == 4:
            # 阶段4：行动转化
            return f"""🛠️ **行动转化：{topic}**

基于我们的讨论，这个主题可以转化为：
**{analysis.get('potential_value', '具体的指引或工具')}**

{path.get('stage4_action', '你觉得是否值得把这个思考固化下来？')}

📋 **建议行动**：
• 形成操作指引文档
• 或开发自动化工具
• 或建立定期检查机制

（回复`形成指引`或`开发工具`，我来帮你落实）"""
        
        return "讨论继续..."
    
    def handle_user_response(self, user_input: str) -> Optional[str]:
        """
        处理用户回应，决定下一步
        
        策略：
        1. 分析用户回应的情绪和方向
        2. 决定是否推进到下一阶段
        3. 生成针对性的追问或建议
        """
        if not self.state['current_topic']:
            return None
        
        current_stage = self.state['stage']
        
        # 简单启发式：用户回应长度>20字，推进到下一阶段
        if len(user_input) > 20 and current_stage < 4:
            self.state['stage'] = current_stage + 1
            self.state['messages_sent'] += 1
            self._save_state()
            
            # 生成下一阶段消息（需要重新分析，简化版）
            return self.generate_stage_message(
                self.state['current_topic'],
                self.state.get('analysis', {}),
                self.state['stage']
            )
        
        # 如果用户短回复，继续追问
        return f"再多说说你的想法？我想更深入理解你的思路。"
    
    def start_topic_discussion(self, topic: str = None) -> str:
        """
        启动主题讨论
        
        如果没有指定主题，自动发现
        """
        if not topic:
            # 自动发现主题
            candidates = self.discover_topics_from_recent_notes()
            if not candidates:
                return "近期没有发现特别值得讨论的主题。你可以直接告诉我想讨论什么，或者发送相关链接。"
            
            topic = candidates[0]['title']
        
        # 搜索相关笔记
        related_notes = self._search_related_notes(topic)
        
        # AI分析（简化版）
        analysis = self.analyze_topic_with_ai(topic, related_notes)
        
        # 更新状态
        self.state = {
            'current_topic': topic,
            'stage': 1,
            'messages_sent': 1,
            'last_interaction': datetime.now().isoformat(),
            'analysis': analysis,
            'pending_questions': analysis.get('key_questions', [])
        }
        self._save_state()
        
        # 生成阶段1消息
        return self.generate_stage_message(topic, analysis, 1)
    
    def _search_related_notes(self, topic: str) -> List[Dict]:
        """搜索相关笔记"""
        related = []
        keywords = topic.lower().split()
        
        for search_dir in [MEMORY_DIR, VAULT_DIR]:
            if not search_dir.exists():
                continue
            for md_file in search_dir.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding='utf-8').lower()
                    score = sum(1 for kw in keywords if kw in content)
                    if score > 0:
                        related.append({
                            'path': str(md_file),
                            'file': md_file.name,
                            'score': score
                        })
                except:
                    continue
        
        related.sort(key=lambda x: x['score'], reverse=True)
        return related[:5]
    
    def handle_link_submission(self, link: str, context: str = "") -> Optional[str]:
        """
        处理链接提交
        
        当用户发送链接时，检查是否与当前讨论主题相关
        如果相关，抛出关联指引
        """
        if not self.state['current_topic']:
            # 没有正在进行的讨论，检查是否需要启动新主题
            return None
        
        # 检查链接内容与当前主题的相关性（简化版）
        topic_keywords = self.state['current_topic'].lower().split()
        link_relevant = any(kw in link.lower() or kw in context.lower() for kw in topic_keywords)
        
        if link_relevant:
            return f"""🔗 **关联发现**

你分享的这个链接与当前讨论的「{self.state['current_topic']}」相关。

这让我想到：**基于这个新材料，我们是否可以从XX角度重新审视之前的讨论？**

（说说这个链接给你的新启发）"""
        
        return None


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='主题讨论激发器')
    parser.add_argument('--discover', action='store_true', help='自动发现主题')
    parser.add_argument('--topic', type=str, help='指定讨论主题')
    parser.add_argument('--respond', type=str, help='处理用户回应')
    parser.add_argument('--link', type=str, help='处理链接提交')
    parser.add_argument('--test', action='store_true', help='测试运行')
    args = parser.parse_args()
    
    igniter = TopicDiscussionIgniter()
    
    if args.test:
        # 测试：自动发现主题并启动
        print("🔍 发现近期主题...")
        candidates = igniter.discover_topics_from_recent_notes(days=3)
        
        if candidates:
            print(f"\n发现 {len(candidates)} 个候选主题：")
            for i, c in enumerate(candidates, 1):
                print(f"{i}. {c['title']} ({c['indicator']})")
            
            # 启动第一个主题
            print(f"\n🚀 启动讨论：{candidates[0]['title']}\n")
            message = igniter.start_topic_discussion(candidates[0]['title'])
            print(message)
        else:
            print("近期没有发现值得讨论的主题")
    
    elif args.topic:
        message = igniter.start_topic_discussion(args.topic)
        print(message)
    
    elif args.respond:
        message = igniter.handle_user_response(args.respond)
        if message:
            print(message)
    
    elif args.link:
        message = igniter.handle_link_submission(args.link)
        if message:
            print(message)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
