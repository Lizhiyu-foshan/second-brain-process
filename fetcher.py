#!/usr/bin/env python3
"""
网页内容抓取器 - 使用 kimi_fetch
"""

import subprocess
import sys

def fetch_url(url: str) -> str:
    """使用 kimi_fetch 抓取网页内容"""
    try:
        result = subprocess.run(
            ["python3", "-c", f"""
import sys
sys.path.insert(0, '/usr/lib/node_modules/openclaw')
from tools.kimi_fetch import kimi_fetch
result = kimi_fetch("{url}")
print(result)
"""],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            return f"抓取失败: {result.stderr}\n\n链接：{url}"
    except Exception as e:
        return f"抓取异常: {e}\n\n链接：{url}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 fetcher.py <url>")
        sys.exit(1)
    
    print(fetch_url(sys.argv[1]))
