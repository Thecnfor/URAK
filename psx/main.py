"""应用启动入口"""

import signal
import sys
import uvicorn
from app.main import app
from app.core.config import settings


def signal_handler(signum, frame):
    """信号处理器，用于优雅退出"""
    print(f"\n收到信号 {signum}，正在退出...")
    sys.exit(0)


def main():
    """启动应用"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
    
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower()
        )
    except KeyboardInterrupt:
        print("\n服务器已优雅退出")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
