"""博客数据模型"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = Field(..., description="请求是否成功")
    message: str = Field(..., description="响应消息")
    timestamp: str = Field(..., description="响应时间戳")


class ErrorResponse(BaseResponse):
    """错误响应模型"""
    error: Dict[str, Any] = Field(..., description="错误详情")


class Article(BaseModel):
    """文章模型"""
    id: str = Field(..., description="文章ID")
    title: str = Field(..., description="文章标题")
    content: Optional[str] = Field(None, description="文章内容")
    summary: Optional[str] = Field(None, description="文章摘要")
    author: Optional[str] = Field(None, description="作者")
    date: Optional[str] = Field(None, description="发布日期")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")
    category: Optional[str] = Field(None, description="所属分类")
    slug: Optional[str] = Field(None, description="URL别名")
    featured: Optional[bool] = Field(False, description="是否为特色文章")
    published: Optional[bool] = Field(True, description="是否已发布")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class Category(BaseModel):
    """分类模型"""
    id: str = Field(..., description="分类ID")
    name: str = Field(..., description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")
    slug: Optional[str] = Field(None, description="URL别名")
    articles: List[Article] = Field(default_factory=list, description="分类下的文章列表")
    article_count: int = Field(0, description="文章数量")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class BlogData(BaseModel):
    """博客数据模型"""
    categories: Dict[str, Category] = Field(default_factory=dict, description="分类数据")
    total_articles: int = Field(0, description="总文章数")
    total_categories: int = Field(0, description="总分类数")
    last_updated: Optional[str] = Field(None, description="最后更新时间")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class BlogDataResponse(BaseResponse):
    """博客数据响应模型"""
    data: BlogData = Field(..., description="博客数据")


class ArticleResponse(BaseResponse):
    """文章响应模型"""
    data: Article = Field(..., description="文章数据")


class CategoryResponse(BaseResponse):
    """分类响应模型"""
    data: Category = Field(..., description="分类数据")


class HealthData(BaseModel):
    """健康检查数据模型"""
    status: str = Field(..., description="服务状态")
    service: str = Field(..., description="服务名称")
    version: str = Field(..., description="服务版本")
    timestamp: str = Field(..., description="检查时间")
    uptime: float = Field(..., description="运行时间")
    environment: Dict[str, str] = Field(..., description="环境配置")
    data_sources: Dict[str, Any] = Field(..., description="数据源状态")


class HealthResponse(BaseResponse):
    """健康检查响应模型"""
    data: HealthData = Field(..., description="健康检查数据")


class ScanResult(BaseModel):
    """扫描结果模型"""
    message: str = Field(..., description="扫描消息")
    categories_found: int = Field(..., description="发现的分类数量")
    scan_time: str = Field(..., description="扫描时间")


class ScanResponse(BaseResponse):
    """扫描响应模型"""
    data: ScanResult = Field(..., description="扫描结果")