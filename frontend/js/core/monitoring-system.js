/**
 * 监控和告警系统
 * 负责监控系统运行状态，及时发现和处理问题
 */
class MonitoringSystem {
    constructor() {
        this.metrics = new Map();
        this.alerts = new Map();
        this.alertHandlers = new Set();
        this.performanceObserver = null;
        this.errorThresholds = {
            errorRate: 0.1,        // 10% 错误率
            responseTime: 5000,    // 5秒响应时间
            memoryUsage: 0.8,      // 80% 内存使用率
            cpuUsage: 0.9          // 90% CPU使用率
        };
        
        this.monitoringInterval = 30000; // 30秒
        this.monitoringTimer = null;
        this.isMonitoring = false;
        
        this.performanceMetrics = {
            pageLoadTime: 0,
            apiResponseTimes: [],
            errorCount: 0,
            totalRequests: 0,
            memoryUsage: 0,
            domNodes: 0,
            eventListeners: 0
        };
        
        this.healthChecks = new Map();
        this.lastHealthCheck = null;
        
        // 初始化监控系统
        this._initialize();
    }
    
    /**
     * 初始化监控系统
     * @private
     */
    _initialize() {
        try {
            // 设置性能观察器
            this._setupPerformanceObserver();
            
            // 设置错误监控
            this._setupErrorMonitoring();
            
            // 设置资源监控
            this._setupResourceMonitoring();
            
            // 设置健康检查
            this._setupHealthChecks();
            
            // 开始监控
            this.startMonitoring();
            
            console.log('监控系统初始化完成');
            
        } catch (error) {
            console.error('监控系统初始化失败:', error);
        }
    }
    
    /**
     * 设置性能观察器
     * @private
     */
    _setupPerformanceObserver() {
        if ('PerformanceObserver' in window) {
            try {
                // 监控导航性能
                this.performanceObserver = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    entries.forEach(entry => {
                        this._processPerformanceEntry(entry);
                    });
                });
                
                this.performanceObserver.observe({
                    entryTypes: ['navigation', 'resource', 'measure', 'mark']
                });
                
            } catch (error) {
                console.warn('性能观察器设置失败:', error);
            }
        }
        
        // 记录页面加载时间
        window.addEventListener('load', () => {
            const loadTime = performance.now();
            this.performanceMetrics.pageLoadTime = loadTime;
            this._recordMetric('page_load_time', loadTime);
        });
    }
    
    /**
     * 处理性能条目
     * @private
     */
    _processPerformanceEntry(entry) {
        switch (entry.entryType) {
            case 'navigation':
                this._processNavigationEntry(entry);
                break;
            case 'resource':
                this._processResourceEntry(entry);
                break;
            case 'measure':
                this._processMeasureEntry(entry);
                break;
        }
    }
    
    /**
     * 处理导航性能条目
     * @private
     */
    _processNavigationEntry(entry) {
        const metrics = {
            dns_lookup: entry.domainLookupEnd - entry.domainLookupStart,
            tcp_connect: entry.connectEnd - entry.connectStart,
            request_response: entry.responseEnd - entry.requestStart,
            dom_processing: entry.domContentLoadedEventStart - entry.responseEnd,
            load_complete: entry.loadEventEnd - entry.loadEventStart
        };
        
        Object.keys(metrics).forEach(key => {
            this._recordMetric(`navigation_${key}`, metrics[key]);
        });
        
        // 检查性能阈值
        if (entry.loadEventEnd - entry.navigationStart > this.errorThresholds.responseTime) {
            this._triggerAlert('performance', {
                type: 'slow_page_load',
                value: entry.loadEventEnd - entry.navigationStart,
                threshold: this.errorThresholds.responseTime
            });
        }
    }
    
    /**
     * 处理资源性能条目
     * @private
     */
    _processResourceEntry(entry) {
        const responseTime = entry.responseEnd - entry.requestStart;
        
        // 记录API响应时间
        if (entry.name.includes('/api/')) {
            this.performanceMetrics.apiResponseTimes.push({
                url: entry.name,
                responseTime,
                timestamp: Date.now()
            });
            
            // 限制数组大小
            if (this.performanceMetrics.apiResponseTimes.length > 100) {
                this.performanceMetrics.apiResponseTimes.shift();
            }
            
            this._recordMetric('api_response_time', responseTime);
            
            // 检查API响应时间
            if (responseTime > this.errorThresholds.responseTime) {
                this._triggerAlert('performance', {
                    type: 'slow_api_response',
                    url: entry.name,
                    value: responseTime,
                    threshold: this.errorThresholds.responseTime
                });
            }
        }
    }
    
    /**
     * 处理测量性能条目
     * @private
     */
    _processMeasureEntry(entry) {
        this._recordMetric(`measure_${entry.name}`, entry.duration);
    }
    
    /**
     * 设置错误监控
     * @private
     */
    _setupErrorMonitoring() {
        // 监控JavaScript错误
        window.addEventListener('error', (event) => {
            this.performanceMetrics.errorCount++;
            this._recordMetric('js_error', 1);
            
            this._checkErrorRate();
        });
        
        // 监控Promise拒绝
        window.addEventListener('unhandledrejection', (event) => {
            this.performanceMetrics.errorCount++;
            this._recordMetric('promise_rejection', 1);
            
            this._checkErrorRate();
        });
        
        // 如果有全局错误处理器，注册监控处理器
        if (window.errorHandler) {
            window.errorHandler.onNotification((notification) => {
                if (notification.type === 'error') {
                    this._recordMetric('handled_error', 1);
                    
                    if (notification.severity === 'high') {
                        this._triggerAlert('error', {
                            type: 'high_severity_error',
                            message: notification.message,
                            errorId: notification.errorId
                        });
                    }
                }
            });
        }
    }
    
    /**
     * 检查错误率
     * @private
     */
    _checkErrorRate() {
        this.performanceMetrics.totalRequests++;
        
        const errorRate = this.performanceMetrics.errorCount / this.performanceMetrics.totalRequests;
        
        if (errorRate > this.errorThresholds.errorRate) {
            this._triggerAlert('error', {
                type: 'high_error_rate',
                value: errorRate,
                threshold: this.errorThresholds.errorRate,
                errorCount: this.performanceMetrics.errorCount,
                totalRequests: this.performanceMetrics.totalRequests
            });
        }
    }
    
    /**
     * 设置资源监控
     * @private
     */
    _setupResourceMonitoring() {
        // 监控内存使用
        if ('memory' in performance) {
            setInterval(() => {
                const memoryInfo = performance.memory;
                const memoryUsage = memoryInfo.usedJSHeapSize / memoryInfo.jsHeapSizeLimit;
                
                this.performanceMetrics.memoryUsage = memoryUsage;
                this._recordMetric('memory_usage', memoryUsage);
                
                if (memoryUsage > this.errorThresholds.memoryUsage) {
                    this._triggerAlert('resource', {
                        type: 'high_memory_usage',
                        value: memoryUsage,
                        threshold: this.errorThresholds.memoryUsage,
                        usedMemory: memoryInfo.usedJSHeapSize,
                        totalMemory: memoryInfo.jsHeapSizeLimit
                    });
                }
            }, 60000); // 每分钟检查一次
        }
        
        // 监控DOM节点数量
        setInterval(() => {
            const domNodes = document.querySelectorAll('*').length;
            this.performanceMetrics.domNodes = domNodes;
            this._recordMetric('dom_nodes', domNodes);
            
            // 如果DOM节点过多，可能存在内存泄漏
            if (domNodes > 10000) {
                this._triggerAlert('resource', {
                    type: 'excessive_dom_nodes',
                    value: domNodes,
                    threshold: 10000
                });
            }
        }, 120000); // 每2分钟检查一次
    }
    
    /**
     * 设置健康检查
     * @private
     */
    _setupHealthChecks() {
        // API健康检查
        this.healthChecks.set('api', async () => {
            try {
                if (window.apiClient) {
                    const startTime = performance.now();
                    await window.apiClient.healthCheck();
                    const responseTime = performance.now() - startTime;
                    
                    return {
                        healthy: true,
                        responseTime,
                        message: 'API连接正常'
                    };
                } else {
                    return {
                        healthy: false,
                        message: 'API客户端未初始化'
                    };
                }
            } catch (error) {
                return {
                    healthy: false,
                    message: `API健康检查失败: ${error.message}`
                };
            }
        });
        
        // WebSocket健康检查
        this.healthChecks.set('websocket', async () => {
            try {
                if (window.wsManager && window.wsManager.ws) {
                    const readyState = window.wsManager.ws.readyState;
                    
                    return {
                        healthy: readyState === WebSocket.OPEN,
                        readyState,
                        message: readyState === WebSocket.OPEN ? 'WebSocket连接正常' : 'WebSocket连接异常'
                    };
                } else {
                    return {
                        healthy: false,
                        message: 'WebSocket管理器未初始化'
                    };
                }
            } catch (error) {
                return {
                    healthy: false,
                    message: `WebSocket健康检查失败: ${error.message}`
                };
            }
        });
        
        // 本地存储健康检查
        this.healthChecks.set('storage', async () => {
            try {
                const testKey = 'health_check_test';
                const testValue = Date.now().toString();
                
                localStorage.setItem(testKey, testValue);
                const retrieved = localStorage.getItem(testKey);
                localStorage.removeItem(testKey);
                
                return {
                    healthy: retrieved === testValue,
                    message: retrieved === testValue ? '本地存储正常' : '本地存储异常'
                };
            } catch (error) {
                return {
                    healthy: false,
                    message: `本地存储健康检查失败: ${error.message}`
                };
            }
        });
        
        // 功能模块健康检查
        this.healthChecks.set('features', async () => {
            const issues = [];
            
            // 检查关键类是否加载
            const requiredClasses = [
                'LLMConfigManager',
                'AgentManager',
                'MetaAgentChatManager',
                'ErrorHandler',
                'FeatureFlagManager'
            ];
            
            requiredClasses.forEach(className => {
                if (typeof window[className] === 'undefined') {
                    issues.push(`${className} 类未加载`);
                }
            });
            
            return {
                healthy: issues.length === 0,
                issues,
                message: issues.length === 0 ? '功能模块正常' : `发现 ${issues.length} 个问题`
            };
        });
    }
    
    /**
     * 记录指标
     * @private
     */
    _recordMetric(name, value) {
        const timestamp = Date.now();
        
        if (!this.metrics.has(name)) {
            this.metrics.set(name, []);
        }
        
        const metricData = this.metrics.get(name);
        metricData.push({ value, timestamp });
        
        // 限制数据点数量
        if (metricData.length > 1000) {
            metricData.shift();
        }
    }
    
    /**
     * 触发告警
     * @private
     */
    _triggerAlert(category, alertData) {
        const alertId = `${category}_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
        
        const alert = {
            id: alertId,
            category,
            timestamp: new Date().toISOString(),
            ...alertData,
            acknowledged: false,
            resolved: false
        };
        
        this.alerts.set(alertId, alert);
        
        // 通知告警处理器
        this.alertHandlers.forEach(handler => {
            try {
                handler(alert);
            } catch (error) {
                console.error('告警处理器执行失败:', error);
            }
        });
        
        console.warn(`[监控告警] ${category}:`, alertData);
    }
    
    /**
     * 开始监控
     */
    startMonitoring() {
        if (this.isMonitoring) {
            return;
        }
        
        this.isMonitoring = true;
        
        this.monitoringTimer = setInterval(async () => {
            await this._performHealthChecks();
            this._cleanupOldData();
        }, this.monitoringInterval);
        
        console.log('监控系统已启动');
    }
    
    /**
     * 停止监控
     */
    stopMonitoring() {
        if (!this.isMonitoring) {
            return;
        }
        
        this.isMonitoring = false;
        
        if (this.monitoringTimer) {
            clearInterval(this.monitoringTimer);
            this.monitoringTimer = null;
        }
        
        if (this.performanceObserver) {
            this.performanceObserver.disconnect();
        }
        
        console.log('监控系统已停止');
    }
    
    /**
     * 执行健康检查
     * @private
     */
    async _performHealthChecks() {
        const healthResults = {};
        
        for (const [name, checkFn] of this.healthChecks) {
            try {
                healthResults[name] = await checkFn();
            } catch (error) {
                healthResults[name] = {
                    healthy: false,
                    message: `健康检查执行失败: ${error.message}`
                };
            }
        }
        
        this.lastHealthCheck = {
            timestamp: new Date().toISOString(),
            results: healthResults
        };
        
        // 检查是否有健康问题
        Object.keys(healthResults).forEach(name => {
            const result = healthResults[name];
            if (!result.healthy) {
                this._triggerAlert('health', {
                    type: 'health_check_failed',
                    component: name,
                    message: result.message,
                    details: result
                });
            }
        });
    }
    
    /**
     * 清理旧数据
     * @private
     */
    _cleanupOldData() {
        const cutoffTime = Date.now() - 24 * 60 * 60 * 1000; // 24小时前
        
        // 清理旧的指标数据
        this.metrics.forEach((data, name) => {
            const filteredData = data.filter(point => point.timestamp > cutoffTime);
            this.metrics.set(name, filteredData);
        });
        
        // 清理旧的告警
        this.alerts.forEach((alert, id) => {
            if (new Date(alert.timestamp).getTime() < cutoffTime && alert.resolved) {
                this.alerts.delete(id);
            }
        });
        
        // 清理旧的API响应时间数据
        this.performanceMetrics.apiResponseTimes = this.performanceMetrics.apiResponseTimes
            .filter(entry => entry.timestamp > cutoffTime);
    }
    
    /**
     * 获取指标数据
     * @param {string} name 指标名称
     * @param {number} timeRange 时间范围（毫秒）
     * @returns {Array} 指标数据
     */
    getMetrics(name, timeRange = 3600000) { // 默认1小时
        const data = this.metrics.get(name) || [];
        const cutoffTime = Date.now() - timeRange;
        
        return data.filter(point => point.timestamp > cutoffTime);
    }
    
    /**
     * 获取所有指标名称
     * @returns {Array} 指标名称列表
     */
    getMetricNames() {
        return Array.from(this.metrics.keys());
    }
    
    /**
     * 获取性能摘要
     * @returns {Object} 性能摘要
     */
    getPerformanceSummary() {
        const apiResponseTimes = this.performanceMetrics.apiResponseTimes;
        const avgResponseTime = apiResponseTimes.length > 0 ?
            apiResponseTimes.reduce((sum, entry) => sum + entry.responseTime, 0) / apiResponseTimes.length : 0;
        
        return {
            pageLoadTime: this.performanceMetrics.pageLoadTime,
            averageApiResponseTime: avgResponseTime,
            errorCount: this.performanceMetrics.errorCount,
            totalRequests: this.performanceMetrics.totalRequests,
            errorRate: this.performanceMetrics.totalRequests > 0 ?
                this.performanceMetrics.errorCount / this.performanceMetrics.totalRequests : 0,
            memoryUsage: this.performanceMetrics.memoryUsage,
            domNodes: this.performanceMetrics.domNodes,
            lastHealthCheck: this.lastHealthCheck
        };
    }
    
    /**
     * 获取活动告警
     * @returns {Array} 活动告警列表
     */
    getActiveAlerts() {
        return Array.from(this.alerts.values())
            .filter(alert => !alert.resolved)
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    }
    
    /**
     * 确认告警
     * @param {string} alertId 告警ID
     */
    acknowledgeAlert(alertId) {
        const alert = this.alerts.get(alertId);
        if (alert) {
            alert.acknowledged = true;
            alert.acknowledgedAt = new Date().toISOString();
        }
    }
    
    /**
     * 解决告警
     * @param {string} alertId 告警ID
     * @param {string} resolution 解决方案描述
     */
    resolveAlert(alertId, resolution = '') {
        const alert = this.alerts.get(alertId);
        if (alert) {
            alert.resolved = true;
            alert.resolvedAt = new Date().toISOString();
            alert.resolution = resolution;
        }
    }
    
    /**
     * 注册告警处理器
     * @param {Function} handler 告警处理器
     */
    onAlert(handler) {
        if (typeof handler === 'function') {
            this.alertHandlers.add(handler);
        }
    }
    
    /**
     * 移除告警处理器
     * @param {Function} handler 告警处理器
     */
    offAlert(handler) {
        this.alertHandlers.delete(handler);
    }
    
    /**
     * 设置告警阈值
     * @param {Object} thresholds 阈值配置
     */
    setThresholds(thresholds) {
        this.errorThresholds = { ...this.errorThresholds, ...thresholds };
    }
    
    /**
     * 获取监控状态
     * @returns {Object} 监控状态
     */
    getStatus() {
        return {
            isMonitoring: this.isMonitoring,
            monitoringInterval: this.monitoringInterval,
            metricsCount: this.metrics.size,
            activeAlertsCount: this.getActiveAlerts().length,
            totalAlertsCount: this.alerts.size,
            lastHealthCheck: this.lastHealthCheck,
            thresholds: this.errorThresholds
        };
    }
    
    /**
     * 导出监控数据
     * @returns {Object} 监控数据
     */
    exportData() {
        return {
            metrics: Object.fromEntries(this.metrics),
            alerts: Object.fromEntries(this.alerts),
            performanceMetrics: this.performanceMetrics,
            lastHealthCheck: this.lastHealthCheck,
            exportedAt: new Date().toISOString()
        };
    }
    
    /**
     * 销毁监控系统
     */
    destroy() {
        this.stopMonitoring();
        this.alertHandlers.clear();
        this.metrics.clear();
        this.alerts.clear();
        this.healthChecks.clear();
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MonitoringSystem;
} else {
    window.MonitoringSystem = MonitoringSystem;
}