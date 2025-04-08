import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import time
import yaml
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

from crawl4ai import *
from openai import OpenAI
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.browser_manager import BrowserManager


async def patched_async_playwright__crawler_strategy_close(self) -> None:
    """
    Close the browser and clean up resources.

    This patch addresses an issue with Playwright instance cleanup where the static instance
    wasn't being properly reset, leading to issues with multiple crawls.

    Issue: https://github.com/unclecode/crawl4ai/issues/842

    Returns:
        None
    """
    await self.browser_manager.close()

    # Reset the static Playwright instance
    BrowserManager._playwright_instance = None


AsyncPlaywrightCrawlerStrategy.close = patched_async_playwright__crawler_strategy_close

# 加载.env文件
load_dotenv()

MODEL = os.getenv("ARK_MODEL")  # deepseek-v3
API_KEY = os.getenv("ARK_API_KEY")
BASE_URL = os.getenv("ARK_BASE_URL")

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


timestamp = time.strftime("%Y%m%d", time.localtime())

# create directory
if not os.path.exists(timestamp):
    os.makedirs(timestamp)

# create directory
if not os.path.exists(f"{timestamp}/log"):
    os.makedirs(f"{timestamp}/log")


async def async_search(search_url, bypass_paywall=False):
    """异步爬取网页内容并返回Markdown格式"""
    config = CrawlerRunConfig(
        cache_mode=CacheMode.DISABLED, simulate_user=True, override_navigator=True, magic=True  # 自动处理弹窗
    )
    if bypass_paywall:
        search_url = f"https://archive.ph/newest/{search_url}"

    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=search_url,
                config=config,
            )
        return result.markdown
    except Exception as e:
        logger.error(f"爬取{search_url}时出错: {e}")
        return f"爬取失败: {e}"


def chat_with_deepseek(
    prompt,
    system_message=None,
    model=MODEL,
    api_key=API_KEY,
    base_url=BASE_URL,
    stream=False,
    max_retries=3,
    current_retry=0,
):
    """与DeepSeek API进行异步对话，支持流式输出"""
    api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
    client = OpenAI(api_key=api_key, base_url=base_url)

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(model=model, messages=messages, stream=stream)
        full_response = ""

        if stream:
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
                    full_response += content
            print()  # Final newline
        else:
            full_response = response.choices[0].message.content
        logger.info(f"Token使用量: {response.usage}")
        # 如果响应为空且未超过最大重试次数，则重试
        if not full_response and current_retry < max_retries:
            print(f"Received empty response, retrying... (Attempt {current_retry + 1}/{max_retries})")
            return chat_with_deepseek(
                prompt,
                system_message,
                model,
                api_key,
                base_url,
                stream,
                max_retries,
                current_retry + 1,
            )
        elif not full_response and current_retry >= max_retries:
            raise Exception(f"Failed to get response after {max_retries} attempts")

        return full_response

    except Exception as e:
        if current_retry < max_retries:
            print(f"Error occurred: {str(e)}, retrying... (Attempt {current_retry + 1}/{max_retries})")
            return chat_with_deepseek(
                prompt,
                system_message,
                model,
                api_key,
                base_url,
                stream,
                max_retries,
                current_retry + 1,
            )
        else:
            raise Exception(f"Failed after {max_retries} attempts. Last error: {str(e)}")


async def fetch_news_content(news_urls):
    """并发获取多个新闻内容，同时保留对应链接"""
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
                    await asyncio.sleep(2)  # 等待2秒后重试
            except Exception as e:
                logger.error(f"获取{url}内容时出错: {e}")
                retry_count += 1
                await asyncio.sleep(2)  # 等待2秒后重试
        
        if retry_count == max_retries:
            logger.error(f"获取{url}内容失败，已达到最大重试次数")
            results.append((f"获取失败: 已达到最大重试次数", url.strip()))
    
    return results


def generate_podcast(news_content: str, source_url: str):
    st = time.time()
    if news_content is None or news_content.strip() == "":
        return "无内容，跳过"

    prompt = f"""
你是一位资深的科技新闻分析师，请对以下新闻进行深度分析和解读。

目标受众：
- 关注科技创新、国际局势的年轻专业人士
- 对科技发展有浓厚兴趣的读者
- 希望了解全球科技动态的决策者
- 对地缘政治、国际关系感兴趣的读者

分析要求：
1. 内容深度：
   - 深入分析新闻背后的原因和影响
   - 解释相关的技术原理和发展趋势
   - 探讨对行业和社会的潜在影响
   - 提供相关的历史背景和行业现状

2. 分析角度：
   - 从技术、商业、社会多个维度分析
   - 关注新闻的长期影响和趋势
   - 分析可能的风险和机遇
   - 提供专业的见解和预测

3. 表达方式：
   - 使用专业但易懂的语言
   - 适当使用类比和例子
   - 保持逻辑性和连贯性
   - 突出关键信息和数据

新闻来源: {source_url}

原始新闻内容:
{news_content}

请按以下结构输出深度分析文章：
1. 引人注目的标题（突出核心价值）
2. 新闻概述（简要介绍关键信息）
3. 深度分析（至少3个核心观点）
   - 技术/产品分析
   - 市场/行业影响
   - 社会/政策影响
4. 未来展望（发展趋势和预测）
5. 启示与建议（对相关方的建议）

注意事项：
- 总字数控制在800字以内
- 确保分析的深度和专业性
- 提供具体的数据和例子支持观点
- 保持客观中立的分析态度
"""
    logger.info(f"开始生成{source_url}播客")
    podcast = chat_with_deepseek(
        prompt=prompt,
        stream=False,
    )
    logger.info(f"生成{source_url}播客耗时: {time.time()-st:.2f}s")
    return podcast


@dataclass
class NewsTask:
    url: str
    output_file: str
    strip_line_header: int
    strip_line_bottom: int
    sample_url: str
    sample_url_output: str


def pick_news_from_source(content: str, source_url: str, sample_url: str, sample_url_output: str) -> List[dict]:
    """
    从单个新闻源中提取重要新闻
    
    Args:
        content: 新闻源内容
        source_url: 新闻源URL
        sample_url: 示例URL
        sample_url_output: 示例输出格式
        
    Returns:
        List[dict]: 包含标题和URL的新闻列表
    """
    logger.info(f"开始从{source_url}提取重要新闻")
    
    prompt = f"""
作为一位专业的新闻编辑,请从{source_url}的首页内容中,精选5~10条最值得关注的新闻。选择标准:
1. 重大社会影响: 政策变化、经济动向、科技突破等
2. 时效性: 24小时内的重要进展
3. 深度视角: 独特的分析和见解
4. 创新性: 新趋势、新发现、新思路

请按以下JSON格式输出新闻列表:
[
    {{"title": "新闻标题1", "url": "新闻URL1"}},
    {{"title": "新闻标题2", "url": "新闻URL2"}},
    ...
]

参考示例: {sample_url} 输出为: {sample_url_output}

首页内容如下:
{content}

请只输出JSON格式的新闻列表，不要输出其他内容。确保输出是有效的JSON格式。
"""
    
    try:
        response = chat_with_deepseek(prompt, stream=False)
        
        # 尝试清理响应文本，确保它是有效的JSON
        response = response.strip()
        
        # 如果响应不是以[开头，尝试提取JSON部分
        if not response.startswith('['):
            import re
            json_match = re.search(r'\[(.*)\]', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)
            else:
                # 尝试从文本中提取标题和URL
                logger.warning(f"无法从响应中提取JSON，尝试从文本中提取标题和URL: {response[:100]}...")
                news_list = []
                lines = response.split('\n')
                for line in lines:
                    if 'http' in line and '://' in line:
                        url_match = re.search(r'(https?://[^\s]+)', line)
                        if url_match:
                            url = url_match.group(1)
                            # 尝试从同一行或前一行提取标题
                            title = line.replace(url, '').strip()
                            if not title and len(lines) > 1:
                                title = lines[lines.index(line)-1].strip()
                            if title:
                                news_list.append({"title": title, "url": url})
                if news_list:
                    logger.info(f"从文本中提取到{len(news_list)}条新闻")
                    return news_list
                else:
                    logger.error(f"无法从响应中提取新闻信息: {response[:100]}...")
                    return []
        
        # 尝试解析JSON
        import json
        news_list = json.loads(response)
        
        # 验证JSON格式
        if not isinstance(news_list, list):
            logger.error(f"解析结果不是列表: {type(news_list)}")
            return []
            
        # 验证每个新闻项
        valid_news_list = []
        for item in news_list:
            if isinstance(item, dict) and 'title' in item and 'url' in item:
                valid_news_list.append(item)
            else:
                logger.warning(f"跳过无效的新闻项: {item}")
                
        logger.info(f"从{source_url}提取到{len(valid_news_list)}条有效新闻")
        return valid_news_list
    except Exception as e:
        logger.error(f"解析{source_url}的新闻列表时出错: {e}")
        logger.error(f"响应内容: {response[:200]}...")
        return []


def pick_important_news(all_news: List[dict]) -> List[dict]:
    """
    从所有来源的新闻中精选5-10条最重要的新闻
    
    Args:
        all_news: 所有来源的新闻列表
        
    Returns:
        List[dict]: 精选的5-10条重要新闻
    """
    logger.info("开始从所有来源中精选重要新闻")
    
    # 构建所有新闻的摘要
    news_summary = ""
    for idx, news in enumerate(all_news, start=1):
        news_summary += f"{idx}. 标题: {news['title']}\n   来源: {news['url']}\n\n"
    
    prompt = f"""
作为一位资深的科技新闻主编，请从以下所有新闻源中精选5-10条最值得关注的新闻。选择标准：
1. 重大社会影响：政策变化、经济动向、科技突破等
2. 时效性：24小时内的重要进展
3. 深度视角：独特的分析和见解
4. 创新性：新趋势、新发现、新思路
5. 多样性：确保不同领域的新闻都有代表

以下是所有新闻的列表：

{news_summary}

请按以下JSON格式输出精选的新闻列表（5-10条）：
[
    {{"title": "新闻标题1", "url": "新闻URL1", "reason": "选择原因1"}},
    {{"title": "新闻标题2", "url": "新闻URL2", "reason": "选择原因2"}},
    ...
]

请只输出JSON格式的新闻列表，不要输出其他内容。确保输出是有效的JSON格式。
"""
    
    try:
        response = chat_with_deepseek(prompt, stream=False)
        
        # 尝试清理响应文本，确保它是有效的JSON
        response = response.strip()
        
        # 如果响应不是以[开头，尝试提取JSON部分
        if not response.startswith('['):
            import re
            json_match = re.search(r'\[(.*)\]', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)
            else:
                logger.error(f"无法从响应中提取JSON: {response[:100]}...")
                return []
        
        # 尝试解析JSON
        import json
        selected_news = json.loads(response)
        
        # 验证JSON格式
        if not isinstance(selected_news, list):
            logger.error(f"解析结果不是列表: {type(selected_news)}")
            return []
            
        # 验证每个新闻项
        valid_news = []
        for item in selected_news:
            if isinstance(item, dict) and 'title' in item and 'url' in item:
                # 确保reason字段存在
                if 'reason' not in item:
                    item['reason'] = "未提供选择原因"
                valid_news.append(item)
            else:
                logger.warning(f"跳过无效的新闻项: {item}")
                
        logger.info(f"从所有来源中精选出{len(valid_news)}条重要新闻")
        return valid_news
    except Exception as e:
        logger.error(f"解析精选新闻列表时出错: {e}")
        logger.error(f"响应内容: {response[:200]}...")
        return []


async def scan_news(news_task: NewsTask):
    """处理单个新闻任务，获取并处理新闻内容"""
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
            import json
            json.dump(news_list, f, ensure_ascii=False, indent=2)
        
        # 获取新闻内容
        news_urls = [news["url"] for news in news_list]
        logger.info(f"提取到的新闻链接: {news_urls}")

        # # 并发获取新闻内容
        # logger.info("开始获取新闻内容")
        # fetched_data = await fetch_news_content(news_urls)
        # logger.info(f"成功获取{len(fetched_data)}条新闻内容")

        # # 保存获取的新闻内容
        # with open(f"{timestamp}/log/{output_file}.news", "w", encoding="utf-8") as f:
        #     for ntext, nurl in fetched_data:
        #         f.write(f"=== 来源: {nurl}\n{ntext}\n\n---\n\n")

        # # 生成每条新闻的深度分析
        # logger.info("开始生成新闻分析")
        # thread_pool = ThreadPoolExecutor(max_workers=5)

        # podcast_tasks = []
        # for single_content, single_url in fetched_data:
        #     single_content = "\n".join(single_content.split("\n")[strip_line_header:-strip_line_bottom])
        #     podcast_tasks.append(thread_pool.submit(generate_podcast, single_content, single_url))

        # # 并发执行所有generate_podcast
        # podcasts_result = []
        # for task in podcast_tasks:
        #     try:
        #         result = task.result()
        #         podcasts_result.append(result)
        #     except Exception as e:
        #         logger.error(f"生成新闻分析时出错: {e}")
        #         podcasts_result.append(f"生成失败: {e}")

        # # 将执行结果与对应URL组装起来
        # podcasts = []
        # for i, (single_content, single_url) in enumerate(fetched_data):
        #     podcasts.append((podcasts_result[i], single_url))

        # # 保存分析结果
        # with open(f"{timestamp}/log/{output_file}.analysis", "w", encoding="utf-8") as f:
        #     for ptext, purl in podcasts:
        #         f.write(f"=== 来源: {purl}\n{ptext}\n\n---\n\n")

        return True

    except Exception as e:
        logger.error(f"程序运行出错: {e}", exc_info=True)
        return False


async def integrate_all_podcasts(tasks: List[NewsTask]) -> bool:
    """整合所有来源的新闻分析为一个完整的全球科技日报"""
    # 收集所有新闻列表
    all_news_lists = []
    task_map = {}  # 用于存储URL到NewsTask的映射
    
    for task in tasks:
        news_list_path = f"{timestamp}/log/{task.output_file}.news_list.json"
        if os.path.exists(news_list_path):
            try:
                with open(news_list_path, "r", encoding="utf-8") as f:
                    import json
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
        import json
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
        import json
        analyses_data = [{"title": title, "url": url, "analysis": analysis} for title, analysis, url in analyses]
        json.dump(analyses_data, f, ensure_ascii=False, indent=2)
    
    # 整合所有来源的分析内容
    logger.info("开始整合所有来源的分析内容")
    final_aggregator_prompt = f"""
你是一位资深的科技新闻主编，请从以下几篇深度分析文章中，精选最重要的1-2个主题进行深入解读，其他重要新闻简要概述。

今天是{timestamp}，请以"{timestamp} 全球科技日报"作为标题。

整合要求：
1. 内容组织：
   - 选择1-2个最具影响力的主题进行深度分析
   - 其他重要新闻以简讯形式呈现
   - 确保内容的连贯性和逻辑性
   - 突出新闻之间的关联性

2. 深度分析要求：
   - 深入探讨选定的主题
   - 提供多维度的分析和见解
   - 探讨长期影响和趋势
   - 结合行业背景和历史发展

3. 信息完整性：
   - 保留所有重要新闻的来源链接
   - 确保关键信息的准确性
   - 突出新闻之间的关联性
   - 提供必要的背景信息

以下是需要整合的文章：

"""
    for title, analysis, url in analyses:
        final_aggregator_prompt += f"\n【{title}】\n来源：{url}\n{analysis}\n"

    final_aggregator_prompt += """
请输出一篇完整的全球科技日报，包含：
1. 标题："{timestamp} 全球科技日报"
2. 导语：概述当天最重要的科技新闻
3. 深度分析（1-2个主题）：
   - 详细的技术/产品分析
   - 市场/行业影响分析
   - 社会/政策影响分析
   - 未来趋势预测
4. 其他重要新闻简讯
5. 结语：总结当天科技发展的主要趋势

注意事项：
- 确保深度分析的专业性和可读性
- 保持所有来源链接的完整性
- 突出新闻之间的关联性
- 使用清晰的结构和层次
- 去除重复的内容
"""

    try:
        final_summary = chat_with_deepseek(
            final_aggregator_prompt,
            stream=False,
        )

        # 保存最终整合的日报
        with open(f"{timestamp}/global_tech_daily_{timestamp}.md", "w", encoding="utf-8") as f:
            f.write(final_summary)
            f.write("\n\n")

        logger.info(f"全球科技日报已保存到 global_tech_daily_{timestamp}.md")
        return True
    except Exception as e:
        logger.error(f"整合分析内容时出错: {e}", exc_info=True)
        return False


async def test_run():
    m = await async_search("https://time.com/7274542/colossal-dire-wolf/")
    # m = await async_search("https://nytimes.com")

    with open("try.md", "w", encoding="utf-8") as f:
        f.write(m)


def load_config(config_path: str) -> List[NewsTask]:
    """
    从给定的 config_path 读取配置文件，并返回一个包含 NewsTask 的列表
    """
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # data 应该是一个 dict，比如 {"news_dict": [ {...}, {...}, ... ]}
    news_list = data.get("news_dict", [])
    # 利用解包将 dict -> dataclass
    return [NewsTask(**item) for item in news_list]


if __name__ == "__main__":
    # a = asyncio.run(test_run())

    tasks = load_config("sources.yaml")

    # 处理每个任务
    for t in tasks:
        st = time.time()
        success = asyncio.run(scan_news(t))
        if success:
            logger.info(f"\n任务{t.output_file}耗时: {time.time()-st:.2f}s")
        else:
            logger.error(f"\n任务{t.output_file}失败")

    # 整合所有播客
    asyncio.run(integrate_all_podcasts(tasks))
