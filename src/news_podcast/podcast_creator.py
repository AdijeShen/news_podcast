"""
播客生成主要逻辑模块，整合各个模块完成流程
"""
import asyncio
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Dict, Any, Optional

from src.news_podcast.models.news_task import NewsTask
from src.news_podcast.crawlers.web_crawler import async_search, fetch_news_content
from src.news_podcast.utils.news_processor import (
    pick_news_from_source, 
    pick_important_news, 
    generate_podcast
)
from src.news_podcast.api.llm_client import chat_with_deepseek
from src.news_podcast.wechat_publisher import process_daily_news

# 设置日志
logger = logging.getLogger(__name__)


async def scan_news(news_task: NewsTask, timestamp: str) -> bool:
    """
    处理单个新闻任务，获取并处理新闻内容
    
    参数:
        news_task: 新闻任务对象
        timestamp: 当前时间戳
        
    返回:
        bool: 处理是否成功
    """
    logger.info(f"开始处理任务: {news_task.url}")
    # 检查分析文件是否已存在
    if os.path.exists(f"{timestamp}/log/{news_task.output_file}.analysis"):
        logger.info(f"分析文件 {news_task.output_file}.analysis 已存在,跳过处理")
        return True
    
    try:
        news_url = news_task.url
        output_file = news_task.output_file
        strip_line_header = news_task.strip_line_header
        strip_line_bottom = news_task.strip_line_bottom
        sample_url = news_task.sample_url
        sample_url_output = news_task.sample_url_output
        
        # 获取杂志首页内容
        logger.info(f"开始获取首页内容: {news_url}")
        content = await async_search(news_url)
        if not content:
            logger.error(f"获取首页内容失败: {news_url}")
            return False
            
        logger.info(f"成功获取首页内容，长度: {len(content)}")

        # 保存原始内容
        with open(f"{timestamp}/log/{output_file}.origin", "w", encoding="utf-8") as f:
            f.write(content)

        # 去除首页内容中的无用行
        content = "\n".join(content.split("\n")[strip_line_header:-strip_line_bottom])
        logger.info(f"处理后的首页内容长度: {len(content)}")

        # 从首页内容中提取新闻链接
        news_list = pick_news_from_source(content, news_url, sample_url, sample_url_output)
        
        # 保存提取的新闻列表
        with open(f"{timestamp}/log/{output_file}.news_list.json", "w", encoding="utf-8") as f:
            json.dump(news_list, f, ensure_ascii=False, indent=2)
        
        # 获取新闻内容
        news_urls = [news["url"] for news in news_list]
        logger.info(f"提取到的新闻链接: {news_urls}")

        return True

    except Exception as e:
        logger.error(f"程序运行出错: {e}", exc_info=True)
        return False


async def integrate_all_podcasts(tasks: List[NewsTask], timestamp: str) -> bool:
    """
    整合所有来源的新闻分析为一个完整的全球科技日报
    
    参数:
        tasks: 新闻任务列表
        timestamp: 当前时间戳
        
    返回:
        bool: 处理是否成功
    """
    # 收集所有新闻列表
    all_news_lists = []
    task_map = {}  # 用于存储URL到NewsTask的映射
    
    for task in tasks:
        news_list_path = f"{timestamp}/log/{task.output_file}.news_list.json"
        if os.path.exists(news_list_path):
            try:
                with open(news_list_path, "r", encoding="utf-8") as f:
                    news_list = json.load(f)
                    all_news_lists.extend(news_list)
                    # 将每个新闻的URL映射到对应的task
                    for news in news_list:
                        task_map[news["url"]] = task
            except Exception as e:
                logger.error(f"读取{news_list_path}时出错: {e}")
    
    if not all_news_lists:
        logger.warning("没有找到任何新闻列表")
        return False
    
    # 从所有新闻中精选重要新闻
    selected_news = pick_important_news(all_news_lists)
    
    if not selected_news:
        logger.warning("没有找到任何重要新闻")
        return False
    
    # 保存精选的新闻列表
    with open(f"{timestamp}/log/selected_news.json", "w", encoding="utf-8") as f:
        json.dump(selected_news, f, ensure_ascii=False, indent=2)
    
    # 获取选中新闻的详细内容
    logger.info("开始获取选中新闻的详细内容")
    news_contents = []
    for news in selected_news:
        content = await async_search(news["url"])
        if content:
            news_contents.append((news["title"], content, news["url"]))
    
    # 生成深度分析
    logger.info("开始生成新闻深度分析")
    analyses = []
    for title, content, url in news_contents:
        # 获取对应的task
        task = task_map.get(url)
        if task:
            # 去除内容头尾，减少token使用
            processed_content = "\n".join(content.split("\n")[task.strip_line_header:-task.strip_line_bottom])
            logger.info(f"处理内容: 原始长度 {len(content)} -> 处理后长度 {len(processed_content)}")
            
            # 生成分析
            analysis = generate_podcast(processed_content, url)
        else:
            # 如果没有找到对应的task，使用原始内容
            logger.warning(f"未找到URL {url}对应的task，使用原始内容")
            analysis = generate_podcast(content, url)
            
        analyses.append((title, analysis, url))

    # 保存分析结果到JSON文件
    with open(f"{timestamp}/log/analyses.json", "w", encoding="utf-8") as f:
        analyses_data = [{"title": title, "url": url, "analysis": analysis} for title, analysis, url in analyses]
        json.dump(analyses_data, f, ensure_ascii=False, indent=2)
    
    # 整合所有来源的分析内容
    logger.info("开始整合所有来源的分析内容")
    final_aggregator_prompt = f"""
我需要你扮演一个有个性的科技评论人，把下面这些分析过的新闻整合成一期有态度的国际新闻订阅号推送。

今天是{timestamp}，给这期推送起个吸引眼球的标题，格式就是"{timestamp} XXX"。

以下是你要整合的文章：

"""
    for title, analysis, url in analyses:
        final_aggregator_prompt += f"\n【{title}】\n来源：{url}\n{analysis}\n"

    final_aggregator_prompt += """
最终的推送内容要包括：
1. 一个吸引人的标题
2. 开场白：用吸引人的方式概述今天的内容
3. 深度吐槽3~4个主题：
   - 到底发生了什么事情（要提供足够的信息）。
   - 给不了解的听众解释一下这件事情的背景。
   - 这东西到底靠不靠谱？亮点和缺陷在哪？（如果适用）
   - 对市场和行业有什么实际影响？别客套，直说
   - 社会和政策层面什么影响？敢说敢评
4. 其他新闻简单聊聊，但要注意提供足够的信息（包括发生了什么，背景是什么，然后做个简评）
5. 结尾：给读者一些建议，不需要中立，就说你真实的想法

记住，最重要的是：
- 非正式、口语化表达为主
- 不要用太多的专业术语，就像跟朋友聊天
- 自然流畅最重要，不要太死板地按格式来
- 保留新闻链接，但整体结构可以很灵活，不需要按格式来，不需要分点等，大段大段的文字就行
- 不要给出没有来源的数据
- 记得保留所有新闻的链接（链接不需要用markdown格式，直接用文字给出链接）
- （内容量）字数要足够多，最好在7000字以上
- 你是一个爱国的中国人，不要出现任何不尊重中国的言论
"""

    try:
        final_summary = chat_with_deepseek(
            final_aggregator_prompt,
            stream=False,
            max_tokens=30000,
        )

        # 保存最终整合的日报
        with open(f"{timestamp}/global_tech_daily_{timestamp}.md", "w", encoding="utf-8") as f:
            f.write(final_summary)
            f.write("\n\n")

        logger.info(f"全球科技日报已保存到 global_tech_daily_{timestamp}.md")
        
        # 发布到微信公众号
        try:
            logger.info("开始将全球科技日报发布到微信公众号...")
            media_id = process_daily_news(timestamp, auto_publish=False)
            if media_id:
                logger.info(f"成功将全球科技日报发布到微信公众号，草稿ID: {media_id}")
            else:
                logger.warning("发布到微信公众号失败，但不影响其他流程")
        except Exception as wx_error:
            logger.error(f"发布到微信公众号时发生错误: {wx_error}", exc_info=True)
            logger.warning("微信发布失败，但不影响全球科技日报的生成")
        
        return True
    except Exception as e:
        logger.error(f"整合分析内容时出错: {e}", exc_info=True)
        return False 