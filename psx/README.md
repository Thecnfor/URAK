# URAK Blog API Backend

基于 FastAPI 的现代化博客后端服务，集成 MySQL 数据库、安全认证、性能监控和备份恢复功能。

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
- **数据库**: MySQL 8.0+ / SQLAlchemy 2.0+
- **数据验证**: Pydantic 2.5+
- **认证**: JWT + bcrypt
- **安全**: CSRF保护、数据加密、IP限制
- **监控**: 性能监控、健康检查、慢查询分析
- **备份**: 自动备份、增量备份、定时任务
- **配置管理**: Pydantic Settings
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

# 编辑数据库配置
# 必须配置 MySQL 数据库连接信息
DATABASE_URL=mysql+aiomysql://username:password@localhost:3306/urak_blog
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=urak_blog
DATABASE_USER=your_username
DATABASE_PASSWORD=your_password

# JWT 密钥配置
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# 安全配置
ENCRYPTION_KEY=your-encryption-key-here
CSRF_SECRET_KEY=your-csrf-secret-key
```

### 数据库初始化

```bash
# 初始化数据库（首次运行）
uv run python scripts/init_database.py

# 重置数据库（谨慎使用）
uv run python scripts/init_database.py --reset

# 创建备份
uv run python scripts/backup_manager.py create --type full

# 恢复备份
uv run python scripts/backup_manager.py restore --file backup_file.sql
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

### 默认管理员账户

- 用户名: `admin`
- 密码: `admin123`
- 邮箱: `admin@example.com`

**注意**: 生产环境中请立即修改默认密码！

## API 接口

### 核心端点

- `GET /health` - 健康检查
- `GET /api/v1/blog-data` - 获取完整博客数据
- `GET /api/v1/articles/{category}/{article_id}` - 获取文章详情
- `GET /api/v1/categories/{category}` - 获取分类详情
- `GET /api/v1/categories` - 获取分类列表
- `GET /api/v1/scan` - 强制重新扫描

### 认证端点

- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出
- `POST /api/auth/register` - 用户注册
- `GET /api/auth/me` - 获取当前用户信息
- `PUT /api/auth/me` - 更新用户信息
- `POST /api/auth/change-password` - 修改密码

### 监控端点

- `GET /api/monitoring/dashboard` - 监控仪表板数据
- `GET /api/monitoring/metrics` - 性能指标
- `GET /api/monitoring/health` - 数据库健康状态
- `GET /api/monitoring/slow-queries` - 慢查询列表
- `GET /api/monitoring/pool-status` - 连接池状态
- `GET /api/monitoring/query-stats` - 查询统计
- `POST /api/monitoring/reset-stats` - 重置统计数据

### 备份端点

- `POST /api/backup/create` - 创建备份
- `POST /api/backup/restore` - 恢复备份
- `GET /api/backup/list` - 列出备份文件
- `DELETE /api/backup/cleanup` - 清理旧备份
- `POST /api/backup/schedule/start` - 启动定时备份
- `POST /api/backup/schedule/stop` - 停止定时备份
- `GET /api/backup/schedule/status` - 获取定时备份状态
- `GET /api/backup/health` - 备份系统健康检查

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

### 数据库管理

```bash
# 查看数据库状态
uv run python scripts/init_database.py --health-check

# 创建完整备份
uv run python scripts/backup_manager.py create --type full

# 创建增量备份
uv run python scripts/backup_manager.py create --type incremental

# 启动定时备份服务
uv run python scripts/backup_manager.py schedule --start

# 查看备份列表
uv run python scripts/backup_manager.py list
```

### 性能监控

```bash
# 访问监控仪表板
curl http://localhost:8000/api/monitoring/dashboard

# 查看慢查询
curl http://localhost:8000/api/monitoring/slow-queries

# 查看连接池状态
curl http://localhost:8000/api/monitoring/pool-status
```

### 安全配置

```bash
# 生成新的加密密钥
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 生成JWT密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 生成CSRF密钥
python -c "import secrets; print(secrets.token_hex(32))"
```

### 性能优化

- 启用数据库连接池优化
- 配置慢查询监控
- 使用Redis缓存（可选）
- 启用Gzip压缩
- 配置CDN加速

## 部署指南

### 生产环境配置

```bash
# 生产环境变量
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=INFO

# 数据库配置
DATABASE_URL=mysql+aiomysql://user:pass@prod-db:3306/urak_blog
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# 安全配置
JWT_SECRET_KEY=your-production-secret-key
ENCRYPTION_KEY=your-production-encryption-key
CSRF_SECRET_KEY=your-production-csrf-key
ALLOWED_HOSTS=["yourdomain.com", "api.yourdomain.com"]

# 备份配置
BACKUP_SCHEDULE_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_STORAGE_PATH=/var/backups/urak
```

### Docker 部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync --frozen

EXPOSE 8000
CMD ["uv", "run", "python", "main.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+aiomysql://root:password@db:3306/urak_blog
    depends_on:
      - db
  
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: urak_blog
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"

volumes:
  mysql_data:
```

### 系统要求

- **CPU**: 2核心以上
- **内存**: 4GB以上
- **存储**: 20GB以上（含备份空间）
- **数据库**: MySQL 8.0+
- **Python**: 3.8+

### 监控和日志

- 应用日志: `/var/log/urak/app.log`
- 访问日志: `/var/log/urak/access.log`
- 错误日志: `/var/log/urak/error.log`
- 备份日志: `/var/log/urak/backup.log`

### 故障排除

```bash
# 检查数据库连接
uv run python -c "from app.core.database import db_manager; import asyncio; asyncio.run(db_manager.health_check())"

# 检查备份状态
uv run python scripts/backup_manager.py health

# 查看应用日志
tail -f /var/log/urak/app.log

# 重启服务
sudo systemctl restart urak-api
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v2.0.0 (2024-01-XX)
- 集成 MySQL 数据库支持
- 添加用户认证和授权
- 实现数据库安全和监控
- 添加自动备份和恢复功能
- 性能优化和连接池管理

### v1.0.0 (2024-01-XX)
- 初始版本
- 基础 FastAPI 框架
- JSON 文件存储
- 基本博客 API

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