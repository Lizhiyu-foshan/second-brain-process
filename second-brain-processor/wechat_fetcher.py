#!/usr/bin/env python3
"""
微信公众号文章抓取器 - 增强版 v2.0
支持多种策略，解决长文章获取失败问题
"""

import json
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import hashlib

@dataclass
class FetchResult:
    """抓取结果"""
    success: bool
    title: str
    content: str
    source: str  # 使用的抓取策略
    error: Optional[str] = None
    metadata: Optional[Dict] = None

class WeChatArticleFetcher:
    """
    微信公众号文章抓取器
    
    策略优先级：
    1. kimi_fetch API (最快，但可能受限于内容长度)
    2. web_fetch 工具 (备用)
    3. 浏览器模拟 (处理动态加载，最可靠但较慢)
    4. 降级方案 (返回待手动处理标记)
    """
    
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.cache_dir = Path("/tmp/wechat_fetch_cache")
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_cache_key(self, url: str) -> str:
        """生成缓存键"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cached(self, url: str) -> Optional[FetchResult]:
        """获取缓存内容"""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            # 检查缓存是否过期（24小时）
            mtime = cache_file.stat().st_mtime
            if time.time() - mtime < 86400:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return FetchResult(**data)
                except:
                    pass
        return None
    
    def _save_cache(self, url: str, result: FetchResult):
        """保存缓存"""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'success': result.success,
                    'title': result.title,
                    'content': result.content,
                    'source': result.source,
                    'error': result.error,
                    'metadata': result.metadata
                }, f, ensure_ascii=False)
        except Exception as e:
            print(f"缓存保存失败: {e}")
    
    def _clean_wechat_content(self, html: str) -> str:
        """
        清理微信公众号文章内容
        
        微信文章特点：
        - 内容在 #js_content 或 .rich_media_content 中
        - 有大量微信特有的标签和样式
        - 图片使用 data-src 延迟加载
        """
        from html import unescape
        
        # 解码 HTML 实体
        html = unescape(html)
        
        # 移除 script 和 style
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # 提取标题
        title = "未知标题"
        title_match = re.search(r'<h1[^>]*class="rich_media_title[^"]*"[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
        if title_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        
        # 提取正文 - 尝试多种选择器
        content = ""
        
        # 方法1: js_content (新版微信文章)
        content_match = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*<script', html, re.DOTALL | re.IGNORECASE)
        if content_match:
            content = content_match.group(1)
        
        # 方法2: rich_media_content (旧版)
        if not content:
            content_match = re.search(r'<div[^>]*class="rich_media_content[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*<script', html, re.DOTALL | re.IGNORECASE)
            if content_match:
                content = content_match.group(1)
        
        # 方法3: 通用内容区域
        if not content:
            # 找最多文字的区域
            divs = re.findall(r'<div[^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
            if divs:
                content = max(divs, key=lambda x: len(re.sub(r'<[^>]+>', '', x)))
        
        # 处理图片 - 将 data-src 替换为 src
        content = re.sub(r'<img[^>]*data-src="([^"]*)"[^>]*>', r'![图片](\1)', content, flags=re.IGNORECASE)
        content = re.sub(r'<img[^>]*src="([^"]*)"[^>]*>', r'![图片](\1)', content, flags=re.IGNORECASE)
        
        # 移除剩余 HTML 标签
        content = re.sub(r'<[^>]+>', ' ', content)
        
        # 合并空白
        content = re.sub(r'\s+', ' ', content)
        content = content.replace('&nbsp;', ' ')
        
        # 清理行
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        content = '\n'.join(lines)
        
        return title, content
    
    def strategy_1_kimi_fetch(self, url: str) -> FetchResult:
        """
        策略1: 使用 kimi_fetch 工具
        优点：快速，集成度高
        缺点：可能受限于内容长度，对动态内容支持有限
        """
        try:
            import requests
            
            response = requests.post(
                "https://kimi.moonshot.cn/api/web/fetch",
                json={"url": url, "max_chars": 15000},
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("text", "")
                
                if len(content) > 200:
                    # 提取标题（通常在开头）
                    lines = content.split('\n')
                    title = lines[0].strip() if lines else "未知标题"
                    
                    # 如果是微信文章，可能需要额外处理
                    if "mp.weixin.qq.com" in url:
                        title, content = self._clean_wechat_content(content)
                    
                    return FetchResult(
                        success=True,
                        title=title,
                        content=content,
                        source="kimi_fetch"
                    )
            
            return FetchResult(
                success=False,
                title="",
                content="",
                source="kimi_fetch",
                error=f"API返回状态码: {response.status_code}"
            )
            
        except Exception as e:
            return FetchResult(
                success=False,
                title="",
                content="",
                source="kimi_fetch",
                error=str(e)
            )
    
    def strategy_2_web_fetch(self, url: str) -> FetchResult:
        """
        策略2: 使用 OpenClaw web_fetch 工具
        优点：可能有不同的抓取逻辑
        缺点：同样可能受限于反爬
        """
        try:
            result = subprocess.run(
                ['openclaw', 'tools', 'web_fetch', url, '--max-chars', '15000'],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    content = data.get("text", "")
                    
                    if len(content) > 200:
                        title = data.get("title", "未知标题")
                        
                        if "mp.weixin.qq.com" in url:
                            title, content = self._clean_wechat_content(content)
                        
                        return FetchResult(
                            success=True,
                            title=title,
                            content=content,
                            source="web_fetch"
                        )
                except json.JSONDecodeError:
                    # 如果不是 JSON，直接使用文本
                    if len(result.stdout) > 200:
                        return FetchResult(
                            success=True,
                            title="未知标题",
                            content=result.stdout,
                            source="web_fetch"
                        )
            
            return FetchResult(
                success=False,
                title="",
                content="",
                source="web_fetch",
                error=result.stderr or "抓取失败"
            )
            
        except Exception as e:
            return FetchResult(
                success=False,
                title="",
                content="",
                source="web_fetch",
                error=str(e)
            )
    
    def strategy_3_browser_fetch(self, url: str) -> FetchResult:
        """
        策略3: 使用浏览器模拟（Playwright/Selenium）
        优点：可以执行 JS，处理动态加载内容
        缺点：较慢，需要浏览器环境
        """
        try:
            # 使用 Playwright 脚本
            script = '''
from playwright.sync_api import sync_playwright
import json

url = ''' + repr(url) + '''

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 设置 User-Agent
    page.set_extra_http_headers({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        
        # 等待内容加载
        page.wait_for_selector("#js_content, .rich_media_content", timeout=10000)
        
        # 获取标题
        title = page.title()
        
        # 获取正文内容
        content_element = page.query_selector("#js_content") or page.query_selector(".rich_media_content")
        content = content_element.inner_text() if content_element else page.content()
        
        # 获取完整 HTML 用于清理
        html = page.content()
        
        browser.close()
        
        print(json.dumps({
            "success": True,
            "title": title,
            "content": content,
            "html": html
        }, ensure_ascii=False))
        
    except Exception as e:
        browser.close()
        print(json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False))
'''
            
            result = subprocess.run(
                ['python3', '-c', script],
                capture_output=True,
                text=True,
                timeout=self.timeout + 30  # 浏览器需要更多时间
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get("success"):
                    title = data.get("title", "未知标题")
                    content = data.get("content", "")
                    html = data.get("html", "")
                    
                    # 清理微信内容
                    if "mp.weixin.qq.com" in url and html:
                        title, content = self._clean_wechat_content(html)
                    
                    if len(content) > 200:
                        return FetchResult(
                            success=True,
                            title=title,
                            content=content,
                            source="browser_fetch"
                        )
            
            return FetchResult(
                success=False,
                title="",
                content="",
                source="browser_fetch",
                error="浏览器抓取失败"
            )
            
        except Exception as e:
            return FetchResult(
                success=False,
                title="",
                content="",
                source="browser_fetch",
                error=str(e)
            )
    
    def strategy_4_fallback(self, url: str, errors: List[str]) -> FetchResult:
        """
        策略4: 降级方案
        当所有抓取策略都失败时，返回待手动处理的信息
        """
        return FetchResult(
            success=True,  # 标记为成功，但内容是提示信息
            title="待手动处理",
            content=f"""## 文章内容待抓取

链接：{url}

**自动抓取失败，原因如下：**
{chr(10).join(['- ' + e for e in errors])}

**建议处理方式：**
1. 点击链接在浏览器中打开文章
2. 复制文章内容
3. 粘贴到 Obsidian 中整理

---
*抓取时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}*
""",
            source="fallback",
            metadata={"errors": errors, "url": url}
        )
    
    def fetch(self, url: str, use_cache: bool = True) -> FetchResult:
        """
        主抓取方法，自动选择最佳策略
        优先级: Playwright (browser_fetch) -> kimi_fetch -> web_fetch -> fallback
        
        Args:
            url: 文章链接
            use_cache: 是否使用缓存
        
        Returns:
            FetchResult: 抓取结果
        """
        print(f"开始抓取: {url}")
        
        # 检查缓存
        if use_cache:
            cached = self._get_cached(url)
            if cached:
                print(f"  ✓ 使用缓存")
                return cached
        
        errors = []
        
        # 策略1: browser_fetch (Playwright) - 优先使用，最完整
        print("  尝试策略1: browser_fetch (Playwright)...")
        result = self.strategy_3_browser_fetch(url)
        if result.success and len(result.content) > 500:
            print(f"  ✓ browser_fetch 成功，内容长度: {len(result.content)}")
            self._save_cache(url, result)
            return result
        else:
            errors.append(f"browser_fetch: {result.error or '内容过短'}")
            print(f"  ✗ browser_fetch 失败")
        
        # 策略2: kimi_fetch - 快速备用
        print("  尝试策略2: kimi_fetch...")
        result = self.strategy_1_kimi_fetch(url)
        if result.success and len(result.content) > 500:
            print(f"  ✓ kimi_fetch 成功，内容长度: {len(result.content)}")
            self._save_cache(url, result)
            return result
        else:
            errors.append(f"kimi_fetch: {result.error or '内容过短'}")
            print(f"  ✗ kimi_fetch 失败")
        
        # 策略3: web_fetch - 最后备用
        print("  尝试策略3: web_fetch...")
        result = self.strategy_2_web_fetch(url)
        if result.success and len(result.content) > 500:
            print(f"  ✓ web_fetch 成功，内容长度: {len(result.content)}")
            self._save_cache(url, result)
            return result
        else:
            errors.append(f"web_fetch: {result.error or '内容过短'}")
            print(f"  ✗ web_fetch 失败")
        
        # 策略4: 降级方案
        print("  所有策略失败，使用降级方案...")
        result = self.strategy_4_fallback(url, errors)
        self._save_cache(url, result)
        return result


# 便捷函数
def fetch_wechat_article(url: str) -> str:
    """
    便捷函数：抓取微信文章内容
    
    Args:
        url: 微信文章链接
    
    Returns:
        str: 文章内容或提示信息
    """
    fetcher = WeChatArticleFetcher()
    result = fetcher.fetch(url)
    
    if result.success:
        if result.source == "fallback":
            return result.content
        else:
            return f"{result.title}\n\n{result.content}"
    else:
        return f"抓取失败: {result.error}"


if __name__ == "__main__":
    # 测试
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        result = WeChatArticleFetcher().fetch(url)
        
        print("\n" + "="*50)
        print(f"抓取结果")
        print("="*50)
        print(f"成功: {result.success}")
        print(f"策略: {result.source}")
        print(f"标题: {result.title}")
        print(f"内容长度: {len(result.content)}")
        if result.error:
            print(f"错误: {result.error}")
        print("\n内容预览:")
        print(result.content[:500] + "..." if len(result.content) > 500 else result.content)
    else:
        print("Usage: wechat_fetcher.py <url>")
