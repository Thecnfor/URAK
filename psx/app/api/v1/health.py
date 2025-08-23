"""健康检查API路由"""

import os
import time
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services.blog import BlogService

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查端点
    
    Returns:
        dict: 服务健康状态信息
    """
    try:
        # 检查数据源状态
        blog_service = BlogService()
        categories_count = len(await blog_service.scan_categories())
        json_file_exists = os.path.exists(settings.BLOG_DATA_FILE)
        
        health_data = {
            "success": True,
            "data": {
                "status": "healthy",
                "service": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "uptime": time.time(),
                "environment": {
                    "docs_dir": settings.DOCS_DIR,
                    "categories_dir": settings.CATEGORIES_DIR,
                    "content_dir": settings.CONTENT_DIR,
                    "blog_data_file": settings.BLOG_DATA_FILE
                },
                "data_sources": {
                    "categories_from_scan": categories_count,
                    "json_file_exists": json_file_exists,
                    "cache_enabled": settings.CACHE_ENABLED,
                    "cache_ttl": settings.CACHE_TTL
                }
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return JSONResponse(
            status_code=200,
            content=health_data,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except Exception as e:
        error_data = {
            "success": False,
            "error": {
                "code": "HEALTH_CHECK_FAILED",
                "message": "健康检查失败",
                "details": {"error": str(e)}
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return JSONResponse(
            status_code=503,
            content=error_data
        )