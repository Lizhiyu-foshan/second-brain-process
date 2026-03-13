#!/usr/bin/env python3
"""
知乎文章爬取 - 使用 Cookie 登录
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

# Cookie 配置（从用户获取）
ZHIHU_COOKIE = "2|1:0|10:1772117976|4:z_c0|92:Mi4xQkgyMkdBQUFBQUFRczlNZTllQndHaVlBQUFCZ0FsVk5qYTJOYWdDc1JjNWxXLW1xYUVZZWcyX0NqUXpDbVdlbmhn|b4fdf1648b91395409e3d7ea9516e516ee38c15f259006575445147b8dd01a65"

def random_delay(min_seconds=1, max_seconds=3):
    """随机延迟"""
    time.sleep(random.uniform(min_seconds, max_seconds))

async def crawl_zhihu_article(url):
    """爬取知乎文章 - 使用 Cookie"""
    async with async_playwright() as p:
        print(f"[INFO] 正在启动浏览器...")
        
        # 启动浏览器
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
            extra_http_headers={
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Referer': 'https://www.zhihu.com/',
            }
        )
        
        # 添加 Cookie（关键步骤）
        await context.add_cookies([
            {
                'name': 'z_c0',
                'value': ZHIHU_COOKIE,
                'domain': '.zhihu.com',
                'path': '/',
            }
        ])
        
        # 移除 webdriver 标识
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        page = await context.new_page()
        
        try:
            print(f"[INFO] 正在加载: {url}")
            response = await page.goto(url, wait_until='networkidle', timeout=30000)
            
            print(f"[INFO] HTTP状态: {response.status}")
            
            if response.status != 200:
                print(f"[ERROR] 加载失败: HTTP {response.status}")
                await page.screenshot(path='/tmp/zhihu_error_cookie.png')
                await browser.close()
                return None
            
            # 等待内容加载
            print("[INFO] 等待内容加载...")
            await asyncio.sleep(3)
            
            # 模拟滚动
            for _ in range(3):
                await page.mouse.wheel(0, random.randint(300, 600))
                random_delay(1, 2)
            
            # 提取标题
            title_selectors = ['h1.Post-Title', 'h1.ContentItem-title', 'h1.QuestionHeader-title', 'h1']
            article_title = "未找到标题"
            for selector in title_selectors:
                try:
                    article_title = await page.locator(selector).first.inner_text(timeout=3000)
                    if article_title and len(article_title.strip()) > 0:
                        print(f"[INFO] 找到标题: {article_title[:50]}...")
                        break
                except:
                    continue
            
            # 提取内容
            content_selectors = ['.Post-RichTextContainer', '.RichContent-inner', '.ContentItem-RichText', 'article']
            article_content = "未找到内容"
            for selector in content_selectors:
                try:
                    article_content = await page.locator(selector).first.inner_text(timeout=3000)
                    if article_content and len(article_content) > 100:
                        print(f"[INFO] 找到内容，长度: {len(article_content)}")
                        break
                except:
                    continue
            
            # 保存截图
            await page.screenshot(path='/tmp/zhihu_success.png', full_page=True)
            print("[INFO] 截图已保存: /tmp/zhihu_success.png")
            
            result = {
                'title': article_title.strip(),
                'content': article_content.strip(),
                'url': url
            }
            
            await browser.close()
            return result
            
        except Exception as e:
            print(f"[ERROR] {e}")
            await page.screenshot(path='/tmp/zhihu_error.png')
            await browser.close()
            return None

if __name__ == '__main__':
    url = "https://zhuanlan.zhihu.com/p/2015499913631385385"
    
    print("=" * 60)
    print("知乎文章爬取 - 使用 Cookie")
    print("=" * 60)
    
    result = asyncio.run(crawl_zhihu_article(url))
    
    if result:
        print(f"\n✅ 爬取成功！")
        print(f"\n标题: {result['title']}")
        print(f"\n内容前500字:\n{result['content'][:500]}...")
        
        # 保存到文件
        output_file = Path('/tmp/zhihu_article.txt')
        output_file.write_text(f"标题: {result['title']}\n\n{result['content']}", encoding='utf-8')
        print(f"\n完整内容已保存: {output_file}")
    else:
        print("\n❌ 爬取失败")
        sys.exit(1)
