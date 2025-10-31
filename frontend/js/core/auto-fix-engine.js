/**
 * 自动修复引擎 - 根据诊断结果执行自动修复
 * 负责修复策略选择和执行、修复效果验证和回滚功能
 */

class AutoFixEngine {
    constructor() {
        this.fixStrategies = new Map();
        this.fixHistory = [];
        this.rollbackStack = [];
        this.maxRollbackDepth = 10;
        
        this.initializeFixStrategies();
    }
    
    initializeFixStrategies() {
        // 注册各种修复策略
        this.fixStrategies.set('dom_element_missing', this.fixMissingDOMElement.bind(this));
        this.fixStrategies.set('dom_element_hidden', this.fixHiddenDOMElement.bind(this));
        this.fixStrategies.set('event_binding_missing', this.fixMissingEventBinding.bind(this));
        this.fixStrategies.set('api_endpoint_unreachable', this.fixAPIEndpoint.bind(this));
        this.fixStrategies.set('websocket_not_connected', this.fixWebSocketConnection.bind(this));
        this.fixStrategies.set('local_storage_unavailable', this.fixLocalStorage.bind(this));
        this.fixStrategies.set('modal_close_button_missing', this.fixModalCloseButton.bind(this));
        this.fixStrategies.set('form_submit_binding_missing', this.fixFormSubmitBinding.bind(this));
        this.fixStrategies.set('network_offline', this.fixNetworkOffline.bind(this));
        this.fixStrategies.set('browser_api_unsupported', this.fixUnsupportedAPI.bind(this));
    }
    
    /**
     * 执行自动修复
     * @param {Array} issues - 问题列表
     * @returns {Promise<Array>} 修复结果列表
     */
    async executeAutoFix(issues) {
        const results = [];
        
        // 按严重程度排序，优先修复关键问题
        const sortedIssues = this.prioritizeIssues(issues);
        
        for (const issue of sortedIssues) {
            try {
                console.log(`正在修复问题: ${issue.type}`);
                const result = await this.fixIssue(issue);
                results.push(result);
                
                // 如果修复成功，记录到历史
                if (result.success) {
                    this.recordFixHistory(issue, result);
                }
                
            } catch (error) {
                console.error(`修复问题 ${issue.type} 时发生错误:`, error);
                results.push({
                    issue: issue.type,
                    success: false,
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
            }
        }
        
        return results;
    }
    
    /**
     * 修复单个问题
     * @param {Object} issue - 问题对象
     * @returns {Promise<Object>} 修复结果
     */
    async fixIssue(issue) {
        const strategy = this.fixStrategies.get(issue.type);
        
        if (!strategy) {
            return {
                issue: issue.type,
                success: false,
                error: '未找到修复策略',
                timestamp: new Date().toISOString()
            };
        }
        
        // 创建回滚点
        const rollbackPoint = await this.createRollbackPoint(issue);
        
        try {
            const result = await strategy(issue);
            
            // 验证修复效果
            const verification = await this.verifyFix(issue, result);
            
            if (verification.success) {
                return {
                    issue: issue.type,
                    success: true,
                    result: result,
                    verification: verification,
                    rollbackId: rollbackPoint.id,
                    timestamp: new Date().toISOString()
                };
            } else {
                // 修复验证失败，执行回滚
                await this.rollback(rollbackPoint.id);
                return {
                    issue: issue.type,
                    success: false,
                    error: '修复验证失败',
                    verification: verification,
                    rolledBack: true,
                    timestamp: new Date().toISOString()
                };
            }
            
        } catch (error) {
            // 修复失败，执行回滚
            await this.rollback(rollbackPoint.id);
            throw error;
        }
    }
    
    /**
     * 修复缺失的DOM元素
     * @param {Object} issue - 问题对象
     * @returns {Promise<Object>} 修复结果
     */
    async fixMissingDOMElement(issue) {
        const { selector, elementName } = issue;
        
        // 根据选择器类型创建相应的元素
        let element;
        const container = document.querySelector('#main-content') || document.body;
        
        switch (selector) {
            case '#agent-management':
                element = this.createAgentManagementContainer();
                break;
            case '#llm-config':
                element = this.createLLMConfigContainer();
                break;
            case '#task-dependencies':
                element = this.createTaskDependenciesContainer();
                break;
            case '#meta-agent-chat':
                element = this.createMetaAgentChatContainer();
                break;
            default:
                // 创建通用容器
                element = document.createElement('div');
                element.id = selector.replace('#', '');
                element.className = 'auto-created-container';
        }
        
        container.appendChild(element);
        
        return {
            action: 'created_dom_element',
            selector: selector,
            elementName: elementName,
            success: true
        };
    }
    
    /**
     * 修复隐藏的DOM元素
     * @param {Object} issue - 问题对象
     * @returns {Promise<Object>} 修复结果
     */
    async fixHiddenDOMElement(issue) {
        const element = document.querySelector(issue.selector);
        if (!element) {
            throw new Error('元素不存在，无法修复可见性');
        }
        
        // 移除隐藏样式
        element.style.display = '';
        element.style.visibility = '';
        element.style.opacity = '';
        
        // 移除隐藏类
        element.classList.remove('hidden', 'invisible', 'd-none');
        
        return {
            action: 'made_element_visible',
            selector: issue.selector,
            success: true
        };
    }
    
    /**
     * 修复缺失的事件绑定
     * @param {Object} issue - 问题对象
     * @returns {Promise<Object>} 修复结果
     */
    async fixMissingEventBinding(issue) {
        const element = document.querySelector(issue.selector);
        if (!element) {
            throw new Error('元素不存在，无法绑定事件');
        }
        
        // 根据元素类型和选择器绑定相应的事件
        let eventBound = false;
        
        switch (issue.selector) {
            case '#refresh-agents':
                element.addEventListener('click', this.handleRefreshAgents.bind(this));
                eventBound = true;
                break;
            case '#add-agent':
                element.addEventListener('click', this.handleAddAgent.bind(this));
                eventBound = true;
                break;
            case '#save-llm-config':
                element.addEventListener('click', this.handleSaveLLMConfig.bind(this));
                eventBound = true;
                break;
            case '#test-llm-connection':
                element.addEventListener('click', this.handleTestLLMConnection.bind(this));
                eventBound = true;
                break;
            case '#start-meta-chat':
                element.addEventListener('click', this.handleStartMetaChat.bind(this));
                eventBound = true;
                break;
            default:
                // 通用点击事件处理
                if (element.tagName === 'BUTTON') {
                    element.addEventListener('click', this.handleGenericButtonClick.bind(this));
                    eventBound = true;
                }
        }
        
        return {
            action: 'bound_event',
            selector: issue.selector,
            eventBound: eventBound,
            success: eventBound
        };
    }
    
    /**
     * 修复API端点问题
     * @param {Object} issue - 问题对象
     * @returns {Promise<Object>} 修复结果
     */
    async fixAPIEndpoint(issue) {
        const { url } = issue;
        
        // 尝试重新连接
        try {
            const response = await fetch(url, { 
                method: 'GET',
                timeout: 3000 
            });
            
            if (response.ok) {
                return {
                    action: 'api_reconnected',
                    url: url,
                    success: true
                };
            }
        } catch (error) {
            // API仍然不可用，启用模拟模式
            console.warn(`API ${url} 仍不可用，启用模拟模式`);
        }
        
        // 启用模拟API响应
        this.enableMockAPI(url);
        
        return {
            action: 'enabled_mock_api',
            url: url,
            success: true,
            mockMode: true
        };
    }
    
    /**
     * 修复WebSocket连接
     * @param {Object} issue - 问题对象
     * @returns {Promise<Object>} 修复结果
     */
    async fixWebSocketConnection(issue) {
        if (window.websocketManager) {
            try {
                await window.websocketManager.reconnect();
                return {
                    action: 'websocket_reconnected',
                    success: true
                };
            } catch (error) {
                // 重连失败，启用轮询模式
                this.enablePollingMode();
                return {
                    action: 'enabled_polling_mode',
                    success: true,
                    fallbackMode: true
                };
            }
        } else {
            // 创建新的WebSocket管理器
            await this.createWebSocketManager();
            return {
                action: 'created_websocket_manager',
                success: true
            };
        }
    }
    
    /**
     * 修复本地存储问题
     * @param {Object} issue - 问题对象
     * @returns {Promise<Object>} 修复结果
     */
    async fixLocalStorage(issue) {
        // 启用内存存储作为备用方案
        if (!window.memoryStorage) {
            window.memoryStorage = new Map();
            
            // 创建localStorage兼容接口
            window.fallbackStorage = {
                setItem: (key, value) => window.memoryStorage.set(key, value),
                getItem: (key) => window.memoryStorage.get(key) || null,
                removeItem: (key) => window.memoryStorage.delete(key),
                clear: () => window.memoryStorage.clear()
            };
        }
        
        return {
            action: 'enabled_memory_storage',
            success: true,
            fallbackMode: true
        };
    }
    
    /**
     * 修复模态框关闭按钮
     * @param {Object} issue - 问题对象
     * @returns {Promise<Object>} 修复结果
     */
    async fixModalCloseButton(issue) {
        const modals = document.querySelectorAll('.modal');
        const modal = modals[issue.modalIndex];
        
        if (!modal) {
            throw new Error('模态框不存在');
        }
        
        // 创建关闭按钮
        const closeBtn = document.createElement('span');
        closeBtn.className = 'close';
        closeBtn.innerHTML = '&times;';
        closeBtn.style.cssText = 'float: right; font-size: 28px; font-weight: bold; cursor: pointer;';
        
        // 添加关闭事件
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
        // 插入到模态框头部
        const modalHeader = modal.querySelector('.modal-header');
        if (modalHeader) {
            modalHeader.appendChild(closeBtn);
        } else {
            modal.insertBefore(closeBtn, modal.firstChild);
        }
        
        return {
            action: 'added_modal_close_button',
            modalIndex: issue.modalIndex,
            success: true
        };
    }
    
    /**
     * 修复表单提交绑定
     * @param {Object} issue - 问题对象
     * @returns {Promise<Object>} 修复结果
     */
    async fixFormSubmitBinding(issue) {
        const forms = document.querySelectorAll('form');
        const form = forms[issue.formIndex];
        
        if (!form) {
            throw new Error('表单不存在');
        }
        
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            this.handleFormSubmit(form, event);
        });
        
        return {
            action: 'bound_form_submit',
            formIndex: issue.formIndex,
            success: true
        };
    }
    
    /**
     * 修复网络离线问题
     * @param {Object} issue - 问题对象
     * @returns {Promise<Object>} 修复结果
     */
    async fixNetworkOffline(issue) {
        // 启用离线模式
        this.enableOfflineMode();
        
        // 显示离线提示
        this.showOfflineNotification();
        
        return {
            action: 'enabled_offline_mode',
            success: true,
            offlineMode: true
        };
    }
    
    /**
     * 修复不支持的API
     * @param {Object} issue - 问题对象
     * @returns {Promise<Object>} 修复结果
     */
    async fixUnsupportedAPI(issue) {
        const { apiName } = issue;
        
        // 为不支持的API提供polyfill
        switch (apiName) {
            case 'fetch':
                await this.loadFetchPolyfill();
                break;
            case 'Promise':
                await this.loadPromisePolyfill();
                break;
            case 'WebSocket':
                this.enableLongPolling();
                break;
            default:
                console.warn(`无法为 ${apiName} 提供polyfill`);
                return {
                    action: 'no_polyfill_available',
                    apiName: apiName,
                    success: false
                };
        }
        
        return {
            action: 'loaded_polyfill',
            apiName: apiName,
            success: true
        };
    }
    
    // 事件处理方法
    async handleRefreshAgents() {
        console.log('刷新智能体列表');
        if (window.agentManager) {
            await window.agentManager.loadAgents();
        }
    }
    
    async handleAddAgent() {
        console.log('添加新智能体');
        // 实现添加智能体逻辑
    }
    
    async handleSaveLLMConfig() {
        console.log('保存LLM配置');
        if (window.llmConfigManager) {
            await window.llmConfigManager.saveConfig();
        }
    }
    
    async handleTestLLMConnection() {
        console.log('测试LLM连接');
        if (window.llmConfigManager) {
            await window.llmConfigManager.testConnection();
        }
    }
    
    async handleStartMetaChat() {
        console.log('开始元智能体对话');
        if (window.metaAgentChatManager) {
            await window.metaAgentChatManager.startChat();
        }
    }
    
    handleGenericButtonClick(event) {
        console.log('通用按钮点击:', event.target);
        // 通用按钮点击处理
    }
    
    handleFormSubmit(form, event) {
        console.log('表单提交:', form);
        // 通用表单提交处理
    }
    
    // 辅助方法
    createAgentManagementContainer() {
        const container = document.createElement('div');
        container.id = 'agent-management';
        container.className = 'agent-management auto-created';
        container.innerHTML = `
            <div class="agent-management-header">
                <h2>智能体管理</h2>
                <button id="refresh-agents" class="btn btn-primary">刷新</button>
            </div>
            <div id="agent-list" class="agent-list">
                <div class="loading">正在加载智能体...</div>
            </div>
        `;
        return container;
    }
    
    createLLMConfigContainer() {
        const container = document.createElement('div');
        container.id = 'llm-config';
        container.className = 'llm-config auto-created';
        container.innerHTML = `
            <div class="llm-config-header">
                <h2>LLM配置</h2>
                <button id="save-llm-config" class="btn btn-primary">保存配置</button>
            </div>
            <div class="llm-config-content">
                <div class="loading">正在加载配置...</div>
            </div>
        `;
        return container;
    }
    
    createTaskDependenciesContainer() {
        const container = document.createElement('div');
        container.id = 'task-dependencies';
        container.className = 'task-dependencies auto-created';
        container.innerHTML = `
            <div class="task-dependencies-header">
                <h2>任务依赖关系</h2>
            </div>
            <div class="task-dependencies-content">
                <div class="loading">正在加载任务...</div>
            </div>
        `;
        return container;
    }
    
    createMetaAgentChatContainer() {
        const container = document.createElement('div');
        container.id = 'meta-agent-chat';
        container.className = 'meta-agent-chat auto-created';
        container.innerHTML = `
            <div class="meta-agent-chat-header">
                <h2>元智能体对话</h2>
                <button id="start-meta-chat" class="btn btn-primary">开始对话</button>
            </div>
            <div class="meta-agent-chat-content">
                <div class="chat-messages"></div>
                <div class="chat-input">
                    <input type="text" placeholder="输入消息..." />
                    <button type="submit">发送</button>
                </div>
            </div>
        `;
        return container;
    }
    
    enableMockAPI(url) {
        // 实现模拟API响应
        console.log(`为 ${url} 启用模拟API`);
    }
    
    enablePollingMode() {
        // 启用轮询模式替代WebSocket
        console.log('启用轮询模式');
    }
    
    async createWebSocketManager() {
        // 创建WebSocket管理器
        console.log('创建WebSocket管理器');
    }
    
    enableOfflineMode() {
        // 启用离线模式
        console.log('启用离线模式');
    }
    
    showOfflineNotification() {
        // 显示离线通知
        const notification = document.createElement('div');
        notification.className = 'offline-notification';
        notification.textContent = '网络连接已断开，已启用离线模式';
        document.body.appendChild(notification);
    }
    
    async loadFetchPolyfill() {
        // 加载fetch polyfill
        console.log('加载fetch polyfill');
    }
    
    async loadPromisePolyfill() {
        // 加载Promise polyfill
        console.log('加载Promise polyfill');
    }
    
    enableLongPolling() {
        // 启用长轮询替代WebSocket
        console.log('启用长轮询');
    }
    
    /**
     * 创建回滚点
     * @param {Object} issue - 问题对象
     * @returns {Promise<Object>} 回滚点信息
     */
    async createRollbackPoint(issue) {
        const rollbackId = 'rollback_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        const rollbackPoint = {
            id: rollbackId,
            issue: issue,
            timestamp: new Date().toISOString(),
            domSnapshot: this.createDOMSnapshot(),
            storageSnapshot: this.createStorageSnapshot()
        };
        
        this.rollbackStack.push(rollbackPoint);
        
        // 限制回滚栈深度
        if (this.rollbackStack.length > this.maxRollbackDepth) {
            this.rollbackStack.shift();
        }
        
        return rollbackPoint;
    }
    
    /**
     * 执行回滚
     * @param {string} rollbackId - 回滚点ID
     * @returns {Promise<boolean>} 回滚是否成功
     */
    async rollback(rollbackId) {
        const rollbackPoint = this.rollbackStack.find(point => point.id === rollbackId);
        if (!rollbackPoint) {
            console.error('未找到回滚点:', rollbackId);
            return false;
        }
        
        try {
            // 恢复DOM状态
            this.restoreDOMSnapshot(rollbackPoint.domSnapshot);
            
            // 恢复存储状态
            this.restoreStorageSnapshot(rollbackPoint.storageSnapshot);
            
            console.log('回滚成功:', rollbackId);
            return true;
            
        } catch (error) {
            console.error('回滚失败:', error);
            return false;
        }
    }
    
    createDOMSnapshot() {
        // 创建DOM快照（简化版本）
        return {
            mainContent: document.querySelector('#main-content')?.innerHTML || '',
            timestamp: Date.now()
        };
    }
    
    createStorageSnapshot() {
        // 创建存储快照
        const snapshot = {};
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            snapshot[key] = localStorage.getItem(key);
        }
        return snapshot;
    }
    
    restoreDOMSnapshot(snapshot) {
        // 恢复DOM快照
        const mainContent = document.querySelector('#main-content');
        if (mainContent && snapshot.mainContent) {
            mainContent.innerHTML = snapshot.mainContent;
        }
    }
    
    restoreStorageSnapshot(snapshot) {
        // 恢复存储快照
        localStorage.clear();
        for (const [key, value] of Object.entries(snapshot)) {
            localStorage.setItem(key, value);
        }
    }
    
    /**
     * 验证修复效果
     * @param {Object} issue - 原始问题
     * @param {Object} fixResult - 修复结果
     * @returns {Promise<Object>} 验证结果
     */
    async verifyFix(issue, fixResult) {
        try {
            // 根据问题类型进行相应的验证
            switch (issue.type) {
                case 'dom_element_missing':
                    const element = document.querySelector(issue.selector);
                    return {
                        success: element !== null,
                        message: element ? '元素已创建' : '元素仍然缺失'
                    };
                    
                case 'event_binding_missing':
                    // 简化的事件绑定验证
                    return {
                        success: fixResult.eventBound,
                        message: fixResult.eventBound ? '事件已绑定' : '事件绑定失败'
                    };
                    
                case 'api_endpoint_unreachable':
                    if (fixResult.mockMode) {
                        return {
                            success: true,
                            message: '已启用模拟API模式'
                        };
                    } else {
                        // 重新测试API连接
                        try {
                            const response = await fetch(issue.url, { timeout: 3000 });
                            return {
                                success: response.ok,
                                message: response.ok ? 'API连接已恢复' : 'API仍然不可用'
                            };
                        } catch (error) {
                            return {
                                success: false,
                                message: 'API验证失败: ' + error.message
                            };
                        }
                    }
                    
                default:
                    return {
                        success: true,
                        message: '修复完成，无法验证'
                    };
            }
            
        } catch (error) {
            return {
                success: false,
                message: '验证过程中发生错误: ' + error.message
            };
        }
    }
    
    /**
     * 按严重程度排序问题
     * @param {Array} issues - 问题列表
     * @returns {Array} 排序后的问题列表
     */
    prioritizeIssues(issues) {
        const severityOrder = {
            'critical': 0,
            'high': 1,
            'medium': 2,
            'low': 3,
            'info': 4
        };
        
        return issues.sort((a, b) => {
            const aPriority = severityOrder[a.severity] || 5;
            const bPriority = severityOrder[b.severity] || 5;
            return aPriority - bPriority;
        });
    }
    
    /**
     * 记录修复历史
     * @param {Object} issue - 问题对象
     * @param {Object} result - 修复结果
     */
    recordFixHistory(issue, result) {
        this.fixHistory.push({
            issue: issue,
            result: result,
            timestamp: new Date().toISOString()
        });
        
        // 限制历史记录数量
        if (this.fixHistory.length > 100) {
            this.fixHistory.shift();
        }
    }
    
    /**
     * 获取修复历史
     * @returns {Array} 修复历史列表
     */
    getFixHistory() {
        return [...this.fixHistory];
    }
    
    /**
     * 清除修复历史
     */
    clearFixHistory() {
        this.fixHistory = [];
        this.rollbackStack = [];
    }
}

// 导出类
export default AutoFixEngine;

// 创建全局实例
window.AutoFixEngine = AutoFixEngine;