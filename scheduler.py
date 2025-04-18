"""
定时任务脚本，在指定时间自动运行播客生成程序
"""
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
import schedule

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_podcast():
    """
    运行播客生成程序
    """
    try:
        logger.info("开始运行播客生成程序...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 使用 Python 解释器运行 run_podcast.py，实时输出日志
        process = subprocess.Popen(
            [sys.executable, "run_podcast.py"],
            cwd=current_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 实时读取并记录输出
        while True:
            stdout_line = process.stdout.readline()
            stderr_line = process.stderr.readline()
            
            if stdout_line:
                logger.info(f"子任务输出: {stdout_line.strip()}")
            
            if stderr_line:
                logger.error(f"子任务错误: {stderr_line.strip()}")
                
            # 检查进程是否结束
            if process.poll() is not None:
                # 读取剩余输出
                for line in process.stdout:
                    logger.info(f"子任务输出: {line.strip()}")
                for line in process.stderr:
                    logger.error(f"子任务错误: {line.strip()}")
                break
        
        return_code = process.poll()
        if return_code == 0:
            logger.info("播客生成程序运行成功")
        else:
            logger.error(f"播客生成程序运行失败，错误代码: {return_code}")
        
        return return_code == 0
    except Exception as e:
        logger.error(f"运行播客生成程序时发生错误: {e}", exc_info=True)
        return False

def main():
    """
    主函数，设置定时任务
    """
    logger.info("定时任务启动")
    
    # 设置每天下午3点运行
    schedule.every().day.at("15:00").do(run_podcast)
    
    # 如果当前时间已经过了今天的执行时间，则立即执行一次
    now = datetime.now()
    if now.hour >= 15:
        logger.info("当前时间已过今天的执行时间，立即执行一次")
        run_podcast()
    
    # 无限循环，等待定时任务
    logger.info("等待定时任务...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

if __name__ == "__main__":
    main() 