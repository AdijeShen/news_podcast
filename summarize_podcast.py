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

MODEL = "ep-20250328220825-dgw8j"  # deepseek-v3
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
请你扮演一位专业的公众号写手,为以下新闻内容制作一期简短但富有洞见的公众号分享。

目标受众: 关注科技创新、国际局势的年轻人
风格要求:
- 语气亲且口语化，就像在和观众聊天
- 观点鲜明有深度，知识要专业，但不要晦涩
- （如果涉及一些非常识的内容）请提供一些背景知识
- 你是一个爱国的中国人，不要带有别国的政治倾向

新闻来源: {source_url}

英文原始新闻内容:
[{news_content}]

请输出一段公众号文稿(中文)，包含以下内容
文稿结构要求：
- 请你为这段内容起一个吸引人的标题
- (1) 新闻主体
- (2) （可选）必要知识
- (3) 核心观点
- (4) （可选）启示

- 文稿只需要分段，不需要段落标题。
- 启示应该从个人的角度提，如果没有，那可以不写。
- 你的文稿的承接应该自然，不要说"核心观点是"这样的铺陈，直接展开即可。
- 文稿字数不超过500字。
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


async def summarize_news(news_task: NewsTask):
    logger.info(f"开始处理任务: {news_task.output_file}")
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
            return
            
        logger.info(f"成功获取首页内容，长度: {len(content)}")

        with open(f"{timestamp}/log/{output_file}.origin", "w", encoding="utf-8") as f:
            f.write(content)

        # 去除首页内容中的无用行
        content = "\n".join(content.split("\n")[strip_line_header:-strip_line_bottom])
        logger.info(f"处理后的首页内容长度: {len(content)}")

        # 从首页内容中提取新闻链接
        logger.info("开始提取新闻链接")
        response = chat_with_deepseek(
            f"""
作为一位专业的新闻编辑,请从{news_url}的首页内容中,精选5~10条最值得关注的新闻。选择标准:
1. 重大社会影响: 政策变化、经济动向、科技突破等
2. 时效性: 24小时内的重要进展
3. 深度视角: 独特的分析和见解
4. 创新性: 新趋势、新发现、新思路

请按以下格式输出新闻链接(用逗号分隔):
参考示例: {sample_url} 输出为: {sample_url_output}

首页内容如下:
{content}

- 请输出逗号分隔的url，不要输出其他内容
                """,
            stream=False,
        )

        news_urls = response.split(",")
        logger.info(f"提取到的新闻链接: {news_urls}")

        # 并发获取新闻内容
        logger.info("开始获取新闻内容")
        fetched_data = await fetch_news_content(news_urls)
        logger.info(f"成功获取{len(fetched_data)}条新闻内容")

        with open(f"{timestamp}/log/{output_file}.news", "w", encoding="utf-8") as f:
            # 把每条新闻 + url 写下来，方便调试
            for ntext, nurl in fetched_data:
                f.write(f"=== 来源: {nurl}\n{ntext}\n\n---\n\n")

        # 生成并存储每条播客：并行执行 generate_podcast
        logger.info("开始生成播客内容")
        thread_pool = ThreadPoolExecutor(max_workers=5)  # 减少并发数

        podcast_tasks = []
        for single_content, single_url in fetched_data:
            # 这里进行必要的预处理
            single_content = "\n".join(single_content.split("\n")[strip_line_header:-strip_line_bottom])
            podcast_tasks.append(thread_pool.submit(generate_podcast, single_content, single_url))

        # 并发执行所有generate_podcast
        podcasts_result = []
        for task in podcast_tasks:
            try:
                result = task.result()
                podcasts_result.append(result)
            except Exception as e:
                logger.error(f"生成播客内容时出错: {e}")
                podcasts_result.append(f"生成失败: {e}")

        # 将执行结果与对应URL组装起来
        podcasts = []
        for i, (single_content, single_url) in enumerate(fetched_data):
            podcasts.append((podcasts_result[i], single_url))

        # 记录所有播客文本
        with open(f"{timestamp}/log/{output_file}.podcast", "w", encoding="utf-8") as f:
            # 把每条 podcast + url 写下来，方便调试
            for ptext, purl in podcasts:
                f.write(f"=== 来源: {purl}\n{ptext}\n\n---\n\n")

        # 整合播客内容
        logger.info("开始整合播客内容")
        aggregator_prompt = f"""
你是编辑百晓生，请将以下几期公众号内容整合为一期公众号内容。

今天是{timestamp}，请在文稿中提及。
请一并保留来源链接信息（如文本中已有提及，或重新以"来源: 某某链接"形式挂在该新闻后）。

以下是多条公众号文本和来源链接:
"""
        for idx, (ptext, purl) in enumerate(podcasts, start=1):
            aggregator_prompt += f"\n【播客{idx}】(来源: {purl})\n{ptext}\n"

        aggregator_prompt += """
(请输出一个整合后的公众号文稿，保持逻辑连贯，语气亲切口语化，覆盖所有事件，不要遗漏链接信息。并为这个公众号想一个吸引人的大标题)。
        """

        summarize = chat_with_deepseek(
            aggregator_prompt,
            stream=False,
        )

        # 保存最终汇总播客
        with open(f"{timestamp}/{output_file}.md", "w", encoding="utf-8") as f:
            f.write(summarize)
            f.write("\n\n")

        logger.info(f"播客内容已保存到{output_file}")

    except Exception as e:
        logger.error(f"程序运行出错: {e}", exc_info=True)


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

    tasks = load_config("config.yaml")

    # 现在 tasks 就是一个 [NewsTask, NewsTask, ...] 的列表
    for t in tasks:
        st = time.time()
        asyncio.run(summarize_news(t))
        logger.info(f"\n任务{t.output_file}耗时: {time.time()-st:.2f}s")
