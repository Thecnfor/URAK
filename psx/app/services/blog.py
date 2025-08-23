"""博客服务层"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.core.config import settings
from app.models.blog import Article, Category, BlogData


class BlogService:
    """博客服务类"""
    
    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[float] = None
        self.cache_ttl = settings.CACHE_TTL
        
    async def clear_cache(self):
        """清除缓存"""
        self._cache = None
        self._cache_timestamp = None
        
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not settings.CACHE_ENABLED:
            return False
            
        if self._cache is None or self._cache_timestamp is None:
            return False
            
        import time
        return (time.time() - self._cache_timestamp) < self.cache_ttl
        
    async def get_blog_data(self) -> Dict[str, Any]:
        """获取博客数据
        
        Returns:
            Dict[str, Any]: 博客数据字典
        """
        # 检查缓存
        if self._is_cache_valid():
            return self._cache
            
        # 优先从JSON文件读取
        json_data = await self._load_from_json()
        if json_data:
            self._update_cache(json_data)
            return json_data
            
        # 从文件系统扫描
        scanned_data = await self._scan_from_filesystem()
        self._update_cache(scanned_data)
        
        # 保存到JSON文件
        await self._save_to_json(scanned_data)
        
        return scanned_data
        
    def _update_cache(self, data: Dict[str, Any]):
        """更新缓存"""
        if settings.CACHE_ENABLED:
            import time
            self._cache = data
            self._cache_timestamp = time.time()
            
    async def _load_from_json(self) -> Optional[Dict[str, Any]]:
        """从JSON文件加载数据"""
        try:
            json_path = Path(settings.BLOG_DATA_FILE)
            if not json_path.exists():
                return None
                
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 验证数据结构
            if 'categories' in data:
                return data
                
        except Exception as e:
            print(f"加载JSON文件失败: {e}")
            
        return None
        
    async def _save_to_json(self, data: Dict[str, Any]):
        """保存数据到JSON文件"""
        try:
            json_path = Path(settings.BLOG_DATA_FILE)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存JSON文件失败: {e}")
            
    async def _scan_from_filesystem(self) -> Dict[str, Any]:
        """从文件系统扫描数据"""
        categories = await self.scan_categories()
        
        blog_data = {
            "categories": {},
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "source": "file_scan"
        }
        
        for category_info in categories:
            category_id = category_info["id"]
            articles = await self.scan_articles(category_id)
            
            # 转换文章列表为字典格式（与unified_blog_api.py一致）
            articles_dict = {}
            for article in articles:
                articles_dict[article["id"]] = article
            
            category_data = {
                "title": category_info.get("name", category_id.replace('_', ' ').title()),
                "href": f"/{category_id}",
                "description": category_info.get("description", f"{category_info.get('name', category_id).replace('_', ' ').title()}相关内容"),
                "articles": articles_dict
            }
            
            blog_data["categories"][category_id] = category_data
        
        return blog_data
        
    async def scan_categories(self) -> List[Dict[str, Any]]:
        """扫描分类目录
        
        Returns:
            List[Dict[str, Any]]: 分类信息列表
        """
        categories = []
        categories_dir = Path(settings.CATEGORIES_DIR)
        
        if not categories_dir.exists():
            return categories
            
        for item in categories_dir.iterdir():
            if item.is_dir():
                category_info = {
                    "id": item.name,
                    "name": item.name.replace("-", " ").title(),
                    "description": f"{item.name} 分类"
                }
                
                # 检查是否有分类配置文件
                config_file = item / "config.json"
                if config_file.exists():
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            category_info.update(config)
                    except Exception:
                        pass
                        
                categories.append(category_info)
                
        return categories
        
    async def scan_articles(self, category: str) -> List[Dict[str, Any]]:
        """扫描指定分类下的文章
        
        Args:
            category: 分类标识符
            
        Returns:
            List[Dict[str, Any]]: 文章信息列表
        """
        articles = []
        category_dir = Path(settings.CATEGORIES_DIR) / category
        
        if not category_dir.exists():
            return articles
            
        for item in category_dir.iterdir():
            if item.is_file() and item.suffix.lower() == '.json':
                article_id = item.stem
                
                # 尝试解析JSON文件
                try:
                    with open(item, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 适配unified_blog_api.py的数据结构
                    if 'meta' in data and 'content' in data:
                        meta = data['meta']
                        content = data['content']
                        
                        # 处理content - 如果是结构化内容，转换为字符串
                        content_str = ""
                        if isinstance(content, dict) and 'blocks' in content:
                            # 提取文本内容
                            for block in content.get('blocks', []):
                                if block.get('type') == 'title':
                                    content_str += f"# {block.get('data', {}).get('text', '')}\n\n"
                                elif block.get('type') == 'paragraph':
                                    content_str += f"{block.get('data', {}).get('text', '')}\n\n"
                                elif block.get('type') == 'list':
                                    for item_data in block.get('data', {}).get('items', []):
                                        content_str += f"- {item_data}\n"
                                    content_str += "\n"
                                elif block.get('type') == 'code':
                                    code_text = block.get('data', {}).get('code', '')
                                    content_str += f"```\n{code_text}\n```\n\n"
                        elif isinstance(content, str):
                            content_str = content
                        else:
                            content_str = json.dumps(content, ensure_ascii=False)
                        
                        article_info = {
                            "id": article_id,
                            "title": meta.get('title', article_id.replace("-", " ").title()),
                            "category": category,
                            "publishDate": meta.get('publishDate', ''),
                            "content": content_str,
                            "excerpt": meta.get('excerpt', meta.get('description', '')),
                            "tags": meta.get('tags', []),
                            "readTime": meta.get('readTime', ''),
                            "author": meta.get('author', ''),
                            "imagePath": meta.get('imagePath', ''),
                            "source": "file_system",
                            "structuredContent": content if isinstance(content, dict) else None
                        }
                    else:
                        # 兼容其他JSON格式
                        article_info = {
                            "id": article_id,
                            "title": data.get('title', article_id.replace("-", " ").title()),
                            "category": category,
                            "publishDate": data.get('publishDate', data.get('date', '')),
                            "content": str(data.get('content', '')),
                            "excerpt": data.get('excerpt', data.get('summary', '')),
                            "tags": data.get('tags', []),
                            "readTime": data.get('readTime', ''),
                            "author": data.get('author', ''),
                            "imagePath": data.get('imagePath', ''),
                            "source": "file_system"
                        }
                        
                except Exception as e:
                    print(f"读取文章文件失败 {item}: {e}")
                    article_info = {
                        "id": article_id,
                        "title": article_id.replace("-", " ").title(),
                        "category": category,
                        "publishDate": "",
                        "content": "",
                        "excerpt": "无法读取文章内容",
                        "tags": [],
                        "readTime": "",
                        "author": "",
                        "imagePath": "",
                        "source": "error"
                    }
                    
                articles.append(article_info)
                
        # 按发布日期排序
        articles.sort(key=lambda x: x.get("publishDate", ""), reverse=True)
        
        return articles
        
    async def get_article_content(self, category: str, article_id: str) -> Optional[Dict[str, Any]]:
        """获取指定文章内容
        
        Args:
            category: 分类标识符
            article_id: 文章ID
            
        Returns:
            Optional[Dict[str, Any]]: 文章信息，如果不存在返回None
        """
        # 直接从文件系统加载文章，参考unified_blog_api.py的逻辑
        try:
            article_file = Path(settings.CATEGORIES_DIR) / category / f"{article_id}.json"
            
            if not article_file.exists():
                return None
                
            with open(article_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理meta+content结构（参考unified_blog_api.py）
            if 'meta' in data and 'content' in data:
                meta = data['meta']
                content = data['content']
                
                # 处理结构化内容转换为字符串
                content_str = ""
                if isinstance(content, dict) and 'blocks' in content:
                    for block in content.get('blocks', []):
                        if block.get('type') == 'title':
                            content_str += f"# {block.get('data', {}).get('text', '')}\n\n"
                        elif block.get('type') == 'content':
                            content_str += f"{block.get('data', {}).get('text', '')}\n\n"
                        elif block.get('type') == 'paragraph':
                            content_str += f"{block.get('data', {}).get('text', '')}\n\n"
                        elif block.get('type') == 'list':
                            for item_data in block.get('data', {}).get('items', []):
                                content_str += f"- {item_data}\n"
                            content_str += "\n"
                        elif block.get('type') == 'code':
                            code_text = block.get('data', {}).get('code', '')
                            content_str += f"```\n{code_text}\n```\n\n"
                elif isinstance(content, str):
                    content_str = content
                else:
                    content_str = json.dumps(content, ensure_ascii=False)
                
                return {
                    "id": article_id,
                    "title": meta.get('title', article_id.replace("-", " ").title()),
                    "category": category,
                    "publishDate": meta.get('publishDate', ''),
                    "content": content_str,
                    "excerpt": meta.get('excerpt', meta.get('description', '')),
                    "tags": meta.get('tags', []),
                    "readTime": meta.get('readTime', ''),
                    "author": meta.get('author', ''),
                    "imagePath": meta.get('imagePath', ''),
                    "source": "file_system",
                    "structuredContent": content if isinstance(content, dict) else None
                }
            else:
                # 兼容其他JSON格式
                return {
                    "id": article_id,
                    "title": data.get('title', article_id.replace("-", " ").title()),
                    "category": category,
                    "publishDate": data.get('publishDate', data.get('date', '')),
                    "content": str(data.get('content', '')),
                    "excerpt": data.get('excerpt', data.get('summary', '')),
                    "tags": data.get('tags', []),
                    "readTime": data.get('readTime', ''),
                    "author": data.get('author', ''),
                    "imagePath": data.get('imagePath', ''),
                    "source": "file_system"
                }
                
        except Exception as e:
            print(f"读取文章文件失败 {category}/{article_id}: {e}")
            return None
        
    async def get_category_content(self, category: str) -> Optional[Dict[str, Any]]:
        """获取指定分类内容
        
        Args:
            category: 分类标识符
            
        Returns:
            Optional[Dict[str, Any]]: 分类信息，如果不存在返回None
        """
        blog_data = await self.get_blog_data()
        
        if category not in blog_data.get("categories", {}):
            return None
            
        return blog_data["categories"][category]