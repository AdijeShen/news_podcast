"""
微信公众号发布模块，用于将生成的内容转换为HTML并发布到微信公众号
"""
import os
import logging
import re
import time
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from pathlib import Path
import markdown
import html

from src.news_podcast.api.llm_client import chat_with_deepseek
from src.news_podcast.api.wechat_client import get_access_token, create_news_draft, publish_draft, get_publish_status

# 设置日志
logger = logging.getLogger(__name__)

def markdown_to_html(markdown_text: str) -> str:
    """
    将Markdown文本转换为微信公众号兼容的HTML
    
    参数:
        markdown_text: Markdown格式的文本
        
    返回:
        str: 转换后的HTML文本
    """
    # 使用markdown库进行基本转换
    html_content = markdown.markdown(
        markdown_text,
        extensions=['extra', 'nl2br', 'tables', 'sane_lists']
    )
    
    # 替换不兼容的样式或添加额外的微信公众号兼容样式
    # 例如，调整图片大小，添加居中样式等
    html_content = html_content.replace('<img', '<img style="max-width:100%;height:auto;display:block;margin:0 auto;"')
    
    # 添加全局样式以确保排版在微信公众号中正确显示
    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif; line-height: 1.6; color: #333;">
    {html_content}
    </div>
    """
    
    return html_content

def extract_title_and_summary(content: str) -> Tuple[str, str]:
    """
    使用DeepSeek从内容中提取标题和摘要
    
    参数:
        content: 文章内容
        
    返回:
        Tuple[str, str]: (标题, 摘要)
    """
    prompt = f"""
请从以下文章内容中提取一个吸引人的标题和简短的摘要（200字以内）。
标题应简洁有力，能吸引读者点击阅读。
摘要应该概括文章的主要内容和价值点。

请用JSON格式返回结果，包含title和summary两个字段：
{{
  "title": "文章标题",
  "summary": "文章摘要（不超过64字）"
}}

文章内容：
{content}

仅返回JSON格式的结果，不要有其他文字。
"""

    try:
        response = chat_with_deepseek(prompt, stream=False)
        
        # 提取JSON部分
        json_match = re.search(r'({[\s\S]*})', response)
        if json_match:
            import json
            result = json.loads(json_match.group(1))
            title = result.get('title', '全球科技日报')
            summary = result.get('summary', '今日科技热点汇总')
            return title, summary
        else:
            logger.warning(f"无法从响应中提取JSON: {response[:100]}...")
            # 尝试直接从文本中提取
            lines = response.split('\n')
            title = next((line for line in lines if line and not line.startswith('{')), '全球科技日报')
            summary_lines = [line for line in lines if line and line != title and not line.startswith('{')]
            summary = ' '.join(summary_lines)[:200] if summary_lines else '今日科技热点汇总'
            return title, summary
    
    except Exception as e:
        logger.error(f"提取标题和摘要时出错: {e}")
        # 使用默认值
        return '全球科技日报', '今日科技热点汇总'

def publish_to_wechat(md_file_path: str, author: str = "百晓生", auto_publish: bool = False) -> Optional[str]:
    """
    将Markdown文件内容发布到微信公众号
    
    参数:
        md_file_path: Markdown文件路径
        author: 作者名称
        auto_publish: 是否自动发布草稿
        
    返回:
        Optional[str]: 如果auto_publish为False，返回创建的草稿media_id；
                      如果auto_publish为True，返回发布任务的publish_id；
                      失败则返回None
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(md_file_path):
            logger.error(f"文件不存在: {md_file_path}")
            return None
        
        # 读取Markdown内容
        with open(md_file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        

        # 转换为HTML
        html_content = markdown_to_html(md_content)

        # 保存HTML内容到文件
        html_file_path = md_file_path.replace('.md', '.html')
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"已保存HTML内容到: {html_file_path}")

        # 提取标题和摘要
        title, digest = extract_title_and_summary(html_content)
        logger.info(f"提取的标题和摘要: {title}, {digest}")
        print(f"提取的标题和摘要: {title}, {digest}")
        
        # 获取access_token
        access_token, _ = get_access_token()
        
        # 创建草稿
        media_id = create_news_draft(
            access_token=access_token,
            title=title,
            content=html_content,
            author=author,
            digest=digest
        )
        
        logger.info(f"成功创建草稿，media_id: {media_id}")
        
        # 如果需要自动发布
        if auto_publish:
            try:
                # 发布草稿
                publish_id = publish_draft(access_token, media_id)
                logger.info(f"草稿已发布，publish_id: {publish_id}")
                
                # 等待几秒，然后查询发布状态
                time.sleep(3)
                status = get_publish_status(access_token, publish_id)
                logger.info(f"发布状态: {status}")
                
                return publish_id
            except Exception as pub_e:
                logger.error(f"发布草稿时出错: {pub_e}")
                # 即使发布失败，还是返回草稿ID
                return media_id
        
        return media_id
    
    except Exception as e:
        logger.error(f"发布到微信公众号时出错: {e}", exc_info=True)
        return None

def process_daily_news(timestamp: str, auto_publish: bool = False) -> Optional[str]:
    """
    处理当日新闻并发布到微信公众号
    
    参数:
        timestamp: 时间戳，用于定位文件
        auto_publish: 是否自动发布，而不只是创建草稿
        
    返回:
        Optional[str]: 如果auto_publish为False，返回创建的草稿media_id；
                      如果auto_publish为True，返回发布任务的publish_id；
                      失败则返回None
    """
    try:
        # 构建文件路径
        file_path = f"{timestamp}/global_tech_daily_{timestamp}.md"
        
        if not os.path.exists(file_path):
            logger.error(f"全球科技日报文件不存在: {file_path}")
            return None
        
        # 发布到微信公众号
        result_id = publish_to_wechat(file_path, auto_publish=auto_publish)
        
        if result_id:
            if auto_publish:
                logger.info(f"成功将全球科技日报发布到微信公众号，publish_id: {result_id}")
            else:
                logger.info(f"成功将全球科技日报创建为草稿，media_id: {result_id}")
        else:
            logger.error("发布全球科技日报到微信公众号失败")
        
        return result_id
    
    except Exception as e:
        logger.error(f"处理当日新闻时出错: {e}", exc_info=True)
        return None 