from dataclasses import dataclass
from typing import List

@dataclass
class NewsTask:
    """
    表示一个新闻任务的数据类
    
    属性:
        url: 新闻源URL
        output_file: 输出文件名
        strip_line_header: 要去除的头部行数
        strip_line_bottom: 要去除的尾部行数
        sample_url: 示例URL
        sample_url_output: 示例URL输出格式
    """
    url: str
    output_file: str
    strip_line_header: int
    strip_line_bottom: int
    sample_url: str
    sample_url_output: str 