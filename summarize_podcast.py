import asyncio
from crawl4ai import *
from openai import OpenAI
import os
import logging
import time

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


async def async_search(search_url):
    """异步爬取网页内容并返回Markdown格式"""
    config = CrawlerRunConfig(cache_mode=CacheMode.DISABLED)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=search_url, config=config)
        return result.markdown


async def async_chat_with_deepseek(
    prompt,
    system_message=None,
    model="deepseek-chat",
    api_key=None,
    base_url="https://api.deepseek.com",
    stream=False,
    temperature=1.00,
):
    """与DeepSeek API进行异步对话，支持流式输出"""
    api_key = api_key or os.environ.get('DEEPSEEK_API_KEY')
    client = OpenAI(api_key=api_key, base_url=base_url)

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model, messages=messages, stream=stream, temperature=temperature
    )
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

    return full_response


async def fetch_news_content(news_urls):
    """并发获取多个新闻内容"""
    tasks = [async_search(url.strip()) for url in news_urls]
    return await asyncio.gather(*tasks)


async def generate_podcast(news_content):
    """生成播客内容"""
    podcast = await async_chat_with_deepseek(
        f"""请你扮演一位专业的科技财经播客主播,为以下新闻内容制作一期简短但富有洞见的播客分享。

目标受众: 关注科技创新、投资趋势的年轻专业人士
风格要求:
- 语气亲和但专业
- 观点鲜明有深度
- 结合实际案例
- 提供行动建议

内容结构:
1. 开场铺陈(1-2句)
2. 新闻主体内容(5-10句)
2. 核心观点(2-3点)
3. 实践启示(1~3点)

总字数控制在500字以内。请直接输出播客文稿,无需标注结构。

新闻内容: {news_content}""",
        stream=False,
        temperature=1.5,
    )
    return podcast


async def summarize_news(news_url, output_file, strip_line, sample_url, sample_url_output):
    try:
        # 获取时代杂志首页内容
        content = await async_search(news_url)

        with open(f"{timestamp}/log/{output_file}.origin", "w", encoding='utf-8') as f:
            f.write(content)

        # 去除首页内容中的无用行
        content = '\n'.join(content.split('\n')[strip_line:])

        # 从首页内容中提取新闻链接
        response = await async_chat_with_deepseek(
            f"""
作为一位专业的新闻编辑,请从{news_url}的首页内容中,精选3-7条最值得关注的新闻。选择标准:
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
            stream=True,
            temperature=0.5,
        )

        news_urls = response.split(",")
        logger.info(f"提取到的新闻链接: {news_urls}")

        # 并发获取新闻内容
        news_contents = await fetch_news_content(news_urls)
        
        with open(f"{timestamp}/log/{output_file}.news", "w", encoding='utf-8') as f:
            f.write("\n --- \n".join(news_contents))

        # 生成播客内容
        podcasts = []
        for content in news_contents:
            podcast = await generate_podcast(content)
            podcasts.append(podcast)

        with open(f"{timestamp}/log/{output_file}.podcast", "w", encoding='utf-8') as f:
            f.write("\n --- \n".join(podcasts))

        # 总结播客内容
        summarize = await async_chat_with_deepseek(
            f"""请你将以下几期播客内容,整合为一期15分钟的精品播客。

要求:
1. 主题串联: 找出内容间的关联,形成清晰主线
2. 重点突出: 聚焦最具价值的2-3个核心观点
3. 叙事手法: 采用故事化表达,增强代入感
4. 语言风格: 专业中带有趣,正式中有温度
5. 互动设计: 适当设置互动点,增强听众参与感

请输出一个完整的播客文稿,确保:
- 有清晰的逻辑架构
- 适合口播表达
- 富有感染力
- 能激发思考
- 只需要输出文字，不需要markdown格式
- 不需要说明为什么写成这样
- 确保所有博客内容都覆盖到，就算不在一条主线内
- 阿拉伯数字转换为中文数字
- 今天是{timestamp}，请在文稿中提及
播客内容如下:
{''.join(podcasts)}""",
            stream=False,
            temperature=1.5,
        )

        # 保存播客内容到文件
        with open(f"{timestamp}/{output_file}.md", "w", encoding='utf-8') as f:
            f.write(summarize)
            f.write("\n\n")

        logger.info(f"播客内容已保存到{output_file}")

    except Exception as e:
        logger.error(f"程序运行出错: {e}")


news_dict = [
    [
        "https://nytimes.com",
        "nytimes",
        661,
        "https://times.com/<https:/www.nytimes.com/interactive/2025/01/08/weather/los-angeles-fire-maps-california.html>",
        "https://www.nytimes.com/interactive/2025/01/08/weather/los-angeles-fire-maps-california.html",
    ],
    [
        "https://time.com",
        "time",
        80,
        "https://time.com/</7200909/ceo-of-the-year-2024-lisa-su/>",
        "https://time.com/7200909/ceo-of-the-year-2024-lisa-su/",
    ],
    [
        "https://www.economist.com/",
        "economist",
        88,
        "https://www.economist.com/</united-states/2025/01/09/americas-bet-on-industrial-policy-starts-to-pay-off-for-semiconductors>",
        "https://www.economist.com/united-states/2025/01/09/americas-bet-on-industrial-policy-starts-to-pay-off-for-semiconductors",
    ],
    [
        "https://www.ft.com/",
        "ft",
        191,
        "https://www.ft.com/</content/a973a98d-ba82-41fc-89f9-d34097f44c0b>",
        "https://www.ft.com/content/a973a98d-ba82-41fc-89f9-d34097f44c0b",
    ],
    [
        "https://www.bbc.com/",
        "bbc",
        31,
        "https://www.bbc.com/</news/articles/c20g7705re3o>",
        "https://www.bbc.com/news/articles/c20g7705re3o",
    ],
]


async def test_run():
    m = await async_search("https://www.bbc.com/")
    with open("bbc.md", "w") as f:
        f.write(m)


if __name__ == "__main__":
    for task_args in news_dict:
        st = time.time()
        asyncio.run(summarize_news(*task_args))
        logger.info(f"任务{task_args[0]}耗时: {time.time()-st:.2f}s")

    # a = asyncio.run(test_run())
