"""动态线程池管理器"""

import os
import time
import psutil
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Callable, Any
from dataclasses import dataclass
from app.core.config import settings


@dataclass
class SystemMetrics:
    """系统指标数据类"""
    cpu_percent: float
    memory_percent: float
    active_threads: int
    pending_tasks: int
    timestamp: float


class DynamicThreadPool:
    """动态线程池管理器
    
    根据系统负载和配置自动调整线程池大小
    支持手动调整和监控
    """
    
    def __init__(self):
        self._executor: Optional[ThreadPoolExecutor] = None
        self._current_workers = settings.THREAD_POOL_MIN_WORKERS
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        self._metrics_history = []
        self._last_adjustment = 0
        self._adjustment_cooldown = 10  # 调整冷却时间（秒）
        
        # 初始化线程池
        self._create_executor()
        
    def _create_executor(self):
        """创建新的线程池执行器"""
        if self._executor:
            self._executor.shutdown(wait=False)
            
        self._executor = ThreadPoolExecutor(
            max_workers=self._current_workers,
            thread_name_prefix="URAK-Worker"
        )
        
    def get_system_metrics(self) -> SystemMetrics:
        """获取当前系统指标"""
        return SystemMetrics(
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_percent=psutil.virtual_memory().percent,
            active_threads=threading.active_count(),
            pending_tasks=getattr(self._executor, '_work_queue', type('', (), {'qsize': lambda: 0})).qsize(),
            timestamp=time.time()
        )
        
    def _should_scale_up(self, metrics: SystemMetrics) -> bool:
        """判断是否应该扩容"""
        if self._current_workers >= settings.THREAD_POOL_MAX_WORKERS:
            return False
            
        # CPU或内存负载过高，且有待处理任务
        high_load = (
            metrics.cpu_percent > settings.CPU_THRESHOLD_HIGH or
            metrics.memory_percent > settings.MEMORY_THRESHOLD_HIGH
        )
        
        return high_load and metrics.pending_tasks > 0
        
    def _should_scale_down(self, metrics: SystemMetrics) -> bool:
        """判断是否应该缩容"""
        if self._current_workers <= settings.THREAD_POOL_MIN_WORKERS:
            return False
            
        # CPU和内存负载都较低，且无待处理任务
        low_load = (
            metrics.cpu_percent < settings.CPU_THRESHOLD_LOW and
            metrics.memory_percent < settings.CPU_THRESHOLD_LOW
        )
        
        return low_load and metrics.pending_tasks == 0
        
    def _adjust_pool_size(self, new_size: int, reason: str = "auto"):
        """调整线程池大小"""
        current_time = time.time()
        
        # 检查冷却时间
        if current_time - self._last_adjustment < self._adjustment_cooldown:
            return
            
        with self._lock:
            if new_size == self._current_workers:
                return
                
            old_size = self._current_workers
            self._current_workers = max(
                settings.THREAD_POOL_MIN_WORKERS,
                min(new_size, settings.THREAD_POOL_MAX_WORKERS)
            )
            
            # 重新创建线程池
            self._create_executor()
            self._last_adjustment = current_time
            
            print(f"🔧 线程池调整: {old_size} -> {self._current_workers} ({reason})")
            
    async def _monitor_system_load(self):
        """监控系统负载并自动调整线程池"""
        while True:
            try:
                if not settings.THREAD_POOL_AUTO_SCALE:
                    await asyncio.sleep(settings.LOAD_MONITOR_INTERVAL)
                    continue
                    
                metrics = self.get_system_metrics()
                self._metrics_history.append(metrics)
                
                # 保持最近10次的指标记录
                if len(self._metrics_history) > 10:
                    self._metrics_history.pop(0)
                    
                # 根据负载调整线程池
                if self._should_scale_up(metrics):
                    new_size = min(self._current_workers + 2, settings.THREAD_POOL_MAX_WORKERS)
                    self._adjust_pool_size(new_size, "scale_up")
                elif self._should_scale_down(metrics):
                    new_size = max(self._current_workers - 1, settings.THREAD_POOL_MIN_WORKERS)
                    self._adjust_pool_size(new_size, "scale_down")
                    
                await asyncio.sleep(settings.LOAD_MONITOR_INTERVAL)
                
            except Exception as e:
                print(f"❌ 负载监控错误: {e}")
                await asyncio.sleep(settings.LOAD_MONITOR_INTERVAL)
                
    def start_monitoring(self):
        """启动负载监控"""
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_system_load())
            print(f"📊 启动线程池负载监控 (间隔: {settings.LOAD_MONITOR_INTERVAL}s)")
            
    def stop_monitoring(self):
        """停止负载监控"""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            print("🛑 停止线程池负载监控")
            
    def submit(self, fn: Callable, *args, **kwargs):
        """提交任务到线程池"""
        if not self._executor:
            self._create_executor()
        return self._executor.submit(fn, *args, **kwargs)
        
    def manual_adjust(self, new_size: int) -> bool:
        """手动调整线程池大小"""
        if not (settings.THREAD_POOL_MIN_WORKERS <= new_size <= settings.THREAD_POOL_MAX_WORKERS):
            return False
            
        self._adjust_pool_size(new_size, "manual")
        return True
        
    def get_status(self) -> dict:
        """获取线程池状态信息"""
        metrics = self.get_system_metrics()
        
        return {
            "current_workers": self._current_workers,
            "min_workers": settings.THREAD_POOL_MIN_WORKERS,
            "max_workers": settings.THREAD_POOL_MAX_WORKERS,
            "auto_scale_enabled": settings.THREAD_POOL_AUTO_SCALE,
            "system_metrics": {
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "active_threads": metrics.active_threads,
                "pending_tasks": metrics.pending_tasks
            },
            "thresholds": {
                "cpu_high": settings.CPU_THRESHOLD_HIGH,
                "cpu_low": settings.CPU_THRESHOLD_LOW,
                "memory_high": settings.MEMORY_THRESHOLD_HIGH
            },
            "monitoring": {
                "interval": settings.LOAD_MONITOR_INTERVAL,
                "is_running": self._monitor_task is not None and not self._monitor_task.done()
            }
        }
        
    def shutdown(self):
        """关闭线程池"""
        self.stop_monitoring()
        if self._executor:
            self._executor.shutdown(wait=True)
            print("✅ 线程池已关闭")


# 全局线程池实例
thread_pool = DynamicThreadPool()