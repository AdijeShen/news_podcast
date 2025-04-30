"""
网页爬虫模块，用于爬取网页内容
"""
import logging
from typing import Optional, Tuple, List

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.browser_manager import BrowserManager

# 设置日志
logger = logging.getLogger(__name__)

# 修复crawl4ai中的资源清理问题
async def patched_async_playwright__crawler_strategy_close(self) -> None:
    """
    关闭浏览器并清理资源
    
    这个补丁解决了Playwright实例清理的问题，静态实例没有被正确重置，导致多次爬取时出现问题。
    
    问题：https://github.com/unclecode/crawl4ai/issues/842
    
    返回：
        None
    """
    await self.browser_manager.close()

    # 重置静态Playwright实例
    BrowserManager._playwright_instance = None

# 应用补丁
AsyncPlaywrightCrawlerStrategy.close = patched_async_playwright__crawler_strategy_close

async def async_search(search_url: str, bypass_paywall: bool = False) -> str:
    """
    异步爬取网页内容并返回Markdown格式
    
    参数:
        search_url: 需要爬取的URL
        bypass_paywall: 是否绕过付费墙
        
    返回:
        str: 网页内容的Markdown格式
    """
    config = CrawlerRunConfig(
        cache_mode=CacheMode.DISABLED, 
        simulate_user=True, 
        override_navigator=True, 
        magic=True  # 自动处理弹窗
    )
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        current_url = search_url
        if bypass_paywall:
            current_url = f"https://archive.ph/newest/{search_url}"

        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(
                    url=current_url,
                    config=config,
                )
            
            if result.markdown and len(result.markdown.strip()) > 10:
                return result.markdown
            else:
                logger.warning(f"爬取{current_url}返回内容为空，尝试重新爬取 ({retry_count + 1}/{max_retries})")
                retry_count += 1
                import asyncio
                await asyncio.sleep(2)  # 等待2秒后重试
        except Exception as e:
            logger.error(f"爬取{current_url}时出错: {e}，尝试重新爬取 ({retry_count + 1}/{max_retries})")
            retry_count += 1
            import asyncio
            await asyncio.sleep(2)  # 等待2秒后重试
    
    # 如果常规尝试都失败，尝试使用bypass_paywall模式
    if not bypass_paywall:
        logger.info(f"常规爬取{search_url}失败，尝试使用bypass_paywall模式")
        try:
            bypass_url = f"https://archive.ph/newest/{search_url}"
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(
                    url=bypass_url,
                    config=config,
                )
            return result.markdown if result.markdown else f"爬取失败: 内容为空"
        except Exception as e:
            logger.error(f"使用bypass_paywall爬取{search_url}时出错: {e}")
    
    return f"爬取失败: 已达到最大重试次数"

async def fetch_news_content(news_urls: List[str]) -> List[Tuple[str, str]]:
    """
    并发获取多个新闻内容，同时保留对应链接
    
    参数:
        news_urls: 新闻URL列表
        
    返回:
        List[Tuple[str, str]]: 内容和URL的元组列表
    """
    results = []
    for url in news_urls:
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                logger.info(f"尝试获取{url}内容 (尝试 {retry_count + 1}/{max_retries})")
                content = await async_search(url.strip())
                if content and not content.startswith("爬取失败"):
                    results.append((content, url.strip()))
                    break
                else:
                    logger.warning(f"获取{url}内容失败，准备重试")
                    retry_count += 1
                    import asyncio
                    await asyncio.sleep(2)  # 等待2秒后重试
            except Exception as e:
                logger.error(f"获取{url}内容时出错: {e}")
                retry_count += 1
                import asyncio
                await asyncio.sleep(2)  # 等待2秒后重试
        
        if retry_count == max_retries:
            logger.error(f"获取{url}内容失败，已达到最大重试次数")
            results.append((f"获取失败: 已达到最大重试次数", url.strip()))
    
    return results 