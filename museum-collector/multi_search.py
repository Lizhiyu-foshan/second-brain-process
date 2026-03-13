#!/usr/bin/env python3
"""
多模型搜索备份工具 v1.1
支持：Kimi Search -> Qwen3.5 Search -> Web Search (Brave)
"""

import json
import os
import subprocess
import sys
from datetime import datetime

# API配置
DASHSCOPE_API_KEY = "sk-sp-68f6997fc9924babb9f6b50c03a5a529"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

def log(msg):
    """打印日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def search_kimi(query, limit=5):
    """方法1: 使用 Kimi Search"""
    script = '''
import sys
sys.path.insert(0, "/root/.openclaw/workspace")
from tools.kimi_search import kimi_search
import json

try:
    results = kimi_search(""" + repr(query) + """, limit=""" + str(limit) + """
    print(json.dumps(results, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"error": str(e)}, ensure_ascii=False))
'''
    
    try:
        result = subprocess.run(
            ['python3', '-c', script],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if 'error' not in data:
                return {'success': True, 'source': 'kimi', 'results': data}
        
        return {'success': False, 'source': 'kimi', 'error': result.stderr}
        
    except Exception as e:
        return {'success': False, 'source': 'kimi', 'error': str(e)}

def search_qwen(query, limit=5):
    """方法2: 使用 Qwen3.5 联网搜索"""
    script = '''
import json
import requests

url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
headers = {
    "Authorization": "Bearer sk-sp-68f6997fc9924babb9f6b50c03a5a529",
    "Content-Type": "application/json"
}

payload = {
    "model": "qwen3.5-plus",
    "messages": [{"role": "user", "content": "搜索: """ + repr(query) + """"}],
    "extra_body": {
        "enable_search": True,
        "search_options": {
            "search_strategy": "turbo",
            "enable_source": True
        }
    }
}

try:
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    data = response.json()
    
    if "choices" in data:
        content = data["choices"][0]["message"]["content"]
        search_info = data.get("search_info", {})
        results = []
        
        for item in search_info.get("search_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": content[:500]
            })
        
        print(json.dumps({"success": True, "results": results}, ensure_ascii=False))
    else:
        print(json.dumps({"success": False, "error": "No results"}, ensure_ascii=False))
        
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
'''
    
    try:
        result = subprocess.run(
            ['python3', '-c', script],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get('success'):
                return {'success': True, 'source': 'qwen', 'results': data['results']}
        
        return {'success': False, 'source': 'qwen', 'error': result.stderr}
        
    except Exception as e:
        return {'success': False, 'source': 'qwen', 'error': str(e)}

def search_web_brave(query, limit=5):
    """方法3: 使用 Web Search (Brave)"""
    script = '''
import sys
sys.path.insert(0, "/root/.openclaw/workspace")
from tools.web_search import web_search
import json

try:
    results = web_search(""" + repr(query) + """, count=""" + str(limit) + """
    print(json.dumps(results, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"error": str(e)}, ensure_ascii=False))
'''
    
    try:
        result = subprocess.run(
            ['python3', '-c', script],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if 'error' not in data:
                return {'success': True, 'source': 'brave', 'results': data}
        
        return {'success': False, 'source': 'brave', 'error': result.stderr}
        
    except Exception as e:
        return {'success': False, 'source': 'brave', 'error': str(e)}

def multi_model_search(query, limit=5):
    """
    多模型搜索，自动切换备份
    顺序: Kimi -> Qwen3.5 -> Brave
    """
    log(f"开始多模型搜索: {query}")
    
    # 尝试1: Kimi Search
    log("  尝试 Kimi Search...")
    result = search_kimi(query, limit)
    if result['success']:
        log(f"  ✓ Kimi Search 成功")
        return result
    else:
        log(f"  ✗ Kimi Search 失败")
    
    # 尝试2: Qwen3.5 Search
    log("  尝试 Qwen3.5 Search...")
    result = search_qwen(query, limit)
    if result['success']:
        log(f"  ✓ Qwen3.5 Search 成功")
        return result
    else:
        log(f"  ✗ Qwen3.5 Search 失败")
    
    # 尝试3: Brave Web Search
    log("  尝试 Brave Web Search...")
    result = search_web_brave(query, limit)
    if result['success']:
        log(f"  ✓ Brave Web Search 成功")
        return result
    else:
        log(f"  ✗ Brave Web Search 失败")
    
    log("  ⚠️ 所有搜索方法均失败")
    return {'success': False, 'source': 'none', 'error': 'All search methods failed'}

def main():
    if len(sys.argv) < 2:
        print("Usage: multi_search.py <query> [limit]")
        sys.exit(1)
    
    query = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    result = multi_model_search(query, limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
