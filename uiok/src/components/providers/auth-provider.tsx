'use client';

import { useEffect, ReactNode } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { initializeAuth, validateSession, fetchCSRFToken } from '@/store/slices/authSlice';

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);
  const isLoading = useAppSelector((state) => state.auth.isLoading);

  useEffect(() => {
    // 应用启动时初始化认证状态
    dispatch(initializeAuth());
    // 获取CSRF令牌
    dispatch(fetchCSRFToken());
  }, [dispatch]);

  // 设置会话检查定时器
  useEffect(() => {
    if (isAuthenticated) {
      // 每30分钟检查一次会话
      const interval = setInterval(() => {
        dispatch(validateSession());
      }, 30 * 60 * 1000);

      return () => clearInterval(interval);
    }
  }, [isAuthenticated, dispatch]);

  // 监听页面可见性变化，重新验证会话
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && isAuthenticated) {
        dispatch(validateSession());
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [isAuthenticated, dispatch]);

  return <>{children}</>;
}