/**
 * 统一日志记录系统
 * 提供分级日志记录、日志过滤、日志存储等功能
 */
class Logger {
    constructor(name = 'App') {
        this.name = name;
        this.logs = [];
        this.maxLogSize = 2000;
        this.logLevel = this._getLogLevel();
        this.logHandlers = new Set();
        this.storageEnabled = true;
        
        // 日志级别定义
        this.levels = {
            'debug': { value: 0, color: '#6b7280', method: 'log' },
            'info': { value: 1, color: '#3b82f6', method: 'info' },
            'warn': { value: 2, color: '#f59e0b', method: 'warn' },
            'error': { value: 3, color: '#ef4444', method: 'error' },
            'fatal': { value: 4, color: '#dc2626', method: 'error' }
        };
        
        // 从本地存储加载日志
        this._loadLogsFromStorage();
    }
    
    /**
     * 获取当前日志级别
     * @private
     */
    _getLogLevel() {
        // 从配置或环境变量获取日志级别
        const stored = localStorage.getItem('log_level');
        if (stored && this.levels[stored]) {
            return stored;
        }
        
        // 开发环境默认debug，生产环境默认info
        return window.CONFIG?.FEATURES?.DEBUG_MODE ? 'debug' : 'info';
    }
    
    /**
     * 从本地存储加载日志
     * @private
     */
    _loadLogsFromStorage() {
        try {
            const stored = localStorage.getItem('app_logs');
            if (stored) {
                const logs = JSON.parse(stored);
                this.logs = logs.slice(-this.maxLogSize); // 只保留最近的日志
            }
        } catch (error) {
            console.error('加载日志失败:', error);
        }
    }
    
    /**
     * 保存日志到本地存储
     * @private
     */
    _saveLogsToStorage() {
        if (!this.storageEnabled) return;
        
        try {
            // 只保存最近的日志到存储
            const recentLogs = this.logs.slice(-500);
            localStorage.setItem('app_logs', JSON.stringify(recentLogs));
        } catch (error) {
            console.error('保存日志失败:', error);
        }
    }
    
    /**
     * 创建日志条目
     * @private
     */
    _createLogEntry(level, message, data = null) {
        return {
            id: this._generateLogId(),
            timestamp: new Date().toISOString(),
            level,
            logger: this.name,
            message,
            data,
            url: window.location.href,
            userAgent: navigator.userAgent.substring(0, 100), // 截断用户代理字符串
            sessionId: this._getSessionId()
        };
    }
    
    /**
     * 生成日志ID
     * @private
     */
    _generateLogId() {
        return 'log_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
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
     * 记录日志
     * @private
     */
    _log(level, message, data = null) {
        const levelInfo = this.levels[level];
        const currentLevelInfo = this.levels[this.logLevel];
        
        // 检查日志级别
        if (levelInfo.value < currentLevelInfo.value) {
            return;
        }
        
        // 创建日志条目
        const logEntry = this._createLogEntry(level, message, data);
        
        // 添加到日志数组
        this.logs.push(logEntry);
        
        // 限制日志大小
        if (this.logs.length > this.maxLogSize) {
            this.logs.shift();
        }
        
        // 输出到控制台
        this._outputToConsole(logEntry);
        
        // 通知日志处理器
        this._notifyHandlers(logEntry);
        
        // 保存到存储
        this._saveLogsToStorage();
        
        return logEntry;
    }
    
    /**
     * 输出到控制台
     * @private
     */
    _outputToConsole(logEntry) {
        const levelInfo = this.levels[logEntry.level];
        const timestamp = new Date(logEntry.timestamp).toLocaleTimeString();
        
        const style = `color: ${levelInfo.color}; font-weight: bold;`;
        const prefix = `%c[${timestamp}] [${logEntry.level.toUpperCase()}] [${logEntry.logger}]`;
        
        if (logEntry.data) {
            console[levelInfo.method](prefix, style, logEntry.message, logEntry.data);
        } else {
            console[levelInfo.method](prefix, style, logEntry.message);
        }
    }
    
    /**
     * 通知日志处理器
     * @private
     */
    _notifyHandlers(logEntry) {
        this.logHandlers.forEach(handler => {
            try {
                handler(logEntry);
            } catch (error) {
                console.error('日志处理器执行失败:', error);
            }
        });
    }
    
    /**
     * Debug级别日志
     * @param {string} message 消息
     * @param {*} data 附加数据
     */
    debug(message, data = null) {
        return this._log('debug', message, data);
    }
    
    /**
     * Info级别日志
     * @param {string} message 消息
     * @param {*} data 附加数据
     */
    info(message, data = null) {
        return this._log('info', message, data);
    }
    
    /**
     * Warn级别日志
     * @param {string} message 消息
     * @param {*} data 附加数据
     */
    warn(message, data = null) {
        return this._log('warn', message, data);
    }
    
    /**
     * Error级别日志
     * @param {string} message 消息
     * @param {*} data 附加数据
     */
    error(message, data = null) {
        return this._log('error', message, data);
    }
    
    /**
     * Fatal级别日志
     * @param {string} message 消息
     * @param {*} data 附加数据
     */
    fatal(message, data = null) {
        return this._log('fatal', message, data);
    }
    
    /**
     * 设置日志级别
     * @param {string} level 日志级别
     */
    setLevel(level) {
        if (this.levels[level]) {
            this.logLevel = level;
            localStorage.setItem('log_level', level);
            this.info(`日志级别已设置为: ${level}`);
        } else {
            this.warn(`无效的日志级别: ${level}`);
        }
    }
    
    /**
     * 获取当前日志级别
     * @returns {string} 当前日志级别
     */
    getLevel() {
        return this.logLevel;
    }
    
    /**
     * 获取日志
     * @param {Object} options 查询选项
     * @returns {Array} 日志列表
     */
    getLogs(options = {}) {
        let logs = [...this.logs];
        
        // 按级别过滤
        if (options.level) {
            logs = logs.filter(log => log.level === options.level);
        }
        
        // 按最小级别过滤
        if (options.minLevel) {
            const minLevelValue = this.levels[options.minLevel]?.value || 0;
            logs = logs.filter(log => {
                const logLevelValue = this.levels[log.level]?.value || 0;
                return logLevelValue >= minLevelValue;
            });
        }
        
        // 按logger名称过滤
        if (options.logger) {
            logs = logs.filter(log => log.logger === options.logger);
        }
        
        // 按时间范围过滤
        if (options.startTime) {
            logs = logs.filter(log => new Date(log.timestamp) >= new Date(options.startTime));
        }
        
        if (options.endTime) {
            logs = logs.filter(log => new Date(log.timestamp) <= new Date(options.endTime));
        }
        
        // 按消息内容搜索
        if (options.search) {
            const searchTerm = options.search.toLowerCase();
            logs = logs.filter(log => 
                log.message.toLowerCase().includes(searchTerm) ||
                (log.data && JSON.stringify(log.data).toLowerCase().includes(searchTerm))
            );
        }
        
        // 限制数量
        if (options.limit) {
            logs = logs.slice(-options.limit);
        }
        
        return logs;
    }
    
    /**
     * 清除日志
     * @param {Object} options 清除选项
     */
    clearLogs(options = {}) {
        if (options.level) {
            this.logs = this.logs.filter(log => log.level !== options.level);
        } else if (options.olderThan) {
            const cutoffTime = new Date(options.olderThan);
            this.logs = this.logs.filter(log => new Date(log.timestamp) > cutoffTime);
        } else if (options.logger) {
            this.logs = this.logs.filter(log => log.logger !== options.logger);
        } else {
            this.logs = [];
        }
        
        this._saveLogsToStorage();
        this.info('日志已清除', options);
    }
    
    /**
     * 获取日志统计
     * @returns {Object} 日志统计
     */
    getStats() {
        const stats = {
            total: this.logs.length,
            byLevel: {},
            byLogger: {},
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
        Object.keys(this.levels).forEach(level => {
            stats.byLevel[level] = 0;
        });
        
        // 统计日志
        this.logs.forEach(log => {
            const logTime = new Date(log.timestamp);
            
            // 按级别统计
            stats.byLevel[log.level] = (stats.byLevel[log.level] || 0) + 1;
            
            // 按logger统计
            stats.byLogger[log.logger] = (stats.byLogger[log.logger] || 0) + 1;
            
            // 按时间统计
            if (logTime > oneHourAgo) stats.recent.lastHour++;
            if (logTime > oneDayAgo) stats.recent.lastDay++;
            if (logTime > oneWeekAgo) stats.recent.lastWeek++;
        });
        
        return stats;
    }
    
    /**
     * 注册日志处理器
     * @param {Function} handler 处理器函数
     */
    addHandler(handler) {
        if (typeof handler === 'function') {
            this.logHandlers.add(handler);
        }
    }
    
    /**
     * 移除日志处理器
     * @param {Function} handler 处理器函数
     */
    removeHandler(handler) {
        this.logHandlers.delete(handler);
    }
    
    /**
     * 启用/禁用存储
     * @param {boolean} enabled 是否启用
     */
    setStorageEnabled(enabled) {
        this.storageEnabled = Boolean(enabled);
        if (enabled) {
            this._saveLogsToStorage();
        }
    }
    
    /**
     * 导出日志
     * @param {Object} options 导出选项
     * @returns {string} 导出的日志内容
     */
    exportLogs(options = {}) {
        const logs = this.getLogs(options);
        const format = options.format || 'json';
        
        if (format === 'json') {
            return JSON.stringify(logs, null, 2);
        } else if (format === 'csv') {
            const headers = ['timestamp', 'level', 'logger', 'message', 'data'];
            const csvContent = [
                headers.join(','),
                ...logs.map(log => [
                    log.timestamp,
                    log.level,
                    log.logger,
                    `"${log.message.replace(/"/g, '""')}"`,
                    log.data ? `"${JSON.stringify(log.data).replace(/"/g, '""')}"` : ''
                ].join(','))
            ].join('\n');
            return csvContent;
        } else if (format === 'text') {
            return logs.map(log => {
                const timestamp = new Date(log.timestamp).toLocaleString();
                const dataStr = log.data ? ` | Data: ${JSON.stringify(log.data)}` : '';
                return `[${timestamp}] [${log.level.toUpperCase()}] [${log.logger}] ${log.message}${dataStr}`;
            }).join('\n');
        }
        
        return JSON.stringify(logs, null, 2);
    }
    
    /**
     * 创建子logger
     * @param {string} name 子logger名称
     * @returns {Logger} 子logger实例
     */
    createChild(name) {
        const childName = `${this.name}.${name}`;
        const child = new Logger(childName);
        child.logLevel = this.logLevel;
        child.storageEnabled = this.storageEnabled;
        return child;
    }
    
    /**
     * 记录性能指标
     * @param {string} name 指标名称
     * @param {number} value 指标值
     * @param {string} unit 单位
     */
    metric(name, value, unit = 'ms') {
        this.info(`Performance: ${name}`, {
            metric: name,
            value,
            unit,
            timestamp: Date.now()
        });
    }
    
    /**
     * 记录用户操作
     * @param {string} action 操作名称
     * @param {Object} details 操作详情
     */
    userAction(action, details = {}) {
        this.info(`User Action: ${action}`, {
            action,
            details,
            timestamp: Date.now(),
            url: window.location.href
        });
    }
    
    /**
     * 记录API调用
     * @param {string} method HTTP方法
     * @param {string} url API URL
     * @param {number} status 响应状态码
     * @param {number} duration 请求耗时
     */
    apiCall(method, url, status, duration) {
        const level = status >= 400 ? 'error' : status >= 300 ? 'warn' : 'info';
        this._log(level, `API Call: ${method} ${url}`, {
            method,
            url,
            status,
            duration,
            timestamp: Date.now()
        });
    }
}

// 创建全局logger实例
const globalLogger = new Logger('Global');

// 导出类和全局实例
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Logger, globalLogger };
} else {
    window.Logger = Logger;
    window.logger = globalLogger;
}