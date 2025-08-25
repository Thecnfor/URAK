#!/usr/bin/env python3
"""数据库初始化脚本"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json
import uuid
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import DatabaseManager, db_manager, init_database, close_database
from app.core.config import settings
from app.core.backup import backup_manager
from app.core.monitoring import db_monitor
from app.models.db_models import (
    Base, User, Category, Article, LoginLog, UserSession
)
from sqlalchemy import text
from passlib.context import CryptContext
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class DatabaseInitializer:
    """数据库初始化器"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.docs_dir = Path(settings.DOCS_DIR)
        self.categories_dir = Path(settings.CATEGORIES_DIR)
        self.blog_data_file = Path(settings.BLOG_DATA_FILE)
    
    async def initialize(self):
        """初始化数据库"""
        try:
            logger.info("开始初始化数据库...")
            
            # 初始化数据库连接
            await self.db_manager.initialize()
            
            # 执行数据库健康检查
            await self.health_check()
            
            # 创建所有表
            await self.create_tables()
            
            # 创建默认管理员用户
            await self.create_admin_user()
            
            # 创建初始备份
            await self.create_initial_backup()
            
            # 迁移现有数据
            await self.migrate_existing_data()
            
            logger.info("数据库初始化完成！")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
        finally:
            await self.db_manager.close()
    
    async def health_check(self):
        """执行数据库健康检查"""
        try:
            logger.info("执行数据库健康检查...")
            health_status = await self.db_manager.health_check()
            
            if health_status.get('database_connected'):
                logger.info("数据库连接正常")
            else:
                logger.error("数据库连接异常")
                raise Exception("数据库健康检查失败")
                
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            raise
    
    async def create_initial_backup(self):
        """创建初始备份"""
        try:
            logger.info("创建初始数据库备份...")
            
            async with self.db_manager.get_session() as session:
                backup_file = await backup_manager.create_full_backup(
                    session, 
                    backup_name="initial_setup"
                )
                logger.info(f"初始备份创建成功: {backup_file}")
                
        except Exception as e:
            logger.warning(f"创建初始备份失败: {e}")
            # 备份失败不应该阻止初始化过程
    
    async def create_tables(self):
        """创建数据库表"""
        print("创建数据库表...")
        
        async with self.db_manager.get_session() as session:
            # 获取数据库引擎
            engine = session.get_bind()
            
            # 创建所有表
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            print("数据库表创建完成")
    
    async def create_admin_user(self):
        """创建默认管理员用户"""
        print("创建默认管理员用户...")
        
        async with self.db_manager.get_session() as session:
            # 检查是否已存在管理员用户
            result = await session.execute(
                text("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            )
            admin_count = result.scalar()
            
            if admin_count == 0:
                # 创建默认管理员
                admin_user = User(
                    id=str(uuid.uuid4()),
                    username="admin",
                    email="admin@example.com",
                    password_hash=pwd_context.hash("admin123"),
                    role="admin",
                    status="active",
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                session.add(admin_user)
                await session.commit()
                print(f"创建管理员用户: {admin_user.username}")
            else:
                print("管理员用户已存在，跳过创建")
    
    async def migrate_existing_data(self):
        """迁移现有数据"""
        print("开始迁移现有数据...")
        
        # 迁移分类和文章数据
        await self.migrate_blog_data()
        
        # 迁移用户数据（如果存在）
        await self.migrate_user_data()
        
        print("数据迁移完成")
    
    async def migrate_blog_data(self):
        """迁移博客数据"""
        print("迁移博客数据...")
        
        # 检查blog-data.json是否存在
        if not self.blog_data_file.exists():
            print(f"博客数据文件不存在: {self.blog_data_file}")
            return
        
        try:
            # 读取blog-data.json
            with open(self.blog_data_file, 'r', encoding='utf-8') as f:
                blog_data = json.load(f)
            
            async with self.db_manager.get_session() as session:
                categories_migrated = 0
                articles_migrated = 0
                
                # 迁移分类和文章
                for category_key, category_data in blog_data.get('categories', {}).items():
                    # 检查分类是否已存在
                    result = await session.execute(
                        text("SELECT COUNT(*) FROM categories WHERE slug = :slug"),
                        {"slug": category_key}
                    )
                    
                    if result.scalar() == 0:
                        # 创建分类
                        category = Category(
                            id=str(uuid.uuid4()),
                            name=category_key,
                            slug=category_key,
                            title=category_data.get('title', category_key),
                            description=f"从{category_key}迁移的分类",
                            href=category_data.get('href', f'/{category_key}'),
                            has_submenu=category_data.get('hasSubmenu', True),
                            default_article=category_data.get('defaultArticle'),
                            sort_order=categories_migrated,
                            is_active=True,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                            metadata={"migrated_from": "blog-data.json"}
                        )
                        
                        session.add(category)
                        await session.flush()  # 获取category.id
                        categories_migrated += 1
                        
                        # 迁移该分类下的文章
                        for article_key, article_data in category_data.get('articles', {}).items():
                            # 检查文章是否已存在
                            result = await session.execute(
                                text("SELECT COUNT(*) FROM articles WHERE slug = :slug"),
                                {"slug": article_key}
                            )
                            
                            if result.scalar() == 0:
                                article = Article(
                                    id=str(uuid.uuid4()),
                                    title=article_data.get('title', article_key),
                                    slug=article_key,
                                    content=article_data.get('content', ''),
                                    summary=article_data.get('content', '')[:200] if article_data.get('content') else '',
                                    publish_date=article_data.get('publishDate'),
                                    tags=[],
                                    featured=False,
                                    published=True,
                                    sort_order=articles_migrated,
                                    category_id=category.id,
                                    author_id=None,
                                    published_at=datetime.utcnow(),
                                    view_count=0,
                                    like_count=0,
                                    created_at=datetime.utcnow(),
                                    updated_at=datetime.utcnow(),
                                    blocks=article_data.get('blocks', []),
                                    metadata={"migrated_from": "blog-data.json"}
                                )
                                
                                session.add(article)
                                articles_migrated += 1
                
                await session.commit()
                print(f"迁移完成: {categories_migrated} 个分类, {articles_migrated} 篇文章")
                
        except Exception as e:
            print(f"迁移博客数据失败: {e}")
    
    async def migrate_user_data(self):
        """迁移用户数据"""
        print("检查用户数据...")
        
        users_file = self.docs_dir / "authentic" / "users.json"
        if not users_file.exists():
            print("用户数据文件不存在，跳过用户数据迁移")
            return
        
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
            
            async with self.db_manager.get_session() as session:
                users_migrated = 0
                
                for user_data in users_data:
                    # 检查用户是否已存在
                    result = await session.execute(
                        text("SELECT COUNT(*) FROM users WHERE username = :username"),
                        {"username": user_data.get('username')}
                    )
                    
                    if result.scalar() == 0:
                        user = User(
                            id=user_data.get('id', str(uuid.uuid4())),
                            username=user_data.get('username'),
                            email=user_data.get('email', f"{user_data.get('username')}@example.com"),
                            password_hash=user_data.get('password_hash', ''),
                            role=user_data.get('role', 'user'),
                            status=user_data.get('status', 'active'),
                            is_active=user_data.get('is_active', True),
                            last_login=None,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        
                        session.add(user)
                        users_migrated += 1
                
                await session.commit()
                print(f"迁移完成: {users_migrated} 个用户")
                
        except Exception as e:
            print(f"迁移用户数据失败: {e}")
    
    async def drop_tables(self):
        """删除所有表（危险操作）"""
        print("警告: 即将删除所有数据库表！")
        confirm = input("请输入 'YES' 确认删除: ")
        
        if confirm != 'YES':
            print("操作已取消")
            return
        
        async with self.db_manager.get_session() as session:
            engine = session.get_bind()
            
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            
            print("所有表已删除")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库初始化脚本')
    parser.add_argument('--drop', action='store_true', help='删除所有表')
    parser.add_argument('--reset', action='store_true', help='重置数据库（删除后重新创建）')
    
    args = parser.parse_args()
    
    initializer = DatabaseInitializer()
    
    try:
        if args.drop:
            await initializer.drop_tables()
        elif args.reset:
            await initializer.drop_tables()
            await initializer.initialize()
        else:
            await initializer.initialize()
    except Exception as e:
        print(f"操作失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())