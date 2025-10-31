/**
 * 用户体验和性能优化集成模块
 * 整合所有UX和性能优化功能
 */
class UXPerformanceIntegration {
    constructor() {
        this.initialized = false;
        this.modules = {
            responsive: null,
            performance: null,
            feedback: null,
            help: null,
            sync: null,
            websocket: null
        };
        
        this.config = {
            enableResponsive: true,
            enablePerformance: true,
            enableFeedback: true,
            enableHelp: true,
            enableSync: true,
            enableWebSocket: true,
            enableAnalytics: CONFIG.FEATURES.DEBUG_MODE || false
        };
        
        this.analytics = {
            pageLoadTime: 0,
            interactionCount: 0,
            errorCount: 0,
            performanceMetrics: {}
        };
        
        this.init();
    }
    
    /**
     * 初始化集成模块
     */
    async init() {
        if (this.initialized) {
            return;
        }
        
        console.log('Initializing UX Performance Integration...');
        
        try {
            // 记录开始时间
            const startTime = performance.now();
            
            // 初始化各个模块
            await this.initializeModules();
            
            // 设置模块间的协作
            this.setupModuleIntegration();
            
            // 设置全局事件监听
            this.setupGlobalEventListeners();
            
            // 设置性能监控
            this.setupPerformanceMonitoring();
            
            // 设置用户体验监控
            this.setupUXMonitoring();
            
            // 记录初始化时间
            const initTime = performance.now() - startTime;
            console.log(`UX Performance Integration initialized in ${initTime.toFixed(2)}ms`);
            
            this.initialized = true;
            
            // 触发初始化完成事件
            this.triggerEvent('initialized', { initTime });
            
        } catch (error) {
            console.error('Failed to initialize UX Performance Integration:', error);
            this.handleInitializationError(error);
        }
    }
    
    /**
     * 初始化各个模块
     */
    async initializeModules() {
        const modulePromises = [];
        
        // 响应式管理器
        if (this.config.enableResponsive && window.responsiveManager) {
            this.modules.responsive = window.responsiveManager;
            modulePromises.push(Promise.resolve());
        }
        
        // 性能管理器
        if (this.config.enablePerformance && window.performanceManager) {
            this.modules.performance = window.performanceManager;
            modulePromises.push(Promise.resolve());
        }
        
        // 反馈管理器
        if (this.config.enableFeedback && window.feedbackManager) {
            this.modules.feedback = window.feedbackManager;
            modulePromises.push(Promise.resolve());
        }
        
        // 帮助系统
        if (this.config.enableHelp && window.helpSystem) {
            this.modules.help = window.helpSystem;
            modulePromises.push(Promise.resolve());
        }
        
        // 同步管理器
        if (this.config.enableSync && window.syncManager) {
            this.modules.sync = window.syncManager;
            modulePromises.push(Promise.resolve());
        }
        
        // WebSocket管理器
        if (this.config.enableWebSocket && window.wsManager) {
            this.modules.websocket = window.wsManager;
            modulePromises.push(Promise.resolve());
        }
        
        await Promise.all(modulePromises);
    }
    
    /**
     * 设置模块间的协作
     */
    setupModuleIntegration() {
        // 响应式管理器与其他模块的协作
        if (this.modules.responsive) {
            this.modules.responsive.onResize((breakpoint) => {
                this.handleBreakpointChange(breakpoint);
            });
            
            this.modules.responsive.onOrientationChange((orientation) => {
                this.handleOrientationChange(orientation);
            });
        }
        
        // 同步管理器与反馈系统的协作
        if (this.modules.sync && this.modules.feedback) {
            window.addEventListener('syncStateChanged', (event) => {
                this.handleSyncStateChange(event.detail);
            });
            
            window.addEventListener('networkReconnected', () => {
                this.modules.feedback.showSuccess('网络连接', '网络连接已恢复');
            });
            
            window.addEventListener('networkDisconnected', () => {
                this.modules.feedback.showWarning('网络连接', '网络连接已断开，将在离线模式下工作');
            });
        }
        
        // WebSocket管理器与反馈系统的协作
        if (this.modules.websocket && this.modules.feedback) {
            this.modules.websocket.on('connected', () => {
                this.handleWebSocketConnected();
            });
            
            this.modules.websocket.on('disconnected', () => {
                this.handleWebSocketDisconnected();
            });
            
            this.modules.websocket.on('error', (data) => {
                this.handleWebSocketError(data);
            });
        }
        
        // 性能管理器与分析的协作
        if (this.modules.performance && this.config.enableAnalytics) {
            this.setupPerformanceAnalytics();
        }
    }
    
    /**
     * 设置全局事件监听
     */
    setupGlobalEventListeners() {
        // 全局错误处理
        window.addEventListener('error', (event) => {
            this.handleGlobalError(event);
        });
        
        window.addEventListener('unhandledrejection', (event) => {
            this.handleUnhandledRejection(event);
        });
        
        // 页面加载完成
        window.addEventListener('load', () => {
            this.handlePageLoad();
        });
        
        // 页面卸载
        window.addEventListener('beforeunload', () => {
            this.handlePageUnload();
        });
        
        // 用户交互监控
        ['click', 'keydown', 'scroll', 'resize'].forEach(eventType => {
            document.addEventListener(eventType, () => {
                this.trackUserInteraction(eventType);
            }, { passive: true });
        });
    }
    
    /**
     * 设置性能监控
     */
    setupPerformanceMonitoring() {
        if (!this.config.enableAnalytics) {
            return;
        }
        
        // 监控长任务
        if ('PerformanceObserver' in window) {
            try {
                const longTaskObserver = new PerformanceObserver((list) => {
                    list.getEntries().forEach(entry => {
                        if (entry.duration > 50) {
                            this.trackPerformanceIssue('long-task', {
                                duration: entry.duration,
                                startTime: entry.startTime
                            });
                        }
                    });
                });
                longTaskObserver.observe({ entryTypes: ['longtask'] });
            } catch (e) {
                console.warn('Long task monitoring not supported');
            }
        }
        
        // 监控内存使用
        if ('memory' in performance) {
            setInterval(() => {
                this.trackMemoryUsage();
            }, 60000); // 每分钟检查一次
        }
        
        // 监控FPS
        this.setupFPSMonitoring();
    }
    
    /**
     * 设置FPS监控
     */
    setupFPSMonitoring() {
        let lastTime = performance.now();
        let frameCount = 0;
        let fps = 0;
        
        const measureFPS = (currentTime) => {
            frameCount++;
            
            if (currentTime - lastTime >= 1000) {
                fps = Math.round((frameCount * 1000) / (currentTime - lastTime));
                frameCount = 0;
                lastTime = currentTime;
                
                // 如果FPS过低，记录性能问题
                if (fps < 30) {
                    this.trackPerformanceIssue('low-fps', { fps });
                }
            }
            
            requestAnimationFrame(measureFPS);
        };
        
        requestAnimationFrame(measureFPS);
    }
    
    /**
     * 设置用户体验监控
     */
    setupUXMonitoring() {
        // 监控点击响应时间
        document.addEventListener('click', (event) => {
            const startTime = performance.now();
            
            // 使用MutationObserver监控DOM变化
            const observer = new MutationObserver(() => {
                const responseTime = performance.now() - startTime;
                if (responseTime > 100) { // 超过100ms认为响应慢
                    this.trackUXIssue('slow-click-response', {
                        responseTime,
                        target: event.target.tagName
                    });
                }
                observer.disconnect();
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: true
            });
            
            // 2秒后自动断开观察
            setTimeout(() => observer.disconnect(), 2000);
        });
        
        // 监控表单交互
        document.addEventListener('input', (event) => {
            if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                this.trackFormInteraction(event.target);
            }
        });
    }
    
    /**
     * 处理断点变化
     */
    handleBreakpointChange(breakpoint) {
        console.log(`Breakpoint changed to: ${breakpoint}`);
        
        // 通知所有模块断点变化
        Object.values(this.modules).forEach(module => {
            if (module && typeof module.onBreakpointChange === 'function') {
                module.onBreakpointChange(breakpoint);
            }
        });
        
        // 记录分析数据
        if (this.config.enableAnalytics) {
            this.analytics.breakpointChanges = (this.analytics.breakpointChanges || 0) + 1;
        }
    }
    
    /**
     * 处理方向变化
     */
    handleOrientationChange(orientation) {
        console.log(`Orientation changed to: ${orientation}`);
        
        // 延迟处理，等待布局稳定
        setTimeout(() => {
            this.triggerEvent('orientationChanged', { orientation });
        }, 100);
    }
    
    /**
     * 处理同步状态变化
     */
    handleSyncStateChange(detail) {
        const { type, status, error } = detail;
        
        if (status === 'failed' && this.modules.feedback) {
            this.modules.feedback.showError(
                '同步失败',
                `${type} 数据同步失败: ${error || '未知错误'}`
            );
        }
        
        // 更新UI状态指示器
        this.updateSyncStatusIndicator(type, status);
    }
    
    /**
     * 处理WebSocket连接
     */
    handleWebSocketConnected() {
        console.log('WebSocket connected');
        
        if (this.modules.feedback) {
            // 只在重连时显示通知
            if (this.modules.websocket.reconnectAttempts > 0) {
                this.modules.feedback.showSuccess('连接恢复', 'WebSocket连接已恢复');
            }
        }
        
        // 更新连接状态指示器
        this.updateConnectionStatusIndicator('connected');
    }
    
    /**
     * 处理WebSocket断开
     */
    handleWebSocketDisconnected() {
        console.log('WebSocket disconnected');
        
        // 更新连接状态指示器
        this.updateConnectionStatusIndicator('disconnected');
    }
    
    /**
     * 处理WebSocket错误
     */
    handleWebSocketError(data) {
        console.error('WebSocket error:', data);
        
        if (this.modules.feedback) {
            this.modules.feedback.showError(
                '连接错误',
                'WebSocket连接出现错误，正在尝试重连...'
            );
        }
        
        // 更新连接状态指示器
        this.updateConnectionStatusIndicator('error');
    }
    
    /**
     * 处理全局错误
     */
    handleGlobalError(event) {
        console.error('Global error:', event.error);
        
        this.analytics.errorCount++;
        
        // 记录错误信息
        this.trackError('javascript-error', {
            message: event.message,
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            stack: event.error ? event.error.stack : null
        });
        
        // 显示用户友好的错误消息
        if (this.modules.feedback) {
            this.modules.feedback.showError(
                '系统错误',
                '发生了一个错误，请刷新页面重试'
            );
        }
    }
    
    /**
     * 处理未处理的Promise拒绝
     */
    handleUnhandledRejection(event) {
        console.error('Unhandled promise rejection:', event.reason);
        
        this.trackError('promise-rejection', {
            reason: event.reason,
            stack: event.reason ? event.reason.stack : null
        });
    }
    
    /**
     * 处理页面加载
     */
    handlePageLoad() {
        const loadTime = performance.now();
        this.analytics.pageLoadTime = loadTime;
        
        console.log(`Page loaded in ${loadTime.toFixed(2)}ms`);
        
        // 收集性能指标
        if (this.modules.performance) {
            this.analytics.performanceMetrics = this.modules.performance.getPerformanceMetrics();
        }
        
        // 触发页面加载完成事件
        this.triggerEvent('pageLoaded', { loadTime });
    }
    
    /**
     * 处理页面卸载
     */
    handlePageUnload() {
        // 发送分析数据
        this.sendAnalytics();
        
        // 清理资源
        this.cleanup();
    }
    
    /**
     * 跟踪用户交互
     */
    trackUserInteraction(type) {
        this.analytics.interactionCount++;
        
        // 记录交互类型统计
        if (!this.analytics.interactions) {
            this.analytics.interactions = {};
        }
        this.analytics.interactions[type] = (this.analytics.interactions[type] || 0) + 1;
    }
    
    /**
     * 跟踪性能问题
     */
    trackPerformanceIssue(type, data) {
        if (!this.analytics.performanceIssues) {
            this.analytics.performanceIssues = [];
        }
        
        this.analytics.performanceIssues.push({
            type,
            data,
            timestamp: Date.now()
        });
        
        console.warn(`Performance issue detected: ${type}`, data);
    }
    
    /**
     * 跟踪UX问题
     */
    trackUXIssue(type, data) {
        if (!this.analytics.uxIssues) {
            this.analytics.uxIssues = [];
        }
        
        this.analytics.uxIssues.push({
            type,
            data,
            timestamp: Date.now()
        });
        
        console.warn(`UX issue detected: ${type}`, data);
    }
    
    /**
     * 跟踪错误
     */
    trackError(type, data) {
        if (!this.analytics.errors) {
            this.analytics.errors = [];
        }
        
        this.analytics.errors.push({
            type,
            data,
            timestamp: Date.now()
        });
    }
    
    /**
     * 跟踪内存使用
     */
    trackMemoryUsage() {
        if ('memory' in performance) {
            const memory = performance.memory;
            const memoryData = {
                used: memory.usedJSHeapSize,
                total: memory.totalJSHeapSize,
                limit: memory.jsHeapSizeLimit,
                timestamp: Date.now()
            };
            
            if (!this.analytics.memoryUsage) {
                this.analytics.memoryUsage = [];
            }
            
            this.analytics.memoryUsage.push(memoryData);
            
            // 只保留最近的100条记录
            if (this.analytics.memoryUsage.length > 100) {
                this.analytics.memoryUsage.splice(0, 50);
            }
            
            // 检查内存泄漏
            if (memoryData.used > memoryData.limit * 0.8) {
                this.trackPerformanceIssue('high-memory-usage', memoryData);
            }
        }
    }
    
    /**
     * 跟踪表单交互
     */
    trackFormInteraction(element) {
        const formData = {
            tagName: element.tagName,
            type: element.type,
            name: element.name,
            id: element.id,
            timestamp: Date.now()
        };
        
        if (!this.analytics.formInteractions) {
            this.analytics.formInteractions = [];
        }
        
        this.analytics.formInteractions.push(formData);
    }
    
    /**
     * 更新同步状态指示器
     */
    updateSyncStatusIndicator(type, status) {
        const indicator = document.querySelector('.sync-status-indicator');
        if (indicator) {
            indicator.className = `sync-status-indicator ${status}`;
            indicator.title = `${type} 同步状态: ${status}`;
        }
    }
    
    /**
     * 更新连接状态指示器
     */
    updateConnectionStatusIndicator(status) {
        const indicator = document.querySelector('.connection-status-indicator');
        if (indicator) {
            indicator.className = `connection-status-indicator ${status}`;
            indicator.title = `连接状态: ${status}`;
        }
    }
    
    /**
     * 设置性能分析
     */
    setupPerformanceAnalytics() {
        // 定期收集性能数据
        setInterval(() => {
            if (this.modules.performance) {
                const metrics = this.modules.performance.getPerformanceMetrics();
                this.analytics.performanceMetrics = {
                    ...this.analytics.performanceMetrics,
                    ...metrics,
                    timestamp: Date.now()
                };
            }
        }, 30000); // 每30秒收集一次
    }
    
    /**
     * 发送分析数据
     */
    sendAnalytics() {
        if (!this.config.enableAnalytics || !this.analytics) {
            return;
        }
        
        try {
            // 准备分析数据
            const analyticsData = {
                ...this.analytics,
                sessionDuration: Date.now() - (this.analytics.sessionStart || Date.now()),
                userAgent: navigator.userAgent,
                viewport: {
                    width: window.innerWidth,
                    height: window.innerHeight
                },
                timestamp: Date.now()
            };
            
            // 发送到分析服务（这里使用localStorage存储）
            const existingData = JSON.parse(localStorage.getItem('ux_analytics') || '[]');
            existingData.push(analyticsData);
            
            // 只保留最近的50条记录
            if (existingData.length > 50) {
                existingData.splice(0, existingData.length - 50);
            }
            
            localStorage.setItem('ux_analytics', JSON.stringify(existingData));
            
            console.log('Analytics data sent:', analyticsData);
            
        } catch (error) {
            console.error('Failed to send analytics data:', error);
        }
    }
    
    /**
     * 获取分析报告
     */
    getAnalyticsReport() {
        return {
            current: this.analytics,
            historical: JSON.parse(localStorage.getItem('ux_analytics') || '[]')
        };
    }
    
    /**
     * 处理初始化错误
     */
    handleInitializationError(error) {
        console.error('UX Performance Integration initialization failed:', error);
        
        // 尝试降级模式
        this.enableFallbackMode();
    }
    
    /**
     * 启用降级模式
     */
    enableFallbackMode() {
        console.log('Enabling fallback mode...');
        
        // 禁用可能有问题的功能
        this.config.enablePerformance = false;
        this.config.enableAnalytics = false;
        
        // 只保留基本功能
        document.body.classList.add('fallback-mode');
        
        // 显示降级通知
        if (window.feedbackManager) {
            window.feedbackManager.showWarning(
                '功能降级',
                '部分高级功能已禁用以确保系统稳定运行'
            );
        }
    }
    
    /**
     * 触发事件
     */
    triggerEvent(event, data = null) {
        window.dispatchEvent(new CustomEvent(`ux:${event}`, {
            detail: data
        }));
    }
    
    /**
     * 获取系统状态
     */
    getSystemStatus() {
        const status = {
            initialized: this.initialized,
            modules: {},
            analytics: this.config.enableAnalytics ? this.analytics : null,
            config: this.config
        };
        
        // 收集各模块状态
        Object.keys(this.modules).forEach(key => {
            const module = this.modules[key];
            if (module) {
                if (typeof module.getStatus === 'function') {
                    status.modules[key] = module.getStatus();
                } else if (typeof module.getConnectionStatus === 'function') {
                    status.modules[key] = module.getConnectionStatus();
                } else {
                    status.modules[key] = 'active';
                }
            } else {
                status.modules[key] = 'disabled';
            }
        });
        
        return status;
    }
    
    /**
     * 清理资源
     */
    cleanup() {
        // 清理各个模块
        Object.values(this.modules).forEach(module => {
            if (module && typeof module.destroy === 'function') {
                try {
                    module.destroy();
                } catch (error) {
                    console.error('Error destroying module:', error);
                }
            }
        });
        
        this.modules = {};
        this.initialized = false;
    }
}

// 创建全局实例
window.uxPerformanceIntegration = new UXPerformanceIntegration();

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UXPerformanceIntegration;
}