"""数据库监控和性能分析模块"""

import time
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

@dataclass
class QueryMetrics:
    """查询性能指标"""
    query_hash: str
    execution_time: float
    rows_affected: int
    timestamp: datetime
    client_ip: Optional[str] = None
    error: Optional[str] = None

@dataclass
class ConnectionMetrics:
    """连接池性能指标"""
    timestamp: datetime
    active_connections: int
    idle_connections: int
    total_connections: int
    pool_size: int
    overflow: int
    checked_out: int

class DatabaseMonitor:
    """数据库监控器"""
    
    def __init__(self, max_metrics_history: int = 1000):
        self.max_metrics_history = max_metrics_history
        self.query_metrics: deque = deque(maxlen=max_metrics_history)
        self.connection_metrics: deque = deque(maxlen=max_metrics_history)
        self.slow_query_threshold = 1.0  # 慢查询阈值（秒）
        self.error_count = defaultdict(int)
        self.query_count = defaultdict(int)
        self._start_time = datetime.now()
    
    def record_query(self, query_metrics: QueryMetrics):
        """记录查询指标"""
        self.query_metrics.append(query_metrics)
        
        # 统计查询次数
        self.query_count[query_metrics.query_hash] += 1
        
        # 记录错误
        if query_metrics.error:
            self.error_count[query_metrics.error] += 1
        
        # 记录慢查询
        if query_metrics.execution_time > self.slow_query_threshold:
            logger.warning(
                f"慢查询检测: {query_metrics.query_hash[:50]}... "
                f"执行时间: {query_metrics.execution_time:.3f}s"
            )
    
    def record_connection_metrics(self, metrics: ConnectionMetrics):
        """记录连接池指标"""
        self.connection_metrics.append(metrics)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.query_metrics:
            return {"status": "no_data"}
        
        recent_queries = list(self.query_metrics)[-100:]  # 最近100个查询
        
        # 计算平均执行时间
        avg_execution_time = sum(q.execution_time for q in recent_queries) / len(recent_queries)
        
        # 慢查询统计
        slow_queries = [q for q in recent_queries if q.execution_time > self.slow_query_threshold]
        
        # 错误率
        error_queries = [q for q in recent_queries if q.error]
        error_rate = len(error_queries) / len(recent_queries) * 100
        
        # 最频繁的查询
        top_queries = sorted(self.query_count.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "uptime": str(datetime.now() - self._start_time),
            "total_queries": len(self.query_metrics),
            "avg_execution_time": round(avg_execution_time, 3),
            "slow_queries_count": len(slow_queries),
            "error_rate": round(error_rate, 2),
            "top_queries": top_queries,
            "recent_errors": dict(list(self.error_count.items())[-5:]),
            "connection_pool_status": self._get_latest_connection_status()
        }
    
    def _get_latest_connection_status(self) -> Optional[Dict[str, Any]]:
        """获取最新连接池状态"""
        if not self.connection_metrics:
            return None
        
        latest = self.connection_metrics[-1]
        return {
            "active": latest.active_connections,
            "idle": latest.idle_connections,
            "total": latest.total_connections,
            "pool_size": latest.pool_size,
            "overflow": latest.overflow,
            "checked_out": latest.checked_out,
            "utilization": round(latest.active_connections / latest.pool_size * 100, 2)
        }
    
    def get_slow_queries(self, limit: int = 10) -> List[QueryMetrics]:
        """获取慢查询列表"""
        slow_queries = [q for q in self.query_metrics if q.execution_time > self.slow_query_threshold]
        return sorted(slow_queries, key=lambda x: x.execution_time, reverse=True)[:limit]
    
    def clear_metrics(self):
        """清空监控数据"""
        self.query_metrics.clear()
        self.connection_metrics.clear()
        self.error_count.clear()
        self.query_count.clear()
        self._start_time = datetime.now()
        logger.info("监控数据已清空")

class QueryProfiler:
    """查询性能分析器"""
    
    def __init__(self, monitor: DatabaseMonitor):
        self.monitor = monitor
    
    async def profile_query(self, session: AsyncSession, query: str, 
                          params: Optional[Dict] = None, client_ip: Optional[str] = None) -> Any:
        """分析查询性能"""
        query_hash = str(hash(query))[:16]
        start_time = time.time()
        error = None
        rows_affected = 0
        
        try:
            if params:
                result = await session.execute(text(query), params)
            else:
                result = await session.execute(text(query))
            
            # 尝试获取影响行数
            try:
                rows_affected = result.rowcount
            except:
                pass
            
            return result
        
        except Exception as e:
            error = str(e)
            logger.error(f"查询执行失败: {query_hash} - {error}")
            raise
        
        finally:
            execution_time = time.time() - start_time
            
            # 记录查询指标
            metrics = QueryMetrics(
                query_hash=query_hash,
                execution_time=execution_time,
                rows_affected=rows_affected,
                timestamp=datetime.now(),
                client_ip=client_ip,
                error=error
            )
            
            self.monitor.record_query(metrics)

class HealthChecker:
    """数据库健康检查器"""
    
    def __init__(self, monitor: DatabaseMonitor):
        self.monitor = monitor
    
    async def check_database_health(self, session: AsyncSession) -> Dict[str, Any]:
        """检查数据库健康状态"""
        health_status = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 基本连接测试
            start_time = time.time()
            await session.execute(text("SELECT 1"))
            connection_time = time.time() - start_time
            
            health_status["checks"]["connection"] = {
                "status": "ok",
                "response_time": round(connection_time * 1000, 2)  # 毫秒
            }
            
            # 检查数据库版本
            result = await session.execute(text("SELECT VERSION()"))
            version = result.scalar()
            health_status["checks"]["version"] = {
                "status": "ok",
                "value": version
            }
            
            # 检查当前连接数
            result = await session.execute(text("SHOW STATUS LIKE 'Threads_connected'"))
            connections = result.fetchone()
            if connections:
                health_status["checks"]["connections"] = {
                    "status": "ok",
                    "active_connections": int(connections[1])
                }
            
            # 检查慢查询
            performance_summary = self.monitor.get_performance_summary()
            if performance_summary.get("error_rate", 0) > 5:  # 错误率超过5%
                health_status["status"] = "warning"
                health_status["checks"]["error_rate"] = {
                    "status": "warning",
                    "value": performance_summary["error_rate"]
                }
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            logger.error(f"数据库健康检查失败: {e}")
        
        return health_status

# 全局监控实例
db_monitor = DatabaseMonitor()
query_profiler = QueryProfiler(db_monitor)
health_checker = HealthChecker(db_monitor)