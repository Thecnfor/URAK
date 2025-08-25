#!/usr/bin/env python3
"""数据库备份管理命令行工具"""

import asyncio
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import db_manager, init_database
from app.core.backup import backup_manager, backup_scheduler
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def create_full_backup(args):
    """创建完整备份"""
    try:
        await init_database()
        
        async with db_manager.get_session() as session:
            backup_file = await backup_manager.create_full_backup(
                session, 
                backup_name=args.name
            )
            print(f"✅ 完整备份创建成功: {backup_file}")
            
    except Exception as e:
        print(f"❌ 备份创建失败: {e}")
        logger.error(f"备份创建失败: {e}")
        return 1
    
    return 0

async def create_incremental_backup(args):
    """创建增量备份"""
    try:
        await init_database()
        
        # 解析since参数
        if args.since:
            since = datetime.fromisoformat(args.since)
        else:
            since = datetime.now() - timedelta(hours=args.hours or 24)
        
        async with db_manager.get_session() as session:
            backup_file = await backup_manager.create_incremental_backup(
                session,
                since=since,
                backup_name=args.name
            )
            print(f"✅ 增量备份创建成功: {backup_file}")
            
    except Exception as e:
        print(f"❌ 增量备份创建失败: {e}")
        logger.error(f"增量备份创建失败: {e}")
        return 1
    
    return 0

async def restore_backup(args):
    """恢复备份"""
    try:
        if not args.confirm:
            print("⚠️  警告: 恢复操作将覆盖现有数据!")
            print("请使用 --confirm 参数确认执行恢复操作")
            return 1
        
        await init_database()
        
        async with db_manager.get_session() as session:
            success = await backup_manager.restore_backup(
                session,
                backup_file=args.file,
                confirm=True
            )
            
            if success:
                print(f"✅ 备份恢复成功: {args.file}")
            else:
                print(f"❌ 备份恢复失败")
                return 1
            
    except Exception as e:
        print(f"❌ 备份恢复失败: {e}")
        logger.error(f"备份恢复失败: {e}")
        return 1
    
    return 0

async def list_backups(args):
    """列出所有备份"""
    try:
        backups = await backup_manager.list_backups()
        
        if not backups:
            print("📁 没有找到备份文件")
            return 0
        
        print(f"📁 找到 {len(backups)} 个备份文件:\n")
        
        for backup in backups:
            status = "✅" if backup['exists'] else "❌"
            backup_type = backup.get('backup_type', 'unknown')
            created_at = backup.get('created_at', 'unknown')
            file_size = backup.get('file_size', 0)
            
            # 格式化文件大小
            if file_size > 1024 * 1024:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            elif file_size > 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size} B"
            
            print(f"{status} {backup['backup_name']}")
            print(f"   类型: {backup_type}")
            print(f"   创建时间: {created_at}")
            print(f"   文件大小: {size_str}")
            
            if backup_type == 'incremental' and 'since' in backup:
                print(f"   增量起始: {backup['since']}")
            
            if 'tables_count' in backup:
                print(f"   表数量: {backup['tables_count']}")
            
            print()
            
    except Exception as e:
        print(f"❌ 列出备份失败: {e}")
        logger.error(f"列出备份失败: {e}")
        return 1
    
    return 0

async def cleanup_backups(args):
    """清理旧备份"""
    try:
        deleted_count = await backup_manager.cleanup_old_backups()
        print(f"🗑️  清理完成，删除了 {deleted_count} 个旧备份")
        
    except Exception as e:
        print(f"❌ 清理备份失败: {e}")
        logger.error(f"清理备份失败: {e}")
        return 1
    
    return 0

async def start_scheduler(args):
    """启动定时备份"""
    try:
        await init_database()
        
        print(f"🕐 启动定时备份服务...")
        print(f"   完整备份间隔: {args.full_interval} 小时")
        print(f"   增量备份间隔: {args.incremental_interval} 小时")
        print(f"   按 Ctrl+C 停止服务")
        
        await backup_scheduler.start_scheduled_backups(
            full_backup_interval=args.full_interval,
            incremental_interval=args.incremental_interval
        )
        
        # 保持运行直到收到中断信号
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 收到停止信号，正在关闭定时备份服务...")
            await backup_scheduler.stop_scheduled_backups()
            print("✅ 定时备份服务已停止")
        
    except Exception as e:
        print(f"❌ 启动定时备份失败: {e}")
        logger.error(f"启动定时备份失败: {e}")
        return 1
    
    return 0

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="数据库备份管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 创建完整备份
  python backup_manager.py full-backup
  
  # 创建指定名称的完整备份
  python backup_manager.py full-backup --name my_backup
  
  # 创建最近24小时的增量备份
  python backup_manager.py incremental-backup
  
  # 创建最近6小时的增量备份
  python backup_manager.py incremental-backup --hours 6
  
  # 创建指定时间点的增量备份
  python backup_manager.py incremental-backup --since "2024-01-01T00:00:00"
  
  # 恢复备份（需要确认）
  python backup_manager.py restore --file backups/my_backup.sql.gz --confirm
  
  # 列出所有备份
  python backup_manager.py list
  
  # 清理旧备份
  python backup_manager.py cleanup
  
  # 启动定时备份服务
  python backup_manager.py scheduler --full-interval 24 --incremental-interval 6
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 完整备份命令
    full_parser = subparsers.add_parser('full-backup', help='创建完整备份')
    full_parser.add_argument('--name', help='备份名称（可选）')
    
    # 增量备份命令
    incremental_parser = subparsers.add_parser('incremental-backup', help='创建增量备份')
    incremental_parser.add_argument('--name', help='备份名称（可选）')
    incremental_parser.add_argument('--hours', type=int, help='最近N小时的数据（默认24小时）')
    incremental_parser.add_argument('--since', help='指定起始时间（ISO格式）')
    
    # 恢复备份命令
    restore_parser = subparsers.add_parser('restore', help='恢复备份')
    restore_parser.add_argument('--file', required=True, help='备份文件路径')
    restore_parser.add_argument('--confirm', action='store_true', help='确认执行恢复操作')
    
    # 列出备份命令
    subparsers.add_parser('list', help='列出所有备份')
    
    # 清理备份命令
    subparsers.add_parser('cleanup', help='清理旧备份')
    
    # 定时备份命令
    scheduler_parser = subparsers.add_parser('scheduler', help='启动定时备份服务')
    scheduler_parser.add_argument('--full-interval', type=int, default=24, help='完整备份间隔（小时，默认24）')
    scheduler_parser.add_argument('--incremental-interval', type=int, default=6, help='增量备份间隔（小时，默认6）')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # 执行对应的命令
    command_map = {
        'full-backup': create_full_backup,
        'incremental-backup': create_incremental_backup,
        'restore': restore_backup,
        'list': list_backups,
        'cleanup': cleanup_backups,
        'scheduler': start_scheduler
    }
    
    if args.command in command_map:
        return asyncio.run(command_map[args.command](args))
    else:
        print(f"❌ 未知命令: {args.command}")
        return 1

if __name__ == '__main__':
    sys.exit(main())