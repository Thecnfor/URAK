"""API路由模块"""
from .auth import router as auth_router
from .v1.blog import router as blog_router
from .user import router as user_router
from .backup import router as backup_router
from .monitoring import router as monitoring_router