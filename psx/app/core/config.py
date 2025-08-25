"""应用配置管理"""

import os
from typing import List
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    # 基础配置
    APP_NAME: str = "URAK Blog API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS配置
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    
    # 数据存储配置
    DOCS_DIR: str = str(Path(__file__).parent.parent.parent.parent / "docs")
    CATEGORIES_DIR: str = str(Path(__file__).parent.parent.parent.parent / "docs" / "categories")
    CONTENT_DIR: str = str(Path(__file__).parent.parent.parent.parent / "docs" / "content")
    BLOG_DATA_FILE: str = str(Path(__file__).parent.parent.parent.parent / "docs" / "blog-data.json")
    
    # 缓存配置
    CACHE_TTL: int = 60  # 缓存时间（秒）
    CACHE_ENABLED: bool = True
    
    # 线程池配置
    THREAD_POOL_MIN_WORKERS: int = 2  # 最小工作线程数
    THREAD_POOL_MAX_WORKERS: int = 32  # 最大工作线程数
    THREAD_POOL_AUTO_SCALE: bool = True  # 是否启用自动缩放
    LOAD_MONITOR_INTERVAL: int = 30  # 负载监控间隔（秒）
    CPU_THRESHOLD_HIGH: float = 80.0  # CPU高负载阈值（%）
    CPU_THRESHOLD_LOW: float = 30.0  # CPU低负载阈值（%）
    MEMORY_THRESHOLD_HIGH: float = 85.0  # 内存高负载阈值（%）
    
    # 数据库配置
    DATABASE_URL: str = "mysql+asyncmy://XRAK:yj2mzx4BwMZYm4hf@192.168.1.10:3306/xrak?charset=utf8mb4"
    DB_HOST: str = "192.168.1.10"
    DB_PORT: int = 3306
    DB_NAME: str = "xrak"
    DB_USER: str = "XRAK"
    DB_PASSWORD: str = "yj2mzx4BwMZYm4hf"
    DB_CHARSET: str = "utf8mb4"
    DB_COLLATION: str = "utf8mb4_unicode_ci"
    
    # 数据库连接池配置
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = True
    
    # 数据库安全配置
    DB_SSL_MODE: str = "PREFERRED"
    DB_CONNECT_TIMEOUT: int = 10
    DB_READ_TIMEOUT: int = 30
    DB_WRITE_TIMEOUT: int = 30
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # JWT配置
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 速率限制配置
    RATE_LIMIT_ENABLED: bool = True
    REDIS_URL: str = "redis://localhost:6379"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()