"""Pydantic响应模型和数据传输对象"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = Field(..., description="请求是否成功")
    message: str = Field(..., description="响应消息")
    timestamp: str = Field(..., description="响应时间戳")


class ErrorResponse(BaseResponse):
    """错误响应模型"""
    error: Dict[str, Any] = Field(..., description="错误详情")


# 用户相关模型
class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    role: str = Field(default="user", description="用户角色")
    is_active: bool = Field(default=True, description="是否激活")


class UserCreate(UserBase):
    """创建用户模型"""
    password: str = Field(..., min_length=8, description="密码")


class UserUpdate(BaseModel):
    """更新用户模型"""
    username: Optional[str] = Field(None, description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    role: Optional[str] = Field(None, description="用户角色")
    is_active: Optional[bool] = Field(None, description="是否激活")


class UserResponse(UserBase):
    """用户响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="用户ID")
    status: str = Field(..., description="用户状态")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class LoginResponse(BaseResponse):
    """登录响应模型"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    user: UserResponse = Field(..., description="用户信息")


# 分类相关模型
class CategoryBase(BaseModel):
    """分类基础模型"""
    name: str = Field(..., description="分类名称")
    slug: str = Field(..., description="URL别名")
    title: str = Field(..., description="分类标题")
    description: Optional[str] = Field(None, description="分类描述")
    href: str = Field(..., description="链接地址")
    has_submenu: bool = Field(default=True, description="是否有子菜单")
    default_article: Optional[str] = Field(None, description="默认文章")
    sort_order: int = Field(default=0, description="排序顺序")
    is_active: bool = Field(default=True, description="是否激活")


class CategoryCreate(CategoryBase):
    """创建分类模型"""
    pass


class CategoryUpdate(BaseModel):
    """更新分类模型"""
    name: Optional[str] = Field(None, description="分类名称")
    slug: Optional[str] = Field(None, description="URL别名")
    title: Optional[str] = Field(None, description="分类标题")
    description: Optional[str] = Field(None, description="分类描述")
    href: Optional[str] = Field(None, description="链接地址")
    has_submenu: Optional[bool] = Field(None, description="是否有子菜单")
    default_article: Optional[str] = Field(None, description="默认文章")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    is_active: Optional[bool] = Field(None, description="是否激活")


class CategoryResponse(CategoryBase):
    """分类响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="分类ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


# 文章相关模型
class ArticleBase(BaseModel):
    """文章基础模型"""
    title: str = Field(..., description="文章标题")
    slug: str = Field(..., description="URL别名")
    content: Optional[str] = Field(None, description="文章内容")
    summary: Optional[str] = Field(None, description="文章摘要")
    publish_date: Optional[str] = Field(None, description="发布日期字符串")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")
    featured: bool = Field(default=False, description="是否为特色文章")
    published: bool = Field(default=True, description="是否已发布")
    sort_order: int = Field(default=0, description="排序顺序")


class ArticleCreate(ArticleBase):
    """创建文章模型"""
    category_id: str = Field(..., description="分类ID")
    author_id: Optional[str] = Field(None, description="作者ID")


class ArticleUpdate(BaseModel):
    """更新文章模型"""
    title: Optional[str] = Field(None, description="文章标题")
    slug: Optional[str] = Field(None, description="URL别名")
    content: Optional[str] = Field(None, description="文章内容")
    summary: Optional[str] = Field(None, description="文章摘要")
    publish_date: Optional[str] = Field(None, description="发布日期字符串")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    featured: Optional[bool] = Field(None, description="是否为特色文章")
    published: Optional[bool] = Field(None, description="是否已发布")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    category_id: Optional[str] = Field(None, description="分类ID")


class ArticleResponse(ArticleBase):
    """文章响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="文章ID")
    category_id: str = Field(..., description="分类ID")
    author_id: Optional[str] = Field(None, description="作者ID")
    published_at: Optional[datetime] = Field(None, description="发布时间")
    view_count: int = Field(default=0, description="浏览次数")
    like_count: int = Field(default=0, description="点赞次数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    blocks: Optional[List[Dict[str, Any]]] = Field(None, description="文章块数据")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    
    # 关联数据
    category: Optional[CategoryResponse] = Field(None, description="分类信息")
    author: Optional[UserResponse] = Field(None, description="作者信息")


# 兼容旧版本的模型（保持与原blog-data.json结构兼容）
class LegacyArticle(BaseModel):
    """兼容旧版本的文章模型"""
    id: str = Field(..., description="文章ID")
    title: str = Field(..., description="文章标题")
    publishDate: str = Field(..., description="发布日期")
    content: str = Field(..., description="文章内容")
    blocks: List[Dict[str, Any]] = Field(default_factory=list, description="文章块")


class LegacyCategory(BaseModel):
    """兼容旧版本的分类模型"""
    title: str = Field(..., description="分类标题")
    href: str = Field(..., description="链接地址")
    hasSubmenu: bool = Field(..., description="是否有子菜单")
    defaultArticle: Optional[str] = Field(None, description="默认文章")
    articles: Dict[str, LegacyArticle] = Field(default_factory=dict, description="文章列表")


class LegacyBlogData(BaseModel):
    """兼容旧版本的博客数据模型"""
    categories: Dict[str, LegacyCategory] = Field(default_factory=dict, description="分类数据")


# 博客数据响应模型
class BlogDataResponse(BaseResponse):
    """博客数据响应模型"""
    data: LegacyBlogData = Field(..., description="博客数据")


class ArticleListResponse(BaseResponse):
    """文章列表响应模型"""
    data: List[ArticleResponse] = Field(..., description="文章列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页")
    size: int = Field(..., description="每页大小")


class CategoryListResponse(BaseResponse):
    """分类列表响应模型"""
    data: List[CategoryResponse] = Field(..., description="分类列表")
    total: int = Field(..., description="总数量")


# 健康检查模型
class HealthData(BaseModel):
    """健康检查数据模型"""
    status: str = Field(..., description="服务状态")
    service: str = Field(..., description="服务名称")
    version: str = Field(..., description="服务版本")
    timestamp: str = Field(..., description="检查时间")
    uptime: float = Field(..., description="运行时间")
    environment: Dict[str, str] = Field(..., description="环境配置")
    data_sources: Dict[str, Any] = Field(..., description="数据源状态")
    database: Dict[str, Any] = Field(..., description="数据库状态")


class HealthResponse(BaseResponse):
    """健康检查响应模型"""
    data: HealthData = Field(..., description="健康检查数据")


# 扫描结果模型
class ScanResult(BaseModel):
    """扫描结果模型"""
    message: str = Field(..., description="扫描消息")
    categories_found: int = Field(..., description="发现的分类数量")
    articles_migrated: int = Field(..., description="迁移的文章数量")
    scan_time: str = Field(..., description="扫描时间")


class ScanResponse(BaseResponse):
    """扫描响应模型"""
    data: ScanResult = Field(..., description="扫描结果")