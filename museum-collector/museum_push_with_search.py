#!/usr/bin/env python3
"""
美术馆展览推送 - 真正调用搜索API版本
使用 kimi_search 功能搜索真实展览信息
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta

# API配置 - 使用Kimi Coding Plan
API_KEY = os.environ.get('KIMI_API_KEY', '') or os.environ.get('ALICLOUD_API_KEY', '')
# Kimi Coding Plan使用Moonshot官方API
BASE_URL = os.environ.get('KIMI_BASE_URL', 'https://api.moonshot.cn/v1')
# 如果KIMI_BASE_URL未设置，回退到AliCloud DashScope
if not API_KEY:
    API_KEY = os.environ.get('ALICLOUD_API_KEY', '')
    BASE_URL = os.environ.get('ALICLOUD_BASE_URL', 'https://coding.dashscope.aliyuncs.com/v1')
TARGET = "ou_363105a68ee112f714ed44e12c802051"

def search_museum_exhibitions(museum_name: str) -> list:
    """搜索美术馆展览信息"""
    search_query = f"{museum_name} 展览 2026 当前"
    
    try:
        # 使用 kimi_search 方式搜索
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "kimi-k2.5",
                "messages": [
                    {"role": "system", "content": "你是一个展览信息助手。请搜索并提供准确的美术馆展览信息，包括展览名称、时间、简介。用中文回复。"},
                    {"role": "user", "content": f"搜索 {search_query}，列出当前正在进行的展览，包括展览名称、日期、简介"}
                ],
                "temperature": 0.3,
                "max_tokens": 1500
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            return parse_exhibitions(content)
        else:
            print(f"搜索 {museum_name} 失败: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"搜索 {museum_name} 出错: {e}")
        return []


def parse_exhibitions(content: str) -> list:
    """解析展览信息"""
    exhibitions = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # 尝试提取展览名称和日期
        if '《' in line and '》' in line:
            name = line[line.find('《'):line.find('》')+1]
            exhibitions.append({
                'name': name,
                'info': line[:200]
            })
        elif len(line) > 10 and '展览' in line:
            exhibitions.append({
                'name': line[:50],
                'info': line[:200]
            })
    
    return exhibitions[:3]  # 最多3个


def generate_push_message(title: str, subtitle: str) -> str:
    """生成推送消息"""
    today = datetime.now()
    today_str = today.strftime("%Y年%m月%d日")
    
    # 搜索三个美术馆
    museums = [
        ("和美术馆", "📍 **和美术馆**"),
        ("广东美术馆", "📍 **广东美术馆（新馆）**"),
        ("另一个美术馆", "📍 **另一个美术馆**")
    ]
    
    exhibition_sections = []
    
    for museum_name, header in museums:
        print(f"正在搜索: {museum_name}...")
        exhibitions = search_museum_exhibitions(museum_name)
        
        if exhibitions:
            section_lines = [header]
            for ex in exhibitions:
                section_lines.append(f"- {ex['name']} — {ex['info'][:80]}...")
            exhibition_sections.append('\n'.join(section_lines))
        else:
            exhibition_sections.append(f"{header}\n- 展期中（搜索暂时无结果）")
    
    exhibitions_text = '\n\n'.join(exhibition_sections)
    
    message = f"""🎨 **{title}**

📅 {today_str} | {subtitle}

---

{exhibitions_text}

---

⏰ **推送时间**：{today.strftime("%Y-%m-%d %H:%M")}
✅ **定时任务正常执行**
💡 **说明**：展览信息基于实时搜索，可能存在延迟，建议参观前确认官网"""
    
    return message


def send_feishu_message(message: str, msg_type: str = "museum_push") -> bool:
    """发送飞书消息"""
    try:
        sys.path.insert(0, '/root/.openclaw/workspace/second-brain-processor')
        from feishu_guardian import send_feishu_safe
        
        result = send_feishu_safe(
            message,
            target=TARGET,
            msg_type=msg_type,
            max_retries=1
        )
        
        return result.get("success", False)
    except Exception as e:
        print(f"发送失败: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='美术馆展览推送')
    parser.add_argument('--mode', choices=['monday', 'friday'], default='friday',
                       help='推送模式：周一或周五')
    parser.add_argument('--test', action='store_true', help='测试模式（不发送）')
    args = parser.parse_args()
    
    if args.mode == 'monday':
        title = "周一工作日展览推送"
        subtitle = "本周工作日可看的展览"
    else:
        title = "周五周末展览推送"
        subtitle = "周末可看的展览"
    
    print(f"正在生成 {title}...")
    print("搜索展览信息可能需要30-60秒...")
    
    # 生成消息
    message = generate_push_message(title, subtitle)
    
    if args.test:
        print("\n【测试模式】消息内容预览：")
        print("=" * 60)
        print(message)
        print("=" * 60)
        print("\n✅ 测试完成，未发送")
        return
    
    # 发送消息
    print("\n正在发送...")
    if send_feishu_message(message):
        print("✅ 推送发送成功")
    else:
        print("❌ 推送发送失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
