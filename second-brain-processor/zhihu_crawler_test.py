#!/usr/bin/env python3
"""
知乎文章爬取 - 使用反爬配置
"""

import asyncio
import random
import sys
from pathlib import Path

from playwright.async_api import async_playwright

async def crawl_zhihu_article(url):
    """爬取知乎文章 - 使用反爬配置"""
    async with async_playwright() as p:
        print(f"[INFO] 正在启动浏览器...")
        
        # 启动浏览器（带反爬配置）
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        # 创建上下文
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
            
            if response.status != 200:
                print(f"[ERROR] 加载失败: HTTP {response.status}")
                await browser.close()
                return None
            
            # 等待内容加载
            await asyncio.sleep(3)
            
            # 模拟滚动
            for _ in range(3):
                await page.mouse.wheel(0, random.randint(300, 600))
                await asyncio.sleep(random.uniform(1, 2))
            
            # 提取标题
            try:
                article_title = await page.locator('h1').first.inner_text(timeout=5000)
                print(f"[INFO] 找到标题: {article_title[:50]}...")
            except:
                article_title = "未找到标题"
            
            # 提取内容
            try:
                article_content = await page.locator('.RichContent-inner, .Post-RichTextContainer').first.inner_text(timeout=5000)
                print(f"[INFO] 找到内容，长度: {len(article_content)}")
            except:
                article_content = "未找到内容"
            
            result = {
                'title': article_title.strip(),
                'content': article_content.strip(),
                'url': url
            }
            
            await browser.close()
            return result
            
        except Exception as e:
            print(f"[ERROR] {e}")
            await browser.close()
            return None

if __name__ == '__main__':
    url = "https://zhuanlan.zhihu.com/p/2017188358137357523"
    
    print("=" * 60)
    print("知乎文章爬取 - 反爬配置版")
    print("=" * 60)
    
    result = asyncio.run(crawl_zhihu_article(url))
    
    if result:
        print(f"\n✅ 爬取成功！")
        print(f"\n标题: {result['title']}")
        print(f"\n内容前500字:\n{result['content'][:500]}...")
    else:
        print("\n❌ 爬取失败")
        sys.exit(1)
