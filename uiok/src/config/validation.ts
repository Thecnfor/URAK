// 统一的验证配置，确保前后端一致性

// 验证规则配置
export const VALIDATION_RULES = {
  username: {
    minLength: 3,
    maxLength: 50,
    pattern: /^[a-zA-Z0-9_]+$/,
    patternMessage: '用户名只能包含字母、数字和下划线'
  },
  password: {
    minLength: 8,
    maxLength: 128,
    // 根据后端安全配置的密码策略
    pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{}|;:,.<>?])[A-Za-z\d!@#$%^&*()_+\-=\[\]{}|;:,.<>?]+$/,
    patternMessage: '密码必须包含大小写字母、数字和特殊字符(!@#$%^&*()_+-=[]{}|;:,.<>?)'
  },
  email: {
    maxLength: 255,
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    patternMessage: '邮箱格式不正确'
  },
  confirmPassword: {
    required: true,
    patternMessage: '两次输入的密码不一致'
  }
} as const;

// 错误消息配置
export const ERROR_MESSAGES = {
  required: (field: string) => `${field}不能为空`,
  minLength: (field: string, min: number) => `${field}至少需要${min}个字符`,
  maxLength: (field: string, max: number) => `${field}不能超过${max}个字符`,
  pattern: (message: string) => message,
  passwordMismatch: '两次输入的密码不一致',
  // 通用错误消息
  networkError: '网络错误，请检查网络连接',
  serverError: '服务器错误，请稍后重试',
  unknownError: '未知错误，请稍后重试'
} as const;

// 字段名称映射
export const FIELD_NAMES = {
  username: '用户名',
  password: '密码',
  confirmPassword: '确认密码',
  email: '邮箱'
} as const;

// 验证结果接口
export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

// 验证规则接口
export interface FieldValidationRule {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  patternMessage?: string;
}

// 表单数据接口
export interface LoginFormData {
  username: string;
  password: string;
}

export interface RegisterFormData {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}

// 字段错误接口
export interface FieldErrors {
  [key: string]: string[];
}

// 触摸状态接口
export interface TouchedFields {
  [key: string]: boolean;
}