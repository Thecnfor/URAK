import { NextRequest, NextResponse } from 'next/server';
import { jwtVerify } from 'jose';

// JWT密钥
const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || 'your-super-secret-jwt-key-change-this-in-production'
);

// 受保护的路由
const PROTECTED_ROUTES = [
  '/admin',
  '/dashboard',
  '/api/admin',
  '/api/protected'
];

// 公开路由（不需要认证）
const PUBLIC_ROUTES = [
  '/login',
  '/api/auth/login',
  '/api/auth/csrf',
  '/api/auth/logout',
  '/api/auth/validate'
];

// 验证JWT令牌
async function verifyToken(token: string): Promise<boolean> {
  try {
    await jwtVerify(token, JWT_SECRET);
    return true;
  } catch {
    return false;
  }
}

// 检查路由是否受保护
function isProtectedRoute(pathname: string): boolean {
  return PROTECTED_ROUTES.some(route => pathname.startsWith(route));
}

// 检查路由是否公开
function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some(route => pathname.startsWith(route));
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // 如果是公开路由，直接通过
  if (isPublicRoute(pathname)) {
    return NextResponse.next();
  }

  // 如果是受保护的路由，检查认证
  if (isProtectedRoute(pathname)) {
    const token = request.cookies.get('auth-token')?.value;
    
    if (!token) {
      // 如果是API路由，返回401
      if (pathname.startsWith('/api/')) {
        return NextResponse.json(
          { error: '未授权访问' },
          { status: 401 }
        );
      }
      
      // 重定向到登录页面
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(loginUrl);
    }

    // 验证令牌
    const isValid = await verifyToken(token);
    if (!isValid) {
      // 清除无效的cookie
      const response = pathname.startsWith('/api/')
        ? NextResponse.json({ error: '令牌无效' }, { status: 401 })
        : NextResponse.redirect(new URL('/login', request.url));
      
      response.cookies.delete('auth-token');
      response.cookies.delete('session-id');
      return response;
    }
  }

  // 添加安全头
  const response = NextResponse.next();
  
  // 安全HTTP头
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  response.headers.set(
    'Content-Security-Policy',
    "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:;"
  );
  response.headers.set(
    'Strict-Transport-Security',
    'max-age=31536000; includeSubDomains'
  );
  
  // CSRF保护头
  if (request.method === 'POST' || request.method === 'PUT' || request.method === 'DELETE') {
    const csrfToken = request.headers.get('X-CSRF-Token');
    const sessionCSRF = request.cookies.get('csrf-token')?.value;
    
    if (pathname.startsWith('/api/') && !isPublicRoute(pathname)) {
      if (!csrfToken || !sessionCSRF || csrfToken !== sessionCSRF) {
        return NextResponse.json(
          { error: 'CSRF令牌无效' },
          { status: 403 }
        );
      }
    }
  }

  return response;
}

// 配置中间件匹配的路径
export const config = {
  matcher: [
    /*
     * 匹配所有请求路径，除了以下开头的：
     * - _next/static (静态文件)
     * - _next/image (图像优化文件)
     * - favicon.ico (favicon文件)
     * - public文件夹中的文件
     */
    '/((?!_next/static|_next/image|favicon.ico|public/).*)',
  ],
};