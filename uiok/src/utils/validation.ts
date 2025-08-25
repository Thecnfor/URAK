// 表单验证工具函数

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

export interface LoginFormData {
  username: string;
  password: string;
}

// 验证用户名
export const validateUsername = (username: string): ValidationResult => {
  const errors: string[] = [];
  
  if (!username) {
    errors.push('用户名不能为空');
  } else if (username.length < 3) {
    errors.push('用户名至少需要3个字符');
  } else if (username.length > 50) {
    errors.push('用户名不能超过50个字符');
  } else if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    errors.push('用户名只能包含字母、数字和下划线');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};

// 验证密码
export const validatePassword = (password: string): ValidationResult => {
  const errors: string[] = [];
  
  if (!password) {
    errors.push('密码不能为空');
  } else if (password.length < 6) {
    errors.push('密码至少需要6个字符');
  } else if (password.length > 100) {
    errors.push('密码不能超过100个字符');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};

// 验证整个登录表单
export const validateLoginForm = (formData: LoginFormData): ValidationResult => {
  const usernameValidation = validateUsername(formData.username);
  const passwordValidation = validatePassword(formData.password);
  
  const allErrors = [
    ...usernameValidation.errors,
    ...passwordValidation.errors
  ];
  
  return {
    isValid: allErrors.length === 0,
    errors: allErrors
  };
};

// 通用字段验证
export const validateField = (value: string, fieldName: string, rules: {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  patternMessage?: string;
}): ValidationResult => {
  const errors: string[] = [];
  
  if (rules.required && !value) {
    errors.push(`${fieldName}不能为空`);
    return { isValid: false, errors };
  }
  
  if (value) {
    if (rules.minLength && value.length < rules.minLength) {
      errors.push(`${fieldName}至少需要${rules.minLength}个字符`);
    }
    
    if (rules.maxLength && value.length > rules.maxLength) {
      errors.push(`${fieldName}不能超过${rules.maxLength}个字符`);
    }
    
    if (rules.pattern && !rules.pattern.test(value)) {
      errors.push(rules.patternMessage || `${fieldName}格式不正确`);
    }
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};