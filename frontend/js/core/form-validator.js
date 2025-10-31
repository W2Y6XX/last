/**
 * 表单验证器
 * 提供通用的表单验证功能
 */
class FormValidator {
    constructor() {
        this.rules = {
            required: (value) => value !== null && value !== undefined && value.toString().trim() !== '',
            email: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
            url: (value) => {
                try {
                    new URL(value);
                    return true;
                } catch {
                    return false;
                }
            },
            number: (value) => !isNaN(parseFloat(value)) && isFinite(value),
            integer: (value) => Number.isInteger(parseFloat(value)),
            min: (value, min) => parseFloat(value) >= min,
            max: (value, max) => parseFloat(value) <= max,
            minLength: (value, length) => value.toString().length >= length,
            maxLength: (value, length) => value.toString().length <= length,
            pattern: (value, pattern) => new RegExp(pattern).test(value)
        };
        
        this.messages = {
            required: '此字段为必填项',
            email: '请输入有效的邮箱地址',
            url: '请输入有效的URL地址',
            number: '请输入有效的数字',
            integer: '请输入有效的整数',
            min: '值不能小于 {min}',
            max: '值不能大于 {max}',
            minLength: '长度不能少于 {length} 个字符',
            maxLength: '长度不能超过 {length} 个字符',
            pattern: '格式不正确'
        };
    }
    
    /**
     * 验证单个字段
     * @param {*} value 字段值
     * @param {Array} rules 验证规则
     * @returns {Object} 验证结果
     */
    validateField(value, rules) {
        const errors = [];
        
        for (const rule of rules) {
            if (typeof rule === 'string') {
                // 简单规则
                if (!this.rules[rule](value)) {
                    errors.push(this.messages[rule]);
                }
            } else if (typeof rule === 'object') {
                // 带参数的规则
                const ruleName = rule.rule;
                const params = rule.params || [];
                
                if (this.rules[ruleName] && !this.rules[ruleName](value, ...params)) {
                    let message = this.messages[ruleName];
                    
                    // 替换消息中的参数
                    if (rule.params) {
                        rule.params.forEach((param, index) => {
                            const paramNames = ['min', 'max', 'length'];
                            if (paramNames[index]) {
                                message = message.replace(`{${paramNames[index]}}`, param);
                            }
                        });
                    }
                    
                    errors.push(rule.message || message);
                }
            } else if (typeof rule === 'function') {
                // 自定义验证函数
                const result = rule(value);
                if (result !== true) {
                    errors.push(typeof result === 'string' ? result : '验证失败');
                }
            }
        }
        
        return {
            isValid: errors.length === 0,
            errors
        };
    }
    
    /**
     * 验证表单
     * @param {HTMLFormElement} form 表单元素
     * @param {Object} validationRules 验证规则
     * @returns {Object} 验证结果
     */
    validateForm(form, validationRules) {
        const formData = new FormData(form);
        const results = {};
        let isValid = true;
        
        // 验证每个字段
        Object.keys(validationRules).forEach(fieldName => {
            const value = formData.get(fieldName);
            const rules = validationRules[fieldName];
            const result = this.validateField(value, rules);
            
            results[fieldName] = result;
            if (!result.isValid) {
                isValid = false;
            }
        });
        
        return {
            isValid,
            results
        };
    }
    
    /**
     * 显示验证错误
     * @param {Object} validationResults 验证结果
     */
    displayErrors(validationResults) {
        // 清除之前的错误
        this.clearErrors();
        
        Object.keys(validationResults.results).forEach(fieldName => {
            const result = validationResults.results[fieldName];
            if (!result.isValid) {
                this.showFieldError(fieldName, result.errors[0]);
            }
        });
    }
    
    /**
     * 显示字段错误
     * @param {string} fieldName 字段名
     * @param {string} message 错误消息
     */
    showFieldError(fieldName, message) {
        const errorElement = document.getElementById(`${fieldName}-error`);
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.classList.remove('hidden');
        }
        
        // 为字段添加错误样式
        const field = document.getElementById(`config-${fieldName}`) || 
                     document.querySelector(`[name="${fieldName}"]`);
        if (field) {
            field.classList.add('border-red-400');
        }
    }
    
    /**
     * 清除所有错误
     */
    clearErrors() {
        const errorElements = document.querySelectorAll('[id$="-error"]');
        errorElements.forEach(element => {
            element.textContent = '';
            element.classList.add('hidden');
        });
        
        // 移除错误样式
        const fields = document.querySelectorAll('.border-red-400');
        fields.forEach(field => {
            field.classList.remove('border-red-400');
        });
    }
    
    /**
     * 实时验证字段
     * @param {HTMLElement} field 字段元素
     * @param {Array} rules 验证规则
     */
    setupRealTimeValidation(field, rules) {
        const validateAndShow = () => {
            const result = this.validateField(field.value, rules);
            const fieldName = field.name || field.id.replace('config-', '');
            
            if (!result.isValid) {
                this.showFieldError(fieldName, result.errors[0]);
            } else {
                // 清除该字段的错误
                const errorElement = document.getElementById(`${fieldName}-error`);
                if (errorElement) {
                    errorElement.textContent = '';
                    errorElement.classList.add('hidden');
                }
                field.classList.remove('border-red-400');
            }
        };
        
        field.addEventListener('blur', validateAndShow);
        field.addEventListener('input', () => {
            // 延迟验证，避免用户输入时频繁显示错误
            clearTimeout(field.validationTimeout);
            field.validationTimeout = setTimeout(validateAndShow, 500);
        });
    }
}

// LLM配置专用验证规则
const LLMConfigValidationRules = {
    name: [
        'required',
        { rule: 'minLength', params: [1], message: '配置名称不能为空' },
        { rule: 'maxLength', params: [50], message: '配置名称不能超过50个字符' }
    ],
    provider: [
        'required'
    ],
    apiKey: [
        // API密钥的验证会根据提供商动态调整
    ],
    baseUrl: [
        // URL验证会根据提供商动态调整
    ],
    model: [
        'required',
        { rule: 'minLength', params: [1], message: '模型名称不能为空' }
    ],
    temperature: [
        { rule: 'number', message: '温度参数必须是数字' },
        { rule: 'min', params: [0], message: '温度参数不能小于0' },
        { rule: 'max', params: [2], message: '温度参数不能大于2' }
    ],
    maxTokens: [
        { rule: 'integer', message: '最大令牌数必须是整数' },
        { rule: 'min', params: [1], message: '最大令牌数不能小于1' },
        { rule: 'max', params: [32768], message: '最大令牌数不能大于32768' }
    ],
    timeout: [
        { rule: 'integer', message: '超时时间必须是整数' },
        { rule: 'min', params: [1000], message: '超时时间不能小于1000毫秒' },
        { rule: 'max', params: [300000], message: '超时时间不能大于300000毫秒' }
    ],
    maxRetries: [
        { rule: 'integer', message: '重试次数必须是整数' },
        { rule: 'min', params: [0], message: '重试次数不能小于0' },
        { rule: 'max', params: [10], message: '重试次数不能大于10' }
    ]
};

/**
 * 获取动态验证规则
 * @param {string} provider 提供商
 * @returns {Object} 验证规则
 */
function getDynamicValidationRules(provider) {
    const rules = { ...LLMConfigValidationRules };
    
    if (!window.llmConfigManager) return rules;
    
    const providers = window.llmConfigManager.getSupportedProviders();
    const providerInfo = providers.find(p => p.key === provider);
    
    if (providerInfo) {
        // API密钥验证
        if (providerInfo.requiredFields.includes('apiKey')) {
            rules.apiKey = [
                'required',
                { rule: 'minLength', params: [10], message: 'API密钥长度不能少于10个字符' }
            ];
        } else {
            rules.apiKey = [];
        }
        
        // 基础URL验证
        if (providerInfo.requiredFields.includes('baseUrl')) {
            rules.baseUrl = [
                'required',
                'url'
            ];
        } else if (provider !== 'local') {
            rules.baseUrl = [
                (value) => !value || /^https?:\/\/.+/.test(value) || 'URL格式不正确'
            ];
        }
    }
    
    return rules;
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { FormValidator, LLMConfigValidationRules, getDynamicValidationRules };
} else {
    window.FormValidator = FormValidator;
    window.LLMConfigValidationRules = LLMConfigValidationRules;
    window.getDynamicValidationRules = getDynamicValidationRules;
}