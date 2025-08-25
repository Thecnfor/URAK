'use client';

import { ProtectedLayout } from '@/components/layout/protected-layout';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { logoutUser } from '@/store/slices/authSlice';
import { useRouter } from 'next/navigation';

export default function DashboardPage() {
  const user = useAppSelector((state) => state.auth.user);
  const dispatch = useAppDispatch();
  const router = useRouter();

  const handleLogout = () => {
    dispatch(logoutUser()).then(() => {
      router.push('/login');
    });
  };

  return (
    <ProtectedLayout>
      <div className="min-h-screen bg-gray-50">
        {/* 顶部导航栏 */}
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <h1 className="text-xl font-semibold text-gray-900">
                  用户仪表板
                </h1>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-700">
                  欢迎, {user?.username}
                </span>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {user?.role === 'admin' ? '管理员' : '用户'}
                </span>
                {user?.role === 'admin' && (
                  <button
                    onClick={() => router.push('/admin')}
                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
                  >
                    管理员面板
                  </button>
                )}
                <button
                  onClick={handleLogout}
                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  登出
                </button>
              </div>
            </div>
          </div>
        </nav>

        {/* 主要内容区域 */}
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            <div className="border-4 border-dashed border-gray-200 rounded-lg p-8">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  用户仪表板
                </h2>
                <p className="text-gray-600 mb-8">
                  这是一个受保护的用户页面，需要登录才能访问。
                </p>
                
                {/* 用户信息卡片 */}
                <div className="bg-white overflow-hidden shadow rounded-lg max-w-md mx-auto">
                  <div className="px-4 py-5 sm:p-6">
                    <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                      个人信息
                    </h3>
                    <dl className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2">
                      <div>
                        <dt className="text-sm font-medium text-gray-500">用户ID</dt>
                        <dd className="mt-1 text-sm text-gray-900">{user?.id}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-gray-500">用户名</dt>
                        <dd className="mt-1 text-sm text-gray-900">{user?.username}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-gray-500">邮箱</dt>
                        <dd className="mt-1 text-sm text-gray-900">{user?.email}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-gray-500">角色</dt>
                        <dd className="mt-1 text-sm text-gray-900">
                          {user?.role === 'admin' ? '管理员' : '用户'}
                        </dd>
                      </div>
                      <div className="sm:col-span-2">
                        <dt className="text-sm font-medium text-gray-500">最后登录</dt>
                        <dd className="mt-1 text-sm text-gray-900">
                          {user?.lastLogin ? new Date(user.lastLogin).toLocaleString('zh-CN') : '未知'}
                        </dd>
                      </div>
                    </dl>
                  </div>
                </div>

                {/* 功能说明 */}
                <div className="mt-8 bg-green-50 border border-green-200 rounded-md p-4">
                  <h4 className="text-sm font-medium text-green-900 mb-2">安全登录成功</h4>
                  <p className="text-sm text-green-700">
                    您已成功通过身份验证系统登录，所有安全措施均已启用。
                  </p>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </ProtectedLayout>
  );
}