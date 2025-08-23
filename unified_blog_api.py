#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XRAK 博客系统统一API服务器

功能:
1. 整合auto_blog_api.py和api_test.py的功能
2. 自动扫描 docs/categories 目录下的文章文件
3. 支持从blog-data.json读取数据作为备用
4. 提供RESTful API接口
5. 支持实时文件变更检测
6. 解决端口冲突问题

使用方法:
1. 运行脚本: python unified_blog_api.py
2. 访问 http://localhost:8000/api/blog-data 查看数据
"""

import json
import http.server
import socketserver
import threading
import time
import os
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
import hashlib
import argparse
import glob

# 默认配置
DEFAULT_CONFIG = {
    'port': 8000,
    'host': '0.0.0.0',
    'docs_dir': './docs',
    'blog_data_file': './blog-data.json',
    'auto_scan': True,
    'scan_interval': 30,  # 秒
    'cache_enabled': True,
    'debug': False,
    'content_dir': './docs/content'  # 新增：结构化内容目录
}

DEFAULT_PORT = 8000
DOCS_DIR = "docs"
CATEGORIES_DIR = "docs/categories"
JSON_FILE = "docs/blog-data.json"

# 缓存配置
CACHE_TTL = 60  # 缓存时间（秒）
file_cache = {}
last_scan_time = 0
cached_blog_data = None

class UnifiedBlogDataHandler(http.server.BaseHTTPRequestHandler):
    """统一博客数据处理器"""
    
    def __init__(self, *args, **kwargs):
        self.port = kwargs.pop('port', DEFAULT_PORT)
        self.api_base_url = f"http://localhost:{self.port}"
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """处理 GET 请求"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/api/blog-data":
            self.handle_blog_data()
        elif parsed_path.path == "/health":
            self.handle_health_check()
        elif parsed_path.path.startswith("/api/articles/"):
            self.handle_article_request(parsed_path.path)
        elif parsed_path.path.startswith("/api/categories/"):
            self.handle_category_request(parsed_path.path)
        elif parsed_path.path == "/api/categories":
            self.handle_categories_list()
        elif parsed_path.path == "/api/scan":
            self.handle_force_scan()
        else:
            self.send_error(404, "Not Found")
    
    def handle_blog_data(self):
        """处理博客数据请求 - 优先使用JSON文件，备用自动扫描"""
        try:
            # 优先尝试读取JSON文件
            data = get_json_data()
            
            # 如果JSON文件失败或数据为空，尝试自动扫描
            if not data or not data.get('categories'):
                print("⚠️ JSON文件数据为空，尝试自动扫描")
                data = get_blog_data()
            
            # 设置响应头
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=300')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # 发送 JSON 数据
            response = json.dumps(data, ensure_ascii=False, indent=2)
            self.wfile.write(response.encode('utf-8'))
            
            print(f"✅ 成功响应 /api/blog-data 请求")
            
        except Exception as e:
            print(f"❌ 处理文章请求错误: {e}")
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def handle_health_check(self):
        """健康检查端点"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        # 检查数据源状态
        categories_from_scan = len(scan_categories())
        json_file_exists = os.path.exists(JSON_FILE)
        
        health_data = {
            "status": "healthy",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "service": "XRAK Unified Blog API Server",
            "port": self.port,
            "docs_dir": DOCS_DIR,
            "categories_from_scan": categories_from_scan,
            "json_file_exists": json_file_exists,
            "json_file_path": JSON_FILE,
            "last_scan": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(last_scan_time)) if last_scan_time else "never"
        }
        
        response = json.dumps(health_data, indent=2)
        self.wfile.write(response.encode('utf-8'))
    
    def handle_article_request(self, path):
        """处理文章请求 /api/articles/{category}/{articleId}"""
        try:
            # 解析路径: /api/articles/tech/1
            path_parts = path.strip('/').split('/')
            if len(path_parts) != 4 or path_parts[0] != 'api' or path_parts[1] != 'articles':
                self.send_error(400, "Invalid article path format")
                return
            
            category = path_parts[2]
            article_id = path_parts[3]
            
            # 优先尝试从文件系统获取结构化内容
            article = get_article_content(category, article_id)
            
            # 如果文件系统中没有，尝试从JSON文件获取
            if not article:
                article = get_article_from_json(category, article_id)
            
            if not article:
                self.send_error(404, f"Article '{article_id}' not found in category '{category}'")
                return
            
            # 设置响应头
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=300')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # 发送响应
            response = json.dumps(article, ensure_ascii=False, indent=2)
            self.wfile.write(response.encode('utf-8'))
            
            print(f"✅ 成功响应文章请求: {category}/{article_id}")
            
        except Exception as e:
            print(f"❌ 处理分类请求错误: {e}")
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def handle_category_request(self, path):
        """处理分类请求 /api/categories/{categoryKey}"""
        try:
            # 解析路径: /api/categories/tech
            path_parts = path.strip('/').split('/')
            if len(path_parts) != 3 or path_parts[0] != 'api' or path_parts[1] != 'categories':
                self.send_error(400, "Invalid category path format")
                return
            
            category_key = path_parts[2]
            
            # 优先尝试从文件系统获取分类数据
            category_data = get_category_content(category_key)
            
            # 如果文件系统中没有，尝试从JSON文件获取
            if not category_data:
                category_data = get_category_from_json(category_key)
            
            if not category_data:
                self.send_error(404, f"Category '{category_key}' not found")
                return
            
            # 设置响应头
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=300')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # 发送响应
            response = json.dumps(category_data, ensure_ascii=False, indent=2)
            self.wfile.write(response.encode('utf-8'))
            
            print(f"✅ 成功响应分类请求: {category_key}")
            
        except Exception as e:
            print(f"❌ 处理博客数据请求错误: {e}")
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def handle_categories_list(self):
        """处理分类列表请求 /api/categories"""
        try:
            # 获取博客数据
            data = get_blog_data()
            
            # 如果自动扫描数据为空，尝试JSON文件
            if not data or not data.get('categories'):
                data = get_json_data()
            
            response_data = {
                "blogInfoPool": data.get("categories", {})
            }
            
            # 设置响应头
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=300')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # 发送响应
            response = json.dumps(response_data, ensure_ascii=False, indent=2)
            self.wfile.write(response.encode('utf-8'))
            
            print(f"✅ 成功响应分类列表请求")
            
        except Exception as e:
            print(f"❌ 处理分类列表请求错误: {e}")
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def handle_force_scan(self):
        """强制重新扫描文件"""
        try:
            global cached_blog_data, last_scan_time
            cached_blog_data = None
            last_scan_time = 0
            
            # 重新扫描
            data = get_blog_data()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps({
                "status": "success",
                "message": "文件重新扫描完成",
                "categories_found": len(data.get("categories", {})),
                "scan_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }, ensure_ascii=False, indent=2)
            self.wfile.write(response.encode('utf-8'))
            
            print(f"✅ 强制重新扫描完成")
            
        except Exception as e:
            print(f"❌ 强制扫描错误: {e}")
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

# 文件系统扫描相关函数（来自auto_blog_api.py）
def scan_categories() -> Dict[str, List[str]]:
    """扫描分类目录，返回分类和文章文件映射"""
    categories = {}
    
    # 优先扫描结构化内容目录
    content_dir = DEFAULT_CONFIG['content_dir']
    if os.path.exists(content_dir):
        print(f"🔍 扫描结构化内容目录: {content_dir}")
        for category_dir in os.listdir(content_dir):
            category_path = os.path.join(content_dir, category_dir)
            
            if os.path.isdir(category_path):
                articles = []
                for file_name in os.listdir(category_path):
                    if file_name.endswith('.json'):
                        articles.append(file_name[:-5])  # 移除 .json 扩展名
                
                if articles:
                    categories[category_dir] = sorted(articles)
                    print(f"📁 发现分类 {category_dir}: {len(articles)} 个文章")
    
    # 如果结构化内容目录没有内容，降级扫描传统分类目录
    if not categories and os.path.exists(CATEGORIES_DIR):
        print(f"🔍 降级扫描传统分类目录: {CATEGORIES_DIR}")
        for category_dir in os.listdir(CATEGORIES_DIR):
            category_path = os.path.join(CATEGORIES_DIR, category_dir)
            
            if os.path.isdir(category_path):
                articles = []
                for file_name in os.listdir(category_path):
                    if file_name.endswith('.json'):
                        articles.append(file_name[:-5])  # 移除 .json 扩展名
                
                if articles:
                    categories[category_dir] = sorted(articles)
    
    if not categories:
        print(f"⚠️ 未找到任何内容文件在 {content_dir} 或 {CATEGORIES_DIR}")
    
    return categories

def load_article_file(category: str, article_id: str) -> Optional[Dict[str, Any]]:
    """加载单个文章文件"""
    # 优先从结构化内容目录加载
    content_file_path = os.path.join(CATEGORIES_DIR, category, f"{article_id}.json")
    
    if os.path.exists(content_file_path):
        try:
            with open(content_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 转换结构化内容格式为API格式
                if 'meta' in data and 'content' in data:
                    # 保存原始content用于structuredContent
                    original_content = data['content']
                    return {
                        'title': data['meta'].get('title', ''),
                        'category': data['meta'].get('category', category),
                        'publishDate': data['meta'].get('publishDate', ''),
                        'content': original_content if isinstance(original_content, str) else json.dumps(original_content, ensure_ascii=False),
                        'imagePath': data['meta'].get('imagePath', ''),
                        'excerpt': data['meta'].get('excerpt', ''),
                        'tags': data['meta'].get('tags', []),
                        'readTime': data['meta'].get('readTime', ''),
                        'author': data['meta'].get('author', ''),
                        'source': 'structured_content',
                        'structuredContent': original_content if isinstance(original_content, dict) else None
                    }
                return data
        except Exception as e:
            print(f"❌ 加载结构化内容文件失败 {content_file_path}: {e}")
    
    # 降级到传统分类目录
    file_path = os.path.join(CATEGORIES_DIR, category, f"{article_id}.json")
    
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载文章文件失败 {file_path}: {e}")
        return None

def get_blog_data() -> Dict[str, Any]:
    """获取博客数据（自动扫描）"""
    global cached_blog_data, last_scan_time
    
    current_time = time.time()
    
    # 检查缓存是否有效
    if cached_blog_data and (current_time - last_scan_time) < CACHE_TTL:
        return cached_blog_data
    
    print("🔄 开始扫描文章文件...")
    
    categories_map = scan_categories()
    blog_data = {
        "categories": {},
        "lastUpdated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "file_scan"
    }
    
    for category_key, article_ids in categories_map.items():
        category_info = {
            "title": category_key.replace('_', ' ').title(),
            "href": f"/{category_key}",
            "description": f"{category_key.replace('_', ' ').title()}相关内容",
            "articles": {}
        }
        
        for article_id in article_ids:
            article_data = load_article_file(category_key, article_id)
            if article_data:
                category_info["articles"][article_id] = article_data
        
        if category_info["articles"]:
            blog_data["categories"][category_key] = category_info
    
    # 更新缓存
    cached_blog_data = blog_data
    last_scan_time = current_time
    
    print(f"✅ 扫描完成，找到 {len(blog_data['categories'])} 个分类")
    return blog_data

def get_article_content(category: str, article_id: str) -> Optional[Dict[str, Any]]:
    """获取文章内容（从文件系统）"""
    try:
        print(f"🔍 获取文章内容: {category}/{article_id}")
        article_data = load_article_file(category, article_id)
        if not article_data:
            print(f"❌ 未找到文章数据: {category}/{article_id}")
            return None
        
        print(f"✅ 找到文章数据: {type(article_data)}")
        
        # 安全获取content
        content = article_data.get("content", "")
        if content is None:
            content = ""
        
        # 安全生成excerpt
        excerpt = article_data.get("excerpt")
        if not excerpt:
            excerpt = str(content)[:160] + "..." if content else "..."
        
        # 构造详细文章数据
        return {
            "id": article_data.get("id", article_id),
            "title": article_data.get("title", "Untitled"),
            "category": category,
            "publishDate": article_data.get("publishDate", "2024-01-01"),
            "content": str(content),
            "excerpt": str(excerpt),
            "tags": article_data.get("tags", ["技术", "博客"]),
            "readTime": article_data.get("readTime", "5分钟"),
            "author": article_data.get("author", "XRAK"),
            "imagePath": article_data.get("imagePath"),
            "source": article_data.get("source", "file_system"),
            "structuredContent": article_data.get("structuredContent")
        }
    except Exception as e:
        print(f"❌ get_article_content错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_category_content(category_key: str) -> Optional[Dict[str, Any]]:
    """获取分类内容（从文件系统）"""
    data = get_blog_data()
    
    if category_key not in data.get('categories', {}):
        return None
    
    category_data = data['categories'][category_key]
    
    # 构造分类响应数据
    articles = []
    if 'articles' in category_data:
        for article_id, article in category_data['articles'].items():
            articles.append({
                "id": article.get("id", article_id),
                "title": article.get("title", "Untitled"),
                "category": category_data.get("title", category_key),
                "publishDate": article.get("publishDate", "2024-01-01"),
                "content": article.get("content", ""),
                "excerpt": article.get("excerpt") or (str(article.get("content", ""))[:160] + "..."),
                "tags": article.get("tags", ["技术", "博客"]),
                "readTime": article.get("readTime", "5分钟"),
                "author": article.get("author", "XRAK"),
                "imagePath": article.get("imagePath"),
                "source": "file_system"
            })
    
    return {
        "categoryInfo": {
            "name": category_data.get("title", category_key),
            "href": category_data.get("href", f"/{category_key}"),
            "description": category_data.get("description", f"{category_data.get('title', category_key)}相关内容"),
            "defaultArticle": category_data.get("defaultArticle")
        },
        "articles": articles
    }

# JSON文件读取相关函数（来自api_test.py）
def get_json_data() -> Dict[str, Any]:
    """从JSON文件获取博客数据"""
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data["source"] = "json_file"
        return data
    except FileNotFoundError:
        print(f"⚠️ JSON文件不存在: {JSON_FILE}")
        return {"categories": {}, "source": "empty"}
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        return {"categories": {}, "source": "error"}

def get_article_from_json(category: str, article_id: str) -> Optional[Dict[str, Any]]:
    """从JSON文件获取文章内容"""
    try:
        print(f"🔍 从JSON获取文章: {category}/{article_id}")
        data = get_json_data()
        
        if category not in data.get('categories', {}):
            print(f"❌ 分类不存在: {category}")
            return None
        
        category_data = data['categories'][category]
        if 'articles' not in category_data or article_id not in category_data['articles']:
            print(f"❌ 文章不存在: {article_id}")
            return None
        
        article = category_data['articles'][article_id]
        print(f"✅ 找到JSON文章数据: {type(article)}")
        
        # 安全获取content
        content = article.get("content", "")
        if content is None:
            content = ""
        
        # 安全生成excerpt
        excerpt = article.get("excerpt")
        if not excerpt:
            excerpt = str(content)[:160] + "..." if content else "..."
        
        # 构造详细文章数据
        return {
            "id": article.get("id", article_id),
            "title": article.get("title", "Untitled"),
            "category": category_data.get("title", category),
            "publishDate": article.get("publishDate", "2024-01-01"),
            "content": str(content),
            "excerpt": str(excerpt),
            "tags": article.get("tags", ["技术", "博客"]),
            "readTime": article.get("readTime", "5分钟"),
            "author": article.get("author", "XRAK"),
            "imagePath": article.get("imagePath"),
            "source": "json_file",
            "structuredContent": {
                "blocks": article.get("blocks", [])
            } if article.get("blocks") else None
        }
    except Exception as e:
        print(f"❌ 从JSON获取文章失败: {e}")
        return None

def get_category_from_json(category_key: str) -> Optional[Dict[str, Any]]:
    """从JSON文件获取分类内容"""
    try:
        data = get_json_data()
        
        if category_key not in data.get('categories', {}):
            return None
        
        category_data = data['categories'][category_key]
        
        # 构造分类响应数据
        articles = []
        if 'articles' in category_data:
            for article_id, article in category_data['articles'].items():
                articles.append({
                    "id": article.get("id", article_id),
                    "title": article.get("title", "Untitled"),
                    "category": category_data.get("title", category_key),
                    "publishDate": article.get("publishDate", "2024-01-01"),
                    "content": article.get("content", ""),
                    "excerpt": article.get("excerpt") or (str(article.get("content", ""))[:160] + "..."),
                    "tags": article.get("tags", ["技术", "博客"]),
                    "readTime": article.get("readTime", "5分钟"),
                    "author": article.get("author", "XRAK"),
                    "imagePath": article.get("imagePath"),
                    "source": "json_file"
                })
        
        return {
            "categoryInfo": {
                "name": category_data.get("title", category_key),
                "href": category_data.get("href", f"/{category_key}"),
                "description": category_data.get("description", f"{category_data.get('title', category_key)}相关内容"),
                "defaultArticle": category_data.get("defaultArticle")
            },
            "articles": articles
        }
    except Exception as e:
        print(f"❌ 从JSON获取分类失败: {e}")
        return None

def create_handler_class(port):
    """创建带端口参数的处理器类"""
    class PortAwareHandler(UnifiedBlogDataHandler):
        def __init__(self, *args, **kwargs):
            kwargs['port'] = port
            super().__init__(*args, **kwargs)
    return PortAwareHandler

def start_server(port=DEFAULT_PORT):
    """启动服务器"""
    try:
        handler_class = create_handler_class(port)
        with socketserver.TCPServer(("", port), handler_class) as httpd:
            print(f"🚀 XRAK 统一博客API服务器启动成功!")
            print(f"📡 服务地址: http://localhost:{port}")
            print(f"📊 健康检查: http://localhost:{port}/health")
            print(f"📚 博客数据: http://localhost:{port}/api/blog-data")
            print(f"📁 文档目录: {DOCS_DIR}")
            print(f"📂 分类目录: {CATEGORIES_DIR}")
            print(f"📄 JSON文件: {JSON_FILE}")
            print("\n按 Ctrl+C 停止服务器")
            print("=" * 50)
            
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 10048:  # Windows: Address already in use
            print(f"❌ 端口 {port} 已被占用，请尝试其他端口")
            print(f"💡 建议使用: python unified_blog_api.py --port {port + 1}")
        else:
            print(f"❌ 启动服务器失败: {e}")
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")

def main():
    """主函数"""
    # 声明全局变量
    global DOCS_DIR, CATEGORIES_DIR, JSON_FILE
    
    parser = argparse.ArgumentParser(description='XRAK 统一博客API服务器')
    parser.add_argument('--port', '-p', type=int, default=DEFAULT_PORT,
                       help=f'服务器端口 (默认: {DEFAULT_PORT})')
    parser.add_argument('--docs-dir', '-d', type=str, default=DOCS_DIR,
                       help=f'文档目录 (默认: {DOCS_DIR})')
    
    args = parser.parse_args()
    
    # 更新全局配置
    DOCS_DIR = args.docs_dir
    CATEGORIES_DIR = os.path.join(DOCS_DIR, "categories")
    JSON_FILE = os.path.join(DOCS_DIR, "blog-data.json")
    
    print(f"📁 使用文档目录: {DOCS_DIR}")
    print(f"📂 使用分类目录: {CATEGORIES_DIR}")
    print(f"📄 使用JSON文件: {JSON_FILE}")
    
    start_server(args.port)

if __name__ == "__main__":
    main()