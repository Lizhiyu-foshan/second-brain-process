#!/usr/bin/env python3
"""
美术馆展览推送 - 智能过滤版
根据当前日期过滤过期展览，并提醒临近结束的展览
"""

import re
from datetime import datetime, timedelta
from tools.web_search import web_search

# 美术馆配置
MUSEUMS = [
    {"name": "和美术馆", "city": "佛山顺德", "query": "和美术馆 展览 2026"},
    {"name": "广东美术馆", "city": "广州", "query": "广东美术馆 展览 2026"},
    {"name": "另一个美术馆", "city": "广州", "query": "另一个美术馆 展览 2026"}
]

def parse_date(date_str):
    """解析日期字符串"""
    if not date_str:
        return None
    
    # 模式1: 2026.3.15 - 2026.6.20
    match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})\s*-\s*(\d{4})\.(\d{1,2})\.(\d{1,2})', date_str)
    if match:
        try:
            start = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            end = datetime(int(match.group(4)), int(match.group(5)), int(match.group(6)))
            return (start, end)
        except:
            pass
    
    # 模式2: 2026年3月15日 - 2026年6月20日
    match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*[—~至-]\s*(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
    if match:
        try:
            start = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            end = datetime(int(match.group(4)), int(match.group(5)), int(match.group(6)))
            return (start, end)
        except:
            pass
    
    # 模式3: 2026.3.15 起
    match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})\s*起', date_str)
    if match:
        try:
            start = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            # 长期展览，假设结束时间为一年后
            end = start + timedelta(days=365)
            return (start, end)
        except:
            pass
    
    return None

def is_exhibition_valid(exh, today=None):
    """检查展览是否有效（未结束）"""
    if today is None:
        today = datetime.now()
    
    date_range = parse_date(exh.get('date', ''))
    if not date_range:
        # 无法解析日期，默认显示
        return True, None
    
    start, end = date_range
    
    # 展览已结束
    if end < today:
        return False, None
    
    # 展览未开始
    if start > today:
        return False, None
    
    # 检查是否临近结束（7天内）
    days_to_end = (end - today).days
    if days_to_end <= 7:
        return True, days_to_end
    
    return True, None

def search_exhibitions(museum):
    """搜索单个美术馆的展览"""
    name = museum['name']
    query = museum['query']
    
    print(f"\n🔍 搜索 {name}...")
    
    try:
        results = web_search(query, count=10)
        
        exhibitions = []
        today = datetime.now()
        
        for item in results:
            title = item.get('title', '')
            url = item.get('url', '')
            snippet = item.get('snippet', '')
            
            # 提取展览日期
            date_str = None
            # 展期：2026年1月16日–2026年3月29日
            date_match = re.search(r'展期[:：]\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s*[—~至-]\s*(\d{4})年(\d{1,2})月(\d{1,2})日', snippet)
            if date_match:
                date_str = f"{date_match.group(1)}.{date_match.group(2)}.{date_match.group(3)} - {date_match.group(4)}.{date_match.group(5)}.{date_match.group(6)}"
            
            # 模式2: 2026.1.16-2026.3.29
            if not date_str:
                date_match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})\s*[—~至-]\s*(\d{4})\.(\d{1,2})\.(\d{1,2})', snippet)
                if date_match:
                    date_str = f"{date_match.group(1)}.{date_match.group(2)}.{date_match.group(3)} - {date_match.group(4)}.{date_match.group(5)}.{date_match.group(6)}"
            
            # 模式3: 2026年1月16日起
            if not date_str:
                date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日起', snippet)
                if date_match:
                    date_str = f"{date_match.group(1)}.{date_match.group(2)}.{date_match.group(3)} 起"
            
            # 提取展览标题
            exh_title = None
            if '：' in title:
                parts = title.split('：')
                if len(parts) > 1:
                    exh_title = parts[1].strip()
            elif '|' in title:
                parts = title.split('|')
                for part in parts:
                    if '展' in part or '展览' in part:
                        exh_title = part.strip()
                        break
            elif '展' in title:
                exh_title = title
            
            if exh_title:
                exh_title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9·\-\s]', '', exh_title).strip()[:50]
                
                exhibition = {
                    'museum': name,
                    'title': exh_title,
                    'date': date_str or '展期中',
                    'link': url
                }
                
                # 检查是否有效
                is_valid, days_remaining = is_exhibition_valid(exhibition, today)
                
                if is_valid:
                    exhibition['days_remaining'] = days_remaining
                    exhibitions.append(exhibition)
        
        print(f"  找到 {len(exhibitions)} 个有效展览")
        return exhibitions[:5]
        
    except Exception as e:
        print(f"  ⚠️ 搜索异常: {e}")
        return []

def format_for_feishu(exhibitions, is_weekend=False):
    """格式化为飞书消息"""
    today = datetime.now()
    weekday = today.weekday()
    
    if is_weekend or weekday >= 5:  # 周五、周六、周日
        title = "🎨 周末展览推荐"
        subtitle = "周末可看的展览"
    else:
        title = "🎨 本周展览推荐"
        subtitle = "工作日可看的展览"
    
    lines = [
        title,
        "",
        f"📅 {today.strftime('%Y年%m月%d日')} | {subtitle}",
        ""
    ]
    
    # 分离即将结束的展览
    ending_soon = []
    normal = []
    
    for exh in exhibitions:
        if exh.get('days_remaining') is not None:
            ending_soon.append(exh)
        else:
            normal.append(exh)
    
    # 先显示即将结束的
    if ending_soon:
        lines.append("⏰ **即将结束（抓紧去看！）**")
        lines.append("")
        
        for exh in ending_soon:
            lines.append(f"🏛️ {exh['museum']}")
            lines.append(f"  📌 {exh['title']}")
            lines.append(f"  📆 {exh['date']}")
            lines.append(f"  ⚠️ 还剩 **{exh['days_remaining']}** 天")
            if exh.get('link'):
                lines.append(f"  🔗 [查看详情]({exh['link']})")
            lines.append("")
    
    # 显示正常展览
    if normal:
        if ending_soon:
            lines.append("---")
            lines.append("")
        
        # 按美术馆分组
        by_museum = {}
        for exh in normal:
            museum = exh['museum']
            if museum not in by_museum:
                by_museum[museum] = []
            by_museum[museum].append(exh)
        
        for museum, exhs in by_museum.items():
            lines.append(f"🏛️ **{museum}**")
            for exh in exhs:
                lines.append(f"  • {exh['title']}")
                lines.append(f"    📆 {exh['date']}")
            lines.append("")
    
    if not exhibitions:
        lines.append("暂无找到有效展览信息，建议访问官网查看最新动态。")
        lines.append("")
    
    lines.append("---")
    lines.append("💡 建议提前在官方公众号预约参观")
    
    return "\n".join(lines)

def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("美术馆展览信息收集（智能过滤版）")
    print("=" * 50 + "\n")
    
    today = datetime.now()
    is_weekend = today.weekday() >= 5  # 5=周六, 6=周日
    
    all_exhibitions = []
    
    for museum in MUSEUMS:
        try:
            exhibitions = search_exhibitions(museum)
            all_exhibitions.extend(exhibitions)
        except Exception as e:
            print(f"  搜索 {museum['name']} 异常: {e}")
    
    print(f"\n总计有效展览: {len(all_exhibitions)} 个")
    
    message = format_for_feishu(all_exhibitions, is_weekend)
    
    print("\n" + "=" * 50)
    print("消息内容:")
    print("=" * 50)
    print(message[:800] + "..." if len(message) > 800 else message)
    
    return message

if __name__ == "__main__":
    main()
