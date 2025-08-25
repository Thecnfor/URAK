"""SQLAlchemy数据库模型"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, JSON, ForeignKey,
    Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import CHAR, LONGTEXT, MEDIUMTEXT

from app.core.database import Base


class TimestampMixin:
    """时间戳混入类"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="更新时间"
    )


class User(Base, TimestampMixin):
    """用户模型"""
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="用户ID"
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="用户名"
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="邮箱"
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="密码哈希"
    )
    salt: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="密码盐值"
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="user",
        comment="用户角色"
    )
    permissions: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="用户权限"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        comment="用户状态"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否激活"
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后登录时间"
    )
    login_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="登录尝试次数"
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="锁定到期时间"
    )
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="密码修改时间"
    )
    two_factor_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否启用双因子认证"
    )
    two_factor_secret: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="双因子认证密钥"
    )
    session_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="会话数据"
    )
    
    def can_login(self) -> tuple[bool, str]:
        """检查用户是否可以登录"""
        from datetime import datetime, timezone
        
        # 检查用户是否激活
        if not self.is_active:
            return False, "用户账户已被禁用"
        
        # 检查用户状态
        if self.status != "active":
            if self.status == "suspended":
                return False, "用户账户已被暂停"
            elif self.status == "pending":
                return False, "用户账户待激活"
            elif self.status == "inactive":
                return False, "用户账户未激活"
            else:
                return False, "用户账户状态异常"
        
        # 检查账户是否被锁定
        if self.locked_until and self.locked_until > datetime.now(timezone.utc):
            return False, "用户账户已被锁定"
        
        return True, "可以登录"
    
    # 关系
    articles: Mapped[List["Article"]] = relationship(
        "Article",
        back_populates="author",
        cascade="all, delete-orphan"
    )
    login_logs: Mapped[List["LoginLog"]] = relationship(
        "LoginLog",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    user_sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # 约束
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'editor', 'user', 'guest')", name="check_user_role"),
        CheckConstraint("status IN ('active', 'inactive', 'suspended', 'pending')", name="check_user_status"),
        Index("idx_user_status_active", "status", "is_active"),
        Index("idx_user_last_login", "last_login"),
        {"comment": "用户表"}
    )


class Category(Base, TimestampMixin):
    """分类模型"""
    __tablename__ = "categories"
    
    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="分类ID"
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="分类名称"
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="URL别名"
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="分类标题"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="分类描述"
    )
    href: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="链接地址"
    )
    has_submenu: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否有子菜单"
    )
    default_article: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="默认文章"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="排序顺序"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否激活"
    )
    meta_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="元数据"
    )
    
    # 关系
    articles: Mapped[List["Article"]] = relationship(
        "Article",
        back_populates="category",
        cascade="all, delete-orphan"
    )
    
    # 约束
    __table_args__ = (
        Index("idx_category_active_sort", "is_active", "sort_order"),
        {"comment": "分类表"}
    )


class Article(Base, TimestampMixin):
    """文章模型"""
    __tablename__ = "articles"
    
    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="文章ID"
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        comment="文章标题"
    )
    slug: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        comment="URL别名"
    )
    content: Mapped[Optional[str]] = mapped_column(
        LONGTEXT,
        nullable=True,
        comment="文章内容"
    )
    summary: Mapped[Optional[str]] = mapped_column(
        MEDIUMTEXT,
        nullable=True,
        comment="文章摘要"
    )
    publish_date: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="发布日期字符串"
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="发布时间"
    )
    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="标签列表"
    )
    featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否为特色文章"
    )
    published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否已发布"
    )
    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="浏览次数"
    )
    like_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="点赞次数"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="排序顺序"
    )
    blocks: Mapped[Optional[List[dict]]] = mapped_column(
        JSON,
        nullable=True,
        comment="文章块数据"
    )
    meta_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="元数据"
    )
    
    # 外键
    category_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="分类ID"
    )
    author_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="作者ID"
    )
    
    # 关系
    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="articles"
    )
    author: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="articles"
    )
    
    # 约束
    __table_args__ = (
        UniqueConstraint("category_id", "slug", name="uq_article_category_slug"),
        Index("idx_article_published_date", "published", "published_at"),
        Index("idx_article_featured", "featured", "published"),
        Index("idx_article_category_sort", "category_id", "sort_order"),
        {"comment": "文章表"}
    )


class LoginLog(Base, TimestampMixin):
    """登录日志模型"""
    __tablename__ = "login_logs"
    
    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="日志ID"
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        index=True,
        comment="IP地址"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="用户代理"
    )
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="是否成功"
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="失败原因"
    )
    
    # 外键
    user_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID"
    )
    
    # 关系
    user: Mapped["User"] = relationship(
        "User",
        back_populates="login_logs"
    )
    
    # 约束
    __table_args__ = (
        Index("idx_login_log_user_time", "user_id", "created_at"),
        Index("idx_login_log_ip_time", "ip_address", "created_at"),
        {"comment": "登录日志表"}
    )


class UserSession(Base, TimestampMixin):
    """用户会话模型"""
    __tablename__ = "user_sessions"
    
    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="会话ID"
    )
    session_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="会话标识"
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        comment="IP地址"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="用户代理"
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="最后活动时间"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否激活"
    )
    csrf_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="CSRF令牌"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="过期时间"
    )
    
    # 外键
    user_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID"
    )
    
    # 关系
    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_sessions"
    )
    
    # 约束
    __table_args__ = (
        Index("idx_session_user_active", "user_id", "is_active"),
        Index("idx_session_expires", "expires_at"),
        {"comment": "用户会话表"}
    )