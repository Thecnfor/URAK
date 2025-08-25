import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

// 后端API基础URL
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get('auth-token')?.value;

    if (!token) {
      return NextResponse.json(
        { error: '未找到认证令牌' },
        { status: 401 }
      );
    }

    // 调用后端验证API
    const backendResponse = await fetch(`${BACKEND_URL}/api/auth/validate`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    const backendData = await backendResponse.json();

    if (!backendResponse.ok) {
      // 清除无效的cookies
      const response = NextResponse.json(
        { error: backendData.message || '会话无效或已过期' },
        { status: backendResponse.status }
      );

      response.cookies.set('auth-token', '', {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 0,
        path: '/'
      });

      response.cookies.set('session-id', '', {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 0,
        path: '/'
      });

      return response;
    }

    // 从后端响应中提取用户信息
    const { user, expires_in } = backendData.data;
    
    // 计算会话过期时间
    const sessionExpiry = Date.now() + (expires_in || 24 * 60 * 60) * 1000;

    // 返回用户信息
    return NextResponse.json({
      user: {
        id: user.user_id,
        username: user.username,
        email: user.email,
        role: user.role,
        lastLogin: new Date().toISOString(),
      },
      sessionExpiry,
      tokenRefreshed: false,
    });
  } catch (error) {
    console.error('会话验证错误:', error);
    
    // 清除无效的cookies
    const response = NextResponse.json(
      { error: '网络错误，请稍后重试' },
      { status: 500 }
    );

    response.cookies.set('auth-token', '', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 0,
      path: '/'
    });

    response.cookies.set('session-id', '', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 0,
      path: '/'
    });

    return response;
  }
}