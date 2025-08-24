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
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()