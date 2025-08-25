"""应用启动入口"""

import signal
import sys
import os
import uvicorn
from app.main import app
from app.core.config import settings
from app.core.thread_pool import thread_pool


def signal_handler(signum, frame):
    """信号处理器，用于退出"""
    print(f"\n收到信号 {signum}，正在退出...")
    sys.exit(0)


def main():
    """启动应用"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
    
    # 优化多线程性能
    cpu_count = os.cpu_count() or 4
    workers = min(cpu_count * 2, settings.THREAD_POOL_MAX_WORKERS)
    
    print(f"🚀 启动 URAK Blog API 服务")
    print(f"📊 系统信息: CPU核心数={cpu_count}, 建议工作进程数={workers}")
    print(f"🔧 线程池配置: 最小={settings.THREAD_POOL_MIN_WORKERS}, 最大={settings.THREAD_POOL_MAX_WORKERS}")
    print(f"⚙️  自动缩放: {'启用' if settings.THREAD_POOL_AUTO_SCALE else '禁用'}")
    
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower(),
            workers=1 if settings.DEBUG else workers,  # 开发模式使用单进程
            loop="asyncio",
            http="httptools",
            access_log=True,
            use_colors=True
        )
    except KeyboardInterrupt:
        print("\n🛑 收到中断信号，正在退出...")
        thread_pool.shutdown()
        print("✅ 服务器已退出")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        thread_pool.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    main()
