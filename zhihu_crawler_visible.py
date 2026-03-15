#!/usr/bin/env python3
"""
知乎文章爬取 - 非无头模式（headless=False）
使用豆包提供的反爬方案
"""

import asyncio
import random
import sys
import time
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("[ERROR] playwright 未安装")
    sys.exit(1)

def random_delay(min_seconds=1, max_seconds=3):
    """随机延迟"""
    time.sleep(random.uniform(min_seconds, max_seconds))

async def crawl_zhihu_article(url):
    """爬取知乎文章 - 非无头模式"""
    async with async_playwright() as p:
        print(f"[INFO] 正在启动浏览器（非无头模式）...")
        
        # 关键：headless=False + 反爬参数
        browser = await p.chromium.launch(
            headless=False,  # 非无头模式！
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--start-maximized',
            ]
        )
        
        # 创建上下文（模拟真实环境）
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            extra_http_headers={
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://www.zhihu.com/',
            }
        )
        
        # 移除 webdriver 标识
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        page = await context.new_page()
        
        try:
            print(f"[INFO] 正在加载: {url}")
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            print(f"[INFO] HTTP状态: {response.status}")
            
            if response.status == 403:
                print("[ERROR] 被拦截 (403)，即使非无头模式也无法访问")
                await browser.close()
                return None
            
            # 等待并滚动
            await asyncio.sleep(3)
            for _ in range(3):
                await page.mouse.wheel(0, random.randint(300, 600))
                random_delay(1, 2)
            
            # 提取标题
            try:
                title = await page.locator('h1').first.inner_text(timeout=5000)
            except:
                title = "未找到标题"
            
            # 提取内容
            try:
                content = await page.locator('.Post-RichTextContainer, .RichContent-inner').first.inner_text(timeout=5000)
            except:
                try:
                    content = await page.locator('article').inner_text()
                except:
                    content = await page.locator('body').inner_text()
                    content = content[:2000]  # 限制长度
            
            # 截图
            await page.screenshot(path='/tmp/zhihu_test.png', full_page=False)
            
            result = {
                'title': title.strip(),
                'content': content.strip()[:1500],
                'url': url
            }
            
            await browser.close()
            return result
            
        except Exception as e:
            print(f"[ERROR] {e}")
            await browser.close()
            return None

if __name__ == '__main__':
    url = "https://zhuanlan.zhihu.com/p/2015499913631385385?share_code=kRZ3H1NMVx9l"
    
    print("=" * 60)
    print("知乎爬取测试 - 非无头模式（headless=False）")
    print("=" * 60)
    
    result = asyncio.run(crawl_zhihu_article(url))
    
    if result:
        print(f"\n标题: {result['title']}")
        print(f"\n内容:\n{result['content'][:500]}...")
    else:
        print("\n爬取失败")
