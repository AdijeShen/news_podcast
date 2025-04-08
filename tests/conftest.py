"""
Pytest配置文件
"""
import os
import sys
import pytest

# 确保可以正确导入src目录下的模块
sys.path.insert(0, os.path.abspath('.'))

# 明确设置pytest-asyncio为默认的异步测试模式
pytest_plugins = ["pytest_asyncio"]

# 设置默认的asyncio模式
def pytest_configure(config):
    """配置pytest-asyncio默认模式"""
    config.addinivalue_line("asyncio_mode", "auto") 