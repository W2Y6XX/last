/**
 * 交互监控系统 - 监控修复状态和验证机制
 * 负责记录修复历史、性能监控、状态跟踪等功能
 */

class InteractionMonitoring {
    constructor() {
        this.fixRecords = [];
        this.performanceMetrics = [];
        this.statusChecks = [];
        this.alerts = [];
        this.monitoringInterval = null;
        this.isMonitoring = false;
        
        this.thresholds = {
            fixSuccessRate: 0.8, // 修复成功率阈值
            responseTime: 5000,   // 响应时间阈值(ms)
            errorRate: 0.1,       // 错误率阈值
            criticalIssues: 3     // 关键问题数量阈值
        };
        
        this.init();
    }
    
    init() {
        // 初始化监控系统
        this.startMonitoring();
        this.setupPerformanceObserver();
        this.setupErrorTracking();
        
        console.log('交互监控系统已初始化');
    }
    
    /**
     * 记录修复操作
     * @param {Object} fixRecord - 修复记录
     */
    recordFix(fixRecord) {
        const record = {
            ...fixRecord,
            id: this.generateRecordId(),
            recordedAt: new Date().toISOString()
        };
        
        this.fixRecords.push(record);
        
        // 限制记录数量
        if (this.fixRecords.length > 1000) {
            this.fixRecords.shift();
        }
        
        // 分析修复记录
        this.analyzeFix(record);
        
        // 触发监控事件
        this.triggerMonitoringEvent('fix_recorded', record);
        
        console.log('修复记录已保存:', record.id);
    }
    
    /**
     * 开始监控
     */
    startMonitoring() {
        if (this.isMonitoring) {
            return;
        }
        
        this.isMonitoring = true;
        
        // 定期执行状态检查
        this.monitoringInterval = setInterval(() => {
            this.performStatusCheck();
        }, 30000); // 每30秒检查一次
        
        console.log('交互监控已启动');
    }
    
    /**
     * 停止监控
     */
    stopMonitoring() {
        if (!this.isMonitoring) {
            return;
        }
        
        this.isMonitoring = false;
        
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
        }
        
        console.log('交互监控已停止');
    }
    
    /**
     * 执行状态检查
     */
    async performStatusCheck() {
        const checkId = this.generateRecordId();
        const startTime = Date.now();
        
        try {
            const status = await this.checkSystemStatus();
            const endTime = Date.now();
            
            const statusCheck = {
                id: checkId,
                timestamp: new Date().toISOString(),
                duration: endTime - startTime,
                status: status,
                healthy: this.evaluateSystemHealth(status)
            };
            
            this.statusChecks.push(statusCheck);
            
            // 限制状态检查记录数量
            if (this.statusChecks.length > 100) {
                this.statusChecks.shift();
            }
            
            // 检查是否需要发出警报
            this.checkAlerts(statusCheck);
            
        } catch (error) {
            console.error('状态检查失败:', error);
            this.recordAlert('status_check_failed', 'high', error.message);
        }
    }
    
    /**
     * 检查系统状态
     * @returns {Promise<Object>} 系统状态
     */
    async checkSystemStatus() {
        const status = {
            timestamp: new Date().toISOString(),
            components: {},
            metrics: {},
            issues: []
        };
        
        // 检查关键组件状态
        status.components.dom = this.checkDOMStatus();
        status.components.api = await this.checkAPIStatus();
        status.components.websocket = this.checkWebSocketStatus();
        status.components.storage = this.checkStorageStatus();
        status.components.events = this.checkEventStatus();
        
        // 收集性能指标
        status.metrics = this.collectPerformanceMetrics();
        
        // 检查当前问题
        status.issues = await this.detectCurrentIssues();
        
        return status;
    }
    
    /**
     * 检查DOM状态
     * @returns {Object} DOM状态
     */
    checkDOMStatus() {
        const criticalElements = [
            '#main-content',
            '#agent-management',
            '#llm-config',
            '#task-dependencies',
            '#meta-agent-chat'
        ];
        
        const status = {
            healthy: true,
            missingElements: [],
            hiddenElements: [],
            totalElements: criticalElements.length
        };
        
        for (const selector of criticalElements) {
            const element = document.querySelector(selector);
            if (!element) {
                status.missingElements.push(selector);
                status.healthy = false;
            } else if (!this.isElementVisible(element)) {
                status.hiddenElements.push(selector);
            }
        }
        
        return status;
    }
    
    /**
     * 检查API状态
     * @returns {Promise<Object>} API状态
     */
    async checkAPIStatus() {
        const endpoints = [
            '/api/v1/health',
            '/api/v1/agents',
            '/api/v1/llm-configs'
        ];
        
        const status = {
            healthy: true,
            availableEndpoints: [],
            unavailableEndpoints: [],
            totalEndpoints: endpoints.length,
            averageResponseTime: 0
        };
        
        const responseTimes = [];
        
        for (const endpoint of endpoints) {
            const startTime = Date.now();
            try {
                const response = await fetch(endpoint, { 
                    method: 'GET',
                    timeout: 3000 
                });
                
                const responseTime = Date.now() - startTime;
                responseTimes.push(responseTime);
                
                if (response.ok) {
                    status.availableEndpoints.push({
                        endpoint,
                        responseTime,
                        status: response.status
                    });
                } else {
                    status.unavailableEndpoints.push({
                        endpoint,
                        responseTime,
                        status: response.status,
                        error: response.statusText
                    });
                    status.healthy = false;
                }
                
            } catch (error) {
                const responseTime = Date.now() - startTime;
                status.unavailableEndpoints.push({
                    endpoint,
                    responseTime,
                    error: error.message
                });
                status.healthy = false;
            }
        }
        
        status.averageResponseTime = responseTimes.length > 0 
            ? responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length 
            : 0;
        
        return status;
    }
    
    /**
     * 检查WebSocket状态
     * @returns {Object} WebSocket状态
     */
    checkWebSocketStatus() {
        const status = {
            healthy: false,
            connected: false,
            manager: null,
            lastActivity: null
        };
        
        if (window.websocketManager) {
            status.manager = true;
            status.connected = window.websocketManager.isConnected();
            status.healthy = status.connected;
            status.lastActivity = window.websocketManager.getLastActivity();
        }
        
        return status;
    }
    
    /**
     * 检查存储状态
     * @returns {Object} 存储状态
     */
    checkStorageStatus() {
        const status = {
            healthy: true,
            localStorage: false,
            sessionStorage: false,
            fallbackStorage: false,
            criticalDataPresent: false
        };
        
        // 检查localStorage
        try {
            const testKey = 'monitoring_test_' + Date.now();
            localStorage.setItem(testKey, 'test');
            localStorage.removeItem(testKey);
            status.localStorage = true;
        } catch (error) {
            status.localStorage = false;
            status.healthy = false;
        }
        
        // 检查sessionStorage
        try {
            const testKey = 'monitoring_test_' + Date.now();
            sessionStorage.setItem(testKey, 'test');
            sessionStorage.removeItem(testKey);
            status.sessionStorage = true;
        } catch (error) {
            status.sessionStorage = false;
        }
        
        // 检查备用存储
        status.fallbackStorage = window.fallbackStorage !== undefined;
        
        // 检查关键数据
        const criticalKeys = ['llm_configs', 'agent_settings'];
        status.criticalDataPresent = criticalKeys.some(key => 
            localStorage.getItem(key) || 
            (window.fallbackStorage && window.fallbackStorage.getItem(key))
        );
        
        return status;
    }
    
    /**
     * 检查事件状态
     * @returns {Object} 事件状态
     */
    checkEventStatus() {
        const status = {
            healthy: true,
            boundButtons: 0,
            unboundButtons: 0,
            boundForms: 0,
            unboundForms: 0
        };
        
        // 检查按钮事件绑定
        const buttons = document.querySelectorAll('button');
        buttons.forEach(button => {
            if (this.hasEventListener(button, 'click')) {
                status.boundButtons++;
            } else {
                status.unboundButtons++;
            }
        });
        
        // 检查表单事件绑定
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            if (this.hasEventListener(form, 'submit')) {
                status.boundForms++;
            } else {
                status.unboundForms++;
            }
        });
        
        status.healthy = status.unboundButtons === 0 && status.unboundForms === 0;
        
        return status;
    }
    
    /**
     * 收集性能指标
     * @returns {Object} 性能指标
     */
    collectPerformanceMetrics() {
        const metrics = {
            timestamp: new Date().toISOString(),
            memory: {},
            timing: {},
            navigation: {}
        };
        
        // 内存使用情况
        if (performance.memory) {
            metrics.memory = {
                usedJSHeapSize: performance.memory.usedJSHeapSize,
                totalJSHeapSize: performance.memory.totalJSHeapSize,
                jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
            };
        }
        
        // 页面加载时间
        if (performance.timing) {
            const timing = performance.timing;
            metrics.timing = {
                domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                loadComplete: timing.loadEventEnd - timing.navigationStart,
                domInteractive: timing.domInteractive - timing.navigationStart
            };
        }
        
        // 导航信息
        if (performance.navigation) {
            metrics.navigation = {
                type: performance.navigation.type,
                redirectCount: performance.navigation.redirectCount
            };
        }
        
        return metrics;
    }
    
    /**
     * 检测当前问题
     * @returns {Promise<Array>} 问题列表
     */
    async detectCurrentIssues() {
        const issues = [];
        
        // 检查控制台错误
        if (window.consoleErrors && window.consoleErrors.length > 0) {
            issues.push({
                type: 'console_errors',
                severity: 'medium',
                count: window.consoleErrors.length,
                message: `检测到 ${window.consoleErrors.length} 个控制台错误`
            });
        }
        
        // 检查网络状态
        if (!navigator.onLine) {
            issues.push({
                type: 'network_offline',
                severity: 'critical',
                message: '网络连接已断开'
            });
        }
        
        // 检查修复成功率
        const recentFixes = this.getRecentFixes(24); // 最近24小时
        if (recentFixes.length > 0) {
            const successRate = recentFixes.filter(fix => fix.success).length / recentFixes.length;
            if (successRate < this.thresholds.fixSuccessRate) {
                issues.push({
                    type: 'low_fix_success_rate',
                    severity: 'high',
                    successRate: successRate,
                    message: `修复成功率过低: ${(successRate * 100).toFixed(1)}%`
                });
            }
        }
        
        return issues;
    }
    
    /**
     * 评估系统健康状况
     * @param {Object} status - 系统状态
     * @returns {Object} 健康评估结果
     */
    evaluateSystemHealth(status) {
        const health = {
            overall: 'healthy',
            score: 100,
            issues: [],
            recommendations: []
        };
        
        // 评估各组件健康状况
        const components = status.components;
        
        if (!components.dom.healthy) {
            health.score -= 20;
            health.issues.push('DOM结构不完整');
            health.recommendations.push('修复缺失的DOM元素');
        }
        
        if (!components.api.healthy) {
            health.score -= 30;
            health.issues.push('API连接异常');
            health.recommendations.push('检查后端服务状态');
        }
        
        if (!components.websocket.healthy) {
            health.score -= 15;
            health.issues.push('WebSocket连接断开');
            health.recommendations.push('重新建立WebSocket连接');
        }
        
        if (!components.storage.healthy) {
            health.score -= 10;
            health.issues.push('存储功能异常');
            health.recommendations.push('启用备用存储方案');
        }
        
        if (!components.events.healthy) {
            health.score -= 15;
            health.issues.push('事件绑定不完整');
            health.recommendations.push('重新绑定事件监听器');
        }
        
        // 评估性能指标
        if (status.metrics.memory && status.metrics.memory.usedJSHeapSize > 50 * 1024 * 1024) {
            health.score -= 5;
            health.issues.push('内存使用过高');
            health.recommendations.push('优化内存使用');
        }
        
        // 确定整体健康状况
        if (health.score >= 90) {
            health.overall = 'healthy';
        } else if (health.score >= 70) {
            health.overall = 'warning';
        } else if (health.score >= 50) {
            health.overall = 'unhealthy';
        } else {
            health.overall = 'critical';
        }
        
        return health;
    }
    
    /**
     * 检查警报条件
     * @param {Object} statusCheck - 状态检查结果
     */
    checkAlerts(statusCheck) {
        const { status, healthy } = statusCheck;
        
        // 系统不健康警报
        if (!healthy.overall === 'critical') {
            this.recordAlert('system_critical', 'critical', '系统处于关键状态');
        } else if (healthy.overall === 'unhealthy') {
            this.recordAlert('system_unhealthy', 'high', '系统健康状况不佳');
        }
        
        // API响应时间警报
        if (status.components.api.averageResponseTime > this.thresholds.responseTime) {
            this.recordAlert('slow_api_response', 'medium', 
                `API响应时间过长: ${status.components.api.averageResponseTime}ms`);
        }
        
        // 关键问题数量警报
        const criticalIssues = status.issues.filter(issue => issue.severity === 'critical').length;
        if (criticalIssues >= this.thresholds.criticalIssues) {
            this.recordAlert('too_many_critical_issues', 'high', 
                `关键问题过多: ${criticalIssues} 个`);
        }
    }
    
    /**
     * 记录警报
     * @param {string} type - 警报类型
     * @param {string} severity - 严重程度
     * @param {string} message - 警报消息
     */
    recordAlert(type, severity, message) {
        const alert = {
            id: this.generateRecordId(),
            type: type,
            severity: severity,
            message: message,
            timestamp: new Date().toISOString(),
            acknowledged: false
        };
        
        this.alerts.push(alert);
        
        // 限制警报数量
        if (this.alerts.length > 100) {
            this.alerts.shift();
        }
        
        // 触发警报事件
        this.triggerMonitoringEvent('alert_created', alert);
        
        console.warn('监控警报:', alert);
    }
    
    /**
     * 分析修复记录
     * @param {Object} record - 修复记录
     */
    analyzeFix(record) {
        // 记录性能指标
        if (record.duration) {
            this.performanceMetrics.push({
                type: 'fix_duration',
                component: record.component,
                duration: record.duration,
                success: record.success,
                timestamp: record.timestamp
            });
        }
        
        // 分析修复模式
        this.analyzeFixPatterns(record);
        
        // 更新统计信息
        this.updateFixStatistics(record);
    }
    
    /**
     * 分析修复模式
     * @param {Object} record - 修复记录
     */
    analyzeFixPatterns(record) {
        // 检查重复修复
        const recentSimilarFixes = this.fixRecords
            .filter(fix => 
                fix.component === record.component && 
                Date.now() - new Date(fix.timestamp).getTime() < 3600000 // 1小时内
            )
            .slice(-5); // 最近5次
        
        if (recentSimilarFixes.length >= 3) {
            this.recordAlert('repeated_fixes', 'medium', 
                `组件 ${record.component} 频繁需要修复`);
        }
    }
    
    /**
     * 更新修复统计信息
     * @param {Object} record - 修复记录
     */
    updateFixStatistics(record) {
        // 这里可以更新各种统计信息
        // 例如：成功率、平均修复时间、最常见问题等
    }
    
    /**
     * 设置性能观察器
     */
    setupPerformanceObserver() {
        if ('PerformanceObserver' in window) {
            try {
                const observer = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    entries.forEach(entry => {
                        this.recordPerformanceEntry(entry);
                    });
                });
                
                observer.observe({ entryTypes: ['measure', 'navigation', 'resource'] });
                
            } catch (error) {
                console.warn('无法设置性能观察器:', error);
            }
        }
    }
    
    /**
     * 设置错误跟踪
     */
    setupErrorTracking() {
        // 全局错误处理
        window.addEventListener('error', (event) => {
            this.recordError('javascript_error', event.error, {
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno
            });
        });
        
        // 未捕获的Promise拒绝
        window.addEventListener('unhandledrejection', (event) => {
            this.recordError('unhandled_promise_rejection', event.reason);
        });
        
        // 初始化控制台错误收集
        if (!window.consoleErrors) {
            window.consoleErrors = [];
        }
    }
    
    /**
     * 记录性能条目
     * @param {PerformanceEntry} entry - 性能条目
     */
    recordPerformanceEntry(entry) {
        this.performanceMetrics.push({
            type: entry.entryType,
            name: entry.name,
            duration: entry.duration,
            startTime: entry.startTime,
            timestamp: new Date().toISOString()
        });
        
        // 限制性能指标数量
        if (this.performanceMetrics.length > 500) {
            this.performanceMetrics.shift();
        }
    }
    
    /**
     * 记录错误
     * @param {string} type - 错误类型
     * @param {Error} error - 错误对象
     * @param {Object} context - 错误上下文
     */
    recordError(type, error, context = {}) {
        const errorRecord = {
            id: this.generateRecordId(),
            type: type,
            message: error.message || error.toString(),
            stack: error.stack,
            context: context,
            timestamp: new Date().toISOString()
        };
        
        window.consoleErrors.push(errorRecord);
        
        // 限制错误记录数量
        if (window.consoleErrors.length > 100) {
            window.consoleErrors.shift();
        }
        
        // 触发错误事件
        this.triggerMonitoringEvent('error_recorded', errorRecord);
    }
    
    /**
     * 触发监控事件
     * @param {string} eventType - 事件类型
     * @param {Object} data - 事件数据
     */
    triggerMonitoringEvent(eventType, data) {
        const event = new CustomEvent('monitoring:' + eventType, {
            detail: data
        });
        
        window.dispatchEvent(event);
    }
    
    // 辅助方法
    generateRecordId() {
        return 'record_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    isElementVisible(element) {
        const style = window.getComputedStyle(element);
        return style.display !== 'none' && 
               style.visibility !== 'hidden' && 
               style.opacity !== '0' &&
               element.offsetWidth > 0 && 
               element.offsetHeight > 0;
    }
    
    hasEventListener(element, eventType) {
        // 简化的事件监听器检查
        return element.getEventListeners ? 
            (element.getEventListeners()[eventType] || []).length > 0 : 
            false;
    }
    
    getRecentFixes(hours) {
        const cutoffTime = Date.now() - (hours * 60 * 60 * 1000);
        return this.fixRecords.filter(record => 
            new Date(record.timestamp).getTime() > cutoffTime
        );
    }
    
    // 公共API方法
    
    /**
     * 获取修复记录
     * @param {Object} filters - 过滤条件
     * @returns {Array} 修复记录列表
     */
    getFixRecords(filters = {}) {
        let records = [...this.fixRecords];
        
        if (filters.component) {
            records = records.filter(record => record.component === filters.component);
        }
        
        if (filters.success !== undefined) {
            records = records.filter(record => record.success === filters.success);
        }
        
        if (filters.since) {
            const sinceTime = new Date(filters.since).getTime();
            records = records.filter(record => 
                new Date(record.timestamp).getTime() > sinceTime
            );
        }
        
        return records;
    }
    
    /**
     * 获取状态检查记录
     * @param {number} limit - 限制数量
     * @returns {Array} 状态检查记录
     */
    getStatusChecks(limit = 10) {
        return this.statusChecks.slice(-limit);
    }
    
    /**
     * 获取警报
     * @param {boolean} unacknowledgedOnly - 只返回未确认的警报
     * @returns {Array} 警报列表
     */
    getAlerts(unacknowledgedOnly = false) {
        if (unacknowledgedOnly) {
            return this.alerts.filter(alert => !alert.acknowledged);
        }
        return [...this.alerts];
    }
    
    /**
     * 确认警报
     * @param {string} alertId - 警报ID
     */
    acknowledgeAlert(alertId) {
        const alert = this.alerts.find(alert => alert.id === alertId);
        if (alert) {
            alert.acknowledged = true;
            alert.acknowledgedAt = new Date().toISOString();
        }
    }
    
    /**
     * 获取性能指标
     * @param {string} type - 指标类型
     * @param {number} limit - 限制数量
     * @returns {Array} 性能指标列表
     */
    getPerformanceMetrics(type = null, limit = 50) {
        let metrics = [...this.performanceMetrics];
        
        if (type) {
            metrics = metrics.filter(metric => metric.type === type);
        }
        
        return metrics.slice(-limit);
    }
    
    /**
     * 获取监控统计信息
     * @returns {Object} 统计信息
     */
    getStatistics() {
        const totalFixes = this.fixRecords.length;
        const successfulFixes = this.fixRecords.filter(record => record.success).length;
        const recentAlerts = this.alerts.filter(alert => 
            Date.now() - new Date(alert.timestamp).getTime() < 24 * 60 * 60 * 1000
        ).length;
        
        return {
            totalFixes,
            successfulFixes,
            successRate: totalFixes > 0 ? (successfulFixes / totalFixes * 100).toFixed(1) + '%' : '0%',
            totalAlerts: this.alerts.length,
            recentAlerts,
            unacknowledgedAlerts: this.alerts.filter(alert => !alert.acknowledged).length,
            isMonitoring: this.isMonitoring,
            uptime: this.isMonitoring ? Date.now() - this.startTime : 0
        };
    }
    
    /**
     * 清除所有记录
     */
    clearAllRecords() {
        this.fixRecords = [];
        this.performanceMetrics = [];
        this.statusChecks = [];
        this.alerts = [];
        
        if (window.consoleErrors) {
            window.consoleErrors = [];
        }
        
        console.log('所有监控记录已清除');
    }
}

// 导出类
export default InteractionMonitoring;

// 创建全局实例
window.InteractionMonitoring = InteractionMonitoring;