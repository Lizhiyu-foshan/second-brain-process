#!/usr/bin/env python3
"""
美术馆展览信息收集并通知 - 修复版 v4.1
简化版：直接执行搜索并发送结果
"""

import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 美术馆配置
MUSEUMS = [
    {"name": "和美术馆", "city": "佛山顺德", "query": "和美术馆 当前展览 2026"},
    {"name": "广东美术馆", "city": "广州", "query": "广东美术馆 当前展览 2026"},
    {"name": "另一个美术馆", "city": "广州", "query": "另一个美术馆 当前展览 2026"}
]

# 日志配置
LOG_FILE = "/tmp/museum_collect.log"

def log(msg):
    """打印并记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def search_exhibitions(museum):
    """搜索单个美术馆的展览 - 使用 kimi_search 工具"""
    name = museum['name']
    query = museum['query']
    
    log(f"\n🔍 搜索 {name}...")
    
    # 使用 web_search 工具（通过 Brave API）
    try:
        from tools.web_search import web_search
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
                if date_match.group(4):  # 有结束日期
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
        
        log(f"  找到 {len(exhibitions)} 个展览")
        return exhibitions[:3]
        
    except Exception as e:
        log(f"  ⚠️ 搜索异常: {e}")
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

def send_to_feishu(message):
    """发送到飞书"""
    try:
        result = subprocess.run(
            ['openclaw', 'message', 'send',
             '--target', 'ou_363105a68ee112f714ed44e12c802051',
             '--message', message],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            log("✅ 消息已发送到飞书")
            return True
        else:
            log(f"❌ 发送失败: {result.stderr[:200]}")
            return False
    except Exception as e:
        log(f"❌ 发送异常: {e}")
        return False

def main():
    log("\n" + "=" * 50)
    log("美术馆展览信息收集并通知")
    log("=" * 50 + "\n")
    
    all_exhibitions = []
    
    for museum in MUSEUMS:
        try:
            exhibitions = search_exhibitions(museum)
            all_exhibitions.extend(exhibitions)
        except Exception as e:
            log(f"  搜索 {museum['name']} 异常: {e}")
    
    log(f"\n总计: {len(all_exhibitions)} 个展览")
    
    message = format_for_feishu(all_exhibitions)
    
    log("\n" + "=" * 50)
    log("消息内容预览:")
    log("=" * 50)
    log(message[:500] + "..." if len(message) > 500 else message)
    
    send_to_feishu(message)
    
    log("\n" + "=" * 50)
    log("任务完成")
    log("=" * 50)

if __name__ == "__main__":
    main()
