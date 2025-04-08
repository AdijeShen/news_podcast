"""
测试发布现有的全球科技日报到微信公众号
"""
from datetime import datetime
import os
import sys
from dotenv import load_dotenv
import argparse

# 添加src目录到路径，确保能正确导入模块
sys.path.insert(0, os.path.abspath("."))

from src.news_podcast.wechat_publisher import publish_to_wechat

def publish_existing_file(file_path: str, auto_publish: bool = False) -> bool:
    """
    测试发布已有的全球科技日报文件到微信公众号
    
    参数:
        file_path: Markdown文件路径
        auto_publish: 是否直接发布而不只是创建草稿
        
    返回:
        bool: 发布是否成功
    """
    # 加载环境变量
    load_dotenv()
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        return False
    
    action = "发布" if auto_publish else "创建草稿"
    print(f"开始{action}文件: {file_path}")
    
    # 发布到微信公众号
    try:
        result_id = publish_to_wechat(file_path, author="百晓生", auto_publish=auto_publish)
        
        if result_id:
            if auto_publish:
                print(f"发布成功! publish_id: {result_id}")
            else:
                print(f"草稿创建成功! media_id: {result_id}")
            return True
        else:
            print(f"{action}失败!")
            return False
    except Exception as e:
        print(f"{action}过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    # 设置时间戳
    timestamp = datetime.now().strftime("%Y%m%d")
    # 创建参数解析器
    parser = argparse.ArgumentParser(description="将Markdown文件发布到微信公众号")
    parser.add_argument("file_path", help="Markdown文件路径", default=f"{timestamp}/global_tech_daily_{timestamp}.md", nargs="?")
    parser.add_argument("--publish", "-p", action="store_true", help="是否直接发布而不只是创建草稿")
    
    # 解析参数
    args = parser.parse_args()
    
    # 调用测试函数
    publish_existing_file(args.file_path, args.publish) 