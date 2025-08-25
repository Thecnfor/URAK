"""博客API路由"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.services.blog import BlogService
from app.models.blog import BlogDataResponse, ArticleResponse, CategoryResponse
from app.core.database import db_manager

router = APIRouter()
blog_service = BlogService(db_manager)


@router.get("/blog-data", response_model=BlogDataResponse)
async def get_blog_data():
    """获取完整的博客数据
    
    Returns:
        BlogDataResponse: 包含所有分类和文章的博客数据
    """
    try:
        data = await blog_service.get_blog_data()
        
        response_data = {
            "success": True,
            "data": data,
            "message": "博客数据获取成功",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return JSONResponse(
            status_code=200,
            content=response_data,
            headers={
                "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
                "Content-Type": "application/json; charset=utf-8"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "BLOG_DATA_ERROR",
                "message": "获取博客数据失败",
                "details": {"error": str(e)}
            }
        )


@router.get("/articles/{category}/{article_id}", response_model=ArticleResponse)
async def get_article(
    category: str,
    article_id: str
):
    """获取指定文章详情
    
    Args:
        category: 分类标识符
        article_id: 文章ID
        
    Returns:
        ArticleResponse: 文章详细信息
    """
    try:
        article = await blog_service.get_article_content(category, article_id)
        
        if not article:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "ARTICLE_NOT_FOUND",
                    "message": f"文章 '{article_id}' 在分类 '{category}' 中不存在",
                    "details": {"category": category, "article_id": article_id}
                }
            )
        
        response_data = {
            "success": True,
            "data": article,
            "message": "文章获取成功",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return JSONResponse(
            status_code=200,
            content=response_data,
            headers={
                "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
                "Content-Type": "application/json; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "ARTICLE_ERROR",
                "message": "获取文章失败",
                "details": {"error": str(e)}
            }
        )


@router.get("/categories/{category}", response_model=CategoryResponse)
async def get_category(
    category: str
):
    """获取指定分类详情
    
    Args:
        category: 分类标识符
        
    Returns:
        CategoryResponse: 分类详细信息
    """
    try:
        category_data = await blog_service.get_category_content(category)
        
        if not category_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "CATEGORY_NOT_FOUND",
                    "message": f"分类 '{category}' 不存在",
                    "details": {"category": category}
                }
            )
        
        response_data = {
            "success": True,
            "data": category_data,
            "message": "分类获取成功",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return JSONResponse(
            status_code=200,
            content=response_data,
            headers={
                "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
                "Content-Type": "application/json; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "CATEGORY_ERROR",
                "message": "获取分类失败",
                "details": {"error": str(e)}
            }
        )


@router.get("/categories")
async def get_categories_list():
    """获取所有分类列表
    
    Returns:
        dict: 分类列表信息
    """
    try:
        data = await blog_service.get_blog_data()
        
        response_data = {
            "success": True,
            "data": {
                "blogInfoPool": data.get("categories", {})
            },
            "message": "分类列表获取成功",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return JSONResponse(
            status_code=200,
            content=response_data,
            headers={
                "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
                "Content-Type": "application/json; charset=utf-8"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "CATEGORIES_LIST_ERROR",
                "message": "获取分类列表失败",
                "details": {"error": str(e)}
            }
        )


@router.get("/scan")
async def force_scan():
    """强制重新扫描文档目录
    
    Returns:
        dict: 扫描结果信息
    """
    try:
        # 清除缓存并重新扫描
        await blog_service.clear_cache()
        data = await blog_service.get_blog_data()
        
        response_data = {
            "success": True,
            "data": {
                "message": "文件重新扫描完成",
                "categories_found": len(data.get("categories", {})),
                "scan_time": datetime.utcnow().isoformat() + "Z"
            },
            "message": "扫描完成",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return JSONResponse(
            status_code=200,
            content=response_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SCAN_ERROR",
                "message": "强制扫描失败",
                "details": {"error": str(e)}
            }
        )