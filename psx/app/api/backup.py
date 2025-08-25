"""备份管理API端点"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging
import os

from app.core.database import get_db_session
from app.core.backup import backup_manager, backup_scheduler
from app.services.auth import get_current_user, require_admin
from app.models.user import User

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/api/backup", tags=["backup"])

class BackupRequest(BaseModel):
    """备份请求模型"""
    name: Optional[str] = Field(None, description="备份名称")
    backup_type: str = Field("full", description="备份类型: full 或 incremental")
    since_hours: Optional[int] = Field(24, description="增量备份：最近N小时的数据")
    since_datetime: Optional[datetime] = Field(None, description="增量备份：指定起始时间")

class RestoreRequest(BaseModel):
    """恢复请求模型"""
    backup_file: str = Field(..., description="备份文件路径")
    confirm: bool = Field(False, description="确认执行恢复操作")

class SchedulerConfig(BaseModel):
    """定时备份配置模型"""
    full_backup_interval: int = Field(24, description="完整备份间隔（小时）")
    incremental_interval: int = Field(6, description="增量备份间隔（小时）")
    enabled: bool = Field(True, description="是否启用定时备份")

class BackupResponse(BaseModel):
    """备份响应模型"""
    success: bool
    message: str
    backup_file: Optional[str] = None
    backup_name: Optional[str] = None

class BackupListResponse(BaseModel):
    """备份列表响应模型"""
    backups: List[Dict[str, Any]]
    total_count: int
    total_size: int

@router.post("/create", response_model=BackupResponse)
async def create_backup(
    request: BackupRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
):
    """创建数据库备份"""
    try:
        if request.backup_type == "full":
            # 创建完整备份
            backup_file = await backup_manager.create_full_backup(
                session, 
                backup_name=request.name
            )
            
            return BackupResponse(
                success=True,
                message="完整备份创建成功",
                backup_file=backup_file,
                backup_name=request.name
            )
            
        elif request.backup_type == "incremental":
            # 确定增量备份的起始时间
            if request.since_datetime:
                since = request.since_datetime
            else:
                since = datetime.now() - timedelta(hours=request.since_hours or 24)
            
            # 创建增量备份
            backup_file = await backup_manager.create_incremental_backup(
                session,
                since=since,
                backup_name=request.name
            )
            
            return BackupResponse(
                success=True,
                message="增量备份创建成功",
                backup_file=backup_file,
                backup_name=request.name
            )
            
        else:
            raise HTTPException(
                status_code=400,
                detail="不支持的备份类型，请使用 'full' 或 'incremental'"
            )
            
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"创建备份失败: {str(e)}"
        )

@router.post("/restore", response_model=BackupResponse)
async def restore_backup(
    request: RestoreRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
):
    """恢复数据库备份"""
    try:
        if not request.confirm:
            raise HTTPException(
                status_code=400,
                detail="恢复操作需要明确确认 (confirm=true)"
            )
        
        success = await backup_manager.restore_backup(
            session,
            backup_file=request.backup_file,
            confirm=True
        )
        
        if success:
            return BackupResponse(
                success=True,
                message="备份恢复成功",
                backup_file=request.backup_file
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="备份恢复失败"
            )
            
    except Exception as e:
        logger.error(f"恢复备份失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"恢复备份失败: {str(e)}"
        )

@router.get("/list", response_model=BackupListResponse)
async def list_backups(
    current_user: User = Depends(require_admin)
):
    """获取备份列表"""
    try:
        backups = await backup_manager.list_backups()
        
        # 计算总大小
        total_size = sum(backup.get('file_size', 0) for backup in backups if backup.get('exists', False))
        
        return BackupListResponse(
            backups=backups,
            total_count=len(backups),
            total_size=total_size
        )
        
    except Exception as e:
        logger.error(f"获取备份列表失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取备份列表失败: {str(e)}"
        )

@router.delete("/cleanup")
async def cleanup_old_backups(
    current_user: User = Depends(require_admin)
):
    """清理旧备份"""
    try:
        deleted_count = await backup_manager.cleanup_old_backups()
        
        return {
            "success": True,
            "message": f"清理完成，删除了 {deleted_count} 个旧备份",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"清理备份失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"清理备份失败: {str(e)}"
        )

@router.post("/scheduler/start")
async def start_backup_scheduler(
    config: SchedulerConfig,
    current_user: User = Depends(require_admin)
):
    """启动定时备份"""
    try:
        if config.enabled:
            await backup_scheduler.start_scheduled_backups(
                full_backup_interval=config.full_backup_interval,
                incremental_interval=config.incremental_interval
            )
            
            return {
                "success": True,
                "message": "定时备份已启动",
                "config": config.dict()
            }
        else:
            await backup_scheduler.stop_scheduled_backups()
            
            return {
                "success": True,
                "message": "定时备份已停止"
            }
            
    except Exception as e:
        logger.error(f"配置定时备份失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"配置定时备份失败: {str(e)}"
        )

@router.get("/scheduler/status")
async def get_scheduler_status(
    current_user: User = Depends(require_admin)
):
    """获取定时备份状态"""
    try:
        return {
            "is_running": backup_scheduler.is_running,
            "status": "running" if backup_scheduler.is_running else "stopped"
        }
        
    except Exception as e:
        logger.error(f"获取定时备份状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取定时备份状态失败: {str(e)}"
        )

@router.post("/scheduler/stop")
async def stop_backup_scheduler(
    current_user: User = Depends(require_admin)
):
    """停止定时备份"""
    try:
        await backup_scheduler.stop_scheduled_backups()
        
        return {
            "success": True,
            "message": "定时备份已停止"
        }
        
    except Exception as e:
        logger.error(f"停止定时备份失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"停止定时备份失败: {str(e)}"
        )

@router.get("/health")
async def backup_health_check(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
):
    """备份系统健康检查"""
    try:
        # 检查备份目录
        backup_dir = backup_manager.backup_dir
        backup_dir_exists = backup_dir.exists()
        backup_dir_writable = backup_dir_exists and os.access(backup_dir, os.W_OK)
        
        # 获取最近的备份
        backups = await backup_manager.list_backups()
        recent_backups = [b for b in backups if 
                         datetime.fromisoformat(b['created_at']) > datetime.now() - timedelta(days=7)]
        
        # 检查定时备份状态
        scheduler_running = backup_scheduler.is_running
        
        health_status = {
            "backup_directory": {
                "exists": backup_dir_exists,
                "writable": backup_dir_writable,
                "path": str(backup_dir)
            },
            "recent_backups": {
                "count": len(recent_backups),
                "total_size": sum(b.get('file_size', 0) for b in recent_backups)
            },
            "scheduler": {
                "running": scheduler_running,
                "status": "healthy" if scheduler_running else "stopped"
            },
            "overall_status": "healthy" if (backup_dir_writable and len(recent_backups) > 0) else "warning"
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"备份健康检查失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"备份健康检查失败: {str(e)}"
        )