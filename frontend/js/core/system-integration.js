/**
 * 系统集成管理器
 * 负责协调各个组件，确保系统的整体兼容性和稳定性
 */
class SystemIntegrationManager {
    constructor() {
        this.components = new Map();
        this.integrationStatus = {
            initialized: false,
            compatible: null,
            degraded: false,
            errors: []
        };
        
        this.compatibilityManager = null;
        this.featureFlagManager = null;
        this.monitoringSystem = null;
        this.errorHandler = null;
        this.dataCompatibilityHandler = null;
        
        this.errorBoundaries = new Map();
        this.gracefulDegradation = new Map();
        
        this.initializationOrder = [
            'errorHandler',
            'compatibilityManager',
            'dataCompatibilityHandler',
            'featureFlagManager',
            'monitoringSystem',
            'llmConfigManager',
            'agentManager',
            'metaAgentChatManager'
        ];
        
        // 初始化系统
        this._initialize();
    }
    
    /**
     * 初始化系统集成
     * @private
     */
    async _initialize() {
        try {
            console.log('开始系统集成初始化...');
            
            // 按顺序初始化核心组件
            await this._initializeCoreComponents();
            
            // 设置组件间的集成
            await this._setupComponentIntegration();
            
            // 设置错误边界
            this._setupErrorBoundaries();
            
            // 设置优雅降级
            this._setupGracefulDegradation();
            
            // 执行兼容性检查
            await this._performCompatibilityCheck();
            
            // 启动监控
            this._startMonitoring();
            
            this.integrationStatus.initialized = true;
            console.log('系统集成初始化完成');
            
        } catch (error) {
            console.error('系统集成初始化失败:', error);
            this.integrationStatus.errors.push(error.message);
            
            // 尝试降级启动
            await this._fallbackInitialization();
        }
    }
    
    /**
     * 初始化核心组件
     * @private
     */
    async _initializeCoreComponents() {
        for (const componentName of this.initializationOrder) {
            try {
                await this._initializeComponent(componentName);
            } catch (error) {
                console.error(`初始化组件 ${componentName} 失败:`, error);
                this.integrationStatus.errors.push(`${componentName}: ${error.message}`);
                
                // 对于关键组件，尝试降级初始化
                if (['errorHandler', 'compatibilityManager'].includes(componentName)) {
                    await this._fallbackComponentInit(componentName);
                }
            }
        }
    }
    
    /**
     * 初始化单个组件
     * @private
     */
    async _initializeComponent(componentName) {
        switch (componentName) {
            case 'errorHandler':
                if (typeof ErrorHandler !== 'undefined') {
                    this.errorHandler = new ErrorHandler();
                    this.components.set('errorHandler', this.errorHandler);
                    window.errorHandler = this.errorHandler;
                }
                break;
                
            case 'compatibilityManager':
                if (typeof CompatibilityManager !== 'undefined') {
                    this.compatibilityManager = new CompatibilityManager();
                    this.components.set('compatibilityManager', this.compatibilityManager);
                }
                break;
                
            case 'dataCompatibilityHandler':
                if (typeof DataCompatibilityHandler !== 'undefined') {
                    this.dataCompatibilityHandler = new DataCompatibilityHandler();
                    this.components.set('dataCompatibilityHandler', this.dataCompatibilityHandler);
                }
                break;
                
            case 'featureFlagManager':
                if (typeof FeatureFlagManager !== 'undefined') {
                    this.featureFlagManager = new FeatureFlagManager();
                    this.components.set('featureFlagManager', this.featureFlagManager);
                    window.featureFlagManager = this.featureFlagManager;
                }
                break;
                
            case 'monitoringSystem':
                if (typeof MonitoringSystem !== 'undefined') {
                    this.monitoringSystem = new MonitoringSystem();
                    this.components.set('monitoringSystem', this.monitoringSystem);
                }
                break;
                
            case 'llmConfigManager':
                if (typeof LLMConfigManager !== 'undefined' && 
                    this._isFeatureEnabled('llm-config')) {
                    const llmConfigManager = new LLMConfigManager();
                    this.components.set('llmConfigManager', llmConfigManager);
                    window.llmConfigManager = llmConfigManager;
                }
                break;
                
            case 'agentManager':
                if (typeof AgentManager !== 'undefined' && 
                    this._isFeatureEnabled('enhanced-agent-management')) {
                    const agentManager = new AgentManager();
                    this.components.set('agentManager', agentManager);
                    window.agentManager = agentManager;
                }
                break;
                
            case 'metaAgentChatManager':
                if (typeof MetaAgentChatManager !== 'undefined' && 
                    this._isFeatureEnabled('meta-agent-chat')) {
                    const metaAgentChatManager = new MetaAgentChatManager();
                    this.components.set('metaAgentChatManager', metaAgentChatManager);
                    window.metaAgentChatManager = metaAgentChatManager;
                }
                break;
        }
    }
    
    /**
     * 降级组件初始化
     * @private
     */
    async _fallbackComponentInit(componentName) {
        switch (componentName) {
            case 'errorHandler':
                // 创建最小错误处理器
                this.errorHandler = {
                    handleError: (error) => console.error('Error:', error),
                    registerHandler: () => {},
                    onNotification: () => {}
                };
                this.components.set('errorHandler', this.errorHandler);
                window.errorHandler = this.errorHandler;
                break;
                
            case 'compatibilityManager':
                // 创建最小兼容性管理器
                this.compatibilityManager = {
                    getCompatibilityStatus: () => ({ overall: 'unknown' }),
                    isFeatureCompatible: () => true,
                    enableFeatureFallback: () => false
                };
                this.components.set('compatibilityManager', this.compatibilityManager);
                break;
        }
    }
    
    /**
     * 设置组件间集成
     * @private
     */
    async _setupComponentIntegration() {
        // 错误处理器与监控系统集成
        if (this.errorHandler && this.monitoringSystem) {
            this.errorHandler.onNotification((notification) => {
                if (notification.type === 'error' && notification.severity === 'high') {
                    // 监控系统会自动处理这些错误
                }
            });
        }
        
        // 功能开关与兼容性管理器集成
        if (this.featureFlagManager && this.compatibilityManager) {
            this.featureFlagManager.onFlagChange((flagName, flagConfig) => {
                // 当功能开关变化时，重新检查兼容性
                if (flagConfig.enabled) {
                    const isCompatible = this.compatibilityManager.isFeatureCompatible(flagName);
                    if (!isCompatible) {
                        console.warn(`功能 ${flagName} 不兼容，建议禁用`);
                    }
                }
            });
        }
        
        // 数据兼容性处理器与其他组件集成
        if (this.dataCompatibilityHandler) {
            // 为各个管理器提供数据迁移支持
            this._setupDataMigrationSupport();
        }
        
        // 监控系统与其他组件集成
        if (this.monitoringSystem) {
            this._setupMonitoringIntegration();
        }
    }
    
    /**
     * 设置数据迁移支持
     * @private
     */
    _setupDataMigrationSupport() {
        const managers = ['llmConfigManager', 'agentManager', 'metaAgentChatManager'];
        
        managers.forEach(managerName => {
            const manager = this.components.get(managerName);
            if (manager && typeof manager.loadData === 'function') {
                // 包装loadData方法以支持数据迁移
                const originalLoadData = manager.loadData.bind(manager);
                manager.loadData = async (data, dataType) => {
                    try {
                        // 尝试迁移数据
                        const migrationResult = this.dataCompatibilityHandler.migrateData(data, dataType);
                        if (migrationResult.success) {
                            return originalLoadData(migrationResult.data);
                        } else {
                            console.warn(`数据迁移失败: ${migrationResult.error}`);
                            return originalLoadData(data);
                        }
                    } catch (error) {
                        console.error(`数据加载失败: ${error.message}`);
                        return originalLoadData(data);
                    }
                };
            }
        });
    }
    
    /**
     * 设置监控集成
     * @private
     */
    _setupMonitoringIntegration() {
        // 监控告警处理
        this.monitoringSystem.onAlert((alert) => {
            console.warn(`[系统告警] ${alert.category}: ${alert.type}`, alert);
            
            // 根据告警类型采取相应措施
            this._handleSystemAlert(alert);
        });
        
        // 为各个组件添加性能监控
        this.components.forEach((component, name) => {
            if (component && typeof component === 'object') {
                this._wrapComponentWithMonitoring(component, name);
            }
        });
    }
    
    /**
     * 为组件添加监控包装
     * @private
     */
    _wrapComponentWithMonitoring(component, componentName) {
        const methodNames = Object.getOwnPropertyNames(Object.getPrototypeOf(component))
            .filter(name => typeof component[name] === 'function' && name !== 'constructor');
        
        methodNames.forEach(methodName => {
            const originalMethod = component[methodName];
            if (typeof originalMethod === 'function') {
                component[methodName] = async (...args) => {
                    const startTime = performance.now();
                    
                    try {
                        const result = await originalMethod.apply(component, args);
                        const duration = performance.now() - startTime;
                        
                        // 记录性能指标
                        if (this.monitoringSystem) {
                            this.monitoringSystem._recordMetric(`${componentName}_${methodName}_duration`, duration);
                            this.monitoringSystem._recordMetric(`${componentName}_${methodName}_success`, 1);
                        }
                        
                        return result;
                    } catch (error) {
                        const duration = performance.now() - startTime;
                        
                        // 记录错误指标
                        if (this.monitoringSystem) {
                            this.monitoringSystem._recordMetric(`${componentName}_${methodName}_duration`, duration);
                            this.monitoringSystem._recordMetric(`${componentName}_${methodName}_error`, 1);
                        }
                        
                        throw error;
                    }
                };
            }
        });
    }
    
    /**
     * 处理系统告警
     * @private
     */
    _handleSystemAlert(alert) {
        switch (alert.category) {
            case 'performance':
                this._handlePerformanceAlert(alert);
                break;
            case 'error':
                this._handleErrorAlert(alert);
                break;
            case 'resource':
                this._handleResourceAlert(alert);
                break;
            case 'health':
                this._handleHealthAlert(alert);
                break;
        }
    }
    
    /**
     * 处理性能告警
     * @private
     */
    _handlePerformanceAlert(alert) {
        if (alert.type === 'slow_api_response') {
            // 可能需要启用缓存或降级到本地数据
            console.log('考虑启用API响应缓存');
        } else if (alert.type === 'slow_page_load') {
            // 可能需要延迟加载非关键功能
            console.log('考虑延迟加载非关键功能');
        }
    }
    
    /**
     * 处理错误告警
     * @private
     */
    _handleErrorAlert(alert) {
        if (alert.type === 'high_error_rate') {
            // 启用更严格的错误边界
            this._enableStrictErrorBoundaries();
        } else if (alert.type === 'high_severity_error') {
            // 可能需要禁用相关功能
            console.log('考虑禁用相关功能以防止错误扩散');
        }
    }
    
    /**
     * 处理资源告警
     * @private
     */
    _handleResourceAlert(alert) {
        if (alert.type === 'high_memory_usage') {
            // 清理缓存和临时数据
            this._cleanupResources();
        } else if (alert.type === 'excessive_dom_nodes') {
            // 可能存在内存泄漏
            console.warn('检测到可能的内存泄漏，建议刷新页面');
        }
    }
    
    /**
     * 处理健康检查告警
     * @private
     */
    _handleHealthAlert(alert) {
        if (alert.component === 'api') {
            // API不可用，启用离线模式
            this._enableOfflineMode();
        } else if (alert.component === 'websocket') {
            // WebSocket不可用，降级到轮询
            this._fallbackToPolling();
        }
    }
    
    /**
     * 设置错误边界
     * @private
     */
    _setupErrorBoundaries() {
        if (typeof ErrorBoundary === 'undefined') {
            return;
        }
        
        // 为每个主要组件创建错误边界
        const componentNames = ['llmConfigManager', 'agentManager', 'metaAgentChatManager'];
        
        componentNames.forEach(componentName => {
            const component = this.components.get(componentName);
            if (component) {
                const errorBoundary = new ErrorBoundary({
                    componentName,
                    isolateErrors: true,
                    retryable: true,
                    maxRetries: 3,
                    onError: (error, errorInfo) => {
                        console.error(`[ErrorBoundary:${componentName}]`, error, errorInfo);
                        
                        // 报告到监控系统
                        if (this.monitoringSystem) {
                            this.monitoringSystem._triggerAlert('error', {
                                type: 'component_error',
                                component: componentName,
                                message: error.message,
                                stack: error.stack
                            });
                        }
                    }
                });
                
                this.errorBoundaries.set(componentName, errorBoundary);
                
                // 包装组件方法
                const wrappedComponent = errorBoundary.wrapObject(component);
                this.components.set(componentName, wrappedComponent);
            }
        });
    }
    
    /**
     * 设置优雅降级
     * @private
     */
    _setupGracefulDegradation() {
        // WebSocket降级到轮询
        this.gracefulDegradation.set('websocket', {
            condition: () => !window.wsManager || window.wsManager.ws?.readyState !== WebSocket.OPEN,
            fallback: () => {
                console.log('WebSocket不可用，启用轮询模式');
                // 这里应该实现轮询逻辑
                this._enablePollingMode();
            }
        });
        
        // API降级到本地缓存
        this.gracefulDegradation.set('api', {
            condition: () => !window.apiClient,
            fallback: () => {
                console.log('API不可用，使用本地缓存数据');
                this._enableOfflineMode();
            }
        });
        
        // 高级功能降级到基础功能
        this.gracefulDegradation.set('advanced-features', {
            condition: () => this.integrationStatus.compatible === 'incompatible',
            fallback: () => {
                console.log('系统不兼容，禁用高级功能');
                this._disableAdvancedFeatures();
            }
        });
    }
    
    /**
     * 执行兼容性检查
     * @private
     */
    async _performCompatibilityCheck() {
        if (this.compatibilityManager) {
            const status = this.compatibilityManager.getCompatibilityStatus();
            this.integrationStatus.compatible = status.overall;
            
            if (status.overall === 'degraded') {
                this.integrationStatus.degraded = true;
                console.warn('系统运行在降级模式');
                
                // 启用相应的降级策略
                this._enableDegradedMode();
            } else if (status.overall === 'incompatible') {
                console.error('系统不兼容，启用最小功能模式');
                this._enableMinimalMode();
            }
        }
    }
    
    /**
     * 启动监控
     * @private
     */
    _startMonitoring() {
        if (this.monitoringSystem) {
            this.monitoringSystem.startMonitoring();
        }
    }
    
    /**
     * 降级初始化
     * @private
     */
    async _fallbackInitialization() {
        console.log('尝试降级初始化...');
        
        try {
            // 只初始化最基本的组件
            const essentialComponents = ['errorHandler', 'compatibilityManager'];
            
            for (const componentName of essentialComponents) {
                if (!this.components.has(componentName)) {
                    await this._fallbackComponentInit(componentName);
                }
            }
            
            this.integrationStatus.initialized = true;
            this.integrationStatus.degraded = true;
            
            console.log('降级初始化完成');
            
        } catch (error) {
            console.error('降级初始化也失败了:', error);
            this.integrationStatus.errors.push(`Fallback failed: ${error.message}`);
        }
    }
    
    /**
     * 检查功能是否启用
     * @private
     */
    _isFeatureEnabled(featureName) {
        return this.featureFlagManager ? this.featureFlagManager.isEnabled(featureName) : true;
    }
    
    /**
     * 启用严格错误边界
     * @private
     */
    _enableStrictErrorBoundaries() {
        this.errorBoundaries.forEach(boundary => {
            boundary.isolateErrors = true;
            boundary.retryable = false;
        });
    }
    
    /**
     * 清理资源
     * @private
     */
    _cleanupResources() {
        // 清理各个组件的缓存
        this.components.forEach(component => {
            if (component && typeof component.clearCache === 'function') {
                component.clearCache();
            }
        });
        
        // 清理监控数据
        if (this.monitoringSystem) {
            this.monitoringSystem._cleanupOldData();
        }
    }
    
    /**
     * 启用离线模式
     * @private
     */
    _enableOfflineMode() {
        console.log('启用离线模式');
        // 这里应该实现离线模式逻辑
    }
    
    /**
     * 降级到轮询模式
     * @private
     */
    _fallbackToPolling() {
        console.log('WebSocket不可用，降级到轮询模式');
        this._enablePollingMode();
    }
    
    /**
     * 启用轮询模式
     * @private
     */
    _enablePollingMode() {
        // 这里应该实现轮询逻辑
        if (this.components.has('agentManager')) {
            const agentManager = this.components.get('agentManager');
            if (agentManager && typeof agentManager.refreshAgentStatus === 'function') {
                setInterval(() => {
                    agentManager.refreshAgentStatus();
                }, 30000); // 每30秒轮询一次
            }
        }
    }
    
    /**
     * 启用降级模式
     * @private
     */
    _enableDegradedMode() {
        // 禁用一些非关键功能
        if (this.featureFlagManager) {
            this.featureFlagManager.setFlag('experimental-features', false);
            this.featureFlagManager.setFlag('advanced-config', false);
        }
    }
    
    /**
     * 启用最小功能模式
     * @private
     */
    _enableMinimalMode() {
        // 只保留最基本的功能
        if (this.featureFlagManager) {
            const essentialFeatures = ['llm-config', 'enhanced-agent-management'];
            const allFlags = this.featureFlagManager.getAllFlags();
            
            Object.keys(allFlags).forEach(flagName => {
                if (!essentialFeatures.includes(flagName)) {
                    this.featureFlagManager.setFlag(flagName, false);
                }
            });
        }
    }
    
    /**
     * 禁用高级功能
     * @private
     */
    _disableAdvancedFeatures() {
        if (this.featureFlagManager) {
            this.featureFlagManager.setFlag('meta-agent-chat', false);
            this.featureFlagManager.setFlag('task-decomposition', false);
            this.featureFlagManager.setFlag('advanced-config', false);
            this.featureFlagManager.setFlag('experimental-features', false);
        }
    }
    
    /**
     * 获取系统状态
     * @returns {Object} 系统状态
     */
    getSystemStatus() {
        const componentStatus = {};
        this.components.forEach((component, name) => {
            componentStatus[name] = {
                initialized: true,
                hasError: this.errorBoundaries.has(name) ? 
                    this.errorBoundaries.get(name).hasError() : false
            };
        });
        
        return {
            integration: this.integrationStatus,
            components: componentStatus,
            monitoring: this.monitoringSystem ? this.monitoringSystem.getStatus() : null,
            compatibility: this.compatibilityManager ? 
                this.compatibilityManager.getCompatibilityStatus() : null,
            featureFlags: this.featureFlagManager ? 
                this.featureFlagManager.getAllFlags() : null
        };
    }
    
    /**
     * 获取组件
     * @param {string} componentName 组件名称
     * @returns {Object|null} 组件实例
     */
    getComponent(componentName) {
        return this.components.get(componentName) || null;
    }
    
    /**
     * 重启组件
     * @param {string} componentName 组件名称
     * @returns {Promise<boolean>} 重启是否成功
     */
    async restartComponent(componentName) {
        try {
            // 停止组件
            const component = this.components.get(componentName);
            if (component && typeof component.destroy === 'function') {
                component.destroy();
            }
            
            // 清除错误状态
            if (this.errorBoundaries.has(componentName)) {
                this.errorBoundaries.get(componentName).clearError();
            }
            
            // 重新初始化组件
            await this._initializeComponent(componentName);
            
            console.log(`组件 ${componentName} 重启成功`);
            return true;
            
        } catch (error) {
            console.error(`组件 ${componentName} 重启失败:`, error);
            return false;
        }
    }
    
    /**
     * 销毁系统集成
     */
    destroy() {
        // 停止监控
        if (this.monitoringSystem) {
            this.monitoringSystem.destroy();
        }
        
        // 销毁所有组件
        this.components.forEach(component => {
            if (component && typeof component.destroy === 'function') {
                component.destroy();
            }
        });
        
        // 清理错误边界
        this.errorBoundaries.forEach(boundary => {
            boundary.destroy();
        });
        
        this.components.clear();
        this.errorBoundaries.clear();
        this.gracefulDegradation.clear();
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SystemIntegrationManager;
} else {
    window.SystemIntegrationManager = SystemIntegrationManager;
}