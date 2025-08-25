"""数据库连接和会话管理模块"""

import logging
import hashlib
import secrets
from typing import AsyncGenerator, Optional, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import QueuePool, StaticPool, NullPool
from sqlalchemy import event, text
from sqlalchemy.exc import DisconnectionError, OperationalError
from cryptography.fernet import Fernet

from app.core.config import settings
from .monitoring import db_monitor, ConnectionMetrics

logger = logging.getLogger(__name__)


class DatabaseSecurity:
    """数据库安全管理器"""
    
    def __init__(self):
        self._connection_attempts: Dict[str, int] = {}
        self._blocked_ips: Dict[str, datetime] = {}
        self._max_attempts = 5
        self._block_duration = timedelta(minutes=15)
        self._query_log: Dict[str, int] = {}
        self._suspicious_queries = 0
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """检查IP是否被阻止"""
        if ip_address in self._blocked_ips:
            block_time = self._blocked_ips[ip_address]
            if datetime.now() - block_time < self._block_duration:
                return True
            else:
                # 解除阻止
                del self._blocked_ips[ip_address]
                if ip_address in self._connection_attempts:
                    del self._connection_attempts[ip_address]
        return False
    
    def record_connection_attempt(self, ip_address: str, success: bool) -> None:
        """记录连接尝试"""
        if success:
            # 成功连接，清除失败记录
            if ip_address in self._connection_attempts:
                del self._connection_attempts[ip_address]
            return
        
        # 失败连接，增加计数
        self._connection_attempts[ip_address] = self._connection_attempts.get(ip_address, 0) + 1
        
        if self._connection_attempts[ip_address] >= self._max_attempts:
            self._blocked_ips[ip_address] = datetime.now()
            logger.warning(f"IP {ip_address} 因连接失败次数过多被阻止")
    
    def get_secure_connection_params(self) -> Dict[str, Any]:
        """获取安全连接参数"""
        return {
            "charset": settings.DB_CHARSET,
            "autocommit": False,
        }
    
    def validate_query(self, query: str) -> bool:
        """验证查询安全性"""
        # 简单的SQL注入防护
        dangerous_patterns = [
            "DROP", "DELETE FROM", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE",
            "LOAD_FILE", "INTO OUTFILE", "INTO DUMPFILE", "UNION SELECT", "--", "/*", "*/",
            "EXEC", "EXECUTE", "xp_", "sp_", "INFORMATION_SCHEMA", "MYSQL.USER"
        ]
        
        query_upper = query.upper().replace(" ", "")
        for pattern in dangerous_patterns:
            if pattern.replace(" ", "") in query_upper:
                logger.warning(f"检测到潜在的危险查询模式: {pattern}")
                self._suspicious_queries += 1
                return False
        
        return True
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """记录安全事件"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details
        }
        logger.info(f"数据库安全事件: {log_entry}")


class Base(DeclarativeBase):
    """SQLAlchemy声明式基类"""
    pass


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._is_connected = False
        self._security = DatabaseSecurity()
        self._connection_pool_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "pool_hits": 0,
            "pool_misses": 0
        }
    
    async def initialize(self) -> None:
        """初始化数据库连接"""
        try:
            # 获取安全连接参数
            secure_connect_args = self._security.get_secure_connection_params()
            
            # 创建异步引擎，使用适合异步的连接池配置
            self._engine = create_async_engine(
                settings.DATABASE_URL,
                poolclass=NullPool,  # 使用NullPool以支持异步，不使用连接池
                echo=settings.DEBUG,
                connect_args=secure_connect_args,
                # 启用查询缓存和优化
                execution_options={
                    "isolation_level": "READ_COMMITTED",
                    "autocommit": False,
                    "compiled_cache": {},  # 启用查询编译缓存
                }
            )
            
            # 创建会话工厂
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            # 注册事件监听器
            self._register_event_listeners()
            
            # 测试连接
            await self._test_connection()
            
            self._is_connected = True
            logger.info("数据库连接初始化成功")
            
        except Exception as e:
            logger.error(f"数据库连接初始化失败: {e}")
            raise
    
    def _register_event_listeners(self) -> None:
        """注册数据库事件监听器"""
        if not self._engine:
            return
            
        @event.listens_for(self._engine.sync_engine, "connect")
        def set_mysql_pragma(dbapi_connection, connection_record):
            """设置MySQL连接参数"""
            with dbapi_connection.cursor() as cursor:
                try:
                    # 设置字符集和排序规则
                    cursor.execute(f"SET NAMES {settings.DB_CHARSET} COLLATE {settings.DB_COLLATION}")
                    
                    # 设置时区为UTC
                    cursor.execute("SET time_zone = '+00:00'")
                    
                    # 设置严格的SQL模式
                    cursor.execute("SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER'")
                    
                    # 设置事务隔离级别
                    cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
                    
                    # 禁用自动提交
                    cursor.execute("SET autocommit = 0")
                    
                    # 设置查询缓存
                    cursor.execute("SET SESSION query_cache_type = ON")
                    
                    # 设置最大执行时间（防止长时间运行的查询）
                    cursor.execute("SET SESSION max_execution_time = 30000")  # 30秒
                    
                    # 设置连接超时
                    cursor.execute("SET SESSION wait_timeout = 300")  # 5分钟
                    cursor.execute("SET SESSION interactive_timeout = 300")
                    
                    logger.debug("数据库安全参数设置完成")
                    
                except Exception as e:
                    logger.error(f"设置数据库安全参数失败: {e}")
        
        @event.listens_for(self._engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """连接检出时的处理"""
            self._connection_pool_stats["active_connections"] += 1
            self._connection_pool_stats["pool_hits"] += 1
            logger.debug(f"数据库连接已检出，活跃连接数: {self._connection_pool_stats['active_connections']}")
            
            # 记录安全事件
            self._security.log_security_event("connection_checkout", {
                "connection_id": id(dbapi_connection),
                "active_connections": self._connection_pool_stats["active_connections"]
            })
            
            # 记录连接池监控数据
            pool = self._engine.pool
            try:
                # 尝试获取连接池信息（NullPool不支持这些方法）
                active_conn = pool.checkedout()
                idle_conn = pool.checkedin()
                total_conn = pool.size()
                overflow_conn = pool.overflow()
            except AttributeError:
                # NullPool不支持这些方法，使用默认值
                active_conn = 0
                idle_conn = 0
                total_conn = 0
                overflow_conn = 0
            
            metrics = ConnectionMetrics(
                timestamp=datetime.now(),
                active_connections=active_conn,
                idle_connections=idle_conn,
                total_connections=total_conn,
                pool_size=total_conn,
                overflow=overflow_conn,
                checked_out=active_conn
            )
            db_monitor.record_connection_metrics(metrics)
        
        @event.listens_for(self._engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """连接归还时的处理"""
            self._connection_pool_stats["active_connections"] = max(0, self._connection_pool_stats["active_connections"] - 1)
            logger.debug(f"数据库连接已归还，活跃连接数: {self._connection_pool_stats['active_connections']}")
            
            # 清理临时表和会话变量
            try:
                with dbapi_connection.cursor() as cursor:
                    cursor.execute("SET @temp_var = NULL")
            except Exception as e:
                logger.error(f"连接归还清理失败: {e}")
        
        @event.listens_for(self._engine.sync_engine, "invalidate")
        def receive_invalidate(dbapi_connection, connection_record, exception):
            """连接失效时的处理"""
            logger.warning(f"数据库连接失效: {exception}")
            self._connection_pool_stats["pool_misses"] += 1
            
            # 记录安全事件
            self._security.log_security_event("connection_invalidate", {
                "connection_id": id(dbapi_connection),
                "exception": str(exception)
            })
    
    async def _test_connection(self) -> None:
        """测试数据库连接"""
        if not self._engine:
            raise RuntimeError("数据库引擎未初始化")
        
        try:
            async with self._engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
                logger.info("数据库连接测试成功")
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            raise
    
    async def close(self) -> None:
        """关闭数据库连接"""
        if self._engine:
            # 记录最终连接池统计
            pool_status = self.get_pool_status()
            logger.info(f"数据库关闭前连接池状态: {pool_status}")
            
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._is_connected = False
            logger.info("数据库连接已关闭")
    
    @asynccontextmanager
    async def get_session(self, client_ip: str = None) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话"""
        if not self._session_factory:
            raise RuntimeError("数据库会话工厂未初始化")
        
        # 安全检查
        if client_ip and self._security.is_ip_blocked(client_ip):
            self._security.log_security_event("blocked_connection", {"ip": client_ip})
            raise RuntimeError(f"IP地址 {client_ip} 被阻止访问数据库")
        
        session = self._session_factory()
        try:
            # 记录会话创建
            if client_ip:
                self._security.log_security_event("session_created", {"ip": client_ip})
            yield session
        except Exception as e:
            await session.rollback()
            if client_ip:
                self._security.log_security_event("session_error", {"ip": client_ip, "error": str(e)})
            logger.error(f"数据库会话异常: {e}")
            raise
        finally:
            await session.close()
            if client_ip:
                self._security.log_security_event("session_closed", {"ip": client_ip})
    
    async def get_session_direct(self) -> AsyncSession:
        """直接获取数据库会话（需要手动管理）"""
        if not self._session_factory:
            raise RuntimeError("数据库会话工厂未初始化")
        
        return self._session_factory()
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._is_connected
    
    @property
    def engine(self) -> Optional[AsyncEngine]:
        """获取数据库引擎"""
        return self._engine
    
    def get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态"""
        if not self._engine:
            return {"status": "disconnected"}
        
        pool = self._engine.pool
        status = {
            "status": "connected" if self._is_connected else "disconnected",
            "pool_type": type(pool).__name__,
            "stats": self._connection_pool_stats.copy(),
        }
        
        # NullPool没有这些方法，需要检查
        try:
            status.update({
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
                "total_connections": pool.size() + pool.overflow()
            })
        except AttributeError:
            # NullPool不支持这些方法
            status.update({
                "pool_size": "N/A (NullPool)",
                "checked_in": "N/A",
                "checked_out": "N/A",
                "overflow": "N/A",
                "invalid": "N/A",
                "total_connections": "N/A"
            })
        
        return status
    
    async def health_check(self) -> Dict[str, Any]:
        """数据库健康检查"""
        health_status = {
            "database": "unknown",
            "database_connected": False,
            "connection_pool": "unknown",
            "response_time_ms": None,
            "error": None
        }
        
        try:
            start_time = datetime.now()
            
            # 测试数据库连接
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1 as health_check"))
                assert result.scalar() == 1
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            health_status.update({
                "database": "healthy",
                "database_connected": True,
                "connection_pool": "healthy",
                "response_time_ms": round(response_time, 2)
            })
            
        except Exception as e:
            health_status.update({
                "database": "unhealthy",
                "database_connected": False,
                "connection_pool": "unhealthy",
                "error": str(e)
            })
            logger.error(f"数据库健康检查失败: {e}")
        
        # 添加连接池状态
        health_status["pool_status"] = self.get_pool_status()
        
        return health_status
    
    def validate_query_security(self, query: str) -> bool:
        """验证查询安全性"""
        return self._security.validate_query(query)
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """记录安全事件"""
        self._security.log_security_event(event_type, details)
    
    def get_monitoring_data(self) -> Dict[str, Any]:
        """获取监控数据"""
        from .monitoring import db_monitor
        return {
            "performance_summary": db_monitor.get_performance_summary(),
            "pool_status": self.get_pool_status(),
            "health_status": "healthy" if self.is_connected else "disconnected"
        }
    
    def get_slow_queries(self, limit: int = 10) -> list:
        """获取慢查询列表"""
        from .monitoring import db_monitor
        return [{
            "query_hash": q.query_hash,
            "execution_time": q.execution_time,
            "timestamp": q.timestamp.isoformat(),
            "rows_affected": q.rows_affected,
            "client_ip": q.client_ip
        } for q in db_monitor.get_slow_queries(limit)]


# 全局数据库管理器实例
db_manager = DatabaseManager()

# 全局安全管理器实例
db_security = DatabaseSecurity()


async def get_db_session(client_ip: str = None) -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的便捷函数"""
    async with db_manager.get_session(client_ip=client_ip) as session:
        yield session


async def init_database() -> None:
    """初始化数据库"""
    await db_manager.initialize()


async def close_database() -> None:
    """关闭数据库连接"""
    await db_manager.close()