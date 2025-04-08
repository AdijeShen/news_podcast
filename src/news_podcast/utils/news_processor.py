"""
新闻处理模块，用于提取和处理新闻内容
"""
import json
import logging
import re
import time
from typing import List, Dict, Any, Optional

from src.news_podcast.api.llm_client import chat_with_deepseek

# 设置日志
logger = logging.getLogger(__name__)

def pick_news_from_source(content: str, source_url: str, sample_url: str, sample_url_output: str) -> List[Dict[str, str]]:
    """
    从单个新闻源中提取重要新闻
    
    参数:
        content: 新闻源内容
        source_url: 新闻源URL
        sample_url: 示例URL
        sample_url_output: 示例输出格式
        
    返回:
        List[Dict[str, str]]: 包含标题和URL的新闻列表
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


def pick_important_news(all_news: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    从所有来源的新闻中精选5-10条最重要的新闻
    
    参数:
        all_news: 所有来源的新闻列表
        
    返回:
        List[Dict[str, str]]: 精选的5-10条重要新闻
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
            json_match = re.search(r'\[(.*)\]', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)
            else:
                logger.error(f"无法从响应中提取JSON: {response[:100]}...")
                return []
        
        # 尝试解析JSON
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


def generate_podcast(news_content: str, source_url: str) -> str:
    """
    生成播客内容
    
    参数:
        news_content: 新闻内容
        source_url: 新闻来源URL
        
    返回:
        str: 生成的播客内容
    """
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