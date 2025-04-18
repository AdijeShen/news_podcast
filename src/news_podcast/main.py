"""
主程序入口，负责启动新闻播客生成流程
"""
import asyncio
import os
import time
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv

from src.news_podcast.models.news_task import NewsTask
from src.news_podcast.utils.config_manager import load_config
from src.news_podcast.utils.logger import setup_logging
from src.news_podcast.podcast_creator import scan_news, integrate_all_podcasts


async def main(config_path: str = "sources.yaml", timestamp: Optional[str] = None) -> None:
    """
    主程序入口函数
    
    参数:
        config_path: 配置文件路径
        timestamp: 时间戳，如果为None则使用当前日期
    """
    # 加载环境变量
    load_dotenv()
    
    # 设置时间戳
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d")
    
    # 创建目录
    if not os.path.exists(timestamp):
        os.makedirs(timestamp)
    
    # 检查今天是否已经生成过播客
    def check_already_generated(timestamp: str) -> bool:
        """
        检查指定日期的播客是否已经生成
        
        参数:
            timestamp: 日期时间戳
            
        返回:
            bool: 如果已生成返回True，否则返回False
        """
        target_file = f"global_tech_daily_{timestamp}.html"
        target_path = os.path.join(timestamp, target_file)
        return os.path.exists(target_path)
    
    # 如果已经生成过，则直接返回
    if check_already_generated(timestamp):
        print(f"今日({timestamp})播客已经生成，跳过处理")
        return

    # 创建日志目录
    log_dir = f"{timestamp}/log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 设置日志
    logger = setup_logging(log_dir=log_dir)
    
    # 加载配置
    tasks = load_config(config_path)
    
    # 处理每个任务
    for task in tasks:
        st = time.time()
        success = await scan_news(task, timestamp)
        if success:
            logger.info(f"\n任务{task.output_file}耗时: {time.time()-st:.2f}s")
        else:
            logger.error(f"\n任务{task.output_file}失败")
    
    # 整合所有播客
    await integrate_all_podcasts(tasks, timestamp)


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main()) 