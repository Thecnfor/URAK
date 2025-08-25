import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

// 后端API基础URL
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const { username, password } = await request.json();
    const csrfToken = request.headers.get('X-CSRF-Token');

    // 验证输入
    if (!username || !password) {
      return NextResponse.json(
        { error: '用户名和密码不能为空' },
        { status: 400 }
      );
    }

    // 调用后端登录API
    const backendResponse = await fetch(`${BACKEND_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRF-Token': csrfToken }),
      },
      body: JSON.stringify({
        username,
        password,
      }),
    });

    const backendData = await backendResponse.json();

    if (!backendResponse.ok) {
      return NextResponse.json(
        { error: backendData.message || '登录失败' },
        { status: backendResponse.status }
      );
    }

    // 从后端响应中提取令牌和用户信息
    const { access_token, user, expires_in } = backendData.data;
    
    // 设置安全的cookies
    const cookieStore = await cookies();
    
    // 设置认证令牌cookie
    cookieStore.set('auth-token', access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: expires_in || 24 * 60 * 60, // 使用后端返回的过期时间或默认24小时
      path: '/',
    });

    // 生成会话ID
    const sessionId = crypto.randomUUID();
    cookieStore.set('session-id', sessionId, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: expires_in || 24 * 60 * 60,
      path: '/',
    });

    // 计算会话过期时间
    const sessionExpiry = Date.now() + (expires_in || 24 * 60 * 60) * 1000;

    return NextResponse.json({
      message: '登录成功',
      user: {
        id: user.user_id,
        username: user.username,
        email: user.email,
        role: user.role,
        lastLogin: new Date().toISOString(),
      },
      sessionExpiry,
    });
  } catch (error) {
    console.error('登录错误:', error);
    return NextResponse.json(
      { error: '网络错误，请稍后重试' },
      { status: 500 }
    );
  }
}