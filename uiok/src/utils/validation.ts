import { 
  VALIDATION_RULES, 
  ERROR_MESSAGES, 
  FIELD_NAMES,
  ValidationResult,
  FieldValidationRule,
  LoginFormData,
  RegisterFormData,
  FieldErrors,
  TouchedFields
} from '../config/validation';

// 验证用户名
export const validateUsername = (username: string): ValidationResult => {
  const errors: string[] = [];
  const rules = VALIDATION_RULES.username;
  
  if (!username) {
    errors.push(ERROR_MESSAGES.required(FIELD_NAMES.username));
  } else if (username.length < rules.minLength) {
    errors.push(ERROR_MESSAGES.minLength(FIELD_NAMES.username, rules.minLength));
  } else if (username.length > rules.maxLength) {
    errors.push(ERROR_MESSAGES.maxLength(FIELD_NAMES.username, rules.maxLength));
  } else if (!rules.pattern.test(username)) {
    errors.push(ERROR_MESSAGES.pattern(rules.patternMessage));
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};

// 验证密码
export const validatePassword = (password: string): ValidationResult => {
  const errors: string[] = [];
  const rules = VALIDATION_RULES.password;
  
  if (!password) {
    errors.push(ERROR_MESSAGES.required(FIELD_NAMES.password));
  } else if (password.length < rules.minLength) {
    errors.push(ERROR_MESSAGES.minLength(FIELD_NAMES.password, rules.minLength));
  } else if (password.length > rules.maxLength) {
    errors.push(ERROR_MESSAGES.maxLength(FIELD_NAMES.password, rules.maxLength));
  } else if (!rules.pattern.test(password)) {
    errors.push(ERROR_MESSAGES.pattern(rules.patternMessage));
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};

// 验证邮箱
export const validateEmail = (email: string): ValidationResult => {
  const errors: string[] = [];
  const rules = VALIDATION_RULES.email;
  
  if (!email) {
    errors.push(ERROR_MESSAGES.required(FIELD_NAMES.email));
  } else if (email.length > rules.maxLength) {
    errors.push(ERROR_MESSAGES.maxLength(FIELD_NAMES.email, rules.maxLength));
  } else if (!rules.pattern.test(email)) {
    errors.push(ERROR_MESSAGES.pattern(rules.patternMessage));
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
    errors.push(ERROR_MESSAGES.required(FIELD_NAMES.confirmPassword));
  } else if (password !== confirmPassword) {
    errors.push(ERROR_MESSAGES.passwordMismatch);
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

// 通用字段验证函数
export const validateField = (value: string, fieldName: string, rules: FieldValidationRule): ValidationResult => {
  const errors: string[] = [];
  
  if (rules.required && !value) {
    errors.push(ERROR_MESSAGES.required(fieldName));
    return { isValid: false, errors };
  }
  
  if (value) {
    if (rules.minLength && value.length < rules.minLength) {
      errors.push(ERROR_MESSAGES.minLength(fieldName, rules.minLength));
    }
    
    if (rules.maxLength && value.length > rules.maxLength) {
      errors.push(ERROR_MESSAGES.maxLength(fieldName, rules.maxLength));
    }
    
    if (rules.pattern && !rules.pattern.test(value)) {
      errors.push(ERROR_MESSAGES.pattern(rules.patternMessage || `${fieldName}格式不正确`));
    }
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};

// 获取字段验证规则
export const getFieldValidationRules = (fieldName: keyof typeof VALIDATION_RULES): FieldValidationRule => {
  const rules = VALIDATION_RULES[fieldName];
  
  // 确保安全访问属性，避免 undefined 错误
  return {
    required: rules.required ?? true,
    minLength: rules.minLength,
    maxLength: rules.maxLength,
    pattern: rules.pattern,
    patternMessage: rules.patternMessage
  };
};

// 统一的错误处理函数
export const handleApiError = (error: any): string => {
  if (typeof error === 'string') {
    return error;
  }
  
  if (error?.message) {
    // 过滤掉复杂的数据库错误信息
    if (error.message.includes('SQLAlchemy') || error.message.includes('[SQL:')) {
      return ERROR_MESSAGES.serverError;
    }
    return String(error.message);
  }
  
  // 处理FastAPI验证错误格式
  if (error?.detail) {
    // 如果detail是数组（FastAPI验证错误）
    if (Array.isArray(error.detail)) {
      const validationErrors = error.detail.map((err: any) => {
        if (err.msg) {
          return err.msg;
        }
        return '验证失败';
      });
      return validationErrors.join('; ');
    }
    // 如果detail是字符串
    if (typeof error.detail === 'string') {
      return error.detail;
    }
    // 如果detail是对象，尝试转换为字符串
    return String(error.detail);
  }
  
  // 网络错误
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return ERROR_MESSAGES.networkError;
  }
  
  // 如果是对象，尝试提取有用信息
  if (typeof error === 'object' && error !== null) {
    // 尝试获取常见的错误字段
    const errorText = error.error || error.msg || error.description || error.reason;
    if (errorText) {
      return String(errorText);
    }
    
    // 如果有状态码，包含在错误信息中
    if (error.status || error.statusCode) {
      const status = error.status || error.statusCode;
      return `请求失败 (${status}): ${ERROR_MESSAGES.serverError}`;
    }
  }
  
  return ERROR_MESSAGES.unknownError;
};