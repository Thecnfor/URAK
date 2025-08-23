import { createSlice, PayloadAction } from '@reduxjs/toolkit';

// 定义应用状态接口
interface AppState {
  isLoading: boolean;
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
}

// 初始状态
const initialState: AppState = {
  isLoading: false,
  theme: 'light',
  sidebarOpen: false,
};

// 创建slice
const appSlice = createSlice({
  name: 'app',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    toggleTheme: (state) => {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
    },
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload;
    },
  },
});

// 导出actions
export const { setLoading, toggleTheme, toggleSidebar, setSidebarOpen } = appSlice.actions;

// 导出reducer
export default appSlice.reducer;

// 选择器
export const selectIsLoading = (state: { app: AppState }) => state.app.isLoading;
export const selectTheme = (state: { app: AppState }) => state.app.theme;
export const selectSidebarOpen = (state: { app: AppState }) => state.app.sidebarOpen;