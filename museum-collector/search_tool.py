#!/usr/bin/env python3
"""
搜索工具 - 供定时任务调用
"""
import sys
import json

# 添加路径
sys.path.insert(0, '/root/.openclaw/workspace')

def search(query, limit=5):
    """执行搜索"""
    try:
        # 尝试使用 kimi_search 工具
        try:
            from kimi_search import kimi_search
            results = kimi_search(query, limit=limit)
            print(json.dumps({"success": True, "results": results}))
            return
        except:
            pass
        
        # 备用：直接调用 web_search
        import subprocess
        result = subprocess.run(
            ['python3', '-c', f'''
import json
# 使用 kimi_search 工具
query = "{query}"
limit = {limit}

# 直接执行搜索
from tools.kimi_search import kimi_search
results = kimi_search(query, limit=limit)
print(json.dumps(results))
'''],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            print(json.dumps({"success": True, "results": result.stdout}))
        else:
            print(json.dumps({"success": False, "error": result.stderr}))
            
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: search_tool.py <query> [limit]", file=sys.stderr)
        sys.exit(1)
    
    query = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    search(query, limit)
