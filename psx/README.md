# URAK Blog API Backend

基于 FastAPI 的博客后端服务，为 URAK 双站协同架构提供 API 支持。

## 项目架构

```
psx/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        # 配置管理
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── health.py    # 健康检查
│   │       └── blog.py      # 博客API
│   ├── models/
│   │   ├── __init__.py
│   │   └── blog.py          # 数据模型
│   └── services/
│       ├── __init__.py
│       └── blog.py          # 业务逻辑
├── docs/
│   └── api_summary.md       # API接口文档
├── main.py                  # 应用启动入口
├── pyproject.toml          # 项目配置
├── .env.example            # 环境变量示例
└── README.md               # 项目文档
```

## 技术栈

- **框架**: FastAPI 0.104+
- **ASGI服务器**: Uvicorn
- **数据验证**: Pydantic 2.5+
- **配置管理**: Pydantic Settings
- **数据存储**: JSON 文件
- **包管理**: UV

## 快速开始

### 环境要求

- Python 3.8+
- UV 包管理器

### 安装依赖

```bash
# 安装生产依赖
uv sync

# 安装开发依赖
uv sync --dev
```

### 环境配置

```bash
# 复制环境变量文件
cp .env.example .env

# 编辑配置（可选）
# 默认配置已适用于开发环境
```

### 启动服务

```bash
# 开发模式启动
uv run python main.py

# 或使用脚本启动
uv run start

# 生产模式启动
DEBUG=false uv run python main.py
```

服务将在 `http://localhost:8000` 启动

## API 接口

### 核心端点

- `GET /health` - 健康检查
- `GET /api/v1/blog-data` - 获取完整博客数据
- `GET /api/v1/articles/{category}/{article_id}` - 获取文章详情
- `GET /api/v1/categories/{category}` - 获取分类详情
- `GET /api/v1/categories` - 获取分类列表
- `GET /api/v1/scan` - 强制重新扫描

### API 文档

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 数据结构

### 目录结构要求

```
../docs/
├── categories/
│   ├── tech/
│   │   ├── config.json      # 分类配置（可选）
│   │   ├── article1.md
│   │   └── article2.md
│   └── life/
│       ├── article3.md
│       └── article4.md
├── content/                 # 额外内容目录
└── blog-data.json          # 缓存数据文件
```

### 文章格式

支持 Markdown 文件，可包含 YAML frontmatter：

```markdown
---
title: "文章标题"
author: "作者"
date: "2024-01-01"
tags: ["标签1", "标签2"]
summary: "文章摘要"
---

# 文章内容

这里是文章正文...
```

## 开发指南

### 代码规范

```bash
# 代码格式化
uv run black .
uv run isort .

# 代码检查
uv run flake8
uv run mypy .
```

### 测试

```bash
# 运行测试
uv run pytest

# 测试覆盖率
uv run pytest --cov=app
```

### 性能优化

- 启用缓存机制（默认60秒TTL）
- 支持 CORS 跨域请求
- 响应压缩和缓存头设置
- 异步文件操作

## 部署

### 生产环境

```bash
# 设置生产环境变量
export DEBUG=false
export LOG_LEVEL=WARNING
export SECRET_KEY=your-production-secret-key

# 启动服务
uv run python main.py
```

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync --frozen

EXPOSE 8000
CMD ["uv", "run", "python", "main.py"]
```

## 监控

### 健康检查

```bash
curl http://localhost:8000/health
```

### 日志

- 应用日志：控制台输出
- 访问日志：Uvicorn 自动记录
- 错误追踪：FastAPI 异常处理

## 故障排除

### 常见问题

1. **端口占用**：修改 `.env` 中的 `PORT` 配置
2. **文件权限**：确保对 `docs` 目录有读写权限
3. **依赖冲突**：使用 `uv sync --refresh` 重新安装

### 调试模式

```bash
# 启用详细日志
LOG_LEVEL=DEBUG uv run python main.py
```

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交代码（遵循代码规范）
4. 创建 Pull Request

## 许可证

MIT License