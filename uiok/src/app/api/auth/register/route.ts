import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { username, email, password, csrf_token } = body;

    // 验证必填字段
    if (!username || !email || !password) {
      return NextResponse.json(
        { success: false, message: '用户名、邮箱和密码为必填项' },
        { status: 400 }
      );
    }

    // 调用后端注册API
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    const backendResponse = await fetch(`${backendUrl}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username,
        email,
        password,
        csrf_token
      }),
    });

    const backendData = await backendResponse.json();

    if (backendResponse.ok && backendData.success) {
      // 注册成功
      return NextResponse.json({
        success: true,
        message: backendData.message || '注册成功',
        user: {
          id: backendData.user_info.id,
          username: backendData.user_info.username,
          email: backendData.user_info.email,
          role: backendData.user_info.role
        }
      });
    } else {
      // 注册失败
      return NextResponse.json(
        { 
          success: false, 
          message: backendData.detail || backendData.message || '注册失败' 
        },
        { status: backendResponse.status }
      );
    }
  } catch (error) {
    console.error('注册API错误:', error);
    return NextResponse.json(
      { success: false, message: '服务器错误，请稍后重试' },
      { status: 500 }
    );
  }
}