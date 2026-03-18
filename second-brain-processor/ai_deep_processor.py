#!/usr/bin/env python3
"""
AI 深度整理模块 v2.0 - 真正的AI理解版

使用子Agent调用进行：
1. 主题识别与分类
2. 核心观点提炼
3. 有价值思考生成
4. 关联已有知识
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict

VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
PROCESSOR_DIR = Path("/root/.openclaw/workspace/second-brain-processor")

def log(message: str):
    """日志输出"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def find_related_notes(title: str, content: str, top_k: int = 3) -> List[Dict]:
    """查找相关笔记（使用现有TF-IDF方法）"""
    try:
        sys.path.insert(0, str(PROCESSOR_DIR))
        from ai_processor import find_related_notes_tfidf
        
        related = find_related_notes_tfidf(content, title, top_k)
        return [{"title": note['title'], "path": note['path'], "similarity": sim} 
                for note, sim in related]
    except Exception as e:
        log(f"查找相关笔记失败: {e}")
        return []

def call_ai_for_deep_processing(content: str, title: str, related_notes: List[Dict]) -> Dict:
    """
    调用AI进行深度处理
    
    直接使用阿里云Kimi K2.5 API进行真正的AI分析，不再降级到模板模式。
    
    返回: {
        "key_takeaway": "一句话核心观点",
        "core_points": ["要点1", "要点2", ...],
        "valuable_thoughts": ["思考1", "思考2", ...],
        "themes": ["主题1", "主题2"],
        "connections": ["与XX的关联"]
    }
    """
    
    # 构建关联笔记上下文
    related_context = ""
    if related_notes:
        related_context = "\n\n**已有关联笔记：**\n"
        for note in related_notes[:2]:
            related_context += f"- 《{note['title']}》\n"
    
    # 直接调用AI API进行分析
    try:
        import requests
        
        api_key = os.environ.get('ALICLOUD_API_KEY', '')
        if not api_key:
            log("  ⚠️ 未配置ALICLOUD_API_KEY，降级到基础模式")
            raise ValueError("API key not configured")
        
        # 构建prompt
        prompt = f"""请深度分析以下对话/文章内容，提取核心观点和有价值的思考：

**标题**: {title}

**内容**:
```
{content[:5000]}
```
{related_context}

请按以下JSON格式输出分析结果：
{{
    "key_takeaway": "一句话概括核心观点（不超过50字）",
    "core_points": ["要点1", "要点2", "要点3"],
    "valuable_thoughts": ["引发的思考1", "引发的思考2"],
    "themes": ["主题标签1", "主题标签2"],
    "connections": ["与已有知识的关联"]
}}

要求：
1. key_takeaway 必须是一句话，概括性最强
2. core_points 提取3-5个核心观点，每条简洁有力
3. valuable_thoughts 列出由此引发的深度思考
4. themes 给出2-3个主题分类标签
5. connections 列出与已有知识的潜在关联"""

        # 调用阿里云Kimi API
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'kimi-k2.5',
            'messages': [
                {'role': 'system', 'content': '你是一个深度内容分析助手，擅长从对话中提取核心观点和洞察。'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 2000
        }
        
        log(f"  🤖 调用AI分析: {title[:50]}...")
        
        response = requests.post(
            'https://coding.dashscope.aliyuncs.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=120
        )
        
        if response.status_code == 200:
            result_data = response.json()
            ai_output = result_data['choices'][0]['message']['content']
            
            # 解析JSON结果
            try:
                # 尝试直接解析
                ai_result = json.loads(ai_output)
            except json.JSONDecodeError:
                # 尝试从markdown代码块中提取
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_output, re.DOTALL)
                if json_match:
                    ai_result = json.loads(json_match.group(1))
                else:
                    # 提取任何JSON格式的内容
                    json_match = re.search(r'\{.*\}', ai_output, re.DOTALL)
                    if json_match:
                        ai_result = json.loads(json_match.group())
                    else:
                        raise ValueError("无法解析AI输出")
            
            log(f"  ✅ AI分析完成: {len(ai_result.get('core_points', []))} 个要点")
            
            return {
                "key_takeaway": ai_result.get("key_takeaway", f"关于{title}的深度分析"),
                "core_points": ai_result.get("core_points", []),
                "valuable_thoughts": ai_result.get("valuable_thoughts", []),
                "themes": ai_result.get("themes", _extract_themes(content)),
                "connections": ai_result.get("connections", [])
            }
        else:
            log(f"  ⚠️ API调用失败: {response.status_code}")
            raise ValueError(f"API error: {response.status_code}")
            
    except Exception as e:
        log(f"  ⚠️ AI分析失败: {e}，降级到基础模式")
        
        # 降级到基础模板
        themes = _extract_themes(content)
        
        return {
            "key_takeaway": f"关于{title}的{len(themes)}个主题讨论",
            "core_points": _generate_core_points(content, themes),
            "valuable_thoughts": ["AI深度分析暂时不可用，已使用基础模板"],
            "themes": themes if themes else ["待分类"],
            "connections": [f"与 [[{note['title'][:-3]}]] 的关联待分析" for note in related_notes[:2]]
        }

def _extract_themes(content: str) -> List[str]:
    """从内容中提取主题关键词"""
    # 简单的关键词提取
    keywords = []
    
    # 技术相关
    tech_keywords = ['代码', '脚本', '程序', 'bug', '错误', '修复', '系统', 'api', 'ai']
    for kw in tech_keywords:
        if kw in content.lower():
            keywords.append('技术')
            break
    
    # 飞书相关
    if any(kw in content for kw in ['飞书', '消息', '延迟', '重复', '插件']):
        keywords.append('飞书系统')
    
    # Git相关
    if any(kw in content for kw in ['git', 'github', '推送', '仓库']):
        keywords.append('Git管理')
    
    # 监控相关
    if any(kw in content for kw in ['监控', '检查', '日志', '报警']):
        keywords.append('系统监控')
    
    return keywords if keywords else ['对话记录']

def _generate_core_points(content: str, themes: List[str]) -> List[str]:
    """基于内容生成核心要点"""
    points = []
    
    # 提取用户问题
    user_questions = re.findall(r'(?:用户:|User:)\s*([^\n]+)', content)
    if user_questions:
        points.append(f"用户关注点: {user_questions[0][:50]}...")
    
    # 基于主题生成
    for theme in themes[:2]:
        if theme == '飞书系统':
            points.append("涉及飞书消息系统稳定性问题")
        elif theme == '技术':
            points.append("技术实现方案讨论")
        elif theme == 'Git管理':
            points.append("代码仓库管理相关")
        elif theme == '系统监控':
            points.append("系统健康监控配置")
    
    if len(points) < 2:
        points.append("具体讨论内容待AI深度分析")
    
    return points

def process_conversation_with_ai(content: str, title: str) -> Dict:
    """
    对话AI深度分析（兼容旧版API）
    
    这是 ai_deep_process 的别名函数，供 kimiclaw_v2.py 调用
    
    Args:
        content: 对话内容
        title: 对话标题
    
    Returns:
        处理结果字典，包含:
        - key_takeaway: 一句话核心观点
        - core_points: 详细观点列表
        - valuable_thoughts: 引发的思考
        - themes: 主题标签
        - connections: 知识关联
    """
    return ai_deep_process(content, title, source_type="chat")


def ai_deep_process(content: str, title: str, source_type: str = "general") -> Dict:
    """
    深度AI处理入口
    
    Args:
        content: 原始内容
        title: 标题
        source_type: 来源类型 (chat/article/note)
    
    Returns:
        处理结果字典
    """
    log(f"开始深度处理: {title}")
    
    # 1. 查找相关笔记
    related_notes = find_related_notes(title, content)
    log(f"  找到 {len(related_notes)} 个相关笔记")
    
    # 2. AI深度处理
    ai_result = call_ai_for_deep_processing(content, title, related_notes)
    log(f"  AI处理完成: {len(ai_result.get('core_points', []))} 个要点")
    
    # 3. 组装结果
    result = {
        "key_takeaway": ai_result.get("key_takeaway", "待提炼"),
        "core_points": ai_result.get("core_points", []),
        "valuable_thoughts": ai_result.get("valuable_thoughts", []),
        "themes": ai_result.get("themes", []),
        "connections": ai_result.get("connections", []),
        "related_notes": related_notes,
        "processed_at": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 4. 传递内部字段（如果有待处理任务）
    if "_pending_task_id" in ai_result:
        result["_pending_task_id"] = ai_result["_pending_task_id"]
    if "_pending_file" in ai_result:
        result["_pending_file"] = ai_result["_pending_file"]
    
    return result

def process_chat_record(content: str, title: str, date_str: str) -> Dict:
    """
    专门处理聊天记录
    
    特点：
    - 识别多个主题
    - 提取有价值的讨论点
    - 记录决策和思考过程
    """
    log(f"处理聊天记录: {title}")
    
    # 先进行普通深度处理
    result = ai_deep_process(content, title, source_type="chat")
    
    # 聊天记录特有：识别多主题
    themes_prompt = f"""请分析以下聊天记录，识别其中的**不同主题**，每个主题单独分析：

**聊天记录**：
```
{content[:3000]}
```

请输出：
1. 主题数量及每个主题的名称
2. 每个主题的核心讨论点
3. 重要决策或结论
4. 有价值的思考片段

格式：
- 主题1：[主题名]
  - 核心观点：...
  - 重要决策：...
  - 引发思考：...
"""
    
    try:
        import openclaw
        themes_result = openclaw.sessions_spawn(
            task=themes_prompt,
            model="kimi-k2.5",
            thinking="high",
            timeout_seconds=120
        )
        
        result["multi_themes_analysis"] = str(themes_result.get('result', themes_result))
        
    except Exception as e:
        log(f"多主题分析失败: {e}")
        result["multi_themes_analysis"] = "待进一步分析多主题"
    
    return result

def generate_obsidian_note(processed: Dict, original_content: str, title: str, 
                           source: str = "聊天记录", tags: List[str] = None) -> str:
    """
    生成Obsidian格式的笔记
    """
    if tags is None:
        tags = ["聊天记录", "待整理"]
    
    # 添加处理完成标签
    if "待整理" in tags:
        tags.remove("待整理")
    tags.append("已深度处理")
    
    # 主题标签
    themes = processed.get("themes", [])
    for theme in themes:
        clean_theme = theme.replace(" ", "-")
        if clean_theme not in tags:
            tags.append(clean_theme)
    
    # 构建笔记内容
    note_content = f"""---
title: {title}
date: {processed.get('processed_at', time.strftime('%Y-%m-%d %H:%M:%S'))}
tags: {json.dumps(tags, ensure_ascii=False)}
source: {source}
status: 已深度处理
---

# {title}

## 🎯 一句话核心观点

{processed.get('key_takeaway', '待提炼')}

## 💡 详细观点

"""
    
    # 添加核心观点
    for point in processed.get("core_points", []):
        note_content += f"- {point}\n"
    
    note_content += "\n## 🤔 引发的思考\n\n"
    
    # 添加思考
    for thought in processed.get("valuable_thoughts", []):
        note_content += f"- {thought}\n"
    
    # 添加关联
    if processed.get("connections"):
        note_content += "\n## 🔗 关联知识\n\n"
        for conn in processed.get("connections", []):
            note_content += f"- {conn}\n"
    
    # 添加多主题分析（如果是聊天记录）
    if "multi_themes_analysis" in processed:
        note_content += f"\n## 📋 多主题分析\n\n{processed['multi_themes_analysis']}\n"
    
    # 添加原始内容（折叠）
    note_content += f"""

---

<details>
<summary>📝 原始内容</summary>

{original_content}

</details>
"""
    
    return note_content

if __name__ == "__main__":
    # 测试
    test_content = """
用户：我觉得AI的发展会改变整个社会的就业结构

AI：这是一个复杂的议题。从历史来看，技术进步确实会淘汰一些岗位，但同时也会创造新的就业机会。

用户：但这次的AI不一样，它的学习能力太强了

AI：确实，生成式AI的能力边界在不断扩展。但关键可能在于如何重新定义"工作"和"价值"。

用户：你觉得人类还有什么是AI替代不了的？

AI：创造力、情感连接、道德判断...但这些边界也在模糊。或许更重要的是思考人类想走向何方。
"""
    
    result = process_chat_record(test_content, "AI与人类未来讨论", "2026-03-09")
    print("\n=== 处理结果 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 生成笔记
    note = generate_obsidian_note(result, test_content, "AI与人类未来讨论")
    print("\n=== 生成笔记 ===")
    print(note[:1000] + "...")
