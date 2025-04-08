"""
日志工具模块，用于设置和管理日志
"""
import logging
import os
from typing import Optional

def setup_logging(level: int = logging.INFO, 
                  log_format: Optional[str] = None, 
                  log_dir: Optional[str] = None) -> logging.Logger:
    """
    设置日志系统
    
    参数:
        level: 日志级别
        log_format: 日志格式
        log_dir: 日志目录
        
    返回:
        logging.Logger: 配置好的日志记录器
    """
    # 默认日志格式
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'
    
    # 配置根日志记录器
    logging.basicConfig(
        level=level,
        format=log_format
    )
    
    # 创建日志记录器
    logger = logging.getLogger('news_podcast')
    
    # 如果指定了日志目录，添加文件处理器
    if log_dir:
        # 确保日志目录存在
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 创建文件处理器
        file_handler = logging.FileHandler(os.path.join(log_dir, 'news_podcast.log'))
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)
    
    return logger 