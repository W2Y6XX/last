/**
 * 智能体管理器
 * 负责管理智能体信息的获取、状态更新、配置管理等功能
 */
class AgentManager {
    constructor() {
        this.agents = new Map();
        this.statusUpdateHandlers = new Set();
        this.refreshInterval = 30000; // 30秒
        this.refreshTimer = null;
        this.wsConnected = false;
        this.lastUpdateTime = null;
        
        // 智能体类型定义
        this.agentTypes = {
            'meta_agent': {
                name: '元智能体',
                description: '负责任务分析和规划的智能体',
                icon: 'robot',
                capabilities: ['任务分析', '任务规划', '复杂度评估']
            },
            'task_decomposer': {
                name: '任务分解器',
                description: '负责将复杂任务分解为子任务',
                icon: 'split',
                capabilities: ['任务分解', '依赖分析', '优先级排序']
            },
            'coordinator': {
                name: '协调器',
                description: '负责协调多个智能体的工作',
                icon: 'network',
                capabilities: ['任务调度', '资源分配', '状态监控']
            },
            'generic': {
                name: '通用智能体',
                description: '执行具体任务的通用智能体',
                icon: 'cog',
                capabilities: ['任务执行', '结果反馈']
            }
        };
        
        // 状态颜色映射
        this.statusColors = {
            'active': '#10b981',    // 绿色
            'idle': '#6b7280',      // 灰色
            'busy': '#f59e0b',      // 黄色
            'error': '#ef4444',     // 红色
            'offline': '#9ca3af'    // 浅灰色
        };
        
        // 初始化
        this._initialize();
    }
    
    /**
     * 初始化管理器
     * @private
     */
    async _initialize() {
        try {
            // 设置WebSocket消息处理
            this._setupWebSocketHandlers();
            
            // 加载智能体信息
            await this.loadAgents();
            
            // 开始定期刷新
            this._startRefreshTimer();
            
        } catch (error) {
            console.error('智能体管理器初始化失败:', error);
        }
    }
    
    /**
     * 设置WebSocket消息处理器
     * @private
     */
    _setupWebSocketHandlers() {
        if (window.wsManager) {
            // 监听连接状态
            window.wsManager.onMessage('connection_status', (data) => {
                this.wsConnected = data.connected;
                if (this.wsConnected) {
                    console.log('WebSocket已连接，开始接收智能体状态更新');
                }
            });
            
            // 监听智能体状态更新
            window.wsManager.onMessage('agent_status_update', (data) => {
                this._handleAgentStatusUpdate(data);
            });
            
            // 监听智能体配置更新
            window.wsManager.onMessage('agent_config_update', (data) => {
                this._handleAgentConfigUpdate(data);
            });
            
            // 监听智能体统计更新
            window.wsManager.onMessage('agent_stats_update', (data) => {
                this._handleAgentStatsUpdate(data);
            });
        }
    }
    
    /**
     * 处理智能体状态更新
     * @private
     */
    _handleAgentStatusUpdate(data) {
        const { agentId, status, currentTask, timestamp } = data;
        
        if (this.agents.has(agentId)) {
            const agent = this.agents.get(agentId);
            const oldStatus = agent.status;
            
            // 更新状态
            agent.status = status;
            agent.currentTask = currentTask;
            agent.lastStatusUpdate = timestamp || new Date().toISOString();
            
            // 更新健康状态
            agent.healthStatus.lastHealthCheck = new Date().toISOString();
            agent.healthStatus.isHealthy = status !== 'error';
            
            // 触发状态更新事件
            this._notifyStatusUpdate(agentId, {
                oldStatus,
                newStatus: status,
                currentTask,
                timestamp: agent.lastStatusUpdate
            });
        }
    }
    
    /**
     * 处理智能体配置更新
     * @private
     */
    _handleAgentConfigUpdate(data) {
        const { agentId, configuration } = data;
        
        if (this.agents.has(agentId)) {
            const agent = this.agents.get(agentId);
            agent.configuration = { ...agent.configuration, ...configuration };
            agent.updatedAt = new Date().toISOString();
            
            // 触发配置更新事件
            this._notifyConfigUpdate(agentId, configuration);
        }
    }
    
    /**
     * 处理智能体统计更新
     * @private
     */
    _handleAgentStatsUpdate(data) {
        const { agentId, stats } = data;
        
        if (this.agents.has(agentId)) {
            const agent = this.agents.get(agentId);
            agent.executionStats = { ...agent.executionStats, ...stats };
            
            // 重新计算成功率和平均执行时间
            this._recalculateStats(agent);
            
            // 触发统计更新事件
            this._notifyStatsUpdate(agentId, agent.executionStats);
        }
    }
    
    /**
     * 重新计算统计信息
     * @private
     */
    _recalculateStats(agent) {
        const stats = agent.executionStats;
        
        // 计算成功率
        if (stats.totalExecutions > 0) {
            stats.successRate = Math.round((stats.successfulExecutions / stats.totalExecutions) * 100);
        } else {
            stats.successRate = 0;
        }
        
        // 计算平均执行时间（如果有执行时间数据）
        if (stats.totalExecutionTime && stats.totalExecutions > 0) {
            stats.averageExecutionTime = Math.round(stats.totalExecutionTime / stats.totalExecutions);
        }
    }
    
    /**
     * 通知状态更新
     * @private
     */
    _notifyStatusUpdate(agentId, updateData) {
        this.statusUpdateHandlers.forEach(handler => {
            try {
                handler('status_update', { agentId, ...updateData });
            } catch (error) {
                console.error('状态更新处理器执行失败:', error);
            }
        });
    }
    
    /**
     * 通知配置更新
     * @private
     */
    _notifyConfigUpdate(agentId, configuration) {
        this.statusUpdateHandlers.forEach(handler => {
            try {
                handler('config_update', { agentId, configuration });
            } catch (error) {
                console.error('配置更新处理器执行失败:', error);
            }
        });
    }
    
    /**
     * 通知统计更新
     * @private
     */
    _notifyStatsUpdate(agentId, stats) {
        this.statusUpdateHandlers.forEach(handler => {
            try {
                handler('stats_update', { agentId, stats });
            } catch (error) {
                console.error('统计更新处理器执行失败:', error);
            }
        });
    }
    
    /**
     * 开始定期刷新定时器
     * @private
     */
    _startRefreshTimer() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        
        this.refreshTimer = setInterval(async () => {
            if (!this.wsConnected) {
                // 如果WebSocket未连接，使用轮询方式更新
                await this.refreshAgentStatus();
            }
        }, this.refreshInterval);
    }
    
    /**
     * 停止定期刷新定时器
     * @private
     */
    _stopRefreshTimer() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }
    
    /**
     * 加载智能体信息
     * @returns {Promise<Object>} 加载结果
     */
    async loadAgents() {
        try {
            if (!window.apiClient) {
                return {
                    success: false,
                    errors: ['API客户端未初始化']
                };
            }
            
            const response = await window.apiClient.get('/api/v1/agents/enhanced');
            
            if (response.success && response.data) {
                // 清空现有智能体信息
                this.agents.clear();
                
                // 加载智能体信息
                response.data.agents.forEach(agentData => {
                    const agent = this._normalizeAgentData(agentData);
                    this.agents.set(agent.agentId, agent);
                });
                
                this.lastUpdateTime = new Date().toISOString();
                
                // 触发加载完成事件
                this.statusUpdateHandlers.forEach(handler => {
                    try {
                        handler('agents_loaded', { 
                            count: this.agents.size,
                            timestamp: this.lastUpdateTime
                        });
                    } catch (error) {
                        console.error('智能体加载处理器执行失败:', error);
                    }
                });
                
                return {
                    success: true,
                    data: {
                        count: this.agents.size,
                        agents: Array.from(this.agents.values())
                    }
                };
            }
            
            return {
                success: false,
                errors: ['加载智能体信息失败']
            };
            
        } catch (error) {
            console.error('加载智能体失败:', error);
            return {
                success: false,
                errors: ['加载智能体时发生错误']
            };
        }
    }
    
    /**
     * 标准化智能体数据
     * @private
     */
    _normalizeAgentData(agentData) {
        const agentType = this.agentTypes[agentData.agentType] || this.agentTypes.generic;
        
        return {
            agentId: agentData.agentId || agentData.id,
            agentType: agentData.agentType || 'generic',
            name: agentData.name || agentType.name,
            description: agentData.description || agentType.description,
            capabilities: agentData.capabilities || agentType.capabilities,
            status: agentData.status || 'idle',
            currentTask: agentData.currentTask || null,
            configuration: {
                llmConfig: agentData.configuration?.llmConfig || null,
                parameters: agentData.configuration?.parameters || {},
                constraints: agentData.configuration?.constraints || []
            },
            executionStats: {
                totalExecutions: agentData.executionStats?.totalExecutions || 0,
                successfulExecutions: agentData.executionStats?.successfulExecutions || 0,
                failedExecutions: agentData.executionStats?.failedExecutions || 0,
                successRate: 0,
                averageExecutionTime: agentData.executionStats?.averageExecutionTime || 0,
                lastExecutionTime: agentData.executionStats?.lastExecutionTime || null,
                totalExecutionTime: agentData.executionStats?.totalExecutionTime || 0
            },
            healthStatus: {
                isHealthy: agentData.healthStatus?.isHealthy !== false,
                lastHealthCheck: agentData.healthStatus?.lastHealthCheck || new Date().toISOString(),
                issues: agentData.healthStatus?.issues || []
            },
            createdAt: agentData.createdAt || new Date().toISOString(),
            updatedAt: agentData.updatedAt || new Date().toISOString(),
            lastStatusUpdate: agentData.lastStatusUpdate || new Date().toISOString()
        };
    }
    
    /**
     * 刷新智能体状态
     * @returns {Promise<Object>} 刷新结果
     */
    async refreshAgentStatus() {
        try {
            if (!window.apiClient) {
                return {
                    success: false,
                    errors: ['API客户端未初始化']
                };
            }
            
            const response = await window.apiClient.get('/api/v1/agents/status');
            
            if (response.success && response.data) {
                response.data.forEach(statusData => {
                    if (this.agents.has(statusData.agentId)) {
                        this._handleAgentStatusUpdate(statusData);
                    }
                });
                
                return { success: true };
            }
            
            return {
                success: false,
                errors: ['刷新智能体状态失败']
            };
            
        } catch (error) {
            console.error('刷新智能体状态失败:', error);
            return {
                success: false,
                errors: ['刷新智能体状态时发生错误']
            };
        }
    }
    
    /**
     * 获取所有智能体
     * @returns {Array} 智能体列表
     */
    getAllAgents() {
        return Array.from(this.agents.values()).map(agent => ({
            ...agent,
            typeInfo: this.agentTypes[agent.agentType] || this.agentTypes.generic,
            statusColor: this.statusColors[agent.status] || this.statusColors.idle
        }));
    }
    
    /**
     * 获取智能体详情
     * @param {string} agentId 智能体ID
     * @returns {Object|null} 智能体详情
     */
    getAgentDetails(agentId) {
        const agent = this.agents.get(agentId);
        if (!agent) return null;
        
        return {
            ...agent,
            typeInfo: this.agentTypes[agent.agentType] || this.agentTypes.generic,
            statusColor: this.statusColors[agent.status] || this.statusColors.idle
        };
    }
    
    /**
     * 更新智能体配置
     * @param {string} agentId 智能体ID
     * @param {Object} configUpdate 配置更新
     * @returns {Promise<Object>} 更新结果
     */
    async updateAgentConfig(agentId, configUpdate) {
        try {
            if (!this.agents.has(agentId)) {
                return {
                    success: false,
                    errors: ['智能体不存在']
                };
            }
            
            if (!window.apiClient) {
                return {
                    success: false,
                    errors: ['API客户端未初始化']
                };
            }
            
            const response = await window.apiClient.put(
                `/api/v1/agents/${agentId}/config`,
                configUpdate
            );
            
            if (response.success) {
                // 更新本地配置
                const agent = this.agents.get(agentId);
                agent.configuration = { ...agent.configuration, ...configUpdate };
                agent.updatedAt = new Date().toISOString();
                
                // 触发配置更新事件
                this._notifyConfigUpdate(agentId, configUpdate);
                
                return { success: true };
            }
            
            return {
                success: false,
                errors: [response.message || '更新智能体配置失败']
            };
            
        } catch (error) {
            console.error('更新智能体配置失败:', error);
            return {
                success: false,
                errors: ['更新智能体配置时发生错误']
            };
        }
    }
    
    /**
     * 获取智能体历史记录
     * @param {string} agentId 智能体ID
     * @param {Object} options 查询选项
     * @returns {Promise<Object>} 历史记录
     */
    async getAgentHistory(agentId, options = {}) {
        try {
            if (!this.agents.has(agentId)) {
                return {
                    success: false,
                    errors: ['智能体不存在']
                };
            }
            
            if (!window.apiClient) {
                return {
                    success: false,
                    errors: ['API客户端未初始化']
                };
            }
            
            const params = new URLSearchParams({
                page: options.page || 1,
                pageSize: options.pageSize || 20,
                startDate: options.startDate || '',
                endDate: options.endDate || '',
                status: options.status || ''
            });
            
            const response = await window.apiClient.get(
                `/api/v1/agents/${agentId}/history?${params}`
            );
            
            if (response.success) {
                return {
                    success: true,
                    data: response.data
                };
            }
            
            return {
                success: false,
                errors: [response.message || '获取智能体历史记录失败']
            };
            
        } catch (error) {
            console.error('获取智能体历史记录失败:', error);
            return {
                success: false,
                errors: ['获取智能体历史记录时发生错误']
            };
        }
    }
    
    /**
     * 获取智能体日志
     * @param {string} agentId 智能体ID
     * @param {Object} options 查询选项
     * @returns {Promise<Object>} 日志数据
     */
    async getAgentLogs(agentId, options = {}) {
        try {
            if (!this.agents.has(agentId)) {
                return {
                    success: false,
                    errors: ['智能体不存在']
                };
            }
            
            if (!window.apiClient) {
                return {
                    success: false,
                    errors: ['API客户端未初始化']
                };
            }
            
            const params = new URLSearchParams({
                level: options.level || 'all',
                limit: options.limit || 100,
                startTime: options.startTime || '',
                endTime: options.endTime || ''
            });
            
            const response = await window.apiClient.get(
                `/api/v1/agents/${agentId}/logs?${params}`
            );
            
            if (response.success) {
                return {
                    success: true,
                    data: response.data
                };
            }
            
            return {
                success: false,
                errors: [response.message || '获取智能体日志失败']
            };
            
        } catch (error) {
            console.error('获取智能体日志失败:', error);
            return {
                success: false,
                errors: ['获取智能体日志时发生错误']
            };
        }
    }
    
    /**
     * 注册状态更新处理器
     * @param {Function} handler 处理器函数
     */
    onStatusUpdate(handler) {
        if (typeof handler === 'function') {
            this.statusUpdateHandlers.add(handler);
        }
    }
    
    /**
     * 移除状态更新处理器
     * @param {Function} handler 处理器函数
     */
    offStatusUpdate(handler) {
        this.statusUpdateHandlers.delete(handler);
    }
    
    /**
     * 订阅智能体更新
     * @returns {Promise<Object>} 订阅结果
     */
    async subscribeToUpdates() {
        try {
            if (window.wsManager && !this.wsConnected) {
                // 尝试连接WebSocket
                window.wsManager.connect();
                
                // 发送订阅请求
                window.wsManager.send({
                    type: 'subscribe',
                    topics: ['agent_status', 'agent_config', 'agent_stats']
                });
                
                return { success: true };
            }
            
            return {
                success: false,
                errors: ['WebSocket管理器未初始化或已连接']
            };
            
        } catch (error) {
            console.error('订阅智能体更新失败:', error);
            return {
                success: false,
                errors: ['订阅智能体更新时发生错误']
            };
        }
    }
    
    /**
     * 取消订阅智能体更新
     */
    unsubscribeFromUpdates() {
        if (window.wsManager) {
            window.wsManager.send({
                type: 'unsubscribe',
                topics: ['agent_status', 'agent_config', 'agent_stats']
            });
        }
    }
    
    /**
     * 获取智能体统计摘要
     * @returns {Object} 统计摘要
     */
    getAgentsSummary() {
        const agents = Array.from(this.agents.values());
        const summary = {
            total: agents.length,
            byStatus: {},
            byType: {},
            totalExecutions: 0,
            totalSuccessfulExecutions: 0,
            averageSuccessRate: 0,
            healthyAgents: 0
        };
        
        // 按状态统计
        Object.keys(this.statusColors).forEach(status => {
            summary.byStatus[status] = 0;
        });
        
        // 按类型统计
        Object.keys(this.agentTypes).forEach(type => {
            summary.byType[type] = 0;
        });
        
        agents.forEach(agent => {
            // 状态统计
            summary.byStatus[agent.status] = (summary.byStatus[agent.status] || 0) + 1;
            
            // 类型统计
            summary.byType[agent.agentType] = (summary.byType[agent.agentType] || 0) + 1;
            
            // 执行统计
            summary.totalExecutions += agent.executionStats.totalExecutions;
            summary.totalSuccessfulExecutions += agent.executionStats.successfulExecutions;
            
            // 健康状态统计
            if (agent.healthStatus.isHealthy) {
                summary.healthyAgents++;
            }
        });
        
        // 计算平均成功率
        if (summary.totalExecutions > 0) {
            summary.averageSuccessRate = Math.round(
                (summary.totalSuccessfulExecutions / summary.totalExecutions) * 100
            );
        }
        
        return summary;
    }
    
    /**
     * 销毁管理器
     */
    destroy() {
        this._stopRefreshTimer();
        this.unsubscribeFromUpdates();
        this.statusUpdateHandlers.clear();
        this.agents.clear();
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AgentManager;
} else {
    window.AgentManager = AgentManager;
}