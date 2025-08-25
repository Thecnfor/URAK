// 表单验证工具函数

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

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
  } else if (password.length < 8) {
    errors.push('密码至少需要8个字符');
  } else if (password.length > 128) {
    errors.push('密码不能超过128个字符');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};

// 验证邮箱
export const validateEmail = (email: string): ValidationResult => {
  const errors: string[] = [];
  
  if (!email) {
    errors.push('邮箱不能为空');
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.push('邮箱格式不正确');
  } else if (email.length > 100) {
    errors.push('邮箱不能超过100个字符');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};

// 验证确认密码
export const validateConfirmPassword = (password: string, confirmPassword: string): ValidationResult => {
  const errors: string[] = [];
  
  if (!confirmPassword) {
    errors.push('确认密码不能为空');
  } else if (password !== confirmPassword) {
    errors.push('两次输入的密码不一致');
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

// 验证整个注册表单
export const validateRegisterForm = (formData: RegisterFormData): ValidationResult => {
  const usernameValidation = validateUsername(formData.username);
  const emailValidation = validateEmail(formData.email);
  const passwordValidation = validatePassword(formData.password);
  const confirmPasswordValidation = validateConfirmPassword(formData.password, formData.confirmPassword);
  
  const allErrors = [
    ...usernameValidation.errors,
    ...emailValidation.errors,
    ...passwordValidation.errors,
    ...confirmPasswordValidation.errors
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