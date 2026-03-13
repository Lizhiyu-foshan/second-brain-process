#!/usr/bin/env python3
"""
美术馆展览推送 - 主会话执行版
由主会话调用，可以使用完整的工具链
"""

import json
import re
from datetime import datetime
from tools.web_search import web_search

# 美术馆配置
MUSEUMS = [
    {"name": "和美术馆", "city": "佛山顺德", "query": "和美术馆 当前展览 2026"},
    {"name": "广东美术馆", "city": "广州", "query": "广东美术馆 当前展览 2026"},
    {"name": "另一个美术馆", "city": "广州", "query": "另一个美术馆 当前展览 2026"}
]

def search_exhibitions(museum):
    """搜索单个美术馆的展览"""
    name = museum['name']
    query = museum['query']
    
    print(f"\n🔍 搜索 {name}...")
    
    try:
        results = web_search(query, count=5)
        
        exhibitions = []
        for item in results:
            title = item.get('title', '')
            url = item.get('url', '')
            snippet = item.get('snippet', '')
            
            # 提取展览日期
            date_str = None
            date_match = re.search(r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})[日\-]?\s*[—~至-]?\s*(\d{4})?[年\-/]?(\d{1,2})?[月\-/]?(\d{1,2})?[日\-]?', snippet)
            if date_match:
                if date_match.group(4):
                    date_str = f"{date_match.group(1)}.{date_match.group(2)}.{date_match.group(3)} - {date_match.group(4)}.{date_match.group(5)}.{date_match.group(6)}"
                else:
                    date_str = f"{date_match.group(1)}.{date_match.group(2)}.{date_match.group(3)} 起"
            
            # 提取展览标题
            exh_title = None
            if '：' in title:
                exh_title = title.split('：')[1].strip()
            elif '|' in title:
                parts = title.split('|')
                for part in parts:
                    if '展' in part:
                        exh_title = part.strip()
                        break
            elif '展' in title:
                exh_title = title
            
            if exh_title and len(exh_title) >= 5:
                exhibitions.append({
                    'museum': name,
                    'title': exh_title[:50],
                    'date': date_str or '展期中',
                    'link': url
                })
        
        print(f"  找到 {len(exhibitions)} 个展览")
        return exhibitions[:3]
        
    except Exception as e:
        print(f"  ⚠️ 搜索异常: {e}")
        return []

def format_for_feishu(exhibitions):
    """格式化为飞书消息"""
    lines = [
        "🎨 美术馆周末展览推荐",
        "",
        f"📅 {datetime.now().strftime('%Y年%m月%d日')}",
        ""
    ]
    
    # 按美术馆分组
    by_museum = {}
    for exh in exhibitions:
        museum = exh['museum']
        if museum not in by_museum:
            by_museum[museum] = []
        by_museum[museum].append(exh)
    
    for museum, exhs in by_museum.items():
        lines.append(f"🏛️ **{museum}**")
        for exh in exhs:
            lines.append(f"  • {exh['title']}")
            if exh.get('date'):
                lines.append(f"    📆 {exh['date']}")
            lines.append("")
    
    if not exhibitions:
        lines.append("暂无找到展览信息，建议访问官网查看最新动态。")
        lines.append("")
    
    lines.append("---")
    lines.append("💡 建议提前在官方公众号预约参观")
    
    return "\n".join(lines)

def main():
    """主函数 - 在主会话中执行"""
    print("\n" + "=" * 50)
    print("美术馆展览信息收集并通知")
    print("=" * 50 + "\n")
    
    all_exhibitions = []
    
    for museum in MUSEUMS:
        try:
            exhibitions = search_exhibitions(museum)
            all_exhibitions.extend(exhibitions)
        except Exception as e:
            print(f"  搜索 {museum['name']} 异常: {e}")
    
    print(f"\n总计: {len(all_exhibitions)} 个展览")
    
    message = format_for_feishu(all_exhibitions)
    
    print("\n" + "=" * 50)
    print("消息内容:")
    print("=" * 50)
    print(message)
    
    return message

if __name__ == "__main__":
    main()
