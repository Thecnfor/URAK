"""博客服务模块 - 使用数据库存储"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import asyncio
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import DatabaseManager
from app.models.db_models import Article as DBArticle, Category as DBCategory
from app.models.schemas import (
    BlogDataResponse, ArticleResponse, CategoryResponse,
    LegacyBlogData, LegacyArticle, LegacyCategory
)


class BlogService:
    """博客服务类 - 使用数据库存储"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.docs_dir = Path(settings.DOCS_DIR)
        self.categories_dir = Path(settings.CATEGORIES_DIR)
        self.content_dir = Path(settings.CONTENT_DIR)
        self.blog_data_file = Path(settings.BLOG_DATA_FILE)
        self.executor = ThreadPoolExecutor(max_workers=settings.THREAD_POOL_MAX_WORKERS)
        
    async def get_blog_data(self, force_refresh: bool = False) -> BlogDataResponse:
        """获取博客数据"""
        async with self.db_manager.get_session() as session:
            # 获取所有分类
            categories_result = await session.execute(
                select(DBCategory)
                .where(DBCategory.is_active == True)
                .order_by(DBCategory.order, DBCategory.created_at)
            )
            categories = categories_result.scalars().all()
            
            # 获取所有已发布的文章
            articles_result = await session.execute(
                select(DBArticle)
                .where(DBArticle.status == 'published')
                .options(selectinload(DBArticle.category))
                .order_by(desc(DBArticle.created_at))
            )
            articles = articles_result.scalars().all()
            
            # 转换为响应格式
            category_responses = [
                CategoryResponse(
                    id=cat.id,
                    name=cat.name,
                    description=cat.description or "",
                    slug=cat.slug,
                    color=cat.color or "#007bff",
                    icon=cat.icon or "folder",
                    order=cat.order,
                    is_active=cat.is_active,
                    article_count=len([a for a in articles if a.category_id == cat.id]),
                    created_at=cat.created_at.isoformat(),
                    updated_at=cat.updated_at.isoformat()
                )
                for cat in categories
            ]
            
            article_responses = [
                ArticleResponse(
                    id=art.id,
                    title=art.title,
                    content=art.content,
                    summary=art.summary or "",
                    category_id=art.category_id,
                    category_name=art.category.name if art.category else None,
                    tags=art.tags or [],
                    author=art.author or "Anonymous",
                    status=art.status,
                    is_featured=art.is_featured,
                    view_count=art.view_count,
                    like_count=art.like_count,
                    reading_time=art.reading_time,
                    created_at=art.created_at.isoformat(),
                    updated_at=art.updated_at.isoformat(),
                    published_at=art.published_at.isoformat() if art.published_at else None
                )
                for art in articles
            ]
            
            return BlogDataResponse(
                categories=category_responses,
                articles=article_responses,
                total_articles=len(article_responses),
                total_categories=len(category_responses),
                last_updated=datetime.utcnow().isoformat()
            )
    
    async def get_legacy_blog_data(self) -> LegacyBlogData:
        """获取兼容旧版本格式的博客数据"""
        blog_data = await self.get_blog_data()
        
        # 转换为旧版本格式
        legacy_categories = [
            LegacyCategory(
                id=cat.id,
                name=cat.name,
                description=cat.description,
                slug=cat.slug,
                color=cat.color,
                icon=cat.icon,
                order=cat.order,
                is_active=cat.is_active,
                created_at=cat.created_at,
                updated_at=cat.updated_at
            )
            for cat in blog_data.categories
        ]
        
        legacy_articles = [
            LegacyArticle(
                id=art.id,
                title=art.title,
                content=art.content,
                summary=art.summary,
                category_id=art.category_id,
                category_name=art.category_name,
                tags=art.tags,
                author=art.author,
                status=art.status,
                is_featured=art.is_featured,
                view_count=art.view_count,
                like_count=art.like_count,
                created_at=art.created_at,
                updated_at=art.updated_at,
                published_at=art.published_at,
                reading_time=art.reading_time
            )
            for art in blog_data.articles
        ]
        
        return LegacyBlogData(
            categories=legacy_categories,
            articles=legacy_articles,
            total_articles=blog_data.total_articles,
            total_categories=blog_data.total_categories,
            last_updated=blog_data.last_updated
        )
            
    async def get_article_by_id(self, article_id: str) -> Optional[ArticleResponse]:
        """根据ID获取文章"""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(DBArticle)
                .where(DBArticle.id == article_id)
                .options(selectinload(DBArticle.category))
            )
            article = result.scalar_one_or_none()
            
            if not article:
                return None
            
            return ArticleResponse(
                id=article.id,
                title=article.title,
                content=article.content,
                summary=article.summary or "",
                category_id=article.category_id,
                category_name=article.category.name if article.category else None,
                tags=article.tags or [],
                author=article.author or "Anonymous",
                status=article.status,
                is_featured=article.is_featured,
                view_count=article.view_count,
                like_count=article.like_count,
                reading_time=article.reading_time,
                created_at=article.created_at.isoformat(),
                updated_at=article.updated_at.isoformat(),
                published_at=article.published_at.isoformat() if article.published_at else None
            )
            
    async def get_articles_by_category(self, category_id: str, skip: int = 0, limit: int = 50) -> List[ArticleResponse]:
        """根据分类获取文章"""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(DBArticle)
                .where(
                    and_(
                        DBArticle.category_id == category_id,
                        DBArticle.status == 'published'
                    )
                )
                .options(selectinload(DBArticle.category))
                .order_by(desc(DBArticle.created_at))
                .offset(skip)
                .limit(limit)
            )
            articles = result.scalars().all()
            
            return [
                ArticleResponse(
                    id=art.id,
                    title=art.title,
                    content=art.content,
                    summary=art.summary or "",
                    category_id=art.category_id,
                    category_name=art.category.name if art.category else None,
                    tags=art.tags or [],
                    author=art.author or "Anonymous",
                    status=art.status,
                    is_featured=art.is_featured,
                    view_count=art.view_count,
                    like_count=art.like_count,
                    reading_time=art.reading_time,
                    created_at=art.created_at.isoformat(),
                    updated_at=art.updated_at.isoformat(),
                    published_at=art.published_at.isoformat() if art.published_at else None
                )
                for art in articles
            ]
        
    async def get_featured_articles(self, limit: int = 10) -> List[ArticleResponse]:
        """获取推荐文章"""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(DBArticle)
                .where(
                    and_(
                        DBArticle.is_featured == True,
                        DBArticle.status == 'published'
                    )
                )
                .options(selectinload(DBArticle.category))
                .order_by(desc(DBArticle.created_at))
                .limit(limit)
            )
            articles = result.scalars().all()
            
            return [
                ArticleResponse(
                    id=art.id,
                    title=art.title,
                    content=art.content,
                    summary=art.summary or "",
                    category_id=art.category_id,
                    category_name=art.category.name if art.category else None,
                    tags=art.tags or [],
                    author=art.author or "Anonymous",
                    status=art.status,
                    is_featured=art.is_featured,
                    view_count=art.view_count,
                    like_count=art.like_count,
                    reading_time=art.reading_time,
                    created_at=art.created_at.isoformat(),
                    updated_at=art.updated_at.isoformat(),
                    published_at=art.published_at.isoformat() if art.published_at else None
                )
                for art in articles
            ]
        
    async def search_articles(self, query: str, skip: int = 0, limit: int = 50) -> List[ArticleResponse]:
        """搜索文章"""
        async with self.db_manager.get_session() as session:
            search_term = f"%{query}%"
            
            result = await session.execute(
                select(DBArticle)
                .where(
                    and_(
                        DBArticle.status == 'published',
                        or_(
                            DBArticle.title.ilike(search_term),
                            DBArticle.summary.ilike(search_term),
                            DBArticle.content.ilike(search_term),
                            DBArticle.tags.ilike(search_term)
                        )
                    )
                )
                .options(selectinload(DBArticle.category))
                .order_by(desc(DBArticle.created_at))
                .offset(skip)
                .limit(limit)
            )
            articles = result.scalars().all()
            
            return [
                ArticleResponse(
                    id=art.id,
                    title=art.title,
                    content=art.content,
                    summary=art.summary or "",
                    category_id=art.category_id,
                    category_name=art.category.name if art.category else None,
                    tags=art.tags or [],
                    author=art.author or "Anonymous",
                    status=art.status,
                    is_featured=art.is_featured,
                    view_count=art.view_count,
                    like_count=art.like_count,
                    reading_time=art.reading_time,
                    created_at=art.created_at.isoformat(),
                    updated_at=art.updated_at.isoformat(),
                    published_at=art.published_at.isoformat() if art.published_at else None
                )
                for art in articles
            ]
        
    async def get_categories(self) -> List[CategoryResponse]:
        """获取所有分类"""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(DBCategory)
                .where(DBCategory.is_active == True)
                .order_by(DBCategory.order, DBCategory.created_at)
            )
            categories = result.scalars().all()
            
            # 计算每个分类的文章数量
            category_responses = []
            for cat in categories:
                article_count_result = await session.execute(
                    select(func.count(DBArticle.id))
                    .where(
                        and_(
                            DBArticle.category_id == cat.id,
                            DBArticle.status == 'published'
                        )
                    )
                )
                article_count = article_count_result.scalar()
                
                category_responses.append(
                    CategoryResponse(
                        id=cat.id,
                        name=cat.name,
                        description=cat.description or "",
                        slug=cat.slug,
                        color=cat.color or "#007bff",
                        icon=cat.icon or "folder",
                        order=cat.order,
                        is_active=cat.is_active,
                        article_count=article_count,
                        created_at=cat.created_at.isoformat(),
                        updated_at=cat.updated_at.isoformat()
                    )
                )
            
            return category_responses
        
    async def get_category_by_id(self, category_id: str) -> Optional[CategoryResponse]:
        """根据ID获取分类"""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(DBCategory).where(DBCategory.id == category_id)
            )
            category = result.scalar_one_or_none()
            
            if not category:
                return None
            
            # 计算文章数量
            article_count_result = await session.execute(
                select(func.count(DBArticle.id))
                .where(
                    and_(
                        DBArticle.category_id == category.id,
                        DBArticle.status == 'published'
                    )
                )
            )
            article_count = article_count_result.scalar()
            
            return CategoryResponse(
                id=category.id,
                name=category.name,
                description=category.description or "",
                slug=category.slug,
                color=category.color or "#007bff",
                icon=category.icon or "folder",
                order=category.order,
                is_active=category.is_active,
                article_count=article_count,
                created_at=category.created_at.isoformat(),
                updated_at=category.updated_at.isoformat()
            )


# 创建全局博客服务实例的工厂函数
def create_blog_service(db_manager: DatabaseManager) -> BlogService:
    """创建博客服务实例"""
    return BlogService(db_manager)