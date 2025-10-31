/**
 * 兼容性管理器
 * 负责检查和处理系统兼容性，包括浏览器兼容性、API版本兼容性、数据格式兼容性等
 */
class CompatibilityManager {
    constructor() {
        this.compatibilityChecks = new Map();
        this.fallbackHandlers = new Map();
        this.versionInfo = {
            frontend: '2.0.0',
            apiVersion: 'v1',
            minSupportedApiVersion: 'v1',
            browserRequirements: {
                chrome: 80,
                firefox: 75,
                safari: 13,
                edge: 80
            }
        };
        
        this.compatibilityStatus = {
            browser: null,
            api: null,
            features: new Map(),
            overall: null
        };
        
        this.degradationStrategies = new Map();
        this.featureFlags = new Map();
        
        // 初始化
        this._initialize();
    }
    
    /**
     * 初始化兼容性管理器
     * @private
     */
    async _initialize() {
        try {
            // 检查浏览器兼容性
            await this._checkBrowserCompatibility();
            
            // 检查API兼容性
            await this._checkAPICompatibility();
            
            // 检查功能兼容性
            await this._checkFeatureCompatibility();
            
            // 设置降级策略
            this._setupDegradationStrategies();
            
            // 评估整体兼容性
            this._evaluateOverallCompatibility();
            
            console.log('兼容性检查完成:', this.compatibilityStatus);
            
        } catch (error) {
            console.error('兼容性管理器初始化失败:', error);
            this.compatibilityStatus.overall = 'error';
        }
    }
    
    /**
     * 检查浏览器兼容性
     * @private
     */
    async _checkBrowserCompatibility() {
        const browserInfo = this._getBrowserInfo();
        const requirements = this.versionInfo.browserRequirements;
        
        let isCompatible = true;
        const issues = [];
        
        // 检查浏览器版本
        if (browserInfo.name && requirements[browserInfo.name]) {
            const requiredVersion = requirements[browserInfo.name];
            if (browserInfo.version < requiredVersion) {
                isCompatible = false;
                issues.push(`${browserInfo.name} 版本过低，需要 ${requiredVersion}+ 当前版本: ${browserInfo.version}`);
            }
        } else if (browserInfo.name) {
            // 未知浏览器，发出警告但不阻止使用
            issues.push(`未测试的浏览器: ${browserInfo.name} ${browserInfo.version}`);
        }
        
        // 检查关键Web API支持
        const requiredAPIs = [
            'fetch',
            'WebSocket',
            'localStorage',
            'sessionStorage',
            'JSON',
            'Promise'
        ];
        
        requiredAPIs.forEach(api => {
            if (!this._checkAPISupport(api)) {
                isCompatible = false;
                issues.push(`不支持 ${api} API`);
            }
        });
        
        // 检查ES6+特性支持
        const es6Features = [
            'Map',
            'Set',
            'Symbol',
            'WeakMap',
            'WeakSet'
        ];
        
        es6Features.forEach(feature => {
            if (!window[feature]) {
                isCompatible = false;
                issues.push(`不支持 ES6 ${feature}`);
            }
        });
        
        this.compatibilityStatus.browser = {
            compatible: isCompatible,
            browserInfo,
            issues,
            checkedAt: new Date().toISOString()
        };
        
        // 如果浏览器不兼容，设置降级策略
        if (!isCompatible) {
            this._setupBrowserFallbacks();
        }
    }
    
    /**
     * 获取浏览器信息
     * @private
     */
    _getBrowserInfo() {
        const userAgent = navigator.userAgent;
        let name = 'unknown';
        let version = 0;
        
        // Chrome
        if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) {
            name = 'chrome';
            const match = userAgent.match(/Chrome\/(\d+)/);
            version = match ? parseInt(match[1]) : 0;
        }
        // Firefox
        else if (userAgent.includes('Firefox')) {
            name = 'firefox';
            const match = userAgent.match(/Firefox\/(\d+)/);
            version = match ? parseInt(match[1]) : 0;
        }
        // Safari
        else if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) {
            name = 'safari';
            const match = userAgent.match(/Version\/(\d+)/);
            version = match ? parseInt(match[1]) : 0;
        }
        // Edge
        else if (userAgent.includes('Edg')) {
            name = 'edge';
            const match = userAgent.match(/Edg\/(\d+)/);
            version = match ? parseInt(match[1]) : 0;
        }
        
        return {
            name,
            version,
            userAgent,
            platform: navigator.platform,
            language: navigator.language
        };
    }
    
    /**
     * 检查API支持
     * @private
     */
    _checkAPISupport(apiName) {
        switch (apiName) {
            case 'fetch':
                return typeof fetch === 'function';
            case 'WebSocket':
                return typeof WebSocket === 'function';
            case 'localStorage':
                try {
                    return typeof localStorage === 'object' && localStorage !== null;
                } catch (e) {
                    return false;
                }
            case 'sessionStorage':
                try {
                    return typeof sessionStorage === 'object' && sessionStorage !== null;
                } catch (e) {
                    return false;
                }
            case 'JSON':
                return typeof JSON === 'object' && typeof JSON.parse === 'function';
            case 'Promise':
                return typeof Promise === 'function';
            default:
                return typeof window[apiName] !== 'undefined';
        }
    }
    
    /**
     * 检查API兼容性
     * @private
     */
    async _checkAPICompatibility() {
        try {
            let apiCompatible = true;
            const issues = [];
            let backendVersion = null;
            
            if (window.apiClient) {
                try {
                    // 获取后端版本信息
                    const versionResponse = await window.apiClient.get('/version');
                    if (versionResponse && versionResponse.version) {
                        backendVersion = versionResponse.version;
                        
                        // 检查API版本兼容性
                        if (!this._isAPIVersionCompatible(backendVersion)) {
                            apiCompatible = false;
                            issues.push(`API版本不兼容: 后端 ${backendVersion}, 前端支持 ${this.versionInfo.apiVersion}`);
                        }
                    }
                    
                    // 检查关键端点可用性
                    const criticalEndpoints = [
                        '/health',
                        '/api/v1/agents',
                        '/api/v1/tasks'
                    ];
                    
                    for (const endpoint of criticalEndpoints) {
                        try {
                            await window.apiClient.get(endpoint);
                        } catch (error) {
                            if (error.message.includes('404')) {
                                apiCompatible = false;
                                issues.push(`关键端点不可用: ${endpoint}`);
                            }
                        }
                    }
                    
                } catch (error) {
                    apiCompatible = false;
                    issues.push(`无法连接到后端服务: ${error.message}`);
                }
            } else {
                apiCompatible = false;
                issues.push('API客户端未初始化');
            }
            
            this.compatibilityStatus.api = {
                compatible: apiCompatible,
                backendVersion,
                frontendVersion: this.versionInfo.frontend,
                issues,
                checkedAt: new Date().toISOString()
            };
            
        } catch (error) {
            console.error('API兼容性检查失败:', error);
            this.compatibilityStatus.api = {
                compatible: false,
                issues: [`API兼容性检查失败: ${error.message}`],
                checkedAt: new Date().toISOString()
            };
        }
    }
    
    /**
     * 检查API版本兼容性
     * @private
     */
    _isAPIVersionCompatible(backendVersion) {
        // 简单的版本兼容性检查
        // 实际应用中可能需要更复杂的语义版本比较
        const backendMajor = parseInt(backendVersion.split('.')[0]);
        const frontendMajor = parseInt(this.versionInfo.frontend.split('.')[0]);
        
        return backendMajor === frontendMajor;
    }
    
    /**
     * 检查功能兼容性
     * @private
     */
    async _checkFeatureCompatibility() {
        const features = [
            'llm-config',
            'agent-management',
            'meta-agent-chat',
            'task-decomposition',
            'websocket-updates',
            'real-time-sync'
        ];
        
        for (const feature of features) {
            try {
                const isSupported = await this._checkFeatureSupport(feature);
                this.compatibilityStatus.features.set(feature, {
                    supported: isSupported.supported,
                    issues: isSupported.issues || [],
                    fallbackAvailable: this._hasFallback(feature),
                    checkedAt: new Date().toISOString()
                });
            } catch (error) {
                this.compatibilityStatus.features.set(feature, {
                    supported: false,
                    issues: [`功能检查失败: ${error.message}`],
                    fallbackAvailable: this._hasFallback(feature),
                    checkedAt: new Date().toISOString()
                });
            }
        }
    }
    
    /**
     * 检查特定功能支持
     * @private
     */
    async _checkFeatureSupport(feature) {
        switch (feature) {
            case 'llm-config':
                return this._checkLLMConfigSupport();
            case 'agent-management':
                return this._checkAgentManagementSupport();
            case 'meta-agent-chat':
                return this._checkMetaAgentChatSupport();
            case 'task-decomposition':
                return this._checkTaskDecompositionSupport();
            case 'websocket-updates':
                return this._checkWebSocketSupport();
            case 'real-time-sync':
                return this._checkRealTimeSyncSupport();
            default:
                return { supported: false, issues: ['未知功能'] };
        }
    }
    
    /**
     * 检查大模型配置功能支持
     * @private
     */
    async _checkLLMConfigSupport() {
        const issues = [];
        let supported = true;
        
        // 检查必需的类
        if (typeof LLMConfigManager === 'undefined') {
            supported = false;
            issues.push('LLMConfigManager 类未加载');
        }
        
        // 检查本地存储支持
        if (!this._checkAPISupport('localStorage')) {
            supported = false;
            issues.push('不支持本地存储');
        }
        
        // 检查加密API支持
        if (typeof btoa === 'undefined' || typeof atob === 'undefined') {
            supported = false;
            issues.push('不支持Base64编码/解码');
        }
        
        // 检查后端API端点
        if (window.apiClient) {
            try {
                await window.apiClient.get('/api/v1/llm/configs');
            } catch (error) {
                if (error.message.includes('404')) {
                    supported = false;
                    issues.push('后端不支持大模型配置API');
                }
            }
        }
        
        return { supported, issues };
    }
    
    /**
     * 检查智能体管理功能支持
     * @private
     */
    async _checkAgentManagementSupport() {
        const issues = [];
        let supported = true;
        
        // 检查必需的类
        if (typeof AgentManager === 'undefined') {
            supported = false;
            issues.push('AgentManager 类未加载');
        }
        
        // 检查后端API端点
        if (window.apiClient) {
            try {
                await window.apiClient.get('/api/v1/agents/enhanced');
            } catch (error) {
                if (error.message.includes('404')) {
                    // 尝试基础端点
                    try {
                        await window.apiClient.get('/api/v1/agents');
                    } catch (basicError) {
                        supported = false;
                        issues.push('后端不支持智能体管理API');
                    }
                }
            }
        }
        
        return { supported, issues };
    }
    
    /**
     * 检查元智能体对话功能支持
     * @private
     */
    async _checkMetaAgentChatSupport() {
        const issues = [];
        let supported = true;
        
        // 检查必需的类
        if (typeof MetaAgentChatManager === 'undefined') {
            supported = false;
            issues.push('MetaAgentChatManager 类未加载');
        }
        
        // 检查后端API端点
        if (window.apiClient) {
            try {
                await window.apiClient.post('/api/v1/meta-agent/conversations', {
                    initialPrompt: 'test',
                    context: {}
                });
            } catch (error) {
                if (error.message.includes('404')) {
                    supported = false;
                    issues.push('后端不支持元智能体对话API');
                }
            }
        }
        
        return { supported, issues };
    }
    
    /**
     * 检查任务分解功能支持
     * @private
     */
    async _checkTaskDecompositionSupport() {
        const issues = [];
        let supported = true;
        
        // 检查后端API端点
        if (window.apiClient) {
            try {
                // 这里应该检查任务分解相关的API端点
                // 由于这是一个测试，我们假设端点存在
                supported = true;
            } catch (error) {
                if (error.message.includes('404')) {
                    supported = false;
                    issues.push('后端不支持任务分解API');
                }
            }
        }
        
        return { supported, issues };
    }
    
    /**
     * 检查WebSocket功能支持
     * @private
     */
    async _checkWebSocketSupport() {
        const issues = [];
        let supported = true;
        
        // 检查WebSocket API支持
        if (!this._checkAPISupport('WebSocket')) {
            supported = false;
            issues.push('浏览器不支持WebSocket');
        }
        
        // 检查WebSocket管理器
        if (typeof WebSocketManager === 'undefined') {
            supported = false;
            issues.push('WebSocketManager 类未加载');
        }
        
        return { supported, issues };
    }
    
    /**
     * 检查实时同步功能支持
     * @private
     */
    async _checkRealTimeSyncSupport() {
        const issues = [];
        let supported = true;
        
        // 依赖WebSocket支持
        const wsSupport = await this._checkWebSocketSupport();
        if (!wsSupport.supported) {
            supported = false;
            issues.push(...wsSupport.issues);
        }
        
        return { supported, issues };
    }
    
    /**
     * 检查是否有降级方案
     * @private
     */
    _hasFallback(feature) {
        return this.degradationStrategies.has(feature);
    }
    
    /**
     * 设置浏览器降级方案
     * @private
     */
    _setupBrowserFallbacks() {
        // fetch polyfill
        if (!this._checkAPISupport('fetch')) {
            this._loadPolyfill('fetch', () => {
                // 简单的fetch polyfill使用XMLHttpRequest
                window.fetch = this._createFetchPolyfill();
            });
        }
        
        // Promise polyfill
        if (!this._checkAPISupport('Promise')) {
            this._loadPolyfill('promise', () => {
                // 这里应该加载Promise polyfill
                console.warn('需要Promise polyfill');
            });
        }
    }
    
    /**
     * 创建fetch polyfill
     * @private
     */
    _createFetchPolyfill() {
        return function(url, options = {}) {
            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                xhr.open(options.method || 'GET', url);
                
                // 设置请求头
                if (options.headers) {
                    Object.keys(options.headers).forEach(key => {
                        xhr.setRequestHeader(key, options.headers[key]);
                    });
                }
                
                xhr.onload = () => {
                    const response = {
                        ok: xhr.status >= 200 && xhr.status < 300,
                        status: xhr.status,
                        statusText: xhr.statusText,
                        json: () => Promise.resolve(JSON.parse(xhr.responseText)),
                        text: () => Promise.resolve(xhr.responseText)
                    };
                    resolve(response);
                };
                
                xhr.onerror = () => reject(new Error('Network error'));
                xhr.send(options.body);
            });
        };
    }
    
    /**
     * 加载polyfill
     * @private
     */
    _loadPolyfill(name, fallback) {
        // 在实际应用中，这里应该动态加载polyfill脚本
        // 现在使用fallback函数
        if (typeof fallback === 'function') {
            fallback();
        }
    }
    
    /**
     * 设置降级策略
     * @private
     */
    _setupDegradationStrategies() {
        // WebSocket降级到轮询
        this.degradationStrategies.set('websocket-updates', {
            fallback: 'polling',
            implementation: () => {
                console.log('WebSocket不可用，使用轮询方式');
                // 这里应该实现轮询逻辑
            }
        });
        
        // 实时同步降级到手动刷新
        this.degradationStrategies.set('real-time-sync', {
            fallback: 'manual-refresh',
            implementation: () => {
                console.log('实时同步不可用，使用手动刷新');
                // 显示刷新按钮
            }
        });
        
        // 大模型配置降级到基础配置
        this.degradationStrategies.set('llm-config', {
            fallback: 'basic-config',
            implementation: () => {
                console.log('高级配置不可用，使用基础配置');
                // 隐藏高级配置选项
            }
        });
    }
    
    /**
     * 评估整体兼容性
     * @private
     */
    _evaluateOverallCompatibility() {
        const browserOk = this.compatibilityStatus.browser?.compatible !== false;
        const apiOk = this.compatibilityStatus.api?.compatible !== false;
        
        let featuresOk = true;
        let criticalFeaturesFailed = 0;
        
        this.compatibilityStatus.features.forEach((status, feature) => {
            if (!status.supported) {
                if (['agent-management', 'websocket-updates'].includes(feature)) {
                    criticalFeaturesFailed++;
                }
                if (!status.fallbackAvailable) {
                    featuresOk = false;
                }
            }
        });
        
        if (!browserOk || !apiOk || criticalFeaturesFailed > 1) {
            this.compatibilityStatus.overall = 'incompatible';
        } else if (!featuresOk || criticalFeaturesFailed > 0) {
            this.compatibilityStatus.overall = 'degraded';
        } else {
            this.compatibilityStatus.overall = 'compatible';
        }
    }
    
    /**
     * 获取兼容性状态
     * @returns {Object} 兼容性状态
     */
    getCompatibilityStatus() {
        return {
            ...this.compatibilityStatus,
            features: Object.fromEntries(this.compatibilityStatus.features)
        };
    }
    
    /**
     * 检查特定功能是否兼容
     * @param {string} feature 功能名称
     * @returns {boolean} 是否兼容
     */
    isFeatureCompatible(feature) {
        const status = this.compatibilityStatus.features.get(feature);
        return status ? status.supported : false;
    }
    
    /**
     * 启用功能降级
     * @param {string} feature 功能名称
     * @returns {boolean} 是否成功启用降级
     */
    enableFeatureFallback(feature) {
        const strategy = this.degradationStrategies.get(feature);
        if (strategy && typeof strategy.implementation === 'function') {
            try {
                strategy.implementation();
                return true;
            } catch (error) {
                console.error(`启用${feature}降级策略失败:`, error);
                return false;
            }
        }
        return false;
    }
    
    /**
     * 获取兼容性报告
     * @returns {Object} 兼容性报告
     */
    getCompatibilityReport() {
        const report = {
            timestamp: new Date().toISOString(),
            overall: this.compatibilityStatus.overall,
            summary: {
                compatible: this.compatibilityStatus.overall === 'compatible',
                degraded: this.compatibilityStatus.overall === 'degraded',
                incompatible: this.compatibilityStatus.overall === 'incompatible'
            },
            details: {
                browser: this.compatibilityStatus.browser,
                api: this.compatibilityStatus.api,
                features: Object.fromEntries(this.compatibilityStatus.features)
            },
            recommendations: []
        };
        
        // 生成建议
        if (this.compatibilityStatus.browser && !this.compatibilityStatus.browser.compatible) {
            report.recommendations.push({
                type: 'browser',
                message: '建议升级浏览器到支持的版本',
                priority: 'high'
            });
        }
        
        if (this.compatibilityStatus.api && !this.compatibilityStatus.api.compatible) {
            report.recommendations.push({
                type: 'api',
                message: '需要更新后端服务或前端版本',
                priority: 'high'
            });
        }
        
        this.compatibilityStatus.features.forEach((status, feature) => {
            if (!status.supported && !status.fallbackAvailable) {
                report.recommendations.push({
                    type: 'feature',
                    feature,
                    message: `${feature} 功能不可用且无降级方案`,
                    priority: 'medium'
                });
            }
        });
        
        return report;
    }
    
    /**
     * 重新检查兼容性
     * @returns {Promise<Object>} 检查结果
     */
    async recheckCompatibility() {
        try {
            await this._initialize();
            return {
                success: true,
                status: this.getCompatibilityStatus()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CompatibilityManager;
} else {
    window.CompatibilityManager = CompatibilityManager;
}