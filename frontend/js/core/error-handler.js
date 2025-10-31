/**
 * 统一错误处理系统
 * 提供全局错误处理、错误分类、错误报告等功能
 */
class ErrorHandler {
    constructor() {
        this.errorHandlers = new Map();
        this.errorLog = [];
        this.maxLogSize = 1000;
        this.errorTypes = {
            'network': {
                name: '网络错误',
                severity: 'high',
                retryable: true
            },
            'api': {
                name: 'API错误',
                severity: 'high',
                retryable: true
            },
            'validation': {
                name: '验证错误',
                severity: 'medium',
                retryable: false
            },
            'ui': {
                name: '界面错误',
                severity: 'low',
                retryable: false
            },
            'storage': {
                name: '存储错误',
                severity: 'medium',
                retryable: true
            },
            'websocket': {
                name: 'WebSocket错误',
                severity: 'medium',
                retryable: true
            },
            'unknown': {
                name: '未知错误',
                severity: 'high',
                retryable: false
            }
        };
        
        this.notificationHandlers = new Set();
        this.reportingEnabled = true;
        
        // 初始化全局错误处理
        this._setupGlobalErrorHandling();
    }
    
    /**
     * 设置全局错误处理
     * @private
     */
    _setupGlobalErrorHandling() {
        // 捕获未处理的JavaScript错误
        window.addEventListener('error', (event) => {
            this.handleError({
                type: 'ui',
                message: event.message,
                source: event.filename,
                line: event.lineno,
                column: event.colno,
                error: event.error,
                context: 'global_error'
            });
        });
        
        // 捕获未处理的Promise拒绝
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError({
                type: 'unknown',
                message: event.reason?.message || 'Unhandled Promise Rejection',
                error: event.reason,
                context: 'unhandled_promise'
            });
        });
    }
    
    /**
     * 处理错误
     * @param {Object} errorInfo 错误信息
     * @returns {Object} 处理结果
     */
    handleError(errorInfo) {
        try {
            // 标准化错误信息
            const standardizedError = this._standardizeError(errorInfo);
            
            // 记录错误
            this._logError(standardizedError);
            
            // 分类处理错误
            const errorType = this.errorTypes[standardizedError.type] || this.errorTypes.unknown;
            
            // 执行特定类型的错误处理器
            if (this.errorHandlers.has(standardizedError.type)) {
                const handler = this.errorHandlers.get(standardizedError.type);
                try {
                    handler(standardizedError);
                } catch (handlerError) {
                    console.error('错误处理器执行失败:', handlerError);
                }
            }
            
            // 通知用户（根据严重程度）
            if (errorType.severity === 'high') {
                this._notifyUser(standardizedError);
            }
            
            // 报告错误（如果启用）
            if (this.reportingEnabled) {
                this._reportError(standardizedError);
            }
            
            return {
                success: true,
                errorId: standardizedError.id,
                handled: true
            };
            
        } catch (error) {
            console.error('错误处理失败:', error);
            return {
                success: false,
                handled: false
            };
        }
    }
    
    /**
     * 标准化错误信息
     * @private
     */
    _standardizeError(errorInfo) {
        const timestamp = new Date().toISOString();
        const id = this._generateErrorId();
        
        return {
            id,
            timestamp,
            type: errorInfo.type || 'unknown',
            message: errorInfo.message || 'Unknown error',
            source: errorInfo.source || 'unknown',
            line: errorInfo.line || null,
            column: errorInfo.column || null,
            stack: errorInfo.error?.stack || null,
            context: errorInfo.context || 'unknown',
            userAgent: navigator.userAgent,
            url: window.location.href,
            userId: this._getCurrentUserId(),
            sessionId: this._getSessionId(),
            additionalData: errorInfo.additionalData || {}
        };
    }
    
    /**
     * 生成错误ID
     * @private
     */
    _generateErrorId() {
        return 'error_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
    }
    
    /**
     * 获取当前用户ID
     * @private
     */
    _getCurrentUserId() {
        // 这里应该从用户会话中获取用户ID
        return localStorage.getItem('user_id') || 'anonymous';
    }
    
    /**
     * 获取会话ID
     * @private
     */
    _getSessionId() {
        let sessionId = sessionStorage.getItem('session_id');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
            sessionStorage.setItem('session_id', sessionId);
        }
        return sessionId;
    }
    
    /**
     * 记录错误到日志
     * @private
     */
    _logError(errorInfo) {
        // 添加到内存日志
        this.errorLog.push(errorInfo);
        
        // 限制日志大小
        if (this.errorLog.length > this.maxLogSize) {
            this.errorLog.shift();
        }
        
        // 保存到本地存储
        try {
            const recentErrors = this.errorLog.slice(-100); // 只保存最近100个错误
            localStorage.setItem('error_log', JSON.stringify(recentErrors));
        } catch (error) {
            console.error('保存错误日志失败:', error);
        }
        
        // 控制台输出
        const errorType = this.errorTypes[errorInfo.type] || this.errorTypes.unknown;
        const logLevel = errorType.severity === 'high' ? 'error' : 
                        errorType.severity === 'medium' ? 'warn' : 'log';
        
        console[logLevel](`[${errorInfo.type.toUpperCase()}] ${errorInfo.message}`, {
            id: errorInfo.id,
            timestamp: errorInfo.timestamp,
            context: errorInfo.context,
            stack: errorInfo.stack
        });
    }
    
    /**
     * 通知用户
     * @private
     */
    _notifyUser(errorInfo) {
        const errorType = this.errorTypes[errorInfo.type] || this.errorTypes.unknown;
        
        // 构建用户友好的错误消息
        let userMessage = this._getUserFriendlyMessage(errorInfo);
        
        // 通知所有注册的通知处理器
        this.notificationHandlers.forEach(handler => {
            try {
                handler({
                    type: 'error',
                    severity: errorType.severity,
                    title: errorType.name,
                    message: userMessage,
                    errorId: errorInfo.id,
                    retryable: errorType.retryable,
                    timestamp: errorInfo.timestamp
                });
            } catch (error) {
                console.error('通知处理器执行失败:', error);
            }
        });
    }
    
    /**
     * 获取用户友好的错误消息
     * @private
     */
    _getUserFriendlyMessage(errorInfo) {
        const messageMap = {
            'network': '网络连接出现问题，请检查网络连接后重试',
            'api': 'API请求失败，请稍后重试',
            'validation': '输入的数据格式不正确，请检查后重新输入',
            'ui': '界面操作出现问题，请刷新页面后重试',
            'storage': '数据存储出现问题，请检查浏览器设置',
            'websocket': '实时连接中断，正在尝试重新连接',
            'unknown': '出现未知错误，请联系技术支持'
        };
        
        return messageMap[errorInfo.type] || messageMap.unknown;
    }
    
    /**
     * 报告错误到服务器
     * @private
     */
    async _reportError(errorInfo) {
        try {
            if (window.apiClient) {
                await window.apiClient.post('/api/v1/errors/report', {
                    errorInfo,
                    clientInfo: {
                        userAgent: navigator.userAgent,
                        url: window.location.href,
                        timestamp: new Date().toISOString()
                    }
                });
            }
        } catch (error) {
            // 静默处理报告错误，避免无限循环
            console.warn('错误报告失败:', error);
        }
    }
    
    /**
     * 注册错误处理器
     * @param {string} errorType 错误类型
     * @param {Function} handler 处理器函数
     */
    registerHandler(errorType, handler) {
        if (typeof handler === 'function') {
            this.errorHandlers.set(errorType, handler);
        }
    }
    
    /**
     * 移除错误处理器
     * @param {string} errorType 错误类型
     */
    unregisterHandler(errorType) {
        this.errorHandlers.delete(errorType);
    }
    
    /**
     * 注册通知处理器
     * @param {Function} handler 通知处理器
     */
    onNotification(handler) {
        if (typeof handler === 'function') {
            this.notificationHandlers.add(handler);
        }
    }
    
    /**
     * 移除通知处理器
     * @param {Function} handler 通知处理器
     */
    offNotification(handler) {
        this.notificationHandlers.delete(handler);
    }
    
    /**
     * 获取错误日志
     * @param {Object} options 查询选项
     * @returns {Array} 错误日志
     */
    getErrorLog(options = {}) {
        let logs = [...this.errorLog];
        
        // 按类型过滤
        if (options.type) {
            logs = logs.filter(log => log.type === options.type);
        }
        
        // 按严重程度过滤
        if (options.severity) {
            logs = logs.filter(log => {
                const errorType = this.errorTypes[log.type] || this.errorTypes.unknown;
                return errorType.severity === options.severity;
            });
        }
        
        // 按时间范围过滤
        if (options.startTime) {
            logs = logs.filter(log => new Date(log.timestamp) >= new Date(options.startTime));
        }
        
        if (options.endTime) {
            logs = logs.filter(log => new Date(log.timestamp) <= new Date(options.endTime));
        }
        
        // 限制数量
        if (options.limit) {
            logs = logs.slice(-options.limit);
        }
        
        return logs;
    }
    
    /**
     * 清除错误日志
     * @param {Object} options 清除选项
     */
    clearErrorLog(options = {}) {
        if (options.type) {
            this.errorLog = this.errorLog.filter(log => log.type !== options.type);
        } else if (options.olderThan) {
            const cutoffTime = new Date(options.olderThan);
            this.errorLog = this.errorLog.filter(log => new Date(log.timestamp) > cutoffTime);
        } else {
            this.errorLog = [];
        }
        
        // 更新本地存储
        try {
            localStorage.setItem('error_log', JSON.stringify(this.errorLog.slice(-100)));
        } catch (error) {
            console.error('更新错误日志失败:', error);
        }
    }
    
    /**
     * 获取错误统计
     * @returns {Object} 错误统计
     */
    getErrorStats() {
        const stats = {
            total: this.errorLog.length,
            byType: {},
            bySeverity: {},
            recent: {
                lastHour: 0,
                lastDay: 0,
                lastWeek: 0
            }
        };
        
        const now = new Date();
        const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
        const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        
        // 初始化统计对象
        Object.keys(this.errorTypes).forEach(type => {
            stats.byType[type] = 0;
        });
        
        ['high', 'medium', 'low'].forEach(severity => {
            stats.bySeverity[severity] = 0;
        });
        
        // 统计错误
        this.errorLog.forEach(log => {
            const logTime = new Date(log.timestamp);
            const errorType = this.errorTypes[log.type] || this.errorTypes.unknown;
            
            // 按类型统计
            stats.byType[log.type] = (stats.byType[log.type] || 0) + 1;
            
            // 按严重程度统计
            stats.bySeverity[errorType.severity]++;
            
            // 按时间统计
            if (logTime > oneHourAgo) stats.recent.lastHour++;
            if (logTime > oneDayAgo) stats.recent.lastDay++;
            if (logTime > oneWeekAgo) stats.recent.lastWeek++;
        });
        
        return stats;
    }
    
    /**
     * 启用/禁用错误报告
     * @param {boolean} enabled 是否启用
     */
    setReportingEnabled(enabled) {
        this.reportingEnabled = Boolean(enabled);
    }
    
    /**
     * 手动报告错误
     * @param {string} type 错误类型
     * @param {string} message 错误消息
     * @param {Object} additionalData 附加数据
     */
    reportError(type, message, additionalData = {}) {
        this.handleError({
            type,
            message,
            context: 'manual_report',
            additionalData
        });
    }
    
    /**
     * 创建错误包装器
     * @param {string} context 上下文
     * @returns {Function} 包装器函数
     */
    createWrapper(context) {
        return (fn) => {
            return async (...args) => {
                try {
                    return await fn(...args);
                } catch (error) {
                    this.handleError({
                        type: 'unknown',
                        message: error.message,
                        error,
                        context,
                        additionalData: { args }
                    });
                    throw error;
                }
            };
        };
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ErrorHandler;
} else {
    window.ErrorHandler = ErrorHandler;
}