/**
 * 功能开关管理器
 * 负责管理功能开关，支持渐进式部署和A/B测试
 */
class FeatureFlagManager {
    constructor() {
        this.flags = new Map();
        this.userSegments = new Map();
        this.flagChangeHandlers = new Set();
        this.storageKey = 'feature_flags';
        this.userSegmentKey = 'user_segment';
        this.remoteConfigUrl = '/api/v1/feature-flags';
        this.syncInterval = 5 * 60 * 1000; // 5分钟
        this.syncTimer = null;
        
        // 默认功能开关配置
        this.defaultFlags = {
            // 大模型配置功能
            'llm-config': {
                enabled: true,
                rolloutPercentage: 100,
                userSegments: ['all'],
                dependencies: [],
                description: '大模型配置管理功能'
            },
            
            // 增强的智能体管理
            'enhanced-agent-management': {
                enabled: true,
                rolloutPercentage: 100,
                userSegments: ['all'],
                dependencies: [],
                description: '增强的智能体管理界面'
            },
            
            // 元智能体对话
            'meta-agent-chat': {
                enabled: true,
                rolloutPercentage: 80,
                userSegments: ['beta', 'admin'],
                dependencies: ['llm-config'],
                description: '元智能体引导的任务创建'
            },
            
            // 任务分解功能
            'task-decomposition': {
                enabled: true,
                rolloutPercentage: 60,
                userSegments: ['beta', 'admin'],
                dependencies: ['meta-agent-chat'],
                description: '复杂任务自动分解功能'
            },
            
            // 实时状态更新
            'real-time-updates': {
                enabled: true,
                rolloutPercentage: 90,
                userSegments: ['all'],
                dependencies: [],
                description: 'WebSocket实时状态更新'
            },
            
            // 高级配置选项
            'advanced-config': {
                enabled: false,
                rolloutPercentage: 20,
                userSegments: ['admin', 'power-user'],
                dependencies: ['llm-config'],
                description: '高级配置选项'
            },
            
            // 性能监控
            'performance-monitoring': {
                enabled: true,
                rolloutPercentage: 100,
                userSegments: ['all'],
                dependencies: [],
                description: '性能监控和分析'
            },
            
            // 错误报告
            'error-reporting': {
                enabled: true,
                rolloutPercentage: 100,
                userSegments: ['all'],
                dependencies: [],
                description: '自动错误报告'
            },
            
            // 调试模式
            'debug-mode': {
                enabled: false,
                rolloutPercentage: 0,
                userSegments: ['developer'],
                dependencies: [],
                description: '调试模式和详细日志'
            },
            
            // 实验性功能
            'experimental-features': {
                enabled: false,
                rolloutPercentage: 5,
                userSegments: ['beta'],
                dependencies: [],
                description: '实验性功能'
            }
        };
        
        // 初始化
        this._initialize();
    }
    
    /**
     * 初始化功能开关管理器
     * @private
     */
    async _initialize() {
        try {
            // 加载本地存储的开关状态
            this._loadFromStorage();
            
            // 设置默认开关
            this._setDefaultFlags();
            
            // 确定用户分组
            this._determineUserSegment();
            
            // 同步远程配置
            await this._syncRemoteConfig();
            
            // 开始定期同步
            this._startSyncTimer();
            
            console.log('功能开关管理器初始化完成');
            
        } catch (error) {
            console.error('功能开关管理器初始化失败:', error);
            // 使用默认配置
            this._setDefaultFlags();
        }
    }
    
    /**
     * 从本地存储加载开关状态
     * @private
     */
    _loadFromStorage() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            if (stored) {
                const flagsData = JSON.parse(stored);
                Object.keys(flagsData).forEach(key => {
                    this.flags.set(key, flagsData[key]);
                });
            }
        } catch (error) {
            console.error('加载功能开关失败:', error);
        }
    }
    
    /**
     * 保存开关状态到本地存储
     * @private
     */
    _saveToStorage() {
        try {
            const flagsData = Object.fromEntries(this.flags);
            localStorage.setItem(this.storageKey, JSON.stringify(flagsData));
        } catch (error) {
            console.error('保存功能开关失败:', error);
        }
    }
    
    /**
     * 设置默认功能开关
     * @private
     */
    _setDefaultFlags() {
        Object.keys(this.defaultFlags).forEach(key => {
            if (!this.flags.has(key)) {
                this.flags.set(key, {
                    ...this.defaultFlags[key],
                    lastUpdated: new Date().toISOString(),
                    source: 'default'
                });
            }
        });
    }
    
    /**
     * 确定用户分组
     * @private
     */
    _determineUserSegment() {
        let userSegment = localStorage.getItem(this.userSegmentKey);
        
        if (!userSegment) {
            // 基于用户ID或其他标识确定分组
            const userId = this._getUserId();
            const hash = this._hashString(userId);
            const percentage = hash % 100;
            
            if (percentage < 5) {
                userSegment = 'beta';
            } else if (percentage < 10) {
                userSegment = 'power-user';
            } else {
                userSegment = 'regular';
            }
            
            // 检查是否是管理员或开发者
            if (this._isAdmin()) {
                userSegment = 'admin';
            } else if (this._isDeveloper()) {
                userSegment = 'developer';
            }
            
            localStorage.setItem(this.userSegmentKey, userSegment);
        }
        
        this.userSegments.set('current', userSegment);
        console.log('用户分组:', userSegment);
    }
    
    /**
     * 获取用户ID
     * @private
     */
    _getUserId() {
        return localStorage.getItem('user_id') || 
               sessionStorage.getItem('session_id') || 
               'anonymous_' + Date.now();
    }
    
    /**
     * 字符串哈希函数
     * @private
     */
    _hashString(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // 转换为32位整数
        }
        return Math.abs(hash);
    }
    
    /**
     * 检查是否是管理员
     * @private
     */
    _isAdmin() {
        // 这里应该根据实际的用户权限系统来判断
        return localStorage.getItem('user_role') === 'admin' ||
               window.location.hostname === 'localhost' ||
               window.location.search.includes('admin=true');
    }
    
    /**
     * 检查是否是开发者
     * @private
     */
    _isDeveloper() {
        return localStorage.getItem('user_role') === 'developer' ||
               window.location.hostname === 'localhost' ||
               window.location.search.includes('dev=true');
    }
    
    /**
     * 同步远程配置
     * @private
     */
    async _syncRemoteConfig() {
        try {
            if (window.apiClient) {
                const response = await window.apiClient.get(this.remoteConfigUrl);
                
                if (response.success && response.data) {
                    const remoteFlags = response.data.flags || {};
                    
                    Object.keys(remoteFlags).forEach(key => {
                        const remoteFlag = remoteFlags[key];
                        const localFlag = this.flags.get(key);
                        
                        // 如果远程配置更新，则更新本地配置
                        if (!localFlag || 
                            new Date(remoteFlag.lastUpdated) > new Date(localFlag.lastUpdated)) {
                            
                            this.flags.set(key, {
                                ...remoteFlag,
                                source: 'remote'
                            });
                            
                            // 触发变更事件
                            this._notifyFlagChange(key, remoteFlag);
                        }
                    });
                    
                    this._saveToStorage();
                }
            }
        } catch (error) {
            console.warn('同步远程功能开关配置失败:', error);
        }
    }
    
    /**
     * 开始定期同步定时器
     * @private
     */
    _startSyncTimer() {
        if (this.syncTimer) {
            clearInterval(this.syncTimer);
        }
        
        this.syncTimer = setInterval(async () => {
            await this._syncRemoteConfig();
        }, this.syncInterval);
    }
    
    /**
     * 停止定期同步定时器
     * @private
     */
    _stopSyncTimer() {
        if (this.syncTimer) {
            clearInterval(this.syncTimer);
            this.syncTimer = null;
        }
    }
    
    /**
     * 通知功能开关变更
     * @private
     */
    _notifyFlagChange(flagName, flagConfig) {
        this.flagChangeHandlers.forEach(handler => {
            try {
                handler(flagName, flagConfig);
            } catch (error) {
                console.error('功能开关变更处理器执行失败:', error);
            }
        });
    }
    
    /**
     * 检查功能是否启用
     * @param {string} flagName 功能开关名称
     * @returns {boolean} 是否启用
     */
    isEnabled(flagName) {
        const flag = this.flags.get(flagName);
        if (!flag) {
            return false;
        }
        
        // 检查基础启用状态
        if (!flag.enabled) {
            return false;
        }
        
        // 检查依赖
        if (flag.dependencies && flag.dependencies.length > 0) {
            for (const dependency of flag.dependencies) {
                if (!this.isEnabled(dependency)) {
                    return false;
                }
            }
        }
        
        // 检查用户分组
        const currentSegment = this.userSegments.get('current') || 'regular';
        if (flag.userSegments && flag.userSegments.length > 0) {
            if (!flag.userSegments.includes('all') && 
                !flag.userSegments.includes(currentSegment)) {
                return false;
            }
        }
        
        // 检查推出百分比
        if (flag.rolloutPercentage < 100) {
            const userId = this._getUserId();
            const hash = this._hashString(userId + flagName);
            const userPercentage = hash % 100;
            
            if (userPercentage >= flag.rolloutPercentage) {
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * 获取功能开关配置
     * @param {string} flagName 功能开关名称
     * @returns {Object|null} 功能开关配置
     */
    getFlag(flagName) {
        return this.flags.get(flagName) || null;
    }
    
    /**
     * 获取所有功能开关
     * @returns {Object} 所有功能开关
     */
    getAllFlags() {
        const result = {};
        this.flags.forEach((config, name) => {
            result[name] = {
                ...config,
                isEnabled: this.isEnabled(name)
            };
        });
        return result;
    }
    
    /**
     * 设置功能开关（仅限本地测试）
     * @param {string} flagName 功能开关名称
     * @param {boolean} enabled 是否启用
     * @param {Object} options 额外选项
     */
    setFlag(flagName, enabled, options = {}) {
        const existingFlag = this.flags.get(flagName) || {};
        
        const updatedFlag = {
            ...existingFlag,
            enabled,
            ...options,
            lastUpdated: new Date().toISOString(),
            source: 'manual'
        };
        
        this.flags.set(flagName, updatedFlag);
        this._saveToStorage();
        
        // 触发变更事件
        this._notifyFlagChange(flagName, updatedFlag);
    }
    
    /**
     * 批量设置功能开关
     * @param {Object} flagUpdates 功能开关更新
     */
    setFlags(flagUpdates) {
        Object.keys(flagUpdates).forEach(flagName => {
            const update = flagUpdates[flagName];
            if (typeof update === 'boolean') {
                this.setFlag(flagName, update);
            } else {
                this.setFlag(flagName, update.enabled, update);
            }
        });
    }
    
    /**
     * 重置功能开关到默认状态
     * @param {string} flagName 功能开关名称
     */
    resetFlag(flagName) {
        if (this.defaultFlags[flagName]) {
            this.flags.set(flagName, {
                ...this.defaultFlags[flagName],
                lastUpdated: new Date().toISOString(),
                source: 'reset'
            });
            this._saveToStorage();
            
            // 触发变更事件
            this._notifyFlagChange(flagName, this.flags.get(flagName));
        }
    }
    
    /**
     * 重置所有功能开关
     */
    resetAllFlags() {
        Object.keys(this.defaultFlags).forEach(flagName => {
            this.resetFlag(flagName);
        });
    }
    
    /**
     * 注册功能开关变更处理器
     * @param {Function} handler 处理器函数
     */
    onFlagChange(handler) {
        if (typeof handler === 'function') {
            this.flagChangeHandlers.add(handler);
        }
    }
    
    /**
     * 移除功能开关变更处理器
     * @param {Function} handler 处理器函数
     */
    offFlagChange(handler) {
        this.flagChangeHandlers.delete(handler);
    }
    
    /**
     * 获取用户分组信息
     * @returns {Object} 用户分组信息
     */
    getUserSegmentInfo() {
        return {
            current: this.userSegments.get('current'),
            available: ['regular', 'power-user', 'beta', 'admin', 'developer'],
            description: {
                'regular': '普通用户',
                'power-user': '高级用户',
                'beta': '测试用户',
                'admin': '管理员',
                'developer': '开发者'
            }
        };
    }
    
    /**
     * 切换用户分组（仅限测试）
     * @param {string} segment 用户分组
     */
    setUserSegment(segment) {
        const validSegments = ['regular', 'power-user', 'beta', 'admin', 'developer'];
        if (validSegments.includes(segment)) {
            this.userSegments.set('current', segment);
            localStorage.setItem(this.userSegmentKey, segment);
            
            console.log('用户分组已切换到:', segment);
            
            // 重新评估所有功能开关
            this.flags.forEach((config, name) => {
                this._notifyFlagChange(name, config);
            });
        }
    }
    
    /**
     * 获取功能开关统计
     * @returns {Object} 统计信息
     */
    getStats() {
        const stats = {
            total: this.flags.size,
            enabled: 0,
            disabled: 0,
            bySource: {},
            bySegment: {},
            dependencies: 0
        };
        
        this.flags.forEach((config, name) => {
            if (this.isEnabled(name)) {
                stats.enabled++;
            } else {
                stats.disabled++;
            }
            
            // 按来源统计
            const source = config.source || 'unknown';
            stats.bySource[source] = (stats.bySource[source] || 0) + 1;
            
            // 统计有依赖的功能
            if (config.dependencies && config.dependencies.length > 0) {
                stats.dependencies++;
            }
        });
        
        return stats;
    }
    
    /**
     * 导出功能开关配置
     * @returns {Object} 配置数据
     */
    exportConfig() {
        return {
            flags: Object.fromEntries(this.flags),
            userSegment: this.userSegments.get('current'),
            exportedAt: new Date().toISOString()
        };
    }
    
    /**
     * 导入功能开关配置
     * @param {Object} config 配置数据
     */
    importConfig(config) {
        if (config.flags) {
            Object.keys(config.flags).forEach(flagName => {
                this.flags.set(flagName, {
                    ...config.flags[flagName],
                    source: 'imported',
                    lastUpdated: new Date().toISOString()
                });
            });
            this._saveToStorage();
        }
        
        if (config.userSegment) {
            this.setUserSegment(config.userSegment);
        }
    }
    
    /**
     * 销毁管理器
     */
    destroy() {
        this._stopSyncTimer();
        this.flagChangeHandlers.clear();
        this.flags.clear();
        this.userSegments.clear();
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FeatureFlagManager;
} else {
    window.FeatureFlagManager = FeatureFlagManager;
}