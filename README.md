# 新闻播客生成器

这个项目是一个自动化工具，用于从多个新闻源爬取新闻内容，进行分析和总结，最终生成一份全球科技日报。

## 项目结构

```
news_podcast/
├── src/
│   └── news_podcast/
│       ├── api/               # API相关模块
│       │   ├── __init__.py
│       │   └── llm_client.py  # 大语言模型客户端
│       ├── crawlers/          # 爬虫相关模块
│       │   ├── __init__.py
│       │   └── web_crawler.py # 网页爬虫
│       ├── models/            # 数据模型
│       │   ├── __init__.py
│       │   └── news_task.py   # 新闻任务模型
│       ├── utils/             # 工具模块
│       │   ├── __init__.py
│       │   ├── config_manager.py # 配置管理
│       │   ├── logger.py      # 日志工具
│       │   └── news_processor.py # 新闻处理
│       ├── __init__.py
│       ├── main.py            # 主程序入口
│       └── podcast_creator.py # 播客生成逻辑
├── tests/                     # 测试目录
│   ├── __init__.py
│   ├── conftest.py            # pytest配置
│   └── test_crawler.py        # 爬虫测试
├── .env                       # 环境变量配置
├── .env.example               # 环境变量示例
├── README.md                  # 项目说明
├── requirements.txt           # 依赖列表
├── run_podcast.py             # 运行脚本
├── run_test.py                # 测试运行脚本
├── pytest.ini                 # pytest配置
└── sources.yaml               # 新闻源配置
```

## 功能特点

1. 多源新闻爬取：支持从多个新闻源网站爬取内容
2. 智能新闻筛选：使用大语言模型从众多新闻中筛选重要内容
3. 深度分析：对选中的新闻进行深度分析和解读
4. 综合日报：将多个新闻分析整合为一份完整的科技日报
5. 模块化设计：各功能模块独立，易于扩展和维护

## 安装与配置

1. 克隆项目
```bash
git clone <repository-url>
cd news_podcast
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
从`.env.example`复制得到`.env`文件，并填写必要的API密钥等信息：
```
ARK_MODEL=<your-llm-model>
ARK_API_KEY=<your-api-key>
ARK_BASE_URL=<api-base-url>
```

4. 配置新闻源
编辑`sources.yaml`文件，配置需要爬取的新闻源信息。

## 使用方法

运行主程序:
```bash
python run_podcast.py
```

这将执行以下步骤:
1. 从配置的新闻源爬取首页内容
2. 分析首页提取重要新闻链接
3. 爬取这些重要新闻的详细内容
4. 对每篇新闻进行深度分析
5. 整合所有分析生成一份全球科技日报

结果将保存在以当前日期命名的目录中，如`20250408/global_tech_daily_20250408.md`。

## 运行测试

本项目使用pytest进行测试。有多种方式运行测试：

### 使用pytest命令运行所有测试

```bash
pytest
```

### 使用项目提供的测试脚本运行测试

```bash
python run_test.py
```

### 运行特定测试文件

```bash
pytest tests/test_crawler.py
```

### 运行自定义URL的爬虫测试

```bash
python run_test.py --url "https://example.com" --output "example_output.md"
```

## 新闻源配置说明

在`sources.yaml`中，可以按以下格式配置新闻源:

```yaml
news_dict:
  - url: "https://news-website.com"
    output_file: "news_website"
    strip_line_header: 80  # 去除头部无用行
    strip_line_bottom: 64  # 去除尾部无用行
    sample_url: "示例URL格式"
    sample_url_output: "期望输出格式"
```

## 扩展与定制

1. 添加新的新闻源：编辑`sources.yaml`文件
2. 修改分析提示：调整`news_processor.py`中的prompt
3. 定制输出格式：修改`podcast_creator.py`中的整合逻辑

## 依赖项

- Python 3.8+
- OpenAI API
- crawl4ai
- dotenv
- pyyaml
- pytest 
- pytest-asyncio 