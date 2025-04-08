"""
微信公众号API客户端模块，用于处理微信公众号操作
"""
import os
import json
import logging
import requests
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# 设置日志
logger = logging.getLogger(__name__)

def get_access_token() -> Tuple[str, int]:
    """
    获取微信公众号access_token
    
    返回:
        Tuple[str, int]: (access_token, 过期时间)
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    # 微信公众号的appid和secret
    appid = os.getenv("WECHAT_APPID")
    secret = os.getenv("WECHAT_SECRET")
    
    if not appid or not secret:
        raise ValueError("环境变量中未设置WECHAT_APPID或WECHAT_SECRET")
    
    # 请求URL
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": appid,
        "secret": secret
    }
    
    # 发送请求
    response = requests.get(url, params=params)
    
    # 检查响应
    if response.status_code != 200:
        logger.error(f"获取access_token失败: {response.text}")
        raise Exception(f"获取access_token失败: {response.text}")
    
    result = response.json()
    if "access_token" not in result:
        logger.error(f"获取access_token响应中没有access_token字段: {result}")
        raise Exception(f"获取access_token响应中没有access_token字段: {result}")
    
    return result["access_token"], result["expires_in"]

def get_media_id(access_token: str, media_type: str = "image") -> str:
    """
    获取一个可用的媒体ID用于发布文章
    
    参数:
        access_token: 微信公众号访问令牌
        media_type: 媒体类型，默认为图片
        
    返回:
        str: 媒体ID
    """
    # 请求URL
    url = f'https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={access_token}'
    
    # 请求参数
    data = {
        "type": media_type,  # 素材类型，这里获取图片
        "offset": 0,         # 从全部素材的该偏移位置开始返回
        "count": 20          # 返回素材的数量，取值在1到20之间
    }
    
    # 发送请求
    response = requests.post(url, json=data)
    
    # 检查响应
    if response.status_code != 200:
        logger.error(f"获取媒体列表失败: {response.text}")
        raise Exception(f"获取媒体列表失败: {response.text}")
    
    result = response.json()
    
    # 检查是否有素材
    if 'item' not in result or not result['item']:
        logger.error(f"未找到类型为{media_type}的素材")
        raise Exception(f"未找到类型为{media_type}的素材")
    
    # 返回第一个素材的media_id
    return result['item'][0]['media_id']

def create_news_draft(
    access_token: str, 
    title: str, 
    content: str, 
    author: str = "", 
    digest: str = "", 
    thumb_media_id: Optional[str] = None,
    need_open_comment: int = 1,
    only_fans_can_comment: int = 0
) -> str:
    """
    创建微信公众号图文素材草稿
    
    参数:
        access_token: 微信公众号访问令牌
        title: 文章标题
        content: 文章内容（HTML格式）
        author: 文章作者
        digest: 文章摘要
        thumb_media_id: 封面图片素材ID，如果为None则自动获取
        need_open_comment: 是否打开评论
        only_fans_can_comment: 是否仅粉丝可评论
        
    返回:
        str: 创建的草稿media_id
    """
    # 如果没有提供封面图，则自动获取一个
    if not thumb_media_id:
        thumb_media_id = get_media_id(access_token)
    
    # 请求URL
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
    
    # 当前时间，用于确保每次发布的文章都有不同的标题
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 请求参数
    data = {
        "articles": [
            {
                "article_type": "news",
                "title": title,
                "author": author,
                "digest": digest,
                "content": content,
                "thumb_media_id": thumb_media_id,
                "need_open_comment": need_open_comment,
                "only_fans_can_comment": only_fans_can_comment
            }
        ]
    }
    
    # 将数据转换为JSON字符串，确保unicode编码正确
    json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
    
    # 发送请求时指定Content-Type和编码
    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    # 发送请求
    response = requests.post(url, data=json_data, headers=headers)
    
    # 检查响应
    if response.status_code != 200:
        logger.error(f"创建草稿失败: {response.text}")
        raise Exception(f"创建草稿失败: {response.text}")
    
    result = response.json()
    
    # 检查是否成功
    if "errcode" in result and result["errcode"] != 0:
        if result["errcode"] == 45028:  # 草稿数量已达上限
            logger.warning("草稿数量已达上限，请先删除一些草稿")
        else:
            logger.error(f"创建草稿失败: {result}")
            raise Exception(f"创建草稿失败: {result}")
    
    if "media_id" not in result:
        logger.error(f"创建草稿响应中没有media_id字段: {result}")
        raise Exception(f"创建草稿响应中没有media_id字段: {result}")
    
    return result["media_id"]

def publish_draft(access_token: str, media_id: str) -> str:
    """
    直接发布草稿到微信公众号
    
    参数:
        access_token: 微信公众号访问令牌
        media_id: 草稿的media_id
        
    返回:
        str: 发布任务的publish_id
    """
    # 请求URL
    url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={access_token}"
    
    # 请求参数
    data = {
        "media_id": media_id
    }
    
    # 将数据转换为JSON字符串，确保unicode编码正确
    json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
    
    # 发送请求时指定Content-Type和编码
    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    # 发送请求
    response = requests.post(url, data=json_data, headers=headers)
    
    # 检查响应
    if response.status_code != 200:
        logger.error(f"发布草稿失败: {response.text}")
        raise Exception(f"发布草稿失败: {response.text}")
    
    result = response.json()
    
    # 检查是否成功
    if "errcode" in result and result["errcode"] != 0:
        logger.error(f"发布草稿失败: {result}")
        raise Exception(f"发布草稿失败: {result}")
    
    if "publish_id" not in result:
        logger.error(f"发布草稿响应中没有publish_id字段: {result}")
        raise Exception(f"发布草稿响应中没有publish_id字段: {result}")
    
    logger.info(f"草稿发布成功，publish_id: {result['publish_id']}")
    return result["publish_id"]

def get_publish_status(access_token: str, publish_id: str) -> Dict[str, Any]:
    """
    查询发布状态
    
    参数:
        access_token: 微信公众号访问令牌
        publish_id: 发布任务ID
        
    返回:
        Dict[str, Any]: 发布状态信息
    """
    # 请求URL
    url = f"https://api.weixin.qq.com/cgi-bin/freepublish/get?access_token={access_token}"
    
    # 请求参数
    data = {
        "publish_id": publish_id
    }
    
    # 发送请求
    response = requests.post(url, json=data)
    
    # 检查响应
    if response.status_code != 200:
        logger.error(f"查询发布状态失败: {response.text}")
        raise Exception(f"查询发布状态失败: {response.text}")
    
    result = response.json()
    
    # 检查是否成功
    if "errcode" in result and result["errcode"] != 0:
        logger.error(f"查询发布状态失败: {result}")
        raise Exception(f"查询发布状态失败: {result}")
    
    return result 