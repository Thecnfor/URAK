#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.database import db_manager
from app.models.db_models import Base, User
from passlib.context import CryptContext
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin_user():
    """创建管理员用户"""
    try:
        # 初始化数据库连接
        await db_manager.initialize()
        
        # 创建表
        engine = db_manager.engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # 创建会话并添加管理员用户
        session = db_manager._session_factory()
        try:
            # 检查是否已存在管理员
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.username == 'xrak')
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                # 更新现有用户的密码
                import secrets
                hashed_password = pwd_context.hash("admin123")
                existing_user.password_hash = hashed_password
                await session.commit()
                print("管理员用户密码已更新: xrak/admin123")
                return
            
            # 创建管理员用户
            import secrets
            hashed_password = pwd_context.hash("admin123")
            salt = secrets.token_hex(16)  # 生成随机盐值
            
            admin_user = User(
                username="xrak",
                email="admin@example.com",
                password_hash=hashed_password,
                salt=salt,
                role="admin",
                status="active",
                is_active=True,
                login_attempts=0,
                two_factor_enabled=False
            )
            
            session.add(admin_user)
            await session.commit()
            print("管理员用户创建成功: xrak/kali")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"创建管理员用户失败: {e}")
            raise
        finally:
            await session.close()
            
    except Exception as e:
        logger.error(f"操作失败: {e}")
        raise
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(create_admin_user())