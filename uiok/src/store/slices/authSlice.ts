import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

// 用户接口定义
export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  lastLogin?: string;
}

// 认证状态接口
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  csrfToken: string | null;
  accessToken: string | null;
  refreshToken: string | null;
}

// 初始状态
const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  csrfToken: null,
  accessToken: null,
  refreshToken: null,
};

// 异步登录action
export const loginUser = createAsyncThunk(
  'auth/loginUser',
  async (credentials: { username: string; password: string }, { rejectWithValue }) => {
    try {
      // 首先获取CSRF令牌
      const csrfResponse = await fetch('/api/auth/csrf-token');
      if (!csrfResponse.ok) {
        throw new Error('获取CSRF令牌失败');
      }
      const csrfData = await csrfResponse.json();
      
      // 执行登录
      const loginResponse = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfData.csrf_token,
        },
        body: JSON.stringify(credentials),
      });

      if (!loginResponse.ok) {
        const errorData = await loginResponse.json();
        throw new Error(errorData.error || '登录失败');
      }

      const userData = await loginResponse.json();
      
      // 存储access token到localStorage
      if (userData.access_token) {
        localStorage.setItem('access_token', userData.access_token);
      }
      if (userData.refresh_token) {
        localStorage.setItem('refresh_token', userData.refresh_token);
      }
      
      return { 
        user: userData.user_info, // 后端返回的是user_info而不是user
        csrfToken: userData.csrf_token || csrfData.csrf_token,
        accessToken: userData.access_token,
        refreshToken: userData.refresh_token
      };
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : '登录失败');
    }
  }
);

// 异步验证session action
export const validateSession = createAsyncThunk(
  'auth/validateSession',
  async (_, { rejectWithValue }) => {
    try {
      const accessToken = localStorage.getItem('access_token');
      if (!accessToken) {
        throw new Error('未找到访问令牌');
      }
      
      const response = await fetch('/api/auth/validate', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        // 如果token无效，清除本地存储
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        throw new Error('会话验证失败');
      }
      
      const userData = await response.json();
      return userData.user_info || userData; // 适配后端响应格式
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : '会话验证失败');
    }
  }
);

// 异步登出action
export const logoutUser = createAsyncThunk(
  'auth/logoutUser',
  async (_, { rejectWithValue }) => {
    try {
      const accessToken = localStorage.getItem('access_token');
      
      if (accessToken) {
        const response = await fetch('/api/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          console.warn('服务器登出失败，但仍清除本地状态');
        }
      }
      
      // 无论服务器响应如何，都清除本地存储
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');

      return true;
    } catch (error) {
      // 即使出错也要清除本地存储
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      return rejectWithValue(error instanceof Error ? error.message : '登出失败');
    }
  }
);

// 获取CSRF令牌action
export const fetchCSRFToken = createAsyncThunk(
  'auth/fetchCSRFToken',
  async (_, { rejectWithValue }) => {
    try {
      const response = await fetch('/api/auth/csrf-token');
      if (!response.ok) {
        throw new Error('获取CSRF令牌失败');
      }
      const data = await response.json();
      return data.csrf_token;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : '获取CSRF令牌失败');
    }
  }
);

// 初始化认证状态（检查localStorage中的token）
export const initializeAuth = createAsyncThunk(
  'auth/initializeAuth',
  async (_, { dispatch, rejectWithValue }) => {
    try {
      const accessToken = localStorage.getItem('access_token');
      if (accessToken) {
        // 如果有token，尝试验证会话
        await dispatch(validateSession()).unwrap();
        return true;
      }
      // 没有token时直接返回false，不抛出错误
      return false;
    } catch (error) {
      // 如果验证失败，清除无效token
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      // 验证失败时返回false而不是抛出错误
      return false;
    }
  }
);

// 认证切片
const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setUser: (state, action: PayloadAction<User>) => {
      state.user = action.payload;
      state.isAuthenticated = true;
    },
    clearAuth: (state) => {
      state.user = null;
      state.isAuthenticated = false;
      state.csrfToken = null;
      state.accessToken = null;
      state.refreshToken = null;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // 登录
      .addCase(loginUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload.user;
        state.isAuthenticated = true;
        state.csrfToken = action.payload.csrfToken;
        state.accessToken = action.payload.accessToken;
        state.refreshToken = action.payload.refreshToken;
        state.error = null;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        state.isAuthenticated = false;
        state.user = null;
        state.accessToken = null;
        state.refreshToken = null;
      })
      // 会话验证
      .addCase(validateSession.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(validateSession.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
        state.error = null;
      })
      .addCase(validateSession.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        state.isAuthenticated = false;
        state.user = null;
        state.accessToken = null;
        state.refreshToken = null;
      })
      // 登出
      .addCase(logoutUser.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(logoutUser.fulfilled, (state) => {
        state.isLoading = false;
        state.user = null;
        state.isAuthenticated = false;
        state.csrfToken = null;
        state.accessToken = null;
        state.refreshToken = null;
        state.error = null;
      })
      .addCase(logoutUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // CSRF令牌
      .addCase(fetchCSRFToken.fulfilled, (state, action) => {
        state.csrfToken = action.payload;
      })
      .addCase(fetchCSRFToken.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      // 初始化认证
      .addCase(initializeAuth.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(initializeAuth.fulfilled, (state) => {
        state.isLoading = false;
        // validateSession已经处理了用户状态更新
      })
      .addCase(initializeAuth.rejected, (state) => {
        state.isLoading = false;
        state.isAuthenticated = false;
        state.user = null;
        state.accessToken = null;
        state.refreshToken = null;
      });
  },
});

export const { clearError, setUser, clearAuth } = authSlice.actions;
export default authSlice.reducer;