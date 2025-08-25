"""数据库监控API端点"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from app.core.database import get_db_session, db_manager
from app.core.monitoring import db_monitor, query_profiler, health_checker
from app.services.auth import get_current_user, require_admin
from app.models.user import User

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

class MonitoringResponse(BaseModel):
    """监控响应模型"""
    timestamp: datetime
    data: Dict[str, Any]
    status: str = "success"

class PerformanceMetrics(BaseModel):
    """性能指标模型"""
    avg_query_time: float
    total_queries: int
    slow_queries: int
    connection_pool_usage: float
    active_connections: int
    idle_connections: int

class HealthStatus(BaseModel):
    """健康状态模型"""
    database_connected: bool
    connection_pool_healthy: bool
    query_performance: str
    overall_status: str
    last_check: datetime

@router.get("/dashboard", response_model=MonitoringResponse)
async def get_monitoring_dashboard(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
):
    """获取监控仪表板数据"""
    try:
        # 获取数据库管理器的监控数据
        monitoring_data = await db_manager.get_monitoring_data()
        
        # 获取查询性能统计
        query_stats = db_monitor.get_performance_summary()
        
        # 获取连接池状态
        pool_status = db_manager.get_pool_status()
        
        # 获取健康检查结果
        health_status = await db_manager.health_check()
        
        dashboard_data = {
            "database_status": monitoring_data,
            "query_performance": query_stats,
            "connection_pool": pool_status,
            "health_check": health_status,
            "timestamp": datetime.now()
        }
        
        return MonitoringResponse(
            timestamp=datetime.now(),
            data=dashboard_data
        )
        
    except Exception as e:
        logger.error(f"获取监控仪表板数据失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取监控数据失败: {str(e)}"
        )

@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    hours: int = 24,
    current_user: User = Depends(require_admin)
):
    """获取性能指标"""
    try:
        # 获取指定时间范围内的性能统计
        since = datetime.now() - timedelta(hours=hours)
        
        # 从监控器获取性能数据
        performance_data = db_monitor.get_performance_summary(since=since)
        
        # 获取连接池状态
        pool_status = db_manager.get_pool_status()
        
        metrics = PerformanceMetrics(
            avg_query_time=performance_data.get('avg_query_time', 0.0),
            total_queries=performance_data.get('total_queries', 0),
            slow_queries=performance_data.get('slow_queries', 0),
            connection_pool_usage=pool_status.get('usage_percentage', 0.0),
            active_connections=pool_status.get('checked_out', 0),
            idle_connections=pool_status.get('checked_in', 0)
        )
        
        return metrics
        
    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取性能指标失败: {str(e)}"
        )

@router.get("/health", response_model=HealthStatus)
async def get_health_status(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
):
    """获取数据库健康状态"""
    try:
        # 执行健康检查
        health_result = await db_manager.health_check()
        
        # 获取连接池状态
        pool_status = db_manager.get_pool_status()
        
        # 获取查询性能状态
        performance_data = db_monitor.get_performance_summary()
        avg_query_time = performance_data.get('avg_query_time', 0.0)
        
        # 判断查询性能状态
        if avg_query_time < 0.1:
            query_performance = "excellent"
        elif avg_query_time < 0.5:
            query_performance = "good"
        elif avg_query_time < 1.0:
            query_performance = "fair"
        else:
            query_performance = "poor"
        
        # 判断整体状态
        overall_status = "healthy"
        if not health_result.get('database_connected', False):
            overall_status = "critical"
        elif pool_status.get('usage_percentage', 0) > 90:
            overall_status = "warning"
        elif query_performance in ['fair', 'poor']:
            overall_status = "warning"
        
        status = HealthStatus(
            database_connected=health_result.get('database_connected', False),
            connection_pool_healthy=pool_status.get('usage_percentage', 0) < 90,
            query_performance=query_performance,
            overall_status=overall_status,
            last_check=datetime.now()
        )
        
        return status
        
    except Exception as e:
        logger.error(f"获取健康状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取健康状态失败: {str(e)}"
        )

@router.get("/slow-queries")
async def get_slow_queries(
    limit: int = 10,
    hours: int = 24,
    current_user: User = Depends(require_admin)
):
    """获取慢查询列表"""
    try:
        # 获取慢查询数据
        slow_queries = await db_manager.get_slow_queries(limit=limit)
        
        return {
            "slow_queries": slow_queries,
            "total_count": len(slow_queries),
            "time_range_hours": hours,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"获取慢查询失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取慢查询失败: {str(e)}"
        )

@router.get("/connection-pool")
async def get_connection_pool_status(
    current_user: User = Depends(require_admin)
):
    """获取连接池状态"""
    try:
        pool_status = db_manager.get_pool_status()
        
        return {
            "pool_status": pool_status,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"获取连接池状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取连接池状态失败: {str(e)}"
        )

@router.get("/query-stats")
async def get_query_statistics(
    hours: int = 24,
    current_user: User = Depends(require_admin)
):
    """获取查询统计信息"""
    try:
        since = datetime.now() - timedelta(hours=hours)
        
        # 获取查询统计
        query_stats = db_monitor.get_performance_summary(since=since)
        
        # 获取查询分析数据
        query_analysis = query_profiler.get_analysis_summary()
        
        return {
            "query_statistics": query_stats,
            "query_analysis": query_analysis,
            "time_range_hours": hours,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"获取查询统计失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取查询统计失败: {str(e)}"
        )

@router.post("/reset-stats")
async def reset_monitoring_stats(
    current_user: User = Depends(require_admin)
):
    """重置监控统计数据"""
    try:
        # 重置监控器统计
        db_monitor.reset_stats()
        
        # 重置查询分析器统计
        query_profiler.reset_stats()
        
        return {
            "success": True,
            "message": "监控统计数据已重置",
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"重置监控统计失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"重置监控统计失败: {str(e)}"
        )

@router.get("/alerts")
async def get_monitoring_alerts(
    current_user: User = Depends(require_admin)
):
    """获取监控告警信息"""
    try:
        alerts = []
        
        # 检查连接池使用率
        pool_status = db_manager.get_pool_status()
        pool_usage = pool_status.get('usage_percentage', 0)
        
        if pool_usage > 90:
            alerts.append({
                "type": "warning",
                "message": f"连接池使用率过高: {pool_usage:.1f}%",
                "timestamp": datetime.now(),
                "severity": "high" if pool_usage > 95 else "medium"
            })
        
        # 检查查询性能
        performance_data = db_monitor.get_performance_summary()
        avg_query_time = performance_data.get('avg_query_time', 0.0)
        
        if avg_query_time > 1.0:
            alerts.append({
                "type": "warning",
                "message": f"平均查询时间过长: {avg_query_time:.3f}s",
                "timestamp": datetime.now(),
                "severity": "high" if avg_query_time > 2.0 else "medium"
            })
        
        # 检查慢查询数量
        slow_query_count = performance_data.get('slow_queries', 0)
        total_queries = performance_data.get('total_queries', 1)
        slow_query_ratio = slow_query_count / total_queries if total_queries > 0 else 0
        
        if slow_query_ratio > 0.1:  # 超过10%的查询是慢查询
            alerts.append({
                "type": "warning",
                "message": f"慢查询比例过高: {slow_query_ratio:.1%}",
                "timestamp": datetime.now(),
                "severity": "medium"
            })
        
        return {
            "alerts": alerts,
            "alert_count": len(alerts),
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"获取监控告警失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取监控告警失败: {str(e)}"
        )