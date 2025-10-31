/**
 * 对话后端LLM配置管理器
 * 负责将前端LLM配置同步到对话后端，实现配置验证和连接测试
 */

class DialogBackendConfig {
    constructor() {
        this.apiEndpoints = {
            health: '/api/v1/health',
            dialogConfig: '/api/v1/dialog/config',
            dialogTest: '/api/v1/dialog/test',
            llmConfigs: '/api/v1/llm-configs'
        };
        
        this.retryConfig = {
            maxRetries: 3,
            retryDelay: 1000,
            backoffMultiplier: 2
        };
        
        this.configValidationRules = {
            apiKey: {
                required: true,
                minLength: 10,
                pattern: /^[a-zA-Z0-9\-_]+$/
            },
            baseUrl: {
                required: true,
                pattern: /^https?:\/\/.+/
            },
            model: {
                required: true,
                minLength: 1
            },
            maxTokens: {
                type: 'number',
                min: 1,
                max: 32000
            },
            temperature: {
                type: 'number',
                min: 0,
                max: 2
            }
        };
        
        this.lastSyncTime = null;
        this.syncHistory = [];
    }
    
    /**
     * 配置对话后端
     * @param {Object} config - LLM配置对象
     * @returns {Promise<Object>} 配置结果
     */
    async configureDialogBackend(config = null) {
        try {
            console.log('开始配置对话后端...');
            
            // 如果没有提供配置，从本地存储获取
            if (!config) {
                config = this.getLocalLLMConfig();
                if (!config) {
                    throw new Error('未找到LLM配置');
                }
            }
            
            // 验证配置
            const validation = this.validateConfiguration(config);
            if (!validation.valid) {
                throw new Error(`配置验证失败: ${validation.errors.join(', ')}`);
            }
            
            // 测试LLM连接
            const connectionTest = await this.testLLMConnection(config);
            if (!connectionTest.success) {
                console.warn('LLM连接测试失败，但继续配置后端:', connectionTest.error);
            }
            
            // 同步配置到后端
            const syncResult = await this.syncConfigurationToBackend(config);
            
            if (syncResult.success) {
                this.lastSyncTime = new Date().toISOString();
                this.recordSyncHistory('success', config, syncResult);
                
                console.log('对话后端配置成功');
                return {
                    success: true,
                    message: '对话后端配置成功',
                    config: config,
                    syncTime: this.lastSyncTime,
                    connectionTest: connectionTest
                };
            } else {
                this.recordSyncHistory('failed', config, syncResult);
                throw new Error(`后端配置失败: ${syncResult.error}`);
            }
            
        } catch (error) {
            console.error('配置对话后端失败:', error);
            this.recordSyncHistory('error', config, { error: error.message });
            
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }
    
    /**
     * 验证LLM配置
     * @param {Object} config - 配置对象
     * @returns {Object} 验证结果
     */
    validateConfiguration(config) {
        const errors = [];
        
        if (!config || typeof config !== 'object') {
            return {
                valid: false,
                errors: ['配置对象无效']
            };
        }
        
        // 验证每个字段
        for (const [field, rules] of Object.entries(this.configValidationRules)) {
            const value = config[field];
            
            // 检查必需字段
            if (rules.required && (!value || value === '')) {
                errors.push(`${field} 是必需的`);
                continue;
            }
            
            // 如果字段为空且不是必需的，跳过其他验证
            if (!value && !rules.required) {
                continue;
            }
            
            // 类型验证
            if (rules.type === 'number') {
                if (typeof value !== 'number' || isNaN(value)) {
                    errors.push(`${field} 必须是有效数字`);
                    continue;
                }
                
                if (rules.min !== undefined && value < rules.min) {
                    errors.push(`${field} 不能小于 ${rules.min}`);
                }
                
                if (rules.max !== undefined && value > rules.max) {
                    errors.push(`${field} 不能大于 ${rules.max}`);
                }
            }
            
            // 字符串长度验证
            if (rules.minLength && value.length < rules.minLength) {
                errors.push(`${field} 长度不能少于 ${rules.minLength} 个字符`);
            }
            
            // 正则表达式验证
            if (rules.pattern && !rules.pattern.test(value)) {
                errors.push(`${field} 格式无效`);
            }
        }
        
        return {
            valid: errors.length === 0,
            errors
        };
    }
    
    /**
     * 测试LLM连接
     * @param {Object} config - LLM配置
     * @returns {Promise<Object>} 连接测试结果
     */
    async testLLMConnection(config) {
        try {
            console.log('测试LLM连接...');
            
            // 测试模型列表端点
            const modelsResponse = await this.makeRequest(`${config.baseUrl}/v1/models`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${config.apiKey}`,
                    'Content-Type': 'application/json'
                },
                timeout: 10000
            });
            
            if (modelsResponse.ok) {
                const models = await modelsResponse.json();
                
                // 检查指定的模型是否可用
                let modelAvailable = false;
                if (models.data && Array.isArray(models.data)) {
                    modelAvailable = models.data.some(model => model.id === config.model);
                }
                
                return {
                    success: true,
                    modelAvailable,
                    availableModels: models.data ? models.data.map(m => m.id) : [],
                    message: modelAvailable ? '连接成功，模型可用' : '连接成功，但指定模型不可用'
                };
            } else {
                return {
                    success: false,
                    error: `HTTP ${modelsResponse.status}: ${modelsResponse.statusText}`,
                    status: modelsResponse.status
                };
            }
            
        } catch (error) {
            console.error('LLM连接测试失败:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    /**
     * 同步配置到后端（带重试机制）
     * @param {Object} config - LLM配置
     * @returns {Promise<Object>} 同步结果
     */
    async syncConfigurationToBackend(config) {
        let lastError = null;
        
        for (let attempt = 1; attempt <= this.retryConfig.maxRetries; attempt++) {
            try {
                console.log(`尝试同步配置到后端 (第 ${attempt} 次)...`);
                
                const response = await this.makeRequest(this.apiEndpoints.dialogConfig, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        ...config,
                        syncTime: new Date().toISOString(),
                        source: 'frontend'
                    }),
                    timeout: 15000
                });
                
                if (response.ok) {
                    const result = await response.json();
                    console.log('配置同步成功');
                    
                    return {
                        success: true,
                        result: result,
                        attempt: attempt
                    };
                } else {
                    const errorData = await response.json().catch(() => ({}));
                    lastError = new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
                    
                    // 如果是客户端错误（4xx），不重试
                    if (response.status >= 400 && response.status < 500) {
                        break;
                    }
                }
                
            } catch (error) {
                console.error(`配置同步失败 (第 ${attempt} 次):`, error);
                lastError = error;
            }
            
            // 如果不是最后一次尝试，等待后重试
            if (attempt < this.retryConfig.maxRetries) {
                const delay = this.retryConfig.retryDelay * Math.pow(this.retryConfig.backoffMultiplier, attempt - 1);
                console.log(`等待 ${delay}ms 后重试...`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
        
        return {
            success: false,
            error: lastError ? lastError.message : '未知错误',
            attempts: this.retryConfig.maxRetries
        };
    }
    
    /**
     * 检查后端配置状态
     * @returns {Promise<Object>} 配置状态
     */
    async checkBackendConfigurationStatus() {
        try {
            console.log('检查后端配置状态...');
            
            const response = await this.makeRequest(this.apiEndpoints.dialogConfig, {
                method: 'GET',
                timeout: 5000
            });
            
            if (response.ok) {
                const backendConfig = await response.json();
                const localConfig = this.getLocalLLMConfig();
                
                const status = {
                    hasBackendConfig: true,
                    backendConfig: backendConfig,
                    localConfig: localConfig,
                    lastSyncTime: this.lastSyncTime,
                    inSync: false,
                    differences: []
                };
                
                // 比较配置
                if (localConfig) {
                    const comparison = this.compareConfigurations(localConfig, backendConfig);
                    status.inSync = !comparison.hasDifferences;
                    status.differences = comparison.differences;
                }
                
                return status;
            } else {
                return {
                    hasBackendConfig: false,
                    error: `HTTP ${response.status}: ${response.statusText}`,
                    status: response.status
                };
            }
            
        } catch (error) {
            console.error('检查后端配置状态失败:', error);
            return {
                hasBackendConfig: false,
                error: error.message
            };
        }
    }
    
    /**
     * 处理配置失败的错误处理和重试逻辑
     * @param {Object} error - 错误对象
     * @param {Object} config - 原始配置
     * @returns {Promise<Object>} 处理结果
     */
    async handleConfigurationFailure(error, config) {
        console.log('处理配置失败，尝试错误恢复...');
        
        const recoveryStrategies = [
            {
                name: '重新验证配置',
                action: async () => {
                    const validation = this.validateConfiguration(config);
                    if (!validation.valid) {
                        throw new Error(`配置验证失败: ${validation.errors.join(', ')}`);
                    }
                    return { success: true, message: '配置验证通过' };
                }
            },
            {
                name: '测试后端连接',
                action: async () => {
                    const response = await this.makeRequest(this.apiEndpoints.health, {
                        method: 'GET',
                        timeout: 5000
                    });
                    
                    if (!response.ok) {
                        throw new Error(`后端不可用: ${response.status}`);
                    }
                    
                    return { success: true, message: '后端连接正常' };
                }
            },
            {
                name: '使用默认配置',
                action: async () => {
                    const defaultConfig = this.getDefaultConfiguration();
                    const syncResult = await this.syncConfigurationToBackend(defaultConfig);
                    
                    if (!syncResult.success) {
                        throw new Error(`默认配置同步失败: ${syncResult.error}`);
                    }
                    
                    return { 
                        success: true, 
                        message: '已使用默认配置',
                        config: defaultConfig 
                    };
                }
            }
        ];
        
        const recoveryResults = [];
        
        for (const strategy of recoveryStrategies) {
            try {
                console.log(`尝试恢复策略: ${strategy.name}`);
                const result = await strategy.action();
                
                recoveryResults.push({
                    strategy: strategy.name,
                    success: true,
                    result: result
                });
                
                // 如果某个策略成功，可以选择继续或停止
                if (result.success) {
                    console.log(`恢复策略 ${strategy.name} 成功`);
                }
                
            } catch (strategyError) {
                console.error(`恢复策略 ${strategy.name} 失败:`, strategyError);
                recoveryResults.push({
                    strategy: strategy.name,
                    success: false,
                    error: strategyError.message
                });
            }
        }
        
        const successfulStrategies = recoveryResults.filter(r => r.success);
        
        return {
            originalError: error.message,
            recoveryAttempted: true,
            recoveryResults: recoveryResults,
            recoverySuccess: successfulStrategies.length > 0,
            message: successfulStrategies.length > 0 ? 
                `部分恢复成功: ${successfulStrategies.map(s => s.strategy).join(', ')}` :
                '所有恢复策略都失败了'
        };
    }
    
    /**
     * 获取本地LLM配置
     * @returns {Object|null} 本地配置
     */
    getLocalLLMConfig() {
        try {
            const config = localStorage.getItem('llm_configs');
            return config ? JSON.parse(config) : null;
        } catch (error) {
            console.error('获取本地LLM配置失败:', error);
            return null;
        }
    }
    
    /**
     * 比较两个配置对象
     * @param {Object} localConfig - 本地配置
     * @param {Object} backendConfig - 后端配置
     * @returns {Object} 比较结果
     */
    compareConfigurations(localConfig, backendConfig) {
        const differences = [];
        const compareFields = ['apiKey', 'baseUrl', 'model', 'maxTokens', 'temperature'];
        
        for (const field of compareFields) {
            const localValue = localConfig[field];
            const backendValue = backendConfig[field];
            
            if (localValue !== backendValue) {
                differences.push({
                    field,
                    local: localValue,
                    backend: backendValue,
                    type: this.getDifferenceType(localValue, backendValue)
                });
            }
        }
        
        return {
            hasDifferences: differences.length > 0,
            differences,
            similarity: 1 - (differences.length / compareFields.length)
        };
    }
    
    /**
     * 获取差异类型
     * @param {*} localValue - 本地值
     * @param {*} backendValue - 后端值
     * @returns {string} 差异类型
     */
    getDifferenceType(localValue, backendValue) {
        if (localValue === undefined || localValue === null) {
            return 'missing_local';
        }
        if (backendValue === undefined || backendValue === null) {
            return 'missing_backend';
        }
        if (typeof localValue !== typeof backendValue) {
            return 'type_mismatch';
        }
        return 'value_mismatch';
    }
    
    /**
     * 获取默认配置
     * @returns {Object} 默认配置
     */
    getDefaultConfiguration() {
        return {
            apiKey: 'default-api-key',
            baseUrl: 'https://api.openai.com',
            model: 'gpt-3.5-turbo',
            maxTokens: 2000,
            temperature: 0.7,
            source: 'default'
        };
    }
    
    /**
     * 记录同步历史
     * @param {string} status - 同步状态
     * @param {Object} config - 配置对象
     * @param {Object} result - 同步结果
     */
    recordSyncHistory(status, config, result) {
        const record = {
            id: 'sync_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9),
            status: status,
            timestamp: new Date().toISOString(),
            config: {
                model: config?.model,
                baseUrl: config?.baseUrl,
                hasApiKey: !!config?.apiKey
            },
            result: result
        };
        
        this.syncHistory.push(record);
        
        // 限制历史记录数量
        if (this.syncHistory.length > 50) {
            this.syncHistory.shift();
        }
        
        console.log('同步历史记录:', record);
    }
    
    /**
     * 发起HTTP请求的通用方法
     * @param {string} url - 请求URL
     * @param {Object} options - 请求选项
     * @returns {Promise<Response>} 响应对象
     */
    async makeRequest(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), options.timeout || 10000);
        
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            return response;
            
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('请求超时');
            }
            
            throw error;
        }
    }
    
    /**
     * 获取同步历史
     * @param {number} limit - 限制数量
     * @returns {Array} 同步历史记录
     */
    getSyncHistory(limit = 10) {
        return this.syncHistory.slice(-limit);
    }
    
    /**
     * 清除同步历史
     */
    clearSyncHistory() {
        this.syncHistory = [];
        console.log('同步历史已清除');
    }
    
    /**
     * 获取配置状态摘要
     * @returns {Promise<Object>} 状态摘要
     */
    async getConfigurationSummary() {
        try {
            const localConfig = this.getLocalLLMConfig();
            const backendStatus = await this.checkBackendConfigurationStatus();
            
            return {
                hasLocalConfig: !!localConfig,
                hasBackendConfig: backendStatus.hasBackendConfig,
                inSync: backendStatus.inSync,
                lastSyncTime: this.lastSyncTime,
                syncHistoryCount: this.syncHistory.length,
                configurationValid: localConfig ? this.validateConfiguration(localConfig).valid : false,
                summary: {
                    local: localConfig ? {
                        model: localConfig.model,
                        baseUrl: localConfig.baseUrl,
                        hasApiKey: !!localConfig.apiKey
                    } : null,
                    backend: backendStatus.backendConfig ? {
                        model: backendStatus.backendConfig.model,
                        baseUrl: backendStatus.backendConfig.baseUrl,
                        hasApiKey: !!backendStatus.backendConfig.apiKey
                    } : null
                }
            };
        } catch (error) {
            return {
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }
}

// 导出类
export default DialogBackendConfig;

// 创建全局实例
window.DialogBackendConfig = DialogBackendConfig;