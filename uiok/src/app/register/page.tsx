'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { registerUser, clearError } from '@/store/slices/authSlice';
import { validateRegisterForm, validateField, getFieldValidationRules, type RegisterFormData } from '@/utils/validation';
import { FIELD_NAMES, FieldErrors, TouchedFields } from '@/config/validation';

export default function RegisterPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const { isLoading, error } = useAppSelector((state) => state.auth);
  
  const [formData, setFormData] = useState<RegisterFormData>({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({
    username: [],
    email: [],
    password: [],
    confirmPassword: [],
  });
  
  const [touched, setTouched] = useState<TouchedFields>({
    username: false,
    email: false,
    password: false,
    confirmPassword: false,
  });
  
  const [success, setSuccess] = useState<string | null>(null);

  // 清除错误信息当组件卸载时
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
    
    // 清除错误信息
    if (error) dispatch(clearError());
    if (success) setSuccess(null);
    
    // 如果字段已被触摸，实时验证
    if (touched[name as keyof typeof touched]) {
      validateSingleField(name, value);
    }
  };

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setTouched(prev => ({
      ...prev,
      [name]: true,
    }));
    
    validateSingleField(name, value);
  };

  const validateSingleField = (fieldName: string, value: string) => {
    if (!['username', 'email', 'password', 'confirmPassword'].includes(fieldName)) return;
    
    const displayName = FIELD_NAMES[fieldName as keyof typeof FIELD_NAMES];
    let validation;
    
    if (fieldName === 'confirmPassword') {
      const rules = getFieldValidationRules('confirmPassword');
      validation = validateField(value, displayName, rules);
      
      // 检查密码是否匹配
      if (validation.isValid && value !== formData.password) {
        validation = {
          isValid: false,
          errors: ['两次输入的密码不一致']
        };
      }
    } else {
      const rules = getFieldValidationRules(fieldName as 'username' | 'email' | 'password');
      validation = validateField(value, displayName, rules);
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
      email: true,
      password: true,
      confirmPassword: true,
    });
    
    // 验证整个表单
    const validation = validateRegisterForm(formData);
    
    if (!validation.isValid) {
      // 设置字段错误
      const usernameRules = getFieldValidationRules('username');
      const emailRules = getFieldValidationRules('email');
      const passwordRules = getFieldValidationRules('password');
      const confirmPasswordRules = getFieldValidationRules('confirmPassword');
      
      const usernameValidation = validateField(formData.username, FIELD_NAMES.username, usernameRules);
      const emailValidation = validateField(formData.email, FIELD_NAMES.email, emailRules);
      const passwordValidation = validateField(formData.password, FIELD_NAMES.password, passwordRules);
      let confirmPasswordValidation = validateField(formData.confirmPassword, FIELD_NAMES.confirmPassword, confirmPasswordRules);
      
      if (confirmPasswordValidation.isValid && formData.confirmPassword !== formData.password) {
        confirmPasswordValidation = {
          isValid: false,
          errors: ['两次输入的密码不一致']
        };
      }
      
      setFieldErrors({
        username: usernameValidation.errors,
        email: emailValidation.errors,
        password: passwordValidation.errors,
        confirmPassword: confirmPasswordValidation.errors,
      });
      
      return;
    }
    
    // 清除字段错误
    setFieldErrors({
      username: [],
      email: [],
      password: [],
      confirmPassword: [],
    });

    dispatch(clearError());
    setSuccess(null);

    try {
      await dispatch(registerUser({
        username: formData.username,
        email: formData.email,
        password: formData.password,
      })).unwrap();
      
      setSuccess('注册成功！正在跳转到登录页面...');
      setTimeout(() => {
        router.push('/login');
      }, 2000);
    } catch (err) {
      // 错误已经通过Redux状态管理处理
      console.error('注册失败:', err);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            注册管理员账户
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            创建您的管理员账户
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm space-y-4">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                用户名
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                className={`appearance-none relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm ${
                  touched.username && fieldErrors.username.length > 0
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                    : 'border-gray-300'
                }`}
                placeholder="请输入用户名"
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
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                邮箱
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                className={`appearance-none relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm ${
                  touched.email && fieldErrors.email.length > 0
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                    : 'border-gray-300'
                }`}
                placeholder="请输入邮箱地址"
                value={formData.email}
                onChange={handleInputChange}
                onBlur={handleBlur}
                disabled={isLoading}
              />
              {touched.email && fieldErrors.email.length > 0 && (
                <div className="mt-1">
                  {fieldErrors.email.map((error, index) => (
                    <p key={index} className="text-sm text-red-600">{error}</p>
                  ))}
                </div>
              )}
            </div>
            
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                密码
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className={`appearance-none relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm ${
                  touched.password && fieldErrors.password.length > 0
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                    : 'border-gray-300'
                }`}
                placeholder="请输入密码（至少6位）"
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
            
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
                确认密码
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                required
                className={`appearance-none relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm ${
                  touched.confirmPassword && fieldErrors.confirmPassword.length > 0
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                    : 'border-gray-300'
                }`}
                placeholder="请再次输入密码"
                value={formData.confirmPassword}
                onChange={handleInputChange}
                onBlur={handleBlur}
                disabled={isLoading}
              />
              {touched.confirmPassword && fieldErrors.confirmPassword.length > 0 && (
                <div className="mt-1">
                  {fieldErrors.confirmPassword.map((error, index) => (
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
          
          {success && (
            <div className="rounded-md bg-green-50 p-4">
              <div className="text-sm text-green-700">{success}</div>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={isLoading || !formData.username || !formData.email || !formData.password || !formData.confirmPassword}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? '注册中...' : '注册'}
            </button>
          </div>

          <div className="text-center">
            <div className="text-sm text-gray-600">
              <p>
                已有账户？{' '}
                <Link href="/login" className="font-medium text-indigo-600 hover:text-indigo-500">
                  立即登录
                </Link>
              </p>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}