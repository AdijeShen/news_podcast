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
from flask import Flask
from threading import Thread

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

# 全局状态变量
start_time = datetime.now()
podcast_count = 0
last_run_status = "未运行"
last_error_message = ""

app = Flask(__name__)

def check_podcast_exists():
    """检查今天的播客是否已生成"""
    today = datetime.now().strftime("%Y%m%d")
    target_file = f"{today}/global_tech_daily_{today}.html"
    return os.path.exists(target_file)

@app.route('/')
def status_page():
    uptime = datetime.now() - start_time
    return f"""
    <html>
        <body>
            <h1>播客生成服务状态</h1>
            <p>服务运行时间: {uptime}</p>
            <p>已生成播客次数: {podcast_count}</p>
            <p>最近一次运行状态: {last_run_status}</p>
            <p>错误信息: {last_error_message}</p>
        </body>
    </html>
    """

def run_web_server():
    """运行Web服务器"""
    app.run(host='0.0.0.0', port=80)

def run_podcast():
    """
    运行播客生成程序
    """
    global podcast_count, last_run_status, last_error_message
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
        error_output = []
        while True:
            stdout_line = process.stdout.readline()
            stderr_line = process.stderr.readline()
            
            if stdout_line:
                logger.info(f"子任务输出: {stdout_line.strip()}")
            
            if stderr_line:
                error_msg = stderr_line.strip()
                logger.error(f"子任务错误: {error_msg}")
                error_output.append(error_msg)
                
            # 检查进程是否结束
            if process.poll() is not None:
                # 读取剩余输出
                for line in process.stdout:
                    logger.info(f"子任务输出: {line.strip()}")
                for line in process.stderr:
                    error_msg = line.strip()
                    logger.error(f"子任务错误: {error_msg}")
                    error_output.append(error_msg)
                break
        
        return_code = process.poll()
        if return_code == 0 and check_podcast_exists():
            logger.info("播客生成程序运行成功")
            podcast_count += 1
            last_run_status = "成功"
            last_error_message = ""
        else:
            error_msg = "\n".join(error_output) if error_output else "未知错误"
            logger.error(f"播客生成程序运行失败，错误代码: {return_code}")
            last_run_status = "失败"
            last_error_message = error_msg
        
        return return_code == 0 and check_podcast_exists()
    except Exception as e:
        error_msg = str(e)
        logger.error(f"运行播客生成程序时发生错误: {error_msg}", exc_info=True)
        last_run_status = "错误"
        last_error_message = error_msg
        return False

def check_and_retry():
    """检查是否需要重试生成播客"""
    if not check_podcast_exists():
        logger.info("检测到今日播客未生成，尝试重新生成...")
        run_podcast()

def main():
    """
    主函数，设置定时任务
    """
    logger.info("定时任务启动")
    
    # 启动Web服务器
    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    # 设置每天下午3点运行
    schedule.every().day.at("15:00").do(run_podcast)
    
    # 设置每半小时检查一次
    schedule.every(30).minutes.do(check_and_retry)
    
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