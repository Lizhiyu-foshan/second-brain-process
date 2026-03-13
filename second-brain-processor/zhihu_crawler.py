#!/usr/bin/env python3
"""
知乎文章爬取 - 无 Cookie 版
使用 Playwright + 反反爬技术
"""

import asyncio
import random
import sys
from pathlib import Path

# 检查 playwright 是否安装
try:
    from playwright.async_api import async_playwright
except ImportError:
    print("[ERROR] playwright 未安装")
    print("请先运行: pip install playwright")
    print("然后运行: playwright install chromium")
    sys.exit(1)

def random_delay(min_seconds=1, max_seconds=3):
    """随机延迟"""
    import time
    time.sleep(random.uniform(min_seconds, max_seconds))

async def crawl_zhihu_article(url):
    """爬取知乎文章"""
    async with async_playwright() as p:
        print(f"[INFO] 正在爬取: {url}")
        
        # 启动浏览器（带反爬配置）
        browser = await p.chromium.launch(
            headless=True,  # 使用无头模式
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(110, 120)}.0.0.0 Safari/537.36'
            ]
        )
        
        # 创建上下文
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
            window.chrome = { runtime: {} };
        """)
        
        # 打开页面
        page = await context.new_page()
        
        try:
            print("[INFO] 正在加载页面...")
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            if response.status != 200:
                print(f"[ERROR] 页面加载失败: HTTP {response.status}")
                await browser.close()
                return None
            
            # 等待内容加载
            print("[INFO] 等待内容加载...")
            await asyncio.sleep(3)
            
            # 尝试多种选择器提取标题
            title_selectors = [
                'h1.Post-Title',
                'h1.ContentItem-title',
                'h1.QuestionHeader-title',
                'h1'
            ]
            
            article_title = None
            for selector in title_selectors:
                try:
                    article_title = await page.locator(selector).first.inner_text(timeout=2000)
                    if article_title and article_title.strip():
                        print(f"[INFO] 找到标题 (使用 {selector})")
                        break
                except:
                    continue
            
            if not article_title:
                article_title = "未找到标题"
            
            # 尝试多种选择器提取内容
            content_selectors = [
                '.Post-RichTextContainer',
                '.RichContent-inner',
                '.ContentItem-RichText',
                'article'
            ]
            
            article_content = None
            for selector in content_selectors:
                try:
                    article_content = await page.locator(selector).first.inner_text(timeout=2000)
                    if article_content and len(article_content) > 100:
                        print(f"[INFO] 找到内容 (使用 {selector})")
                        break
                except:
                    continue
            
            if not article_content:
                # 如果都不行，尝试获取 body 文本
                try:
                    article_content = await page.locator('body').inner_text()
                    article_content = article_content[:3000]  # 限制长度
                except:
                    article_content = "未找到内容"
            
            # 获取页面截图（用于调试）
            screenshot_path = '/tmp/zhihu_screenshot.png'
            await page.screenshot(path=screenshot_path, full_page=False)
            print(f"[INFO] 截图已保存: {screenshot_path}")
            
            result = {
                'title': article_title.strip(),
                'content': article_content.strip()[:2000],  # 限制长度
                'url': url
            }
            
            await browser.close()
            return result
            
        except Exception as e:
            print(f"[ERROR] 爬取失败: {e}")
            # 尝试截图看发生了什么
            try:
                await page.screenshot(path='/tmp/zhihu_error.png')
                print("[INFO] 错误截图已保存: /tmp/zhihu_error.png")
            except:
                pass
            await browser.close()
            return None

if __name__ == '__main__':
    # 用户提供的知乎文章链接
    target_url = "https://zhuanlan.zhihu.com/p/2015499913631385385?share_code=kRZ3H1NMVx9l&utm_psn=2015890693776777679"
    
    print("=" * 60)
    print("知乎文章爬取测试（无 Cookie）")
    print("=" * 60)
    
    result = asyncio.run(crawl_zhihu_article(target_url))
    
    if result:
        print("\n" + "=" * 60)
        print(f"标题: {result['title']}")
        print("=" * 60)
        print(f"\n内容预览:\n{result['content'][:500]}...")
    else:
        print("\n爬取失败")
        sys.exit(1)
