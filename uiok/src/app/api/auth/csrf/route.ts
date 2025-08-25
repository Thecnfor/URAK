import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

// 后端API基础URL
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    console.log('正在调用后端CSRF端点:', `${BACKEND_URL}/api/auth/csrf-token`);
    
    // 调用后端获取CSRF令牌
    const backendResponse = await fetch(`${BACKEND_URL}/api/auth/csrf-token`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    console.log('后端响应状态:', backendResponse.status, backendResponse.statusText);

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      console.error('后端响应错误:', errorText);
      throw new Error(`后端CSRF令牌获取失败: ${backendResponse.status} ${backendResponse.statusText}`);
    }

    const backendData = await backendResponse.json();
    const csrfToken = backendData.csrf_token;

    if (!csrfToken) {
      throw new Error('后端返回的CSRF令牌无效');
    }
    
    const cookieStore = await cookies();
    
    // 设置CSRF令牌cookie（客户端可读，用于表单提交）
    cookieStore.set('csrf-token', csrfToken, {
      httpOnly: false, // 客户端需要读取
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 24 * 60 * 60, // 24小时
      path: '/'
    });

    return NextResponse.json({
      csrfToken,
      message: 'CSRF令牌获取成功'
    });
  } catch (error) {
    console.error('CSRF令牌获取错误:', error);
    return NextResponse.json(
      { error: 'CSRF令牌获取失败' },
      { status: 500 }
    );
  }
}