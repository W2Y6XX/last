/**
 * 大模型配置管理器
 * 负责管理大语言模型的配置信息，包括增删改查、验证、测试等功能
 */
class LLMConfigManager {
    constructor() {
        this.configs = new Map();
        this.activeConfigId = null;
        this.providers = {
            'siliconflow': {
                name: 'SiliconFlow',
                requiredFields: ['apiKey', 'model'],
                optionalFields: ['baseUrl', 'temperature', 'maxTokens', 'timeout', 'maxRetries'],
                defaultValues: {
                    baseUrl: 'https://api.siliconflow.cn/v1',
                    temperature: 0.7,
                    maxTokens: 2048,
                    timeout: 30000,
                    maxRetries: 3
                }
            },
            'openai': {
                name: 'OpenAI',
                requiredFields: ['apiKey', 'model'],
                optionalFields: ['baseUrl', 'temperature', 'maxTokens', 'timeout', 'maxRetries'],
                defaultValues: {
                    baseUrl: 'https://api.openai.com/v1',
                    temperature: 0.7,
                    maxTokens: 2048,
                    timeout: 30000,
                    maxRetries: 3
                }
            },
            'anthropic': {
                name: 'Anthropic',
                requiredFields: ['apiKey', 'model'],
                optionalFields: ['baseUrl', 'temperature', 'maxTokens', 'timeout', 'maxRetries'],
                defaultValues: {
                    baseUrl: 'https://api.anthropic.com/v1',
                    temperature: 0.7,
                    maxTokens: 2048,
                    timeout: 30000,
                    maxRetries: 3
                }
            },
            'local': {
                name: '本地部署',
                requiredFields: ['baseUrl', 'model'],
                optionalFields: ['apiKey', 'temperature', 'maxTokens', 'timeout', 'maxRetries'],
                defaultValues: {
                    temperature: 0.7,
                    maxTokens: 2048,
                    timeout: 30000,
                    maxRetries: 3
                }
            }
        };
        
        this.storageKey = 'llm_configs';
        this.activeConfigKey = 'active_llm_config';
        this.encryptionKey = this._generateEncryptionKey();
        
        // 初始化
        this._loadFromStorage();
    }
    
    /**
     * 生成加密密钥
     * @private
     */
    _generateEncryptionKey() {
        // 简单的加密密钥生成，实际应用中应使用更安全的方法
        const stored = localStorage.getItem('llm_encryption_key');
        if (stored) {
            return stored;
        }
        
        const key = btoa(Math.random().toString(36).substring(2, 15) + 
                         Math.random().toString(36).substring(2, 15));
        localStorage.setItem('llm_encryption_key', key);
        return key;
    }
    
    /**
     * 简单加密函数
     * @private
     */
    _encrypt(text) {
        if (!text) return text;
        try {
            return btoa(encodeURIComponent(text + this.encryptionKey));
        } catch (error) {
            console.error('加密失败:', error);
            return text;
        }
    }
    
    /**
     * 简单解密函数
     * @private
     */
    _decrypt(encryptedText) {
        if (!encryptedText) return encryptedText;
        try {
            const decoded = decodeURIComponent(atob(encryptedText));
            return decoded.replace(this.encryptionKey, '');
        } catch (error) {
            console.error('解密失败:', error);
            return encryptedText;
        }
    }
    
    /**
     * 从本地存储加载配置
     * @private
     */
    _loadFromStorage() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            if (stored) {
                const configs = JSON.parse(stored);
                configs.forEach(config => {
                    // 解密敏感信息
                    if (config.settings && config.settings.apiKey) {
                        config.settings.apiKey = this._decrypt(config.settings.apiKey);
                    }
                    this.configs.set(config.id, config);
                });
            }
            
            const activeId = localStorage.getItem(this.activeConfigKey);
            if (activeId && this.configs.has(activeId)) {
                this.activeConfigId = activeId;
            }
        } catch (error) {
            console.error('加载配置失败:', error);
        }
    }
    
    /**
     * 保存配置到本地存储
     * @private
     */
    _saveToStorage() {
        try {
            const configsArray = Array.from(this.configs.values()).map(config => {
                const configCopy = JSON.parse(JSON.stringify(config));
                // 加密敏感信息
                if (configCopy.settings && configCopy.settings.apiKey) {
                    configCopy.settings.apiKey = this._encrypt(configCopy.settings.apiKey);
                }
                return configCopy;
            });
            
            localStorage.setItem(this.storageKey, JSON.stringify(configsArray));
            
            if (this.activeConfigId) {
                localStorage.setItem(this.activeConfigKey, this.activeConfigId);
            }
        } catch (error) {
            console.error('保存配置失败:', error);
        }
    }
    
    /**
     * 生成配置ID
     * @private
     */
    _generateId() {
        return 'llm_config_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
    }
    
    /**
     * 验证配置参数
     * @param {Object} config 配置对象
     * @returns {Object} 验证结果 {isValid: boolean, errors: string[]}
     */
    validateConfig(config) {
        const errors = [];
        
        if (!config.name || config.name.trim() === '') {
            errors.push('配置名称不能为空');
        }
        
        if (!config.provider || !this.providers[config.provider]) {
            errors.push('无效的提供商类型');
            return { isValid: false, errors };
        }
        
        const provider = this.providers[config.provider];
        const settings = config.settings || {};
        
        // 检查必需字段
        provider.requiredFields.forEach(field => {
            if (!settings[field] || settings[field].trim() === '') {
                errors.push(`${field} 是必需字段`);
            }
        });
        
        // 验证数值字段
        if (settings.temperature !== undefined) {
            const temp = parseFloat(settings.temperature);
            if (isNaN(temp) || temp < 0 || temp > 2) {
                errors.push('温度参数必须在0-2之间');
            }
        }
        
        if (settings.maxTokens !== undefined) {
            const tokens = parseInt(settings.maxTokens);
            if (isNaN(tokens) || tokens < 1 || tokens > 32768) {
                errors.push('最大令牌数必须在1-32768之间');
            }
        }
        
        if (settings.timeout !== undefined) {
            const timeout = parseInt(settings.timeout);
            if (isNaN(timeout) || timeout < 1000 || timeout > 300000) {
                errors.push('超时时间必须在1000-300000毫秒之间');
            }
        }
        
        if (settings.maxRetries !== undefined) {
            const retries = parseInt(settings.maxRetries);
            if (isNaN(retries) || retries < 0 || retries > 10) {
                errors.push('重试次数必须在0-10之间');
            }
        }
        
        // 验证URL格式
        if (settings.baseUrl) {
            try {
                new URL(settings.baseUrl);
            } catch (error) {
                errors.push('基础URL格式无效');
            }
        }
        
        return {
            isValid: errors.length === 0,
            errors
        };
    }
    
    /**
     * 创建新配置
     * @param {Object} configData 配置数据
     * @returns {Promise<Object>} 创建结果
     */
    async createConfig(configData) {
        try {
            // 验证配置
            const validation = this.validateConfig(configData);
            if (!validation.isValid) {
                return {
                    success: false,
                    errors: validation.errors
                };
            }
            
            // 检查名称是否重复
            const existingConfig = Array.from(this.configs.values())
                .find(config => config.name === configData.name);
            if (existingConfig) {
                return {
                    success: false,
                    errors: ['配置名称已存在']
                };
            }
            
            // 创建配置对象
            const config = {
                id: this._generateId(),
                name: configData.name,
                provider: configData.provider,
                settings: { ...configData.settings },
                isActive: false,
                testResult: {
                    isValid: null,
                    lastTested: null,
                    responseTime: null,
                    errorMessage: null
                },
                usage: {
                    totalRequests: 0,
                    successfulRequests: 0,
                    totalTokens: 0,
                    totalCost: 0
                },
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            };
            
            // 应用默认值
            const provider = this.providers[config.provider];
            Object.keys(provider.defaultValues).forEach(key => {
                if (config.settings[key] === undefined) {
                    config.settings[key] = provider.defaultValues[key];
                }
            });
            
            // 保存配置
            this.configs.set(config.id, config);
            this._saveToStorage();
            
            // 如果是第一个配置，设为活动配置
            if (this.configs.size === 1) {
                await this.setActiveConfig(config.id);
            }
            
            return {
                success: true,
                data: { configId: config.id }
            };
            
        } catch (error) {
            console.error('创建配置失败:', error);
            return {
                success: false,
                errors: ['创建配置时发生错误']
            };
        }
    }
    
    /**
     * 更新配置
     * @param {string} configId 配置ID
     * @param {Object} updateData 更新数据
     * @returns {Promise<Object>} 更新结果
     */
    async updateConfig(configId, updateData) {
        try {
            if (!this.configs.has(configId)) {
                return {
                    success: false,
                    errors: ['配置不存在']
                };
            }
            
            const config = this.configs.get(configId);
            const updatedConfig = {
                ...config,
                ...updateData,
                settings: { ...config.settings, ...updateData.settings },
                updatedAt: new Date().toISOString()
            };
            
            // 验证更新后的配置
            const validation = this.validateConfig(updatedConfig);
            if (!validation.isValid) {
                return {
                    success: false,
                    errors: validation.errors
                };
            }
            
            // 检查名称是否与其他配置重复
            if (updateData.name && updateData.name !== config.name) {
                const existingConfig = Array.from(this.configs.values())
                    .find(c => c.id !== configId && c.name === updateData.name);
                if (existingConfig) {
                    return {
                        success: false,
                        errors: ['配置名称已存在']
                    };
                }
            }
            
            // 更新配置
            this.configs.set(configId, updatedConfig);
            this._saveToStorage();
            
            return { success: true };
            
        } catch (error) {
            console.error('更新配置失败:', error);
            return {
                success: false,
                errors: ['更新配置时发生错误']
            };
        }
    }
    
    /**
     * 删除配置
     * @param {string} configId 配置ID
     * @returns {Promise<Object>} 删除结果
     */
    async deleteConfig(configId) {
        try {
            if (!this.configs.has(configId)) {
                return {
                    success: false,
                    errors: ['配置不存在']
                };
            }
            
            // 如果删除的是活动配置，需要重新选择活动配置
            if (this.activeConfigId === configId) {
                this.activeConfigId = null;
                localStorage.removeItem(this.activeConfigKey);
                
                // 如果还有其他配置，选择第一个作为活动配置
                const remainingConfigs = Array.from(this.configs.values())
                    .filter(config => config.id !== configId);
                if (remainingConfigs.length > 0) {
                    await this.setActiveConfig(remainingConfigs[0].id);
                }
            }
            
            this.configs.delete(configId);
            this._saveToStorage();
            
            return { success: true };
            
        } catch (error) {
            console.error('删除配置失败:', error);
            return {
                success: false,
                errors: ['删除配置时发生错误']
            };
        }
    }
    
    /**
     * 获取所有配置
     * @returns {Array} 配置列表
     */
    getAllConfigs() {
        return Array.from(this.configs.values()).map(config => ({
            ...config,
            settings: {
                ...config.settings,
                // 隐藏API密钥的部分内容
                apiKey: config.settings.apiKey ? 
                    config.settings.apiKey.substring(0, 8) + '...' : undefined
            }
        }));
    }
    
    /**
     * 获取配置详情
     * @param {string} configId 配置ID
     * @returns {Object|null} 配置详情
     */
    getConfig(configId) {
        const config = this.configs.get(configId);
        if (!config) return null;
        
        return {
            ...config,
            settings: {
                ...config.settings,
                // 隐藏API密钥的部分内容
                apiKey: config.settings.apiKey ? 
                    config.settings.apiKey.substring(0, 8) + '...' : undefined
            }
        };
    }
    
    /**
     * 获取完整配置（包含完整API密钥）
     * @param {string} configId 配置ID
     * @returns {Object|null} 完整配置
     */
    getFullConfig(configId) {
        return this.configs.get(configId) || null;
    }
    
    /**
     * 设置活动配置
     * @param {string} configId 配置ID
     * @returns {Promise<Object>} 设置结果
     */
    async setActiveConfig(configId) {
        try {
            if (!this.configs.has(configId)) {
                return {
                    success: false,
                    errors: ['配置不存在']
                };
            }
            
            // 取消之前的活动配置
            if (this.activeConfigId) {
                const prevConfig = this.configs.get(this.activeConfigId);
                if (prevConfig) {
                    prevConfig.isActive = false;
                }
            }
            
            // 设置新的活动配置
            const config = this.configs.get(configId);
            config.isActive = true;
            this.activeConfigId = configId;
            
            this._saveToStorage();
            
            return { success: true };
            
        } catch (error) {
            console.error('设置活动配置失败:', error);
            return {
                success: false,
                errors: ['设置活动配置时发生错误']
            };
        }
    }
    
    /**
     * 获取活动配置
     * @returns {Object|null} 活动配置
     */
    getActiveConfig() {
        if (!this.activeConfigId) return null;
        return this.getFullConfig(this.activeConfigId);
    }
    
    /**
     * 测试配置连接
     * @param {string} configId 配置ID
     * @returns {Promise<Object>} 测试结果
     */
    async testConnection(configId) {
        try {
            const config = this.configs.get(configId);
            if (!config) {
                return {
                    success: false,
                    errors: ['配置不存在']
                };
            }
            
            const startTime = Date.now();
            
            // 构建测试请求
            const testUrl = `${config.settings.baseUrl}/chat/completions`;
            const testData = {
                model: config.settings.model,
                messages: [
                    { role: 'user', content: 'Hello, this is a connection test.' }
                ],
                max_tokens: 10,
                temperature: 0.1
            };
            
            const headers = {
                'Content-Type': 'application/json'
            };
            
            // 添加认证头
            if (config.settings.apiKey) {
                if (config.provider === 'anthropic') {
                    headers['x-api-key'] = config.settings.apiKey;
                    headers['anthropic-version'] = '2023-06-01';
                } else {
                    headers['Authorization'] = `Bearer ${config.settings.apiKey}`;
                }
            }
            
            // 发送测试请求
            const response = await fetch(testUrl, {
                method: 'POST',
                headers,
                body: JSON.stringify(testData),
                timeout: config.settings.timeout || 30000
            });
            
            const responseTime = Date.now() - startTime;
            
            // 更新测试结果
            config.testResult = {
                isValid: response.ok,
                lastTested: new Date().toISOString(),
                responseTime,
                errorMessage: response.ok ? null : `HTTP ${response.status}: ${response.statusText}`
            };
            
            this._saveToStorage();
            
            if (response.ok) {
                return {
                    success: true,
                    data: {
                        isValid: true,
                        responseTime,
                        message: '连接测试成功'
                    }
                };
            } else {
                return {
                    success: false,
                    errors: [`连接测试失败: HTTP ${response.status}`]
                };
            }
            
        } catch (error) {
            console.error('测试连接失败:', error);
            
            // 更新测试结果
            const config = this.configs.get(configId);
            if (config) {
                config.testResult = {
                    isValid: false,
                    lastTested: new Date().toISOString(),
                    responseTime: null,
                    errorMessage: error.message
                };
                this._saveToStorage();
            }
            
            return {
                success: false,
                errors: [`连接测试失败: ${error.message}`]
            };
        }
    }
    
    /**
     * 获取支持的提供商列表
     * @returns {Array} 提供商列表
     */
    getSupportedProviders() {
        return Object.keys(this.providers).map(key => ({
            key,
            name: this.providers[key].name,
            requiredFields: this.providers[key].requiredFields,
            optionalFields: this.providers[key].optionalFields,
            defaultValues: this.providers[key].defaultValues
        }));
    }
    
    /**
     * 根据URL和API密钥获取可用模型列表
     * @param {string} baseUrl - API基础URL
     * @param {string} apiKey - API密钥（可选）
     * @param {number} timeout - 请求超时时间（毫秒）
     * @returns {Promise<Object>} 模型列表结果
     */
    async fetchAvailableModels(baseUrl, apiKey = null, timeout = 10000) {
        try {
            console.log('正在获取可用模型列表...', { baseUrl, hasApiKey: !!apiKey });
            
            // 验证URL格式
            let apiUrl;
            try {
                const url = new URL(baseUrl);
                // 确保URL以/v1结尾（如果还没有的话）
                const pathname = url.pathname.endsWith('/v1') ? url.pathname : url.pathname.replace(/\/$/, '') + '/v1';
                apiUrl = `${url.protocol}//${url.host}${pathname}/models`;
            } catch (error) {
                return {
                    success: false,
                    error: 'URL格式无效',
                    models: []
                };
            }
            
            // 准备请求头
            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            };
            
            // 如果提供了API密钥，添加认证头
            if (apiKey && apiKey.trim()) {
                headers['Authorization'] = `Bearer ${apiKey.trim()}`;
            }
            
            // 创建AbortController用于超时控制
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeout);
            
            try {
                const response = await fetch(apiUrl, {
                    method: 'GET',
                    headers: headers,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    // 尝试解析错误信息
                    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                    try {
                        const errorData = await response.json();
                        if (errorData.error && errorData.error.message) {
                            errorMessage = errorData.error.message;
                        } else if (errorData.message) {
                            errorMessage = errorData.message;
                        }
                    } catch (parseError) {
                        // 忽略JSON解析错误，使用默认错误信息
                    }
                    
                    return {
                        success: false,
                        error: errorMessage,
                        status: response.status,
                        models: []
                    };
                }
                
                const data = await response.json();
                
                // 解析模型数据
                const models = this._parseModelsResponse(data, baseUrl);
                
                console.log(`成功获取 ${models.length} 个模型`);
                
                return {
                    success: true,
                    models: models,
                    totalCount: models.length,
                    fetchedAt: new Date().toISOString()
                };
                
            } catch (fetchError) {
                clearTimeout(timeoutId);
                
                if (fetchError.name === 'AbortError') {
                    return {
                        success: false,
                        error: '请求超时',
                        models: []
                    };
                }
                
                throw fetchError;
            }
            
        } catch (error) {
            console.error('获取模型列表失败:', error);
            
            return {
                success: false,
                error: error.message || '获取模型列表失败',
                models: []
            };
        }
    }
    
    /**
     * 解析模型响应数据
     * @private
     * @param {Object} data - API响应数据
     * @param {string} baseUrl - API基础URL
     * @returns {Array} 解析后的模型列表
     */
    _parseModelsResponse(data, baseUrl) {
        const models = [];
        
        try {
            // OpenAI格式的响应
            if (data.data && Array.isArray(data.data)) {
                data.data.forEach(model => {
                    if (model.id) {
                        models.push({
                            id: model.id,
                            name: model.id,
                            displayName: this._formatModelDisplayName(model.id),
                            provider: this._detectProviderFromUrl(baseUrl),
                            capabilities: this._inferModelCapabilities(model),
                            created: model.created ? new Date(model.created * 1000).toISOString() : null,
                            owned_by: model.owned_by || 'unknown',
                            permission: model.permission || [],
                            root: model.root || model.id,
                            parent: model.parent || null
                        });
                    }
                });
            }
            // 直接数组格式
            else if (Array.isArray(data)) {
                data.forEach(model => {
                    if (typeof model === 'string') {
                        models.push({
                            id: model,
                            name: model,
                            displayName: this._formatModelDisplayName(model),
                            provider: this._detectProviderFromUrl(baseUrl),
                            capabilities: this._inferModelCapabilities({ id: model })
                        });
                    } else if (model.id || model.name) {
                        const modelId = model.id || model.name;
                        models.push({
                            id: modelId,
                            name: modelId,
                            displayName: this._formatModelDisplayName(modelId),
                            provider: this._detectProviderFromUrl(baseUrl),
                            capabilities: this._inferModelCapabilities(model),
                            ...model
                        });
                    }
                });
            }
            // 其他格式尝试
            else if (data.models && Array.isArray(data.models)) {
                data.models.forEach(model => {
                    const modelId = model.id || model.name || model.model;
                    if (modelId) {
                        models.push({
                            id: modelId,
                            name: modelId,
                            displayName: this._formatModelDisplayName(modelId),
                            provider: this._detectProviderFromUrl(baseUrl),
                            capabilities: this._inferModelCapabilities(model),
                            ...model
                        });
                    }
                });
            }
            
        } catch (error) {
            console.error('解析模型数据失败:', error);
        }
        
        // 按名称排序
        return models.sort((a, b) => a.displayName.localeCompare(b.displayName));
    }
    
    /**
     * 格式化模型显示名称
     * @private
     * @param {string} modelId - 模型ID
     * @returns {string} 格式化后的显示名称
     */
    _formatModelDisplayName(modelId) {
        if (!modelId) return 'Unknown Model';
        
        // 移除常见的前缀
        let displayName = modelId
            .replace(/^(openai\/|anthropic\/|google\/|meta\/|microsoft\/|huggingface\/)/i, '')
            .replace(/^(gpt-|claude-|gemini-|llama-|phi-)/i, (match) => match.toUpperCase())
            .replace(/-/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
        
        // 特殊处理一些知名模型
        const specialNames = {
            'gpt-3.5-turbo': 'GPT-3.5 Turbo',
            'gpt-4': 'GPT-4',
            'gpt-4-turbo': 'GPT-4 Turbo',
            'gpt-4o': 'GPT-4o',
            'claude-3-haiku': 'Claude 3 Haiku',
            'claude-3-sonnet': 'Claude 3 Sonnet',
            'claude-3-opus': 'Claude 3 Opus',
            'gemini-pro': 'Gemini Pro',
            'llama-2-7b': 'Llama 2 7B',
            'llama-2-13b': 'Llama 2 13B',
            'llama-2-70b': 'Llama 2 70B'
        };
        
        const lowerModelId = modelId.toLowerCase();
        for (const [key, value] of Object.entries(specialNames)) {
            if (lowerModelId.includes(key.toLowerCase())) {
                return value;
            }
        }
        
        return displayName;
    }
    
    /**
     * 从URL检测提供商
     * @private
     * @param {string} baseUrl - API基础URL
     * @returns {string} 提供商名称
     */
    _detectProviderFromUrl(baseUrl) {
        const url = baseUrl.toLowerCase();
        
        if (url.includes('openai.com')) return 'OpenAI';
        if (url.includes('anthropic.com')) return 'Anthropic';
        if (url.includes('siliconflow.cn')) return 'SiliconFlow';
        if (url.includes('googleapis.com')) return 'Google';
        if (url.includes('azure.com')) return 'Azure OpenAI';
        if (url.includes('huggingface.co')) return 'Hugging Face';
        if (url.includes('localhost') || url.includes('127.0.0.1')) return 'Local';
        
        // 尝试从域名提取
        try {
            const domain = new URL(baseUrl).hostname;
            const parts = domain.split('.');
            if (parts.length > 1) {
                return parts[parts.length - 2].charAt(0).toUpperCase() + parts[parts.length - 2].slice(1);
            }
        } catch (error) {
            // 忽略URL解析错误
        }
        
        return 'Custom';
    }
    
    /**
     * 推断模型能力
     * @private
     * @param {Object} model - 模型对象
     * @returns {Object} 模型能力
     */
    _inferModelCapabilities(model) {
        const modelId = (model.id || model.name || '').toLowerCase();
        
        const capabilities = {
            chat: true,
            completion: true,
            embedding: false,
            vision: false,
            function_calling: false,
            streaming: true,
            max_tokens: 4096
        };
        
        // 根据模型名称推断能力
        if (modelId.includes('embedding')) {
            capabilities.chat = false;
            capabilities.completion = false;
            capabilities.embedding = true;
            capabilities.streaming = false;
        }
        
        if (modelId.includes('vision') || modelId.includes('gpt-4v') || modelId.includes('gpt-4-vision')) {
            capabilities.vision = true;
        }
        
        if (modelId.includes('gpt-4') || modelId.includes('claude-3') || modelId.includes('gemini-pro')) {
            capabilities.function_calling = true;
            capabilities.max_tokens = 8192;
        }
        
        if (modelId.includes('gpt-4-turbo') || modelId.includes('gpt-4o')) {
            capabilities.max_tokens = 128000;
        }
        
        if (modelId.includes('claude-3-opus')) {
            capabilities.max_tokens = 200000;
        }
        
        // 从模型对象中获取更多信息
        if (model.context_length) {
            capabilities.max_tokens = model.context_length;
        }
        
        if (model.capabilities) {
            Object.assign(capabilities, model.capabilities);
        }
        
        return capabilities;
    }
    
    /**
     * 获取模型的缓存列表（如果有的话）
     * @param {string} baseUrl - API基础URL
     * @returns {Array} 缓存的模型列表
     */
    getCachedModels(baseUrl) {
        try {
            const cacheKey = `models_cache_${btoa(baseUrl)}`;
            const cached = localStorage.getItem(cacheKey);
            
            if (cached) {
                const data = JSON.parse(cached);
                const now = Date.now();
                
                // 检查缓存是否过期（1小时）
                if (now - data.timestamp < 3600000) {
                    return data.models || [];
                }
            }
        } catch (error) {
            console.error('获取缓存模型失败:', error);
        }
        
        return [];
    }
    
    /**
     * 缓存模型列表
     * @param {string} baseUrl - API基础URL
     * @param {Array} models - 模型列表
     */
    cacheModels(baseUrl, models) {
        try {
            const cacheKey = `models_cache_${btoa(baseUrl)}`;
            const data = {
                models: models,
                timestamp: Date.now(),
                baseUrl: baseUrl
            };
            
            localStorage.setItem(cacheKey, JSON.stringify(data));
        } catch (error) {
            console.error('缓存模型失败:', error);
        }
    }
    
    /**
     * 清除模型缓存
     * @param {string} baseUrl - API基础URL（可选，如果不提供则清除所有缓存）
     */
    clearModelCache(baseUrl = null) {
        try {
            if (baseUrl) {
                const cacheKey = `models_cache_${btoa(baseUrl)}`;
                localStorage.removeItem(cacheKey);
            } else {
                // 清除所有模型缓存
                const keys = Object.keys(localStorage);
                keys.forEach(key => {
                    if (key.startsWith('models_cache_')) {
                        localStorage.removeItem(key);
                    }
                });
            }
        } catch (error) {
            console.error('清除模型缓存失败:', error);
        }
    }
    
    /**
     * 更新使用统计
     * @param {string} configId 配置ID
     * @param {Object} stats 统计数据
     */
    updateUsageStats(configId, stats) {
        const config = this.configs.get(configId);
        if (!config) return;
        
        config.usage.totalRequests += stats.requests || 0;
        config.usage.successfulRequests += stats.successfulRequests || 0;
        config.usage.totalTokens += stats.tokens || 0;
        config.usage.totalCost += stats.cost || 0;
        
        this._saveToStorage();
    }
    
    /**
     * 同步配置到后端
     * @returns {Promise<Object>} 同步结果
     */
    async syncToBackend() {
        try {
            if (!window.apiClient) {
                return {
                    success: false,
                    errors: ['API客户端未初始化']
                };
            }
            
            const configs = this.getAllConfigs();
            const response = await window.apiClient.post('/api/v1/llm/configs/sync', {
                configs,
                activeConfigId: this.activeConfigId
            });
            
            return {
                success: true,
                data: response
            };
            
        } catch (error) {
            console.error('同步配置到后端失败:', error);
            return {
                success: false,
                errors: ['同步配置失败']
            };
        }
    }
    
    /**
     * 从后端加载配置
     * @returns {Promise<Object>} 加载结果
     */
    async loadFromBackend() {
        try {
            if (!window.apiClient) {
                return {
                    success: false,
                    errors: ['API客户端未初始化']
                };
            }
            
            const response = await window.apiClient.get('/api/v1/llm/configs');
            
            if (response.success && response.data) {
                // 清空现有配置
                this.configs.clear();
                
                // 加载后端配置
                response.data.configs.forEach(config => {
                    this.configs.set(config.id, config);
                });
                
                this.activeConfigId = response.data.activeConfigId;
                this._saveToStorage();
                
                return { success: true };
            }
            
            return {
                success: false,
                errors: ['加载配置失败']
            };
            
        } catch (error) {
            console.error('从后端加载配置失败:', error);
            return {
                success: false,
                errors: ['加载配置失败']
            };
        }
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LLMConfigManager;
} else {
    window.LLMConfigManager = LLMConfigManager;
}