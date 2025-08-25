"""用户模型和认证逻辑"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import DatabaseManager
from app.models.db_models import User as DBUser, LoginLog, UserSession as DBUserSession

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    EDITOR = "editor"
    USER = "user"
    GUEST = "guest"


class UserStatus(str, Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"



class UserRepository:
    """用户数据仓库 - 使用数据库存储"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def create_user(self, username: str, email: str, password: str, 
                         role: UserRole = UserRole.USER) -> DBUser:
        """创建新用户"""
        async with self.db_manager.get_session() as session:
            # 检查用户名是否已存在
            existing_user = await self.get_user_by_username(username, session)
            if existing_user:
                raise ValueError(f"用户名 '{username}' 已存在")
            
            # 检查邮箱是否已存在
            existing_email = await self.get_user_by_email(email, session)
            if existing_email:
                raise ValueError(f"邮箱 '{email}' 已存在")
            
            # 生成密码盐值
            salt = str(uuid.uuid4())[:32]
            
            user = DBUser(
                id=str(uuid.uuid4()),
                username=username,
                email=email,
                password_hash=pwd_context.hash(password),
                salt=salt,
                role=role.value,
                status=UserStatus.ACTIVE.value,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    async def get_user_by_id(self, user_id: str, session: Optional[AsyncSession] = None) -> Optional[DBUser]:
        """根据ID获取用户"""
        if session is None:
            async with self.db_manager.get_session() as session:
                return await self._get_user_by_id(user_id, session)
        else:
            return await self._get_user_by_id(user_id, session)
    
    async def _get_user_by_id(self, user_id: str, session: AsyncSession) -> Optional[DBUser]:
        """内部方法：根据ID获取用户"""
        result = await session.execute(
            select(DBUser).where(DBUser.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str, session: Optional[AsyncSession] = None) -> Optional[DBUser]:
        """根据用户名获取用户"""
        if session is None:
            async with self.db_manager.get_session() as session:
                return await self._get_user_by_username(username, session)
        else:
            return await self._get_user_by_username(username, session)
    
    async def _get_user_by_username(self, username: str, session: AsyncSession) -> Optional[DBUser]:
        """内部方法：根据用户名获取用户"""
        result = await session.execute(
            select(DBUser).where(DBUser.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str, session: Optional[AsyncSession] = None) -> Optional[DBUser]:
        """根据邮箱获取用户"""
        if session is None:
            async with self.db_manager.get_session() as session:
                return await self._get_user_by_email(email, session)
        else:
            return await self._get_user_by_email(email, session)
    
    async def _get_user_by_email(self, email: str, session: AsyncSession) -> Optional[DBUser]:
        """内部方法：根据邮箱获取用户"""
        result = await session.execute(
            select(DBUser).where(DBUser.email == email)
        )
        return result.scalar_one_or_none()
    
    async def update_user(self, user: DBUser) -> None:
        """更新用户信息"""
        async with self.db_manager.get_session() as session:
            user.updated_at = datetime.utcnow()
            session.add(user)
            await session.commit()
    
    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        async with self.db_manager.get_session() as session:
            user = await self._get_user_by_id(user_id, session)
            if user:
                await session.delete(user)
                await session.commit()
                return True
            return False
    
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[DBUser]:
        """获取用户列表"""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(DBUser)
                .order_by(DBUser.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
    
    async def authenticate_user(self, username: str, password: str, 
                               ip_address: str = "", user_agent: str = "") -> Optional[DBUser]:
        """用户认证"""
        async with self.db_manager.get_session() as session:
            user = await self._get_user_by_username(username, session)
            
            # 创建登录日志
            login_log = LoginLog(
                id=str(uuid.uuid4()),
                user_id=user.id if user else None,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                created_at=datetime.utcnow()
            )
            
            if not user:
                login_log.failure_reason = "用户不存在"
                session.add(login_log)
                await session.commit()
                return None
            
            if not user.is_active or user.status != UserStatus.ACTIVE.value:
                login_log.failure_reason = "用户已被禁用"
                session.add(login_log)
                await session.commit()
                return None
            
            if not pwd_context.verify(password, user.password_hash):
                login_log.failure_reason = "密码错误"
                session.add(login_log)
                await session.commit()
                return None
            
            # 认证成功
            login_log.success = True
            user.last_login = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            
            session.add(login_log)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            return user
    
    async def create_session(self, user: DBUser, ip_address: str = "", 
                            user_agent: str = "") -> DBUserSession:
        """创建用户会话"""
        async with self.db_manager.get_session() as session:
            # 清理过期会话
            await self._cleanup_expired_sessions(user.id, session)
            
            user_session = DBUserSession(
                id=str(uuid.uuid4()),
                user_id=user.id,
                session_id=str(uuid.uuid4()),
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.utcnow() + timedelta(hours=24),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(user_session)
            await session.commit()
            await session.refresh(user_session)
            
            return user_session
    
    async def get_session(self, session_token: str) -> Optional[DBUserSession]:
        """获取会话"""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(DBUserSession)
                .where(
                    and_(
                        DBUserSession.session_id == session_token,
                        DBUserSession.is_active == True,
                        DBUserSession.expires_at > datetime.utcnow()
                    )
                )
                .options(selectinload(DBUserSession.user))
            )
            return result.scalar_one_or_none()
    
    async def revoke_session(self, session_token: str) -> bool:
        """撤销会话"""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(DBUserSession)
                .where(DBUserSession.session_id == session_token)
            )
            user_session = result.scalar_one_or_none()
            
            if user_session:
                user_session.is_active = False
                user_session.updated_at = datetime.utcnow()
                session.add(user_session)
                await session.commit()
                return True
            return False
    
    async def _cleanup_expired_sessions(self, user_id: str, session: AsyncSession) -> None:
        """清理过期会话"""
        await session.execute(
            select(DBUserSession)
            .where(
                and_(
                    DBUserSession.user_id == user_id,
                    or_(
                        DBUserSession.expires_at <= datetime.utcnow(),
                        DBUserSession.is_active == False
                    )
                )
            )
        )
        
        # 删除过期会话
        expired_sessions = await session.execute(
            select(DBUserSession)
            .where(
                and_(
                    DBUserSession.user_id == user_id,
                    DBUserSession.expires_at <= datetime.utcnow()
                )
            )
        )
        
        for expired_session in expired_sessions.scalars():
            await session.delete(expired_session)
    
    async def get_login_logs(self, user_id: str, limit: int = 50) -> List[LoginLog]:
        """获取用户登录日志"""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(LoginLog)
                .where(LoginLog.user_id == user_id)
                .order_by(LoginLog.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
    
    async def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[DBUserSession]:
        """获取用户会话列表"""
        async with self.db_manager.get_session() as session:
            query = select(DBUserSession).where(DBUserSession.user_id == user_id)
            
            if active_only:
                query = query.where(
                    and_(
                        DBUserSession.is_active == True,
                        DBUserSession.expires_at > datetime.utcnow()
                    )
                )
            
            result = await session.execute(
                query.order_by(DBUserSession.created_at.desc())
            )
            return result.scalars().all()
    
    async def update_session(self, session_obj: DBUserSession) -> bool:
        """更新用户会话"""
        try:
            async with self.db_manager.get_session() as session:
                # 合并会话对象到当前会话
                session.add(session_obj)
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            return False

# 创建全局用户仓库实例的工厂函数
def create_user_repository(db_manager: DatabaseManager) -> UserRepository:
    """创建用户仓库实例"""
    return UserRepository(db_manager)

# 为了保持向后兼容性，导出User类
User = DBUser

# 创建全局用户仓库实例
from app.core.database import db_manager
user_repository = create_user_repository(db_manager)