import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import time
import yaml
from dataclasses import dataclass
from typing import List

from crawl4ai import *
from openai import OpenAI

MODEL = "ep-20250208184831-9p2c6"  # deepseek-v3
# MODEL = "ep-20250208150109-xl7b5" # deepseek-r1
API_KEY = os.environ.get("ARK_API_KEY")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

# 设置日志
logging.basicConfig(level=logging.INFO)
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

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=search_url, config=config)
        return result.markdown


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
    tasks = [async_search(url.strip()) for url in news_urls]
    results = await asyncio.gather(*tasks)
    # 返回一个列表，每个元素是 (markdown文本, 对应的url)
    return list(zip(results, news_urls))


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

    try:
        news_url = news_task.url
        output_file = news_task.output_file
        strip_line_header = news_task.strip_line_header
        strip_line_bottom = news_task.strip_line_bottom
        sample_url = news_task.sample_url
        sample_url_output = news_task.sample_url_output
        # 获取杂志首页内容
        content = await async_search(news_url)

        with open(f"{timestamp}/log/{output_file}.origin", "w", encoding="utf-8") as f:
            f.write(content)

        # 去除首页内容中的无用行
        content = "\n".join(content.split("\n")[strip_line_header:-strip_line_bottom])

        # 从首页内容中提取新闻链接
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
        # 并发获取新闻内容: [(content, url), (content, url), ...]
        fetched_data = await fetch_news_content(news_urls)

        with open(f"{timestamp}/log/{output_file}.news", "w", encoding="utf-8") as f:
            # 把每条新闻 + url 写下来，方便调试
            for ntext, nurl in fetched_data:
                f.write(f"=== 来源: {nurl}\n{ntext}\n\n---\n\n")

        # 生成并存储每条播客：并行执行 generate_podcast
        thread_pool = ThreadPoolExecutor(max_workers=10)

        podcast_tasks = []
        for single_content, single_url in fetched_data:
            # 这里进行必要的预处理
            single_content = "\n".join(single_content.split("\n")[strip_line_header:-strip_line_bottom])

            podcast_tasks.append(thread_pool.submit(generate_podcast, single_content, single_url))

        # 并发执行所有generate_podcast
        podcasts_result = [task.result() for task in podcast_tasks]

        # 将执行结果与对应URL组装起来
        podcasts = []
        for i, (single_content, single_url) in enumerate(fetched_data):
            podcasts.append((podcasts_result[i], single_url))

        # 记录所有播客文本
        with open(f"{timestamp}/log/{output_file}.podcast", "w", encoding="utf-8") as f:
            # 把每条 podcast + url 写下来，方便调试
            for ptext, purl in podcasts:
                f.write(f"=== 来源: {purl}\n{ptext}\n\n---\n\n")

        # 整合播客内容（依然可以给大模型一个综合 prompt）
        # 如果你想在最终的汇总里也带上链接，可以手动拼接
        aggregator_prompt = f"""
你是编辑百晓生，请将以下几期公众号内容整合为一期公众号内容。

今天是{timestamp}，请在文稿中提及。
请一并保留来源链接信息（如文本中已有提及，或重新以“来源: 某某链接”形式挂在该新闻后）。

以下是多条公众号文本和来源链接:
"""
        for idx, (ptext, purl) in enumerate(podcasts, start=1):
            aggregator_prompt += f"\n【播客{idx}】(来源: {purl})\n{ptext}\n"

        aggregator_prompt += """
(请输出一个整合后的公众号文稿，保持逻辑连贯，语气亲切口语化，覆盖所有事件，不要遗漏链接信息。并为这个公众号想一个吸引人的大标题)
请发挥想象，另外描述这期公众号的封面可以是什么样的。
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
        logger.error(f"程序运行出错: {e}")


async def test_run():
    m = await async_search("https://www.wsj.com")
    # m = await async_search("https://nytimes.com")

    with open("try.md", "w") as f:
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
