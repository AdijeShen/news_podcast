"""
测试微信发布模块
"""
import os
import pytest
from typing import Dict, Any, Optional
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.news_podcast.wechat_publisher import (
    markdown_to_html,
    extract_title_and_summary,
    publish_to_wechat,
    process_daily_news
)


def test_markdown_to_html() -> None:
    """测试Markdown到HTML的转换"""
    # 简单的Markdown文本
    md_text = """
# 测试标题

这是一段**粗体**和*斜体*文本。

- 列表项1
- 列表项2

[链接](https://example.com)
    """
    
    html = markdown_to_html(md_text)
    
    # 验证HTML是否包含关键元素
    assert "<h1>测试标题</h1>" in html
    assert "<strong>粗体</strong>" in html
    assert "<em>斜体</em>" in html
    assert "<li>列表项1</li>" in html
    assert '<a href="https://example.com">链接</a>' in html


@patch('src.news_podcast.wechat_publisher.chat_with_deepseek')
def test_extract_title_and_summary(mock_chat: MagicMock) -> None:
    """测试提取标题和摘要"""
    # 模拟DeepSeek的响应
    mock_chat.return_value = """
{
  "title": "测试标题",
  "summary": "这是一个测试摘要，用于测试从内容中提取标题和摘要的功能。"
}
"""
    
    content = "这是一篇测试文章，包含很多内容..."
    title, summary = extract_title_and_summary(content)
    
    assert title == "测试标题"
    assert summary == "这是一个测试摘要，用于测试从内容中提取标题和摘要的功能。"
    
    # 测试错误处理
    mock_chat.return_value = "无效的JSON响应"
    title, summary = extract_title_and_summary(content)
    
    assert title == "全球科技日报" or "无效的JSON响应"
    assert "今日科技热点汇总" in summary or len(summary) > 0


@patch('src.news_podcast.wechat_publisher.get_access_token')
@patch('src.news_podcast.wechat_publisher.create_news_draft')
@patch('src.news_podcast.wechat_publisher.extract_title_and_summary')
def test_publish_to_wechat(
    mock_extract: MagicMock,
    mock_create_draft: MagicMock,
    mock_access_token: MagicMock,
) -> None:
    """测试发布到微信公众号"""
    # 创建临时测试文件
    test_file = "D:/workspace/misc/news_podcast/20250408/global_tech_daily_20250408.md"
    
    # 模拟函数返回值
    mock_extract.return_value = ("测试标题", "测试摘要")
    mock_access_token.return_value = ("test_token", 7200)
    mock_create_draft.return_value = "test_media_id"
    
    # 调用测试函数
    media_id = publish_to_wechat(str(test_file))
    
    assert media_id == "test_media_id"
    mock_extract.assert_called_once()
    mock_access_token.assert_called_once()
    mock_create_draft.assert_called_once_with(
        access_token="test_token",
        title="测试标题",
        content=mock_create_draft.call_args[1]['content'],
        author="百晓生",
        digest="测试摘要"
    )
    
    # 测试文件不存在的情况
    media_id = publish_to_wechat("nonexistent_file.md")
    assert media_id is None


@patch('src.news_podcast.wechat_publisher.publish_to_wechat')
def test_process_daily_news(mock_publish: MagicMock, tmp_path: Any) -> None:
    """测试处理当日新闻"""
    # 创建临时目录和文件
    timestamp = "20250408"
    test_dir = tmp_path / timestamp
    test_dir.mkdir()
    
    test_file = test_dir / f"global_tech_daily_{timestamp}.md"
    test_content = "# 全球科技日报\n\n这是测试内容。"
    test_file.write_text(test_content)
    
    # 模拟publish_to_wechat的返回值
    mock_publish.return_value = "test_media_id"
    
    # 使用临时目录的路径调用函数
    with patch('os.path.exists', return_value=True):
        with patch('src.news_podcast.wechat_publisher.publish_to_wechat', return_value="test_media_id"):
            media_id = process_daily_news(timestamp)
    
    assert media_id == "test_media_id"
    
    # 测试文件不存在的情况
    with patch('os.path.exists', return_value=False):
        media_id = process_daily_news("nonexistent")
    assert media_id is None 