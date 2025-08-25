"""FastAPI应用主入口"""

import asyncio
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from app.api.v1 import blog, health
from app.api.auth import router as auth_router, get_current_user
from app.api.backup import router as backup_router
from app.api.monitoring import router as monitoring_router
from app.core.config import settings
from app.core.thread_pool import thread_pool
from app.services.auth import auth_service
from app.services.audit import audit_logger
from app.models.user import user_repository
from app.core.security import security_config

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Security headers middleware
class SecurityHeadersMiddleware:
    """Add security headers to all responses."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    
                    # Security headers
                    security_headers = {
                        b"x-content-type-options": b"nosniff",
                        b"x-frame-options": b"DENY",
                        b"x-xss-protection": b"1; mode=block",
                        b"strict-transport-security": b"max-age=31536000; includeSubDomains",
                        b"content-security-policy": b"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
                        b"referrer-policy": b"strict-origin-when-cross-origin",
                        b"permissions-policy": b"geolocation=(), microphone=(), camera=()"
                    }
                    
                    # Add security headers
                    for key, value in security_headers.items():
                        headers[key] = value
                    
                    message["headers"] = list(headers.items())
                
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)

# Cleanup task
async def cleanup_expired_tokens():
    """Background task to cleanup expired tokens."""
    while True:
        try:
            # Cleanup expired tokens every hour
            await asyncio.sleep(3600)
            
            # Cleanup expired tokens
            cleaned_count = auth_service.cleanup_expired_tokens()
            
            if cleaned_count > 0:
                from app.services.audit import AuditEventType, AuditSeverity
                audit_logger.log_event(
                    event_type=AuditEventType.SYSTEM_START,
                    severity=AuditSeverity.LOW,
                    action="token_cleanup",
                    result="success",
                    ip_address="127.0.0.1",
                    user_agent="system",
                    details={"cleaned_tokens": cleaned_count}
                )
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            from app.services.audit import AuditEventType, AuditSeverity
            audit_logger.log_event(
                event_type=AuditEventType.SYSTEM_START,
                severity=AuditSeverity.MEDIUM,
                action="token_cleanup",
                result="failed",
                ip_address="127.0.0.1",
                user_agent="system",
                details={"error": str(e)}
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    from app.services.audit import AuditEventType, AuditSeverity
    from app.core.database import init_database, close_database
    
    # 启动时执行
    print("🚀 URAK Blog API 服务启动中...")
    print(f"📊 初始化动态线程池 (工作线程: {thread_pool._current_workers})")
    thread_pool.start_monitoring()
    
    # Initialize security components
    try:
        # Initialize database first
        await init_database()
        print(f"💾 数据库已初始化")
        
        # Security configuration is already loaded in SecurityConfig.__init__
        print(f"🔐 安全配置已加载")
        
        # Initialize user repository (already loaded in __init__)
        print(f"👤 用户存储库已初始化")
        
        # Start cleanup tasks
        cleanup_task = asyncio.create_task(cleanup_expired_tokens())
        print(f"🧹 清理任务已启动")
        
        # Log server startup
        audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_START,
            severity=AuditSeverity.LOW,
            action="server_startup",
            result="success",
            ip_address="127.0.0.1",
            user_agent="system",
            details={"timestamp": datetime.now(timezone.utc).isoformat()}
        )
        
        print(f"🔒 安全认证系统已就绪!")
        
    except Exception as e:
        print(f"❌ 安全系统初始化失败: {e}")
        audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_START,
            severity=AuditSeverity.CRITICAL,
            action="server_startup",
            result="failed",
            ip_address="127.0.0.1",
            user_agent="system",
            details={"error": str(e)}
        )
        raise
    
    yield
    
    # 关闭时执行
    print("🛑 URAK Blog API 服务正在关闭...")
    
    # Cancel cleanup task
    if 'cleanup_task' in locals():
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    
    # Log server shutdown
    audit_logger.log_event(
        event_type=AuditEventType.SYSTEM_SHUTDOWN,
        severity=AuditSeverity.LOW,
        action="server_shutdown",
        result="success",
        ip_address="127.0.0.1",
        user_agent="system",
        details={"timestamp": datetime.now(timezone.utc).isoformat()}
    )
    
    # Close database
    await close_database()
    print("💾 数据库连接已关闭")
    
    thread_pool.shutdown()
    print("✅ 资源清理完成，服务已退出")


# 创建FastAPI应用实例
app = FastAPI(
    title="URAK Blog API with Security",
    description="URAK 博客系统后端API服务 - 集成安全认证",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS + ["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token"]
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

# 注册路由
app.include_router(health.router, tags=["健康检查"])
app.include_router(blog.router, prefix="/api", tags=["博客"])
app.include_router(auth_router, tags=["认证"])
app.include_router(backup_router, tags=["备份管理"])
app.include_router(monitoring_router, tags=["数据库监控"])


@app.middleware("http")
async def add_process_time_header(request, call_next):
    """添加响应时间头"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Global HTTP exception handler with audit logging."""
    
    # Get client info
    ip_address = (
        request.headers.get("X-Forwarded-For", "")
        or request.headers.get("X-Real-IP", "")
        or request.client.host
        or "unknown"
    )
    
    if "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
    
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # Log security-related exceptions
    if exc.status_code in [401, 403, 429]:
        from app.services.audit import AuditEventType, AuditSeverity
        severity = AuditSeverity.MEDIUM if exc.status_code == 429 else AuditSeverity.HIGH
        
        audit_logger.log_event(
            event_type=AuditEventType.ACCESS_DENIED,
            severity=severity,
            action=f"http_{exc.status_code}",
            result="failed",
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": str(request.url.path),
                "method": request.method
            }
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """404错误处理"""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "请求的资源不存在",
                "details": {"path": str(request.url.path)}
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """500错误处理"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {}
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    
    # Get client info
    ip_address = (
        request.headers.get("X-Forwarded-For", "")
        or request.headers.get("X-Real-IP", "")
        or request.client.host
        or "unknown"
    )
    
    if "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
    
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # Log unhandled exception
    from app.services.audit import AuditEventType, AuditSeverity
    audit_logger.log_event(
        event_type=AuditEventType.ERROR_OCCURRED,
        severity=AuditSeverity.CRITICAL,
        action="unhandled_exception",
        result="failed",
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "path": str(request.url.path),
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.get("/")
@limiter.limit("5/minute")
async def root(request: Request):
    """根路径"""
    return {
        "success": True,
        "data": {
            "message": "URAK Blog API 服务正在运行 - 安全认证已启用",
            "version": "1.0.0",
            "docs": "/docs",
            "redoc": "/redoc",
            "auth": "/api/auth",
            "security": "enabled"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/thread-pool/status")
@limiter.limit("10/minute")
async def get_thread_pool_status(request: Request):
    """获取线程池状态"""
    return {
        "success": True,
        "data": thread_pool.get_status(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/api/thread-pool/adjust/{new_size}")
@limiter.limit("5/minute")
async def adjust_thread_pool(new_size: int, request: Request, current_user: dict = Depends(get_current_user)):
    """手动调整线程池大小 - 需要管理员权限"""
    # Check admin permission
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    success = thread_pool.manual_adjust(new_size)
    
    if success:
        # Log admin action
        from app.services.audit import AuditEventType, AuditSeverity
        audit_logger.log_event(
            event_type=AuditEventType.CONFIGURATION_CHANGE,
            severity=AuditSeverity.MEDIUM,
            user_id=current_user.get("user_id"),
            action="thread_pool_adjust",
            result="success",
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent", "unknown"),
            details={
                "new_size": new_size,
                "status": thread_pool.get_status()
            }
        )
        
        return {
            "success": True,
            "message": f"线程池大小已调整为 {new_size}",
            "data": thread_pool.get_status(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    else:
        # Log failed attempt
        from app.services.audit import AuditEventType, AuditSeverity
        audit_logger.log_event(
            event_type=AuditEventType.CONFIGURATION_CHANGE,
            severity=AuditSeverity.LOW,
            user_id=current_user.get("user_id"),
            action="thread_pool_adjust",
            result="failed",
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent", "unknown"),
            details={
                "new_size": new_size,
                "error": "invalid_size"
            }
        )
        
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": f"无效的线程池大小: {new_size}，必须在 {settings.THREAD_POOL_MIN_WORKERS}-{settings.THREAD_POOL_MAX_WORKERS} 之间",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )