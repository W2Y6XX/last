/**
 * 元智能体对话管理器
 * 负责管理与元智能体的对话流程，包括任务创建引导和任务拆解功能
 */
class MetaAgentChatManager {
    constructor() {
        this.conversationId = null;
        this.messages = [];
        this.taskContext = {
            title: '',
            description: '',
            requirements: [],
            constraints: [],
            complexity: 0,
            estimatedDuration: 0,
            priority: 2,
            type: 'general'
        };
        this.currentPhase = 'initial'; // initial, collecting, analyzing, decomposing, finalizing
        this.progress = 0;
        this.canDecompose = false;
        this.decompositionThreshold = 0.7; // 复杂度阈值
        this.decompositionResult = null;
        this.messageHandlers = new Set();
        this.isActive = false;
        
        // 对话阶段定义
        this.phases = {
            'initial': {
                name: '初始化',
                description: '开始任务创建对话',
                progress: 0
            },
            'collecting': {
                name: '信息收集',
                description: '收集任务基本信息',
                progress: 25
            },
            'analyzing': {
                name: '需求分析',
                description: '分析任务需求和约束',
                progress: 50
            },
            'refining': {
                name: '细化完善',
                description: '完善任务细节',
                progress: 75
            },
            'finalizing': {
                name: '最终确认',
                description: '确认任务信息',
                progress: 90
            },
            'decomposing': {
                name: '任务拆解',
                description: '分解复杂任务',
                progress: 95
            },
            'completed': {
                name: '完成',
                description: '任务创建完成',
                progress: 100
            }
        };
        
        // 消息类型定义
        this.messageTypes = {
            'user': {
                name: '用户',
                className: 'user-message',
                avatar: 'user'
            },
            'meta_agent': {
                name: '元智能体',
                className: 'agent-message',
                avatar: 'robot'
            },
            'system': {
                name: '系统',
                className: 'system-message',
                avatar: 'system'
            }
        };
    }
    
    /**
     * 开始新的对话
     * @param {string} initialPrompt 初始提示
     * @param {Object} context 上下文信息
     * @returns {Promise<Object>} 开始结果
     */
    async startConversation(initialPrompt, context = {}) {
        try {
            if (!window.apiClient) {
                return {
                    success: false,
                    errors: ['API客户端未初始化']
                };
            }
            
            // 重置状态
            this._resetState();
            
            // 设置初始上下文
            this.taskContext = { ...this.taskContext, ...context };
            
            // 发送开始对话请求
            const response = await window.apiClient.post('/api/v1/meta-agent/conversations', {
                initialPrompt,
                context: this.taskContext
            });
            
            if (response.success && response.data) {
                // 处理后端返回的字段名差异
                this.conversationId = response.data.conversation_id || response.data.conversationId;
                this.isActive = true;
                this.currentPhase = response.data.current_phase || 'collecting';
                this.progress = response.data.progress || this.phases[this.currentPhase].progress;
                
                // 添加初始消息
                this._addMessage('user', initialPrompt);
                
                const firstQuestion = response.data.first_question || response.data.firstQuestion;
                if (firstQuestion) {
                    this._addMessage('meta_agent', firstQuestion);
                }
                
                // 触发对话开始事件
                this._notifyHandlers('conversation_started', {
                    conversationId: this.conversationId,
                    firstQuestion: firstQuestion,
                    phase: this.currentPhase,
                    progress: this.progress
                });
                
                return {
                    success: true,
                    data: {
                        conversationId: this.conversationId,
                        firstQuestion: firstQuestion,
                        phase: this.currentPhase,
                        progress: this.progress
                    }
                };
            }
            
            return {
                success: false,
                errors: [response.message || '开始对话失败']
            };
            
        } catch (error) {
            console.error('开始对话失败:', error);
            return {
                success: false,
                errors: ['开始对话时发生错误']
            };
        }
    }
    
    /**
     * 发送消息
     * @param {string} message 消息内容
     * @param {string} messageType 消息类型
     * @returns {Promise<Object>} 发送结果
     */
    async sendMessage(message, messageType = 'user') {
        try {
            if (!this.isActive || !this.conversationId) {
                return {
                    success: false,
                    errors: ['对话未激活或对话ID无效']
                };
            }
            
            if (!window.apiClient) {
                return {
                    success: false,
                    errors: ['API客户端未初始化']
                };
            }
            
            // 添加用户消息
            this._addMessage(messageType, message);
            
            // 发送消息到后端
            const response = await window.apiClient.post(
                `/api/v1/meta-agent/conversations/${this.conversationId}/messages`,
                {
                    message,
                    message_type: messageType,  // 后端期望的字段名
                    current_context: this.taskContext
                }
            );
            
            if (response.success && response.data) {
                // 更新任务上下文
                const taskContext = response.data.task_context || response.data.taskContext;
                if (taskContext) {
                    this.taskContext = { ...this.taskContext, ...taskContext };
                }
                
                // 更新对话状态
                const currentPhase = response.data.current_phase || response.data.phase;
                if (currentPhase) {
                    this.currentPhase = currentPhase;
                    this.progress = this.phases[this.currentPhase]?.progress || this.progress;
                }
                
                // 更新复杂度和拆解状态
                const canDecompose = response.data.can_decompose || response.data.canDecompose;
                if (canDecompose !== undefined) {
                    this.canDecompose = canDecompose;
                }
                
                if (response.data.complexity !== undefined) {
                    this.taskContext.complexity = response.data.complexity;
                    this.canDecompose = response.data.complexity >= this.decompositionThreshold;
                } else {
                    // 如果后端没有返回复杂度，进行实时分析
                    setTimeout(() => {
                        this.analyzeComplexityRealTime();
                    }, 500);
                }
                
                // 添加智能体回复
                if (response.data.response) {
                    this._addMessage('meta_agent', response.data.response);
                }
                
                // 触发消息发送事件
                this._notifyHandlers('message_sent', {
                    message,
                    response: response.data.response,
                    phase: this.currentPhase,
                    progress: this.progress,
                    taskContext: this.taskContext,
                    canDecompose: this.canDecompose
                });
                
                return {
                    success: true,
                    data: {
                        response: response.data.response,
                        phase: this.currentPhase,
                        progress: this.progress,
                        taskContext: this.taskContext,
                        canDecompose: this.canDecompose,
                        nextQuestion: response.data.nextQuestion
                    }
                };
            }
            
            return {
                success: false,
                errors: [response.message || '发送消息失败']
            };
            
        } catch (error) {
            console.error('发送消息失败:', error);
            return {
                success: false,
                errors: ['发送消息时发生错误']
            };
        }
    }
    
    /**
     * 分析任务复杂度
     * @param {boolean} realTime 是否实时分析
     * @returns {Promise<Object>} 分析结果
     */
    async analyzeComplexity(realTime = false) {
        try {
            if (!this.isActive || !this.conversationId) {
                return {
                    success: false,
                    errors: ['对话未激活或对话ID无效']
                };
            }
            
            if (!window.apiClient) {
                return {
                    success: false,
                    errors: ['API客户端未初始化']
                };
            }
            
            const response = await window.apiClient.post(
                `/api/v1/meta-agent/conversations/${this.conversationId}/analyze-complexity`,
                {
                    taskContext: this.taskContext,
                    messages: this.messages,
                    realTime: realTime
                }
            );
            
            if (response.success && response.data) {
                this.taskContext.complexity = response.data.complexity;
                this.canDecompose = response.data.complexity >= this.decompositionThreshold;
                
                // 触发复杂度分析事件
                this._notifyHandlers('complexity_analyzed', {
                    complexity: response.data.complexity,
                    canDecompose: this.canDecompose,
                    analysis: response.data.analysis,
                    factors: response.data.factors || [],
                    score: response.data.score || 0,
                    threshold: this.decompositionThreshold,
                    realTime: realTime
                });
                
                return {
                    success: true,
                    data: {
                        complexity: response.data.complexity,
                        canDecompose: this.canDecompose,
                        analysis: response.data.analysis,
                        factors: response.data.factors || [],
                        score: response.data.score || 0,
                        threshold: this.decompositionThreshold
                    }
                };
            }
            
            return {
                success: false,
                errors: [response.message || '分析任务复杂度失败']
            };
            
        } catch (error) {
            console.error('分析任务复杂度失败:', error);
            return {
                success: false,
                errors: ['分析任务复杂度时发生错误']
            };
        }
    }
    
    /**
     * 实时分析任务复杂度
     * @returns {Promise<Object>} 分析结果
     */
    async analyzeComplexityRealTime() {
        return this.analyzeComplexity(true);
    }
    
    /**
     * 设置复杂度阈值
     * @param {number} threshold 新的阈值 (0-1)
     */
    setDecompositionThreshold(threshold) {
        if (threshold >= 0 && threshold <= 1) {
            this.decompositionThreshold = threshold;
            
            // 重新评估是否可以拆解
            this.canDecompose = this.taskContext.complexity >= this.decompositionThreshold;
            
            // 触发阈值更新事件
            this._notifyHandlers('threshold_updated', {
                threshold: this.decompositionThreshold,
                canDecompose: this.canDecompose,
                complexity: this.taskContext.complexity
            });
        }
    }
    
    /**
     * 获取复杂度阈值
     * @returns {number} 当前阈值
     */
    getDecompositionThreshold() {
        return this.decompositionThreshold;
    }
    
    /**
     * 获取复杂度评分的可视化数据
     * @returns {Object} 可视化数据
     */
    getComplexityVisualization() {
        const complexity = this.taskContext.complexity || 0;
        const threshold = this.decompositionThreshold;
        
        return {
            score: complexity,
            percentage: Math.round(complexity * 100),
            threshold: threshold,
            thresholdPercentage: Math.round(threshold * 100),
            canDecompose: this.canDecompose,
            level: this._getComplexityLevel(complexity),
            color: this._getComplexityColor(complexity),
            recommendation: this._getComplexityRecommendation(complexity, threshold)
        };
    }
    
    /**
     * 获取复杂度等级
     * @private
     */
    _getComplexityLevel(complexity) {
        if (complexity < 0.3) return '简单';
        if (complexity < 0.5) return '中等';
        if (complexity < 0.7) return '复杂';
        return '非常复杂';
    }
    
    /**
     * 获取复杂度颜色
     * @private
     */
    _getComplexityColor(complexity) {
        if (complexity < 0.3) return '#10b981'; // 绿色
        if (complexity < 0.5) return '#f59e0b'; // 黄色
        if (complexity < 0.7) return '#f97316'; // 橙色
        return '#ef4444'; // 红色
    }
    
    /**
     * 获取复杂度建议
     * @private
     */
    _getComplexityRecommendation(complexity, threshold) {
        if (complexity < threshold) {
            return '任务复杂度较低，可以直接创建';
        } else {
            return '任务复杂度较高，建议进行任务拆解';
        }
    }
    
    /**
     * 请求任务拆解
     * @returns {Promise<Object>} 拆解结果
     */
    async requestDecomposition() {
        try {
            if (!this.isActive || !this.conversationId) {
                return {
                    success: false,
                    errors: ['对话未激活或对话ID无效']
                };
            }
            
            if (!this.canDecompose) {
                return {
                    success: false,
                    errors: ['任务复杂度不足，无需拆解']
                };
            }
            
            if (!window.apiClient) {
                return {
                    success: false,
                    errors: ['API客户端未初始化']
                };
            }
            
            // 更新阶段
            this.currentPhase = 'decomposing';
            this.progress = this.phases[this.currentPhase].progress;
            
            const response = await window.apiClient.post(
                `/api/v1/meta-agent/conversations/${this.conversationId}/decompose`,
                {
                    taskContext: this.taskContext,
                    messages: this.messages
                }
            );
            
            if (response.success && response.data) {
                this.decompositionResult = {
                    mainTask: response.data.mainTask,
                    subtasks: response.data.subtasks,
                    dependencies: response.data.dependencies || [],
                    complexity: response.data.complexity,
                    estimatedTotalTime: response.data.estimatedTotalTime || 0,
                    decompositionReason: response.data.reason
                };
                
                // 添加系统消息
                this._addMessage('system', '任务拆解完成，请查看拆解结果');
                
                // 触发任务拆解事件
                this._notifyHandlers('task_decomposed', {
                    decompositionResult: this.decompositionResult,
                    phase: this.currentPhase,
                    progress: this.progress
                });
                
                return {
                    success: true,
                    data: this.decompositionResult
                };
            }
            
            return {
                success: false,
                errors: [response.message || '任务拆解失败']
            };
            
        } catch (error) {
            console.error('任务拆解失败:', error);
            return {
                success: false,
                errors: ['任务拆解时发生错误']
            };
        }
    }
    
    /**
     * 完成任务创建
     * @param {Object} finalTaskData 最终任务数据
     * @returns {Promise<Object>} 完成结果
     */
    async finalizeTask(finalTaskData = {}) {
        try {
            if (!this.isActive || !this.conversationId) {
                return {
                    success: false,
                    errors: ['对话未激活或对话ID无效']
                };
            }
            
            if (!window.apiClient) {
                return {
                    success: false,
                    errors: ['API客户端未初始化']
                };
            }
            
            // 合并最终任务数据
            const taskData = {
                ...this.taskContext,
                ...finalTaskData,
                conversationId: this.conversationId,
                messages: this.messages,
                decompositionResult: this.decompositionResult
            };
            
            const response = await window.apiClient.post(
                `/api/v1/meta-agent/conversations/${this.conversationId}/finalize`,
                taskData
            );
            
            if (response.success && response.data) {
                // 更新阶段
                this.currentPhase = 'completed';
                this.progress = this.phases[this.currentPhase].progress;
                
                // 添加完成消息
                this._addMessage('system', '任务创建完成');
                
                // 触发任务完成事件
                this._notifyHandlers('task_finalized', {
                    taskData: response.data,
                    phase: this.currentPhase,
                    progress: this.progress
                });
                
                // 结束对话
                this.isActive = false;
                
                return {
                    success: true,
                    data: response.data
                };
            }
            
            return {
                success: false,
                errors: [response.message || '完成任务创建失败']
            };
            
        } catch (error) {
            console.error('完成任务创建失败:', error);
            return {
                success: false,
                errors: ['完成任务创建时发生错误']
            };
        }
    }
    
    /**
     * 重置对话状态
     * @private
     */
    _resetState() {
        this.conversationId = null;
        this.messages = [];
        this.taskContext = {
            title: '',
            description: '',
            requirements: [],
            constraints: [],
            complexity: 0,
            estimatedDuration: 0,
            priority: 2,
            type: 'general'
        };
        this.currentPhase = 'initial';
        this.progress = 0;
        this.canDecompose = false;
        this.decompositionResult = null;
        this.isActive = false;
    }
    
    /**
     * 添加消息
     * @private
     */
    _addMessage(type, content, metadata = {}) {
        const message = {
            id: this._generateMessageId(),
            type,
            content,
            timestamp: new Date().toISOString(),
            metadata
        };
        
        this.messages.push(message);
        
        // 触发消息添加事件
        this._notifyHandlers('message_added', { message });
        
        return message;
    }
    
    /**
     * 生成消息ID
     * @private
     */
    _generateMessageId() {
        return 'msg_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
    }
    
    /**
     * 通知事件处理器
     * @private
     */
    _notifyHandlers(eventType, data) {
        this.messageHandlers.forEach(handler => {
            try {
                handler(eventType, data);
            } catch (error) {
                console.error('消息处理器执行失败:', error);
            }
        });
    }
    
    /**
     * 注册消息处理器
     * @param {Function} handler 处理器函数
     */
    onMessage(handler) {
        if (typeof handler === 'function') {
            this.messageHandlers.add(handler);
        }
    }
    
    /**
     * 移除消息处理器
     * @param {Function} handler 处理器函数
     */
    offMessage(handler) {
        this.messageHandlers.delete(handler);
    }
    
    /**
     * 获取当前对话状态
     * @returns {Object} 对话状态
     */
    getConversationState() {
        return {
            conversationId: this.conversationId,
            isActive: this.isActive,
            currentPhase: this.currentPhase,
            phaseInfo: this.phases[this.currentPhase],
            progress: this.progress,
            taskContext: { ...this.taskContext },
            canDecompose: this.canDecompose,
            decompositionResult: this.decompositionResult,
            messageCount: this.messages.length,
            lastMessageTime: this.messages.length > 0 ? 
                this.messages[this.messages.length - 1].timestamp : null
        };
    }
    
    /**
     * 获取所有消息
     * @returns {Array} 消息列表
     */
    getMessages() {
        return this.messages.map(message => ({
            ...message,
            typeInfo: this.messageTypes[message.type] || this.messageTypes.system
        }));
    }
    
    /**
     * 获取任务上下文
     * @returns {Object} 任务上下文
     */
    getTaskContext() {
        return { ...this.taskContext };
    }
    
    /**
     * 更新任务上下文
     * @param {Object} contextUpdate 上下文更新
     */
    updateTaskContext(contextUpdate) {
        this.taskContext = { ...this.taskContext, ...contextUpdate };
        
        // 重新分析复杂度
        if (contextUpdate.title || contextUpdate.description || contextUpdate.requirements) {
            this.analyzeComplexity();
        }
        
        // 触发上下文更新事件
        this._notifyHandlers('context_updated', {
            taskContext: this.taskContext
        });
    }
    
    /**
     * 获取拆解结果
     * @returns {Object|null} 拆解结果
     */
    getDecompositionResult() {
        return this.decompositionResult ? { ...this.decompositionResult } : null;
    }
    
    /**
     * 更新拆解结果
     * @param {Object} resultUpdate 结果更新
     */
    updateDecompositionResult(resultUpdate) {
        if (this.decompositionResult) {
            this.decompositionResult = { ...this.decompositionResult, ...resultUpdate };
            
            // 触发拆解结果更新事件
            this._notifyHandlers('decomposition_updated', {
                decompositionResult: this.decompositionResult
            });
        }
    }
    
    /**
     * 重新开始对话
     * @returns {Promise<Object>} 重新开始结果
     */
    async restartConversation() {
        try {
            if (this.isActive && this.conversationId) {
                // 结束当前对话
                await this.endConversation();
            }
            
            // 重置状态
            this._resetState();
            
            // 触发重新开始事件
            this._notifyHandlers('conversation_restarted', {});
            
            return { success: true };
            
        } catch (error) {
            console.error('重新开始对话失败:', error);
            return {
                success: false,
                errors: ['重新开始对话时发生错误']
            };
        }
    }
    
    /**
     * 结束对话
     * @returns {Promise<Object>} 结束结果
     */
    async endConversation() {
        try {
            if (this.isActive && this.conversationId && window.apiClient) {
                // 通知后端结束对话
                await window.apiClient.post(
                    `/api/v1/meta-agent/conversations/${this.conversationId}/end`
                );
            }
            
            // 重置状态
            this._resetState();
            
            // 触发对话结束事件
            this._notifyHandlers('conversation_ended', {});
            
            return { success: true };
            
        } catch (error) {
            console.error('结束对话失败:', error);
            return {
                success: false,
                errors: ['结束对话时发生错误']
            };
        }
    }
    
    /**
     * 导出对话记录
     * @returns {Object} 对话记录
     */
    exportConversation() {
        return {
            conversationId: this.conversationId,
            taskContext: this.taskContext,
            messages: this.messages,
            decompositionResult: this.decompositionResult,
            phases: Object.keys(this.phases).map(phase => ({
                phase,
                ...this.phases[phase],
                completed: this.phases[phase].progress <= this.progress
            })),
            exportTime: new Date().toISOString()
        };
    }
    
    /**
     * 导入对话记录
     * @param {Object} conversationData 对话数据
     * @returns {Object} 导入结果
     */
    importConversation(conversationData) {
        try {
            this._resetState();
            
            this.conversationId = conversationData.conversationId;
            this.taskContext = conversationData.taskContext || {};
            this.messages = conversationData.messages || [];
            this.decompositionResult = conversationData.decompositionResult;
            
            // 根据消息数量估算当前阶段
            const messageCount = this.messages.length;
            if (messageCount === 0) {
                this.currentPhase = 'initial';
            } else if (messageCount < 5) {
                this.currentPhase = 'collecting';
            } else if (messageCount < 10) {
                this.currentPhase = 'analyzing';
            } else if (this.decompositionResult) {
                this.currentPhase = 'decomposing';
            } else {
                this.currentPhase = 'refining';
            }
            
            this.progress = this.phases[this.currentPhase].progress;
            this.isActive = true;
            
            // 触发导入完成事件
            this._notifyHandlers('conversation_imported', {
                conversationId: this.conversationId,
                messageCount: this.messages.length
            });
            
            return { success: true };
            
        } catch (error) {
            console.error('导入对话记录失败:', error);
            return {
                success: false,
                errors: ['导入对话记录时发生错误']
            };
        }
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MetaAgentChatManager;
} else {
    window.MetaAgentChatManager = MetaAgentChatManager;
}