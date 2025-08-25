'use client';

import { useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useAppSelector } from '@/lib/store';
import { selectIsAuthenticated, selectIsLoading, selectUser } from '@/lib/features/auth/authSlice';

interface ProtectedLayoutProps {
  children: ReactNode;
  requireRole?: 'admin' | 'user';
  fallback?: ReactNode;
}

export function ProtectedLayout({ 
  children, 
  requireRole,
  fallback = <div className="flex items-center justify-center min-h-screen">加载中...</div>
}: ProtectedLayoutProps) {
  const router = useRouter();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const isLoading = useAppSelector(selectIsLoading);
  const user = useAppSelector(selectUser);

  useEffect(() => {
    // 如果未认证且不在加载中，重定向到登录页
    if (!isLoading && !isAuthenticated) {
      const currentPath = window.location.pathname;
      router.push(`/login?redirect=${encodeURIComponent(currentPath)}`);
    }
  }, [isAuthenticated, isLoading, router]);

  // 如果正在加载，显示加载状态
  if (isLoading) {
    return <>{fallback}</>;
  }

  // 如果未认证，显示加载状态（等待重定向）
  if (!isAuthenticated) {
    return <>{fallback}</>;
  }

  // 如果需要特定角色但用户角色不匹配
  if (requireRole && user?.role !== requireRole) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">访问被拒绝</h1>
          <p className="text-gray-600">您没有权限访问此页面</p>
          <button
            onClick={() => router.back()}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            返回
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}