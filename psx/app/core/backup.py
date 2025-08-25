"""数据库备份和恢复机制"""

import os
import gzip
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import db_manager

logger = logging.getLogger(__name__)

class DatabaseBackup:
    """数据库备份管理器"""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.max_backups = 30  # 保留最近30个备份
    
    async def create_full_backup(self, session: AsyncSession, backup_name: Optional[str] = None) -> str:
        """创建完整数据库备份"""
        if not backup_name:
            backup_name = f"full_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_file = self.backup_dir / f"{backup_name}.sql.gz"
        
        try:
            # 获取所有表的数据
            tables_data = await self._export_all_tables(session)
            
            # 压缩并保存
            with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
                f.write(tables_data)
            
            # 创建备份元数据
            metadata = {
                "backup_name": backup_name,
                "backup_type": "full",
                "created_at": datetime.now().isoformat(),
                "file_size": backup_file.stat().st_size,
                "tables_count": len(await self._get_table_names(session))
            }
            
            metadata_file = self.backup_dir / f"{backup_name}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"完整备份创建成功: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            if backup_file.exists():
                backup_file.unlink()
            raise
    
    async def create_incremental_backup(self, session: AsyncSession, since: datetime, backup_name: Optional[str] = None) -> str:
        """创建增量备份"""
        if not backup_name:
            backup_name = f"incremental_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_file = self.backup_dir / f"{backup_name}.sql.gz"
        
        try:
            # 获取自指定时间以来修改的数据
            incremental_data = await self._export_incremental_data(session, since)
            
            # 压缩并保存
            with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
                f.write(incremental_data)
            
            # 创建备份元数据
            metadata = {
                "backup_name": backup_name,
                "backup_type": "incremental",
                "created_at": datetime.now().isoformat(),
                "since": since.isoformat(),
                "file_size": backup_file.stat().st_size
            }
            
            metadata_file = self.backup_dir / f"{backup_name}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"增量备份创建成功: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"创建增量备份失败: {e}")
            if backup_file.exists():
                backup_file.unlink()
            raise
    
    async def restore_backup(self, session: AsyncSession, backup_file: str, confirm: bool = False) -> bool:
        """恢复备份"""
        if not confirm:
            raise ValueError("恢复操作需要明确确认 (confirm=True)")
        
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_file}")
        
        try:
            # 读取备份数据
            if backup_path.suffix == '.gz':
                with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                    sql_content = f.read()
            else:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
            
            # 执行恢复
            await self._execute_restore_sql(session, sql_content)
            
            logger.info(f"备份恢复成功: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"备份恢复失败: {e}")
            await session.rollback()
            raise
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []
        
        for metadata_file in self.backup_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                backup_file = self.backup_dir / f"{metadata['backup_name']}.sql.gz"
                if backup_file.exists():
                    metadata['file_path'] = str(backup_file)
                    metadata['exists'] = True
                else:
                    metadata['exists'] = False
                
                backups.append(metadata)
                
            except Exception as e:
                logger.warning(f"读取备份元数据失败: {metadata_file} - {e}")
        
        # 按创建时间排序
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return backups
    
    async def cleanup_old_backups(self) -> int:
        """清理旧备份"""
        backups = await self.list_backups()
        
        if len(backups) <= self.max_backups:
            return 0
        
        # 删除超出限制的旧备份
        old_backups = backups[self.max_backups:]
        deleted_count = 0
        
        for backup in old_backups:
            try:
                backup_name = backup['backup_name']
                
                # 删除备份文件
                backup_file = self.backup_dir / f"{backup_name}.sql.gz"
                if backup_file.exists():
                    backup_file.unlink()
                
                # 删除元数据文件
                metadata_file = self.backup_dir / f"{backup_name}.json"
                if metadata_file.exists():
                    metadata_file.unlink()
                
                deleted_count += 1
                logger.info(f"删除旧备份: {backup_name}")
                
            except Exception as e:
                logger.error(f"删除备份失败: {backup['backup_name']} - {e}")
        
        return deleted_count
    
    async def _export_all_tables(self, session: AsyncSession) -> str:
        """导出所有表数据"""
        sql_statements = []
        
        # 添加SQL头部
        sql_statements.append("-- Database Backup")
        sql_statements.append(f"-- Created at: {datetime.now().isoformat()}")
        sql_statements.append("-- \n")
        sql_statements.append("SET FOREIGN_KEY_CHECKS = 0;")
        sql_statements.append("")
        
        # 获取所有表名
        table_names = await self._get_table_names(session)
        
        for table_name in table_names:
            try:
                # 获取表结构
                create_table_sql = await self._get_create_table_sql(session, table_name)
                sql_statements.append(f"-- Table: {table_name}")
                sql_statements.append(f"DROP TABLE IF EXISTS `{table_name}`;")
                sql_statements.append(create_table_sql)
                sql_statements.append("")
                
                # 获取表数据
                insert_statements = await self._get_table_data_sql(session, table_name)
                if insert_statements:
                    sql_statements.extend(insert_statements)
                    sql_statements.append("")
                
            except Exception as e:
                logger.warning(f"导出表 {table_name} 失败: {e}")
        
        sql_statements.append("SET FOREIGN_KEY_CHECKS = 1;")
        return "\n".join(sql_statements)
    
    async def _export_incremental_data(self, session: AsyncSession, since: datetime) -> str:
        """导出增量数据"""
        sql_statements = []
        
        # 添加SQL头部
        sql_statements.append("-- Incremental Database Backup")
        sql_statements.append(f"-- Created at: {datetime.now().isoformat()}")
        sql_statements.append(f"-- Since: {since.isoformat()}")
        sql_statements.append("-- \n")
        
        # 导出有时间戳字段的表的增量数据
        timestamp_tables = {
            'articles': 'created_at',
            'users': 'created_at',
            'categories': 'created_at',
            'login_logs': 'login_time',
            'user_sessions': 'created_at'
        }
        
        for table_name, timestamp_field in timestamp_tables.items():
            try:
                # 获取增量数据
                result = await session.execute(
                    text(f"SELECT * FROM {table_name} WHERE {timestamp_field} >= :since"),
                    {"since": since}
                )
                rows = result.fetchall()
                
                if rows:
                    sql_statements.append(f"-- Incremental data for {table_name}")
                    
                    # 获取列名
                    columns = list(result.keys())
                    
                    for row in rows:
                        values = []
                        for value in row:
                            if value is None:
                                values.append('NULL')
                            elif isinstance(value, str):
                                escaped_value = value.replace("'", "''")
                                values.append(f"'{escaped_value}'")
                            elif isinstance(value, datetime):
                                values.append(f"'{value.isoformat()}'")
                            else:
                                values.append(str(value))
                        
                        sql_statements.append(
                            f"INSERT INTO {table_name} ({', '.join(columns)}) "
                            f"VALUES ({', '.join(values)}) ON DUPLICATE KEY UPDATE "
                            f"{', '.join([f'{col}=VALUES({col})' for col in columns])};"
                        )
                    
                    sql_statements.append("")
                
            except Exception as e:
                logger.warning(f"导出表 {table_name} 增量数据失败: {e}")
        
        return "\n".join(sql_statements)
    
    async def _get_table_names(self, session: AsyncSession) -> List[str]:
        """获取所有表名"""
        result = await session.execute(text("SHOW TABLES"))
        return [row[0] for row in result.fetchall()]
    
    async def _get_create_table_sql(self, session: AsyncSession, table_name: str) -> str:
        """获取建表SQL"""
        result = await session.execute(text(f"SHOW CREATE TABLE `{table_name}`"))
        return result.fetchone()[1] + ";"
    
    async def _get_table_data_sql(self, session: AsyncSession, table_name: str) -> List[str]:
        """获取表数据的INSERT语句"""
        result = await session.execute(text(f"SELECT * FROM `{table_name}`"))
        rows = result.fetchall()
        
        if not rows:
            return []
        
        # 获取列名
        columns = list(result.keys())
        insert_statements = []
        
        for row in rows:
            values = []
            for value in row:
                if value is None:
                    values.append('NULL')
                elif isinstance(value, str):
                    escaped_value = value.replace("'", "''")
                    values.append(f"'{escaped_value}'")
                elif isinstance(value, datetime):
                    values.append(f"'{value.isoformat()}'")
                else:
                    values.append(str(value))
            
            insert_statements.append(
                f"INSERT INTO `{table_name}` ({', '.join([f'`{col}`' for col in columns])}) "
                f"VALUES ({', '.join(values)});"
            )
        
        return insert_statements
    
    async def _execute_restore_sql(self, session: AsyncSession, sql_content: str):
        """执行恢复SQL"""
        # 分割SQL语句
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
        
        for statement in statements:
            if statement:
                await session.execute(text(statement))
        
        await session.commit()

class BackupScheduler:
    """备份调度器"""
    
    def __init__(self, backup_manager: DatabaseBackup):
        self.backup_manager = backup_manager
        self.is_running = False
        self._task = None
    
    async def start_scheduled_backups(self, full_backup_interval: int = 24, incremental_interval: int = 6):
        """启动定时备份
        
        Args:
            full_backup_interval: 完整备份间隔（小时）
            incremental_interval: 增量备份间隔（小时）
        """
        if self.is_running:
            return
        
        self.is_running = True
        self._task = asyncio.create_task(
            self._backup_loop(full_backup_interval, incremental_interval)
        )
        logger.info(f"定时备份已启动: 完整备份每{full_backup_interval}小时，增量备份每{incremental_interval}小时")
    
    async def stop_scheduled_backups(self):
        """停止定时备份"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("定时备份已停止")
    
    async def _backup_loop(self, full_interval: int, incremental_interval: int):
        """备份循环"""
        last_full_backup = datetime.now() - timedelta(hours=full_interval)  # 立即执行第一次完整备份
        last_incremental_backup = datetime.now()
        
        while self.is_running:
            try:
                now = datetime.now()
                
                # 检查是否需要完整备份
                if now - last_full_backup >= timedelta(hours=full_interval):
                    async with db_manager.get_session() as session:
                        await self.backup_manager.create_full_backup(session)
                        last_full_backup = now
                        
                        # 清理旧备份
                        await self.backup_manager.cleanup_old_backups()
                
                # 检查是否需要增量备份
                elif now - last_incremental_backup >= timedelta(hours=incremental_interval):
                    async with db_manager.get_session() as session:
                        await self.backup_manager.create_incremental_backup(
                            session, last_incremental_backup
                        )
                        last_incremental_backup = now
                
                # 等待1小时后再次检查
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"定时备份执行失败: {e}")
                await asyncio.sleep(3600)  # 出错后等待1小时再重试

# 全局备份管理器实例
backup_manager = DatabaseBackup()
backup_scheduler = BackupScheduler(backup_manager)