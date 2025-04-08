# 新闻播客测试

本目录包含新闻播客项目的测试代码。

## 测试结构

- `test_crawler.py`: 爬虫模块测试，包含测试URL爬取功能
- `conftest.py`: pytest配置文件，设置异步测试和导入路径

## 运行测试

有多种方式运行测试:

### 使用pytest命令

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_crawler.py

# 运行特定测试函数
pytest tests/test_crawler.py::test_url_crawl
```

### 使用项目提供的测试脚本

```bash
# 运行所有测试
python run_test.py

# 运行特定测试函数
python run_test.py --specific-test test_url_crawl

# 使用自定义URL运行测试
python run_test.py --url "https://example.com" --output "example_output.md"

# 仅运行自定义URL测试，跳过标准测试
python run_test.py --url "https://example.com" --output "example_output.md" --skip-main-tests
```

## 添加新测试

添加新测试时，请遵循以下规则:

1. 测试文件名以`test_`开头
2. 测试函数名以`test_`开头
3. 对于异步测试，使用`@pytest.mark.asyncio`装饰器
4. 每个测试都应包含断言(assert)来验证结果
5. 测试函数应包含详细的文档字符串，说明测试目的和预期结果 