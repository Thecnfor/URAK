# API接口功能总结

## 概述
本文档总结了从测试文件中提取的API接口功能，确保在删除测试文件后API功能的连续性。

## 核心API接口

### 1. 健康检查接口
**端点**: `GET /health`
- **功能**: 检查服务器状态和数据源健康状况
- **响应**: 包含服务状态、时间戳、数据源信息

### 2. 博客数据接口
**端点**: `GET /api/blog-data`
- **功能**: 获取完整的博客数据，包括所有分类和文章信息
- **缓存策略**: `Cache-Control: public, s-maxage=60, stale-while-revalidate=300`
- **数据源优先级**:
  1. 优先读取 `docs/blog-data.json` 文件
  2. 备用自动扫描 `docs/categories` 目录

### 3. 文章详情接口
**端点**: `GET /api/articles/{category}/{articleId}`
- **功能**: 获取指定分类下的特定文章详细内容
- **支持**: 结构化内容和普通内容

### 4. 分类详情接口
**端点**: `GET /api/categories/{category}`
- **功能**: 获取指定分类的详细信息和文章列表

### 5. 分类列表接口
**端点**: `GET /api/categories`
- **功能**: 获取所有可用分类的列表

### 6. 强制扫描接口
**端点**: `GET /api/scan`
- **功能**: 强制重新扫描文档目录，更新缓存数据

## 数据结构规范

### 统一响应格式
```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 错误响应格式
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 文章对象结构
```typescript
interface Article {
  id: string;
  title: string;
  category?: string;
  publishDate: string;
  content: string;
  structuredContent?: {
    title: string;
    sections: Section[];
    conclusion?: string;
  };
}
```

### 分类对象结构
```typescript
interface Category {
  title: string;
  description?: string;
  articles: Record<string, Article>;
}
```

## 核心功能实现要点

### 1. 文件扫描机制
- 优先扫描结构化内容目录 `docs/content`
- 降级扫描传统分类目录 `docs/categories`
- 支持缓存机制，TTL为60秒

### 2. 数据源优先级
1. JSON文件数据源 (`docs/blog-data.json`)
2. 自动文件扫描
3. 错误处理和降级方案

### 3. CORS和缓存配置
- 支持跨域访问 (`Access-Control-Allow-Origin: *`)
- ISR缓存策略 (`s-maxage=60, stale-while-revalidate=300`)
- 内存缓存机制

### 4. 错误处理
- HTTP状态码标准化
- 统一错误响应格式
- 详细错误信息记录

## 部署配置

### 启动参数
- 默认端口: 8000
- 支持自定义端口和文档目录
- 支持调试模式

### 环境要求
- Python 3.13+
- FastAPI框架
- uv包管理器

### 目录结构要求
```
docs/
├── blog-data.json          # 主数据文件
├── content/                # 结构化内容目录
└── categories/             # 传统分类目录
    ├── tech/
    ├── life/
    └── research/
```

## 性能优化要点

1. **缓存策略**: 内存缓存 + HTTP缓存
2. **数据源优化**: JSON文件优先，目录扫描备用
3. **错误处理**: 完善的异常处理机制
4. **CORS支持**: 支持前端跨域访问

## 迁移到FastAPI的注意事项

1. **路由结构**: 使用FastAPI的路由装饰器
2. **依赖注入**: 利用FastAPI的依赖注入系统
3. **数据验证**: 使用Pydantic模型进行数据验证
4. **文档生成**: 自动生成OpenAPI文档
5. **异步支持**: 考虑异步文件操作
6. **中间件**: 实现CORS和缓存中间件

---

**生成时间**: 2024-01-20  
**来源**: unified_blog_api.py, API_DOCUMENTATION.md  
**状态**: 待迁移到FastAPI实现