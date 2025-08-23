"""FastAPI应用主入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from datetime import datetime

from app.api.v1 import blog, health
from app.core.config import settings

# 创建FastAPI应用实例
app = FastAPI(
    title="URAK Blog API",
    description="URAK 博客系统后端API服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, tags=["健康检查"])
app.include_router(blog.router, prefix="/api", tags=["博客"])


@app.middleware("http")
async def add_process_time_header(request, call_next):
    """添加响应时间头"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


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
            "timestamp": datetime.utcnow().isoformat() + "Z"
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
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


@app.get("/")
async def root():
    """根路径"""
    return {
        "success": True,
        "data": {
            "message": "URAK Blog API 服务正在运行",
            "version": "1.0.0",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )