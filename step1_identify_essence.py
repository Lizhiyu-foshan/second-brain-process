#!/usr/bin/env python3
"""
step1_identify_essence.py - v3.1 使用阿里百炼API
主题精华识别 - 真正调用阿里百炼qwen3.5-plus
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Any

# 加载环境变量
def _load_env():
    """手动加载 .env 文件"""
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key, value)

_load_env()

# 阿里百炼配置
ALICLOUD_BASE_URL = os.environ.get("ALICLOUD_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")
ALICLOUD_API_KEY = os.environ.get("ALICLOUD_API_KEY", "")
ALICLOUD_MODEL = os.environ.get("ALICLOUD_MODEL_CHAT_FAST", "qwen3.5-plus")


def extract_conversation_text(content: str) -> str:
    """从markdown文件中提取对话文本，过滤frontmatter和噪音"""
    # 移除frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2].strip()
    
    # 过滤噪音行
    skip_patterns = [
        r'^Read HEARTBEAT\.md',
        r'^HEARTBEAT_OK',
        r'^Current time:',
        r'^Conversation info \(untrusted',
        r'^```json',
        r'^```\s*$',
        r'^System: \[.*\] .*cron.*',
    ]
    
    filtered_lines = []
    for line in content.split('\n'):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        should_skip = any(re.match(pattern, line_stripped, re.I) for pattern in skip_patterns)
        if not should_skip:
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)


def build_analysis_prompt(conversation_text: str) -> str:
    """构建AI分析Prompt"""
    max_len = 8000
    if len(conversation_text) > max_len:
        conversation_text = conversation_text[:max_len] + "\n...[内容过长，已截断]..."
    
    return f"""你是一位深度对话分析专家。请分析以下对话内容，提取有价值的主题讨论精华。

## 对话内容
```
{conversation_text}
```

## 分析要求

### 识别深度讨论主题
关注：哲学思考、社会学洞察、系统论、技术冲击、重要决策、新发现、方法论总结

### 输出格式（严格JSON）
```json
{{
  "topics": [
    {{
      "name": "主题名称（10字以内）",
      "confidence": "high|medium|low",
      "source_type": "纯对话|文章讨论|混合",
      "key_takeaway": "一句话核心观点（30字以内）",
      "detailed_points": ["详细观点1", "详细观点2"],
      "reflection": "思考延伸",
      "connections": ["关联1", "关联2"],
      "fragments": ["原文片段1", "原文片段2"]
    }}
  ],
  "summary": "整体分析总结"
}}
```

### 质量要求
- 如果没有深度讨论，返回空topics
- 不要凑数生成浅层主题
- key_takeaway必须是原创提炼，不是原文复制

只返回JSON，不要其他文字。"""


def call_ai_via_alicloud(prompt: str) -> Dict[str, Any]:
    """
    调用阿里百炼API进行深度分析
    使用qwen3.5-plus模型
    """
    print(f"[AI_CALL] 调用阿里百炼API...")
    print(f"[AI_CALL] 模型: {ALICLOUD_MODEL}")
    print(f"[AI_CALL] API地址: {ALICLOUD_BASE_URL}")
    
    if not ALICLOUD_API_KEY:
        print("[ERROR] 未配置ALICLOUD_API_KEY")
        return {"topics": [], "summary": "错误：未配置阿里百炼API key"}
    
    url = f"{ALICLOUD_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ALICLOUD_API_KEY}"
    }
    
    data = {
        "model": ALICLOUD_MODEL,
        "messages": [
            {"role": "system", "content": "你是一个深度对话分析专家。请严格按照JSON格式输出分析结果。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 4000
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        print(f"[AI_CALL] 发送请求...")
        
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            print(f"[AI_CALL] 收到响应")
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                
                # 提取JSON部分
                try:
                    output = json.loads(content)
                    
                    # 记录调用日志
                    log_entry = {
                        "timestamp": str(os.times().system),
                        "model": ALICLOUD_MODEL,
                        "topics_count": len(output.get('topics', [])),
                        "prompt_tokens": result.get('usage', {}).get('prompt_tokens', 0),
                        "completion_tokens": result.get('usage', {}).get('completion_tokens', 0)
                    }
                    log_file = Path("/root/.openclaw/workspace/.learnings/ai_calls.jsonl")
                    with open(log_file, 'a') as f:
                        f.write(json.dumps(log_entry) + '\n')
                    
                    print(f"[AI_CALL] ✅ 成功，识别到{len(output.get('topics', []))}个主题")
                    return output
                    
                except json.JSONDecodeError:
                    # 尝试从markdown代码块中提取
                    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(1))
                    else:
                        # 尝试找最外层的大括号
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            return json.loads(json_match.group(0))
                        else:
                            raise ValueError(f"无法从响应中提取JSON: {content[:200]}")
            else:
                print(f"[ERROR] API返回异常格式: {result}")
                return {"topics": [], "summary": "API返回异常格式"}
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')[:500]
        print(f"[ERROR] API调用失败: HTTP {e.code} - {error_body}")
        return {"topics": [], "summary": f"API错误: HTTP {e.code}"}
    except Exception as e:
        print(f"[ERROR] AI分析失败: {e}")
        return {"topics": [], "summary": f"分析失败: {str(e)}"}


def identify_essence(conversation_file: Path) -> Dict[str, Any]:
    """识别对话中的主题精华（主入口）"""
    print(f"[Step1] 开始主题精华识别: {conversation_file.name}")
    
    with open(conversation_file, 'r', encoding='utf-8') as f:
        raw_content = f.read()
    
    conversation_text = extract_conversation_text(raw_content)
    
    if len(conversation_text) < 200:
        print("[Step1] 对话内容过短，跳过分析")
        return {"topics": [], "summary": "对话内容不足"}
    
    print(f"[Step1] 提取有效文本: {len(conversation_text)} 字符")
    
    prompt = build_analysis_prompt(conversation_text)
    result = call_ai_via_alicloud(prompt)
    
    print(f"[Step1] 识别完成: {len(result.get('topics', []))} 个主题")
    
    for topic in result.get("topics", []):
        print(f"  - {topic.get('name')}: {topic.get('key_takeaway', '')[:50]}...")
    
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="对话文件路径")
    args = parser.parse_args()
    
    result = identify_essence(Path(args.file))
    print(json.dumps(result, ensure_ascii=False, indent=2))
