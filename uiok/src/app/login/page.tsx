'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { 
  loginUser, 
  fetchCSRFToken, 
  clearError
} from '@/store/slices/authSlice';
import { validateLoginForm, validateField, type LoginFormData } from '@/utils/validation';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const dispatch = useAppDispatch();
  
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);
  const isLoading = useAppSelector((state) => state.auth.isLoading);
  const error = useAppSelector((state) => state.auth.error);
  const csrfToken = useAppSelector((state) => state.auth.csrfToken);
  
  const [formData, setFormData] = useState<LoginFormData>({
    username: '',
    password: '',
  });
  
  const [fieldErrors, setFieldErrors] = useState<{
    username: string[];
    password: string[];
  }>({
    username: [],
    password: [],
  });
  
  const [touched, setTouched] = useState<{
    username: boolean;
    password: boolean;
  }>({
    username: false,
    password: false,
  });
  
  const redirectTo = searchParams.get('redirect') || '/admin';

  // 如果已经登录，重定向到目标页面
  useEffect(() => {
    if (isAuthenticated) {
      router.push(redirectTo);
    }
  }, [isAuthenticated, router, redirectTo]);

  // 获取CSRF令牌
  useEffect(() => {
    if (!csrfToken) {
      dispatch(fetchCSRFToken());
    }
  }, [dispatch, csrfToken]);

  // 清除错误信息
  useEffect(() => {
    return () => {
      dispatch(clearError());
    };
  }, [dispatch]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
    
    // 实时验证
    if (touched[name as keyof typeof touched]) {
      validateSingleField(name as keyof LoginFormData, value);
    }
  };
  
  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    const fieldName = name as keyof LoginFormData;
    
    setTouched(prev => ({
      ...prev,
      [fieldName]: true,
    }));
    
    validateSingleField(fieldName, value);
  };
  
  const validateSingleField = (fieldName: keyof LoginFormData, value: string) => {
    let validation;
    
    if (fieldName === 'username') {
      validation = validateField(value, '用户名', {
        required: true,
        minLength: 3,
        maxLength: 50,
        pattern: /^[a-zA-Z0-9_]+$/,
        patternMessage: '用户名只能包含字母、数字和下划线'
      });
    } else if (fieldName === 'password') {
      validation = validateField(value, '密码', {
        required: true,
        minLength: 6,
        maxLength: 100
      });
    } else {
      return;
    }
    
    setFieldErrors(prev => ({
      ...prev,
      [fieldName]: validation.errors,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // 标记所有字段为已触摸
    setTouched({
      username: true,
      password: true,
    });
    
    // 验证整个表单
    const validation = validateLoginForm(formData);
    
    if (!validation.isValid) {
      // 设置字段错误
      const usernameValidation = validateField(formData.username, '用户名', {
        required: true,
        minLength: 3,
        maxLength: 50,
        pattern: /^[a-zA-Z0-9_]+$/,
        patternMessage: '用户名只能包含字母、数字和下划线'
      });
      
      const passwordValidation = validateField(formData.password, '密码', {
        required: true,
        minLength: 6,
        maxLength: 100
      });
      
      setFieldErrors({
        username: usernameValidation.errors,
        password: passwordValidation.errors,
      });
      
      return;
    }
    
    // 清除字段错误
    setFieldErrors({
      username: [],
      password: [],
    });

    dispatch(loginUser({
      username: formData.username,
      password: formData.password,
    }));
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            登录后台管理系统
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            请使用您的管理员账户登录
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="username" className="sr-only">
                用户名
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                className={`appearance-none rounded-none relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm ${
                  touched.username && fieldErrors.username.length > 0
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                    : 'border-gray-300'
                }`}
                placeholder="用户名"
                value={formData.username}
                onChange={handleInputChange}
                onBlur={handleBlur}
                disabled={isLoading}
              />
              {touched.username && fieldErrors.username.length > 0 && (
                <div className="mt-1">
                  {fieldErrors.username.map((error, index) => (
                    <p key={index} className="text-sm text-red-600">{error}</p>
                  ))}
                </div>
              )}
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                密码
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className={`appearance-none rounded-none relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm ${
                  touched.password && fieldErrors.password.length > 0
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                    : 'border-gray-300'
                }`}
                placeholder="密码"
                value={formData.password}
                onChange={handleInputChange}
                onBlur={handleBlur}
                disabled={isLoading}
              />
              {touched.password && fieldErrors.password.length > 0 && (
                <div className="mt-1">
                  {fieldErrors.password.map((error, index) => (
                    <p key={index} className="text-sm text-red-600">{error}</p>
                  ))}
                </div>
              )}
            </div>
          </div>

          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-700">{error}</div>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={isLoading || !formData.username || !formData.password}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? '登录中...' : '登录'}
            </button>
          </div>

          <div className="text-center space-y-4">
            <div className="text-sm text-gray-600">
              <p>
                还没有账户？{' '}
                <Link href="/register" className="font-medium text-indigo-600 hover:text-indigo-500">
                  立即注册
                </Link>
              </p>
            </div>
            
            <div className="text-sm text-gray-600">
              <p>测试账户：</p>
              <p>管理员 - 用户名: admin, 密码: admin123</p>
              <p>普通用户 - 用户名: user, 密码: user123</p>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}