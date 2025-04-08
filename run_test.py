"""
测试脚本，用于运行测试功能
"""
import os
import sys
import pytest
import asyncio
from argparse import ArgumentParser

# 确保可以正确导入src目录下的模块
sys.path.insert(0, os.path.abspath('.'))

def parse_args():
    """解析命令行参数"""
    parser = ArgumentParser(description="运行新闻播客测试")
    parser.add_argument("--url", type=str, default="https://time.com/7274542/colossal-dire-wolf/",
                        help="要测试爬取的URL")
    parser.add_argument("--output", type=str, default="custom_test_output.md",
                        help="输出文件路径")
    parser.add_argument("--test-dir", type=str, default="tests",
                        help="测试目录路径")
    parser.add_argument("--test-file", type=str, default="test_crawler.py",
                        help="要运行的测试文件")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="增加输出详细度")
    parser.add_argument("--specific-test", type=str, default=None,
                        help="指定要运行的测试函数名，例如 test_url_crawl")
    parser.add_argument("--skip-main-tests", action="store_true",
                        help="跳过标准测试，仅运行自定义URL测试")
    return parser.parse_args()

def run_pytest_tests(args):
    """使用pytest运行测试"""
    test_path = os.path.join(args.test_dir, args.test_file)
    
    # 构建pytest运行参数
    pytest_args = ["-xvs"]  # x: 在第一个错误处停止；v: 详细模式；s: 不捕获输出
    
    # 如果指定了特定测试，添加到参数中
    if args.specific_test:
        test_path = f"{test_path}::{args.specific_test}"
    
    pytest_args.append(test_path)
        
    # 运行pytest
    return pytest.main(pytest_args)

def run_custom_test(args):
    """运行自定义URL测试"""
    try:
        from tests.test_crawler import test_url_crawl_with_params
        
        print(f"\n开始测试爬取URL: {args.url}")
        print(f"输出文件: {args.output}")
        
        # 运行异步测试
        asyncio.run(test_url_crawl_with_params(args.url, args.output))
        
        print(f"自定义URL测试完成: {args.url}")
    except Exception as e:
        print(f"运行自定义测试时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    return 0

if __name__ == "__main__":
    args = parse_args()
    exit_code = 0
    
    # 运行正常pytest测试
    if not args.skip_main_tests:
        print("\n====== 运行标准测试 ======")
        exit_code = run_pytest_tests(args)
    
    # 如果指定了自定义URL，则运行自定义测试
    if args.url != "https://time.com/7274542/colossal-dire-wolf/":
        print("\n====== 运行自定义URL测试 ======")
        custom_exit_code = run_custom_test(args)
        exit_code = exit_code or custom_exit_code
    
    sys.exit(exit_code) 