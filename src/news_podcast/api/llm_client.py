"""
大语言模型客户端模块，用于与各种LLM API通信
"""
import os
import logging
from typing import Optional, Any, List, Dict
from openai import OpenAI

# 设置日志
logger = logging.getLogger(__name__)

def chat_with_deepseek(
    prompt: str,
    system_message: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    stream: bool = False,
    max_retries: int = 3,
    current_retry: int = 0,
) -> str:
    """
    与DeepSeek API进行对话，支持流式输出
    
    参数:
        prompt: 用户提示
        system_message: 系统消息
        model: 模型名称
        api_key: API密钥
        base_url: API基础URL
        stream: 是否使用流式输出
        max_retries: 最大重试次数
        current_retry: 当前重试次数
        
    返回:
        str: 模型响应
    """
    model = model or os.environ.get("ARK_MODEL")
    api_key = api_key or os.environ.get("ARK_API_KEY")
    base_url = base_url or os.environ.get("ARK_BASE_URL")
    
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
            print(f"收到空响应，正在重试... (尝试 {current_retry + 1}/{max_retries})")
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
            raise Exception(f"在{max_retries}次尝试后仍未获得响应")

        return full_response

    except Exception as e:
        if current_retry < max_retries:
            print(f"发生错误: {str(e)}，正在重试... (尝试 {current_retry + 1}/{max_retries})")
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
            raise Exception(f"在{max_retries}次尝试后失败。最后错误: {str(e)}") 