"""
配置管理模块，用于加载和处理配置文件
"""
import yaml
from typing import List, Dict, Any

from src.news_podcast.models.news_task import NewsTask

def load_config(config_path: str) -> List[NewsTask]:
    """
    从配置文件中加载新闻任务列表
    
    参数:
        config_path: 配置文件路径
        
    返回:
        List[NewsTask]: 包含NewsTask对象的列表
    """
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # data应该是一个dict，比如{"news_dict": [...]}
    news_list = data.get("news_dict", [])
    # 将dict转换为NewsTask对象
    return [NewsTask(**item) for item in news_list] 