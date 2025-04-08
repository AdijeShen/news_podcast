# 新闻播客生成器

这个项目是一个自动化新闻采集、分析和发布系统，可以收集各种科技新闻源的内容，使用大语言模型进行分析和整合，生成全球科技日报，并支持发布到微信公众号。

## 主要功能

1. **新闻采集**：从多个科技新闻源收集最新的科技新闻
2. **内容分析**：使用大语言模型（DeepSeek）对新闻进行深度分析
3. **日报生成**：整合各个新闻源的内容，生成全球科技日报
4. **微信发布**：将生成的日报转换为HTML并发布到微信公众号

## 环境配置

### 依赖安装

```bash
uv pip install -r requirements.txt
```

### 环境变量

在项目根目录创建一个`.env`文件，配置以下环境变量：

```
# LLM API配置
ARK_API_KEY=your_api_key
ARK_BASE_URL=your_base_url
ARK_MODEL=your_model_name

# 微信公众号配置
WECHAT_APPID=your_wechat_appid
WECHAT_SECRET=your_wechat_secret
```

## 使用方法

### 运行新闻采集和分析

```bash
uv run python -m src.news_podcast.main
```

### 测试微信发布功能

```bash
uv run pytest tests/test_wechat_publisher.py -v
```

## 微信发布功能

### 主要流程

1. 生成全球科技日报Markdown文件后，系统会自动调用微信发布功能
2. 使用DeepSeek从内容中提取标题和摘要
3. 将Markdown内容转换为微信公众号兼容的HTML
4. 获取微信公众号access_token
5. 创建草稿并发布到微信公众号

### 创建草稿与直接发布

系统支持两种发布模式：
1. **创建草稿模式**：仅创建草稿，需要手动登录微信公众号后台进行审核发布
2. **直接发布模式**：创建草稿后立即提交发布，无需手动操作

### 手动发布到微信

#### 仅创建草稿

```python
from src.news_podcast.wechat_publisher import process_daily_news

# 假设时间戳为20230401
timestamp = "20230401"
media_id = process_daily_news(timestamp)
print(f"成功创建草稿，media_id: {media_id}")
```

#### 直接发布

```python
from src.news_podcast.wechat_publisher import process_daily_news

# 假设时间戳为20230401
timestamp = "20230401"
publish_id = process_daily_news(timestamp, auto_publish=True)
print(f"成功发布，publish_id: {publish_id}")
```

### 使用测试脚本发布现有文件

#### 创建草稿

```bash
uv run python test_publish_example.py 20250408/global_tech_daily_20250408.md
```

#### 直接发布

```bash
uv run python test_publish_example.py 20250408/global_tech_daily_20250408.md --publish
```

## 目录结构

```
├── src/
│   └── news_podcast/
│       ├── api/
│       │   ├── llm_client.py      # 大语言模型客户端
│       │   └── wechat_client.py   # 微信公众号API客户端
│       ├── crawlers/              # 网页爬虫
│       ├── models/                # 数据模型
│       ├── utils/                 # 工具函数
│       ├── main.py                # 主程序入口
│       ├── podcast_creator.py     # 播客生成逻辑
│       └── wechat_publisher.py    # 微信发布模块
├── tests/                         # 测试文件
├── .env                           # 环境变量
├── requirements.txt               # 项目依赖
└── README.md                      # 项目说明
```

## 注意事项

1. 微信公众号API有调用频率限制，请确保不要过于频繁地调用
2. 发布前请确保内容符合微信公众号的规范要求
3. 需要预先上传一些图片素材到微信公众号后台，用于文章封面图片
4. 使用直接发布功能时，会绕过微信公众平台的人工审核，请确保内容符合规范，避免违规发布
5. 系统仅适用于已获得发布权限的认证公众号，非认证公众号只能通过后台手动发布 