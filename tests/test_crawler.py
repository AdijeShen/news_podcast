"""
爬虫模块测试
"""
import os
import pytest
from typing import Optional

# 导入所需模块
import sys
sys.path.insert(0, os.path.abspath('.'))

# 设置为自动异步模式
pytestmark = pytest.mark.asyncio

@pytest.mark.asyncio
async def test_url_crawl():
    """
    测试单个URL的爬取功能
    """
    from src.news_podcast.crawlers.web_crawler import async_search
    
    # 测试URL
    url = "https://www.reuters.com/"
    
    # 执行爬取
    content = await async_search(url)
    
    # 验证结果
    assert content is not None, "爬取内容不应为None"
    assert len(content) > 0, "爬取内容长度应大于0"    
    # 输出到文件(可选)
    output_file = "test_output.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"测试爬取完成，内容长度: {len(content)} 字符")
    print(f"结果已保存到: {output_file}")


@pytest.mark.asyncio
async def test_url_crawl_with_params(url: str = "https://www.bbc.com/news", output_file: str = "bbc_output.md"):
    """
    测试带参数的URL爬取功能
    
    参数:
        url: 要爬取的URL
        output_file: 输出文件名
    """
    from src.news_podcast.crawlers.web_crawler import async_search
    
    print(f"开始测试爬取URL: {url}")
    content = await async_search(url)
    
    # 验证结果
    assert content is not None, "爬取内容不应为None"
    assert len(content) > 0, "爬取内容长度应大于0"
    
    # 保存结果
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"测试完成，结果已保存到{output_file}")
    print(f"内容长度: {len(content)} 字符") 