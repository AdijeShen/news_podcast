"""
启动脚本，用于运行新闻播客生成程序
"""
import asyncio
import os
import sys

# 确保可以正确导入src目录下的模块
sys.path.insert(0, os.path.abspath('.'))

from src.news_podcast.main import main

if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main()) 