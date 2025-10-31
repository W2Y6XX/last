# MVP2前端集成指南

## 概述

本文档详细说明如何将MVP2前端与LangGraph多智能体系统进行集成，包括API对接、数据格式转换、实时通信和错误处理等方面。

## 集成架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   MVP2前端      │    │   适配层         │    │  LangGraph后端      │
│                 │    │                  │    │                     │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────────┐ │
│ │ 任务管理    │ │◄──►│ │ 数据转换器   │ │◄──►│ │ 多智能体工作流  │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────────┘ │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────────┐ │
│ │ 聊天系统    │ │◄──►│ │ 状态同步器   │ │◄──►│ │ 状态管理        │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────────┘ │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────────┐ │
│ │ 数据分析    │ │◄──►│ │ 错误处理器   │ │◄──►│ │ 错误恢复        │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────────┘ │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
```

## API接口对接

### 1. 基础配置

在MVP2前端中配置API基础地址：

```javascript
// config.js
const API_CONFIG = {
    BASE_URL: 'http://localhost:8000/api/v1/mvp2',
    WS_URL: 'ws://localhost:8000/api/v1/mvp2/ws',
    TIMEOUT: 30000,
    RETRY_ATTEMPTS: 3
};
```

### 2. API客户端封装

```javascript
// api-client.js
class MVP2ApiClient {
    constructor(config) {
        this.baseURL = config.BASE_URL;
        this.timeout = config.TIMEOUT;
        this.retryAttempts = config.RETRY_ATTEMPTS;
    }

    async request(method, endpoint, data = null, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            method,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            timeout: this.timeout,
            ...options
        };

        if (data) {
            config.body = JSON.stringify(data);
        }

        let lastError;
        for (let attempt = 0; attempt < this.retryAttempts; attempt++) {
            try {
                const response = await fetch(url, config);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();
                return result;
            } catch (error) {
                lastError = error;
                if (attempt < this.retryAttempts - 1) {
                    await this.delay(1000 * Math.pow(2, attempt)); // 指数退避
                }
            }
        }

        throw lastError;
    }

    async delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // 任务管理API
    async createTask(taskData) {
        return this.request('POST', '/tasks', taskData);
    }

    async getTasks(filters = {}) {
        const params = new URLSearchParams(filters);
        return this.request('GET', `/tasks?${params}`);
    }

    async updateTask(taskId, updates) {
        return this.request('PUT', `/tasks/${taskId}`, updates);
    }

    async deleteTask(taskId) {
        return this.request('DELETE', `/tasks/${taskId}`);
    }

    async getTaskStats() {
        return this.request('GET', '/tasks/stats');
    }

    // 聊天API
    async sendMessage(messageData) {
        return this.request('POST', '/chat/messages', messageData);
    }

    async getChatHistory(options = {}) {
        const params = new URLSearchParams(options);
        return this.request('GET', `/chat/history?${params}`);
    }

    // 数据分析API
    async getDashboard() {
        return this.request('GET', '/analytics/dashboard');
    }

    // 系统API
    async getSystemStatus() {
        return this.request('GET', '/status');
    }

    async submitFeedback(feedbackData) {
        return this.request('POST', '/feedback', feedbackData);
    }

    async exportData() {
        return this.request('GET', '/export');
    }

    async importData(data) {
        return this.request('POST', '/import', data);
    }
}

// 创建全局API客户端实例
const apiClient = new MVP2ApiClient(API_CONFIG);
```

### 3. 数据管理器集成

修改现有的DataManager类以使用API：

```javascript
// data-manager.js
class EnhancedDataManager extends DataManager {
    constructor() {
        super();
        this.apiClient = apiClient;
        this.syncEnabled = true;
        this.offlineMode = false;
    }

    // 重写任务管理方法
    async addTask(task) {
        try {
            if (this.offlineMode) {
                return super.addTask(task);
            }

            const response = await this.apiClient.createTask(task);
            if (response.success) {
                // 同步到本地存储
                const localTasks = this.getTasks();
                localTasks.unshift(response.data);
                this.saveTasks(localTasks);
                
                return true;
            }
        } catch (error) {
            console.error('创建任务失败，切换到离线模式:', error);
            this.offlineMode = true;
            return super.addTask(task);
        }
    }

    async getTasks() {
        try {
            if (this.offlineMode) {
                return super.getTasks();
            }

            const response = await this.apiClient.getTasks();
            if (response.success) {
                // 更新本地缓存
                this.saveTasks(response.data.tasks);
                return response.data.tasks;
            }
        } catch (error) {
            console.error('获取任务失败，使用本地缓存:', error);
            return super.getTasks();
        }
    }

    async updateTask(taskId, updates) {
        try {
            if (this.offlineMode) {
                return super.updateTask(taskId, updates);
            }

            const response = await this.apiClient.updateTask(taskId, updates);
            if (response.success) {
                // 同步到本地存储
                const localTasks = this.getTasks();
                const index = localTasks.findIndex(task => task.id === taskId);
                if (index !== -1) {
                    localTasks[index] = { ...localTasks[index], ...updates };
                    this.saveTasks(localTasks);
                }
                return true;
            }
        } catch (error) {
            console.error('更新任务失败:', error);
            return super.updateTask(taskId, updates);
        }
    }

    async deleteTask(taskId) {
        try {
            if (this.offlineMode) {
                return super.deleteTask(taskId);
            }

            const response = await this.apiClient.deleteTask(taskId);
            if (response.success) {
                // 从本地存储删除
                const localTasks = this.getTasks();
                const filteredTasks = localTasks.filter(task => task.id !== taskId);
                this.saveTasks(filteredTasks);
                return true;
            }
        } catch (error) {
            console.error('删除任务失败:', error);
            return super.deleteTask(taskId);
        }
    }

    // 聊天消息管理
    async addChatMessage(message) {
        try {
            if (message.type === 'user') {
                const response = await this.apiClient.sendMessage({
                    content: message.content,
                    type: 'user'
                });

                if (response.success) {
                    // 保存用户消息和AI回复
                    super.addChatMessage(response.data.user_message);
                    super.addChatMessage(response.data.ai_response);
                    return true;
                }
            }
        } catch (error) {
            console.error('发送消息失败:', error);
            return super.addChatMessage(message);
        }
    }

    // 数据同步
    async syncData() {
        if (!this.syncEnabled || this.offlineMode) {
            return;
        }

        try {
            // 同步任务数据
            await this.getTasks();
            
            // 同步聊天历史
            const chatResponse = await this.apiClient.getChatHistory();
            if (chatResponse.success) {
                this.saveChatHistory(chatResponse.data.messages);
            }

            // 重新上线
            this.offlineMode = false;
            console.log('数据同步完成');
        } catch (error) {
            console.error('数据同步失败:', error);
        }
    }

    // 启用自动同步
    startAutoSync(interval = 30000) {
        setInterval(() => {
            this.syncData();
        }, interval);
    }
}

// 替换全局数据管理器
window.dataManager = new EnhancedDataManager();
```

## WebSocket实时通信

### 1. WebSocket客户端

```javascript
// websocket-client.js
class MVP2WebSocketClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 1000;
        this.messageHandlers = new Map();
        this.isConnected = false;
    }

    connect() {
        try {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('WebSocket连接已建立');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.onConnected();
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('解析WebSocket消息失败:', error);
                }
            };

            this.ws.onclose = () => {
                console.log('WebSocket连接已关闭');
                this.isConnected = false;
                this.onDisconnected();
                this.attemptReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket错误:', error);
                this.onError(error);
            };
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.attemptReconnect();
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    send(message) {
        if (this.isConnected && this.ws) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket未连接，消息发送失败');
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1));
        } else {
            console.error('WebSocket重连失败，已达到最大重试次数');
        }
    }

    handleMessage(message) {
        const handler = this.messageHandlers.get(message.type);
        if (handler) {
            handler(message);
        } else {
            console.log('收到未处理的消息类型:', message.type, message);
        }
    }

    onMessage(type, handler) {
        this.messageHandlers.set(type, handler);
    }

    onConnected() {
        // 订阅所需的事件
        this.send({ type: 'task_subscribe' });
        this.send({ type: 'chat_subscribe' });
        this.send({ type: 'agent_subscribe' });
    }

    onDisconnected() {
        // 连接断开处理
    }

    onError(error) {
        // 错误处理
    }

    // 发送心跳
    sendHeartbeat() {
        this.send({ type: 'ping', timestamp: new Date().toISOString() });
    }

    startHeartbeat(interval = 30000) {
        setInterval(() => {
            if (this.isConnected) {
                this.sendHeartbeat();
            }
        }, interval);
    }
}

// 创建WebSocket客户端实例
const wsClient = new MVP2WebSocketClient(API_CONFIG.WS_URL);
```

### 2. 实时事件处理

```javascript
// real-time-handler.js
class RealTimeHandler {
    constructor(wsClient, dataManager) {
        this.wsClient = wsClient;
        this.dataManager = dataManager;
        this.setupEventHandlers();
    }

    setupEventHandlers() {
        // 任务更新事件
        this.wsClient.onMessage('task_update', (message) => {
            this.handleTaskUpdate(message.data);
        });

        this.wsClient.onMessage('task_created', (message) => {
            this.handleTaskCreated(message.data);
        });

        this.wsClient.onMessage('task_completed', (message) => {
            this.handleTaskCompleted(message.data);
        });

        // 聊天消息事件
        this.wsClient.onMessage('chat_message', (message) => {
            this.handleChatMessage(message.data);
        });

        // 智能体状态事件
        this.wsClient.onMessage('agent_status', (message) => {
            this.handleAgentStatus(message.data);
        });

        // 系统通知事件
        this.wsClient.onMessage('system_notification', (message) => {
            this.handleSystemNotification(message);
        });

        // 心跳响应
        this.wsClient.onMessage('pong', (message) => {
            console.log('收到心跳响应:', message.timestamp);
        });
    }

    handleTaskUpdate(taskData) {
        // 更新本地任务数据
        const tasks = this.dataManager.getTasks();
        const index = tasks.findIndex(task => task.id === taskData.id);
        
        if (index !== -1) {
            tasks[index] = { ...tasks[index], ...taskData };
            this.dataManager.saveTasks(tasks);
            
            // 更新UI
            this.updateTaskUI(taskData);
            
            // 显示通知
            showNotification(`任务 "${taskData.name}" 已更新`, 'info');
        }
    }

    handleTaskCreated(taskData) {
        // 添加新任务到本地存储
        const tasks = this.dataManager.getTasks();
        tasks.unshift(taskData);
        this.dataManager.saveTasks(tasks);
        
        // 更新UI
        this.addTaskToUI(taskData);
        
        // 显示通知
        showNotification(`新任务 "${taskData.name}" 已创建`, 'success');
    }

    handleTaskCompleted(taskData) {
        // 更新任务状态
        this.handleTaskUpdate({ ...taskData, status: 'completed' });
        
        // 显示完成通知
        showNotification(`任务 "${taskData.name}" 已完成！`, 'success');
        
        // 播放完成音效（如果启用）
        this.playCompletionSound();
    }

    handleChatMessage(chatData) {
        // 添加消息到聊天历史
        this.dataManager.addChatMessage(chatData);
        
        // 更新聊天UI
        this.addChatMessageToUI(chatData);
        
        // 滚动到最新消息
        this.scrollChatToBottom();
    }

    handleAgentStatus(agentData) {
        // 更新智能体状态显示
        this.updateAgentStatusUI(agentData);
        
        console.log('智能体状态更新:', agentData);
    }

    handleSystemNotification(notification) {
        // 显示系统通知
        showNotification(notification.message, notification.level || 'info');
        
        console.log('系统通知:', notification);
    }

    // UI更新方法
    updateTaskUI(taskData) {
        const taskCard = document.querySelector(`[data-task-id="${taskData.id}"]`);
        if (taskCard) {
            // 更新任务卡片内容
            const titleElement = taskCard.querySelector('h3');
            if (titleElement) {
                titleElement.textContent = taskData.name;
            }
            
            const progressElement = taskCard.querySelector('.text-center.-mt-10');
            if (progressElement) {
                progressElement.textContent = `${taskData.progress}%`;
            }
            
            // 更新进度环
            const progressRing = taskCard.querySelector('.progress-ring-circle');
            if (progressRing) {
                const circumference = 2 * Math.PI * 54;
                const strokeDashoffset = circumference - (taskData.progress / 100) * circumference;
                progressRing.style.strokeDashoffset = strokeDashoffset;
            }
        }
    }

    addTaskToUI(taskData) {
        // 重新加载任务列表
        if (typeof loadTasks === 'function') {
            loadTasks();
        }
    }

    addChatMessageToUI(chatData) {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            const messageHtml = chatData.type === 'user' ? `
                <div class="chat-bubble" data-message-id="${chatData.timestamp}">
                    <div class="flex items-start justify-end">
                        <div class="glass-morphism p-4 rounded-lg max-w-md mr-3">
                            <p class="text-blue-100">${chatData.content}</p>
                        </div>
                        <div class="w-10 h-10 bg-gradient-to-r from-purple-400 to-purple-600 rounded-full flex items-center justify-center text-white">
                            <i class="fas fa-user"></i>
                        </div>
                    </div>
                </div>
            ` : `
                <div class="chat-bubble" data-message-id="${chatData.timestamp}">
                    <div class="flex items-start">
                        <div class="w-10 h-10 bg-gradient-to-r from-purple-400 to-purple-600 rounded-full flex items-center justify-center text-white mr-3">
                            <i class="fas fa-clock"></i>
                        </div>
                        <div class="glass-morphism p-4 rounded-lg max-w-md">
                            <p class="text-blue-100">${chatData.content}</p>
                        </div>
                    </div>
                </div>
            `;
            
            chatMessages.innerHTML += messageHtml;
            this.scrollChatToBottom();
        }
    }

    scrollChatToBottom() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    updateAgentStatusUI(agentData) {
        // 更新智能体状态显示
        const statusElement = document.querySelector(`[data-agent="${agentData.agent_type}"] .status`);
        if (statusElement) {
            statusElement.textContent = agentData.status;
            statusElement.className = `status ${agentData.status}`;
        }
    }

    playCompletionSound() {
        // 播放任务完成音效
        try {
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT');
            audio.play().catch(e => console.log('音效播放失败:', e));
        } catch (error) {
            console.log('音效播放失败:', error);
        }
    }
}

// 初始化实时处理器
const realTimeHandler = new RealTimeHandler(wsClient, window.dataManager);
```

## 错误处理和用户反馈

### 1. 错误处理

```javascript
// error-handler.js
class MVP2ErrorHandler {
    constructor() {
        this.errorQueue = [];
        this.maxErrors = 100;
    }

    handleError(error, context = '') {
        const errorInfo = {
            id: Date.now().toString(),
            timestamp: new Date().toISOString(),
            message: error.message || '未知错误',
            context: context,
            stack: error.stack,
            userAgent: navigator.userAgent,
            url: window.location.href
        };

        // 添加到错误队列
        this.errorQueue.push(errorInfo);
        if (this.errorQueue.length > this.maxErrors) {
            this.errorQueue.shift();
        }

        // 显示用户友好的错误消息
        this.showUserError(error, context);

        // 发送错误报告
        this.reportError(errorInfo);

        console.error('MVP2错误:', errorInfo);
    }

    showUserError(error, context) {
        let userMessage = '系统遇到问题，请稍后重试';
        let level = 'error';

        // 根据错误类型显示不同消息
        if (error.message.includes('网络') || error.message.includes('fetch')) {
            userMessage = '网络连接异常，请检查网络设置后重试';
        } else if (error.message.includes('验证') || error.message.includes('validation')) {
            userMessage = '输入数据格式不正确，请检查后重新提交';
            level = 'warning';
        } else if (error.message.includes('权限') || error.message.includes('permission')) {
            userMessage = '您没有执行此操作的权限';
        } else if (error.message.includes('超时') || error.message.includes('timeout')) {
            userMessage = '请求处理时间过长，请稍后重试';
        }

        showNotification(userMessage, level);
    }

    async reportError(errorInfo) {
        try {
            await apiClient.submitFeedback({
                type: 'bug_report',
                message: `错误报告: ${errorInfo.message}`,
                context: {
                    error_id: errorInfo.id,
                    timestamp: errorInfo.timestamp,
                    context: errorInfo.context,
                    user_agent: errorInfo.userAgent,
                    url: errorInfo.url
                }
            });
        } catch (reportError) {
            console.error('错误报告发送失败:', reportError);
        }
    }

    getErrorSummary() {
        return {
            total_errors: this.errorQueue.length,
            recent_errors: this.errorQueue.slice(-10),
            error_types: this.getErrorTypes()
        };
    }

    getErrorTypes() {
        const types = {};
        this.errorQueue.forEach(error => {
            const type = error.message.split(':')[0] || 'Unknown';
            types[type] = (types[type] || 0) + 1;
        });
        return types;
    }
}

// 全局错误处理器
const errorHandler = new MVP2ErrorHandler();

// 全局错误捕获
window.addEventListener('error', (event) => {
    errorHandler.handleError(event.error, 'Global Error');
});

window.addEventListener('unhandledrejection', (event) => {
    errorHandler.handleError(new Error(event.reason), 'Unhandled Promise Rejection');
});
```

### 2. 用户反馈系统

```javascript
// feedback-system.js
class FeedbackSystem {
    constructor() {
        this.feedbackModal = null;
        this.createFeedbackModal();
    }

    createFeedbackModal() {
        const modalHtml = `
            <div id="feedbackModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center hidden z-50">
                <div class="glass-morphism rounded-xl p-6 w-full max-w-md text-blue-100">
                    <h3 class="text-xl font-semibold mb-4 flex items-center">
                        <i class="fas fa-comment mr-2 text-purple-300"></i>
                        用户反馈
                    </h3>
                    
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm mb-2">反馈类型</label>
                            <select id="feedbackType" class="w-full bg-white bg-opacity-10 rounded-lg px-3 py-2 focus:outline-none focus:bg-opacity-20 text-blue-100">
                                <option value="bug_report">错误报告</option>
                                <option value="feature_request">功能建议</option>
                                <option value="general">一般反馈</option>
                            </select>
                        </div>
                        
                        <div>
                            <label class="block text-sm mb-2">评分 (1-5星)</label>
                            <div class="flex space-x-1" id="ratingStars">
                                <i class="fas fa-star cursor-pointer text-gray-400 hover:text-yellow-400" data-rating="1"></i>
                                <i class="fas fa-star cursor-pointer text-gray-400 hover:text-yellow-400" data-rating="2"></i>
                                <i class="fas fa-star cursor-pointer text-gray-400 hover:text-yellow-400" data-rating="3"></i>
                                <i class="fas fa-star cursor-pointer text-gray-400 hover:text-yellow-400" data-rating="4"></i>
                                <i class="fas fa-star cursor-pointer text-gray-400 hover:text-yellow-400" data-rating="5"></i>
                            </div>
                        </div>
                        
                        <div>
                            <label class="block text-sm mb-2">详细描述</label>
                            <textarea id="feedbackMessage" class="w-full bg-white bg-opacity-10 rounded-lg px-3 py-2 focus:outline-none focus:bg-opacity-20 text-blue-100" rows="4" placeholder="请描述您的反馈..."></textarea>
                        </div>
                    </div>
                    
                    <div class="flex justify-end space-x-3 mt-6">
                        <button onclick="feedbackSystem.closeFeedbackModal()" class="px-4 py-2 rounded-lg hover:bg-white hover:bg-opacity-10 transition-all">
                            取消
                        </button>
                        <button onclick="feedbackSystem.submitFeedback()" class="px-4 py-2 bg-purple-600 rounded-lg hover:bg-purple-700 transition-all text-white">
                            提交反馈
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        this.feedbackModal = document.getElementById('feedbackModal');
        this.setupRatingStars();
    }

    setupRatingStars() {
        const stars = document.querySelectorAll('#ratingStars i');
        let selectedRating = 0;

        stars.forEach(star => {
            star.addEventListener('click', () => {
                selectedRating = parseInt(star.dataset.rating);
                this.updateStarDisplay(selectedRating);
            });

            star.addEventListener('mouseover', () => {
                const hoverRating = parseInt(star.dataset.rating);
                this.updateStarDisplay(hoverRating, true);
            });
        });

        document.getElementById('ratingStars').addEventListener('mouseleave', () => {
            this.updateStarDisplay(selectedRating);
        });
    }

    updateStarDisplay(rating, isHover = false) {
        const stars = document.querySelectorAll('#ratingStars i');
        stars.forEach((star, index) => {
            if (index < rating) {
                star.className = 'fas fa-star cursor-pointer text-yellow-400';
            } else {
                star.className = 'fas fa-star cursor-pointer text-gray-400 hover:text-yellow-400';
            }
        });
    }

    openFeedbackModal() {
        this.feedbackModal.classList.remove('hidden');
    }

    closeFeedbackModal() {
        this.feedbackModal.classList.add('hidden');
        this.resetForm();
    }

    resetForm() {
        document.getElementById('feedbackType').value = 'general';
        document.getElementById('feedbackMessage').value = '';
        this.updateStarDisplay(0);
    }

    async submitFeedback() {
        const type = document.getElementById('feedbackType').value;
        const message = document.getElementById('feedbackMessage').value.trim();
        const rating = document.querySelectorAll('#ratingStars .text-yellow-400').length;

        if (!message) {
            showNotification('请填写反馈内容', 'warning');
            return;
        }

        try {
            const feedbackData = {
                type: type,
                rating: rating || null,
                message: message,
                context: {
                    page: window.location.pathname,
                    timestamp: new Date().toISOString(),
                    user_agent: navigator.userAgent
                }
            };

            const response = await apiClient.submitFeedback(feedbackData);
            
            if (response.success) {
                showNotification('反馈提交成功，感谢您的宝贵意见！', 'success');
                this.closeFeedbackModal();
            } else {
                throw new Error(response.message || '提交失败');
            }
        } catch (error) {
            errorHandler.handleError(error, 'Feedback Submission');
        }
    }

    // 快速反馈按钮
    addFeedbackButton() {
        const buttonHtml = `
            <button id="feedbackButton" class="fixed bottom-6 right-6 bg-purple-600 hover:bg-purple-700 text-white rounded-full p-3 shadow-lg transition-all z-40" onclick="feedbackSystem.openFeedbackModal()">
                <i class="fas fa-comment text-xl"></i>
            </button>
        `;
        
        document.body.insertAdjacentHTML('beforeend', buttonHtml);
    }
}

// 初始化反馈系统
const feedbackSystem = new FeedbackSystem();
feedbackSystem.addFeedbackButton();
```

## 初始化和启动

### 1. 应用初始化

```javascript
// app-init.js
class MVP2App {
    constructor() {
        this.initialized = false;
        this.components = {};
    }

    async init() {
        if (this.initialized) {
            return;
        }

        try {
            console.log('初始化MVP2应用...');

            // 初始化数据管理器
            this.components.dataManager = window.dataManager;
            
            // 初始化WebSocket连接
            this.components.wsClient = wsClient;
            wsClient.connect();
            wsClient.startHeartbeat();
            
            // 初始化实时处理器
            this.components.realTimeHandler = realTimeHandler;
            
            // 初始化错误处理器
            this.components.errorHandler = errorHandler;
            
            // 初始化反馈系统
            this.components.feedbackSystem = feedbackSystem;

            // 启动自动数据同步
            this.components.dataManager.startAutoSync();

            // 加载初始数据
            await this.loadInitialData();

            // 设置全局错误处理
            this.setupGlobalErrorHandling();

            // 设置键盘快捷键
            this.setupKeyboardShortcuts();

            this.initialized = true;
            console.log('MVP2应用初始化完成');

            // 显示初始化完成通知
            showNotification('系统初始化完成', 'success');

        } catch (error) {
            console.error('MVP2应用初始化失败:', error);
            errorHandler.handleError(error, 'App Initialization');
        }
    }

    async loadInitialData() {
        try {
            // 加载任务数据
            await this.components.dataManager.getTasks();
            
            // 加载聊天历史
            await this.components.dataManager.getChatHistory();
            
            // 更新UI
            if (typeof loadTasks === 'function') {
                loadTasks();
            }
            
            if (typeof loadChatHistory === 'function') {
                loadChatHistory();
            }
            
            if (typeof updateTaskStats === 'function') {
                updateTaskStats();
            }

        } catch (error) {
            console.error('加载初始数据失败:', error);
        }
    }

    setupGlobalErrorHandling() {
        // 包装原有函数以添加错误处理
        const originalFunctions = [
            'sendMessage', 'saveTask', 'updateTask', 'deleteTask',
            'openAddTaskModal', 'closeAddTaskModal'
        ];

        originalFunctions.forEach(funcName => {
            if (typeof window[funcName] === 'function') {
                const originalFunc = window[funcName];
                window[funcName] = (...args) => {
                    try {
                        return originalFunc.apply(this, args);
                    } catch (error) {
                        errorHandler.handleError(error, `Function: ${funcName}`);
                    }
                };
            }
        });
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            // Ctrl/Cmd + K: 打开搜索
            if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
                event.preventDefault();
                const searchInput = document.querySelector('input[placeholder="搜索任务..."]');
                if (searchInput) {
                    searchInput.focus();
                }
            }

            // Ctrl/Cmd + N: 新建任务
            if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
                event.preventDefault();
                if (typeof openAddTaskModal === 'function') {
                    openAddTaskModal();
                }
            }

            // F1: 打开反馈
            if (event.key === 'F1') {
                event.preventDefault();
                feedbackSystem.openFeedbackModal();
            }

            // Esc: 关闭模态框
            if (event.key === 'Escape') {
                const modals = document.querySelectorAll('.fixed.inset-0:not(.hidden)');
                modals.forEach(modal => {
                    if (modal.id === 'addTaskModal' && typeof closeAddTaskModal === 'function') {
                        closeAddTaskModal();
                    } else if (modal.id === 'feedbackModal') {
                        feedbackSystem.closeFeedbackModal();
                    }
                });
            }
        });
    }

    getStatus() {
        return {
            initialized: this.initialized,
            components: Object.keys(this.components),
            websocket_connected: wsClient.isConnected,
            offline_mode: this.components.dataManager?.offlineMode || false,
            error_count: errorHandler.errorQueue.length
        };
    }
}

// 创建全局应用实例
const mvp2App = new MVP2App();

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    mvp2App.init();
});

// 导出全局访问
window.mvp2App = mvp2App;
```

### 2. 集成验证

```javascript
// integration-test.js
class IntegrationTest {
    constructor() {
        this.tests = [];
        this.results = [];
    }

    addTest(name, testFunc) {
        this.tests.push({ name, testFunc });
    }

    async runAllTests() {
        console.log('开始运行集成测试...');
        this.results = [];

        for (const test of this.tests) {
            try {
                console.log(`运行测试: ${test.name}`);
                const startTime = Date.now();
                await test.testFunc();
                const duration = Date.now() - startTime;
                
                this.results.push({
                    name: test.name,
                    status: 'passed',
                    duration: duration
                });
                
                console.log(`✓ ${test.name} (${duration}ms)`);
            } catch (error) {
                this.results.push({
                    name: test.name,
                    status: 'failed',
                    error: error.message
                });
                
                console.error(`✗ ${test.name}: ${error.message}`);
            }
        }

        this.printResults();
        return this.results;
    }

    printResults() {
        const passed = this.results.filter(r => r.status === 'passed').length;
        const failed = this.results.filter(r => r.status === 'failed').length;
        
        console.log(`\n测试结果: ${passed} 通过, ${failed} 失败`);
        
        if (failed > 0) {
            console.log('\n失败的测试:');
            this.results
                .filter(r => r.status === 'failed')
                .forEach(r => console.log(`  - ${r.name}: ${r.error}`));
        }
    }
}

// 创建集成测试实例
const integrationTest = new IntegrationTest();

// 添加测试用例
integrationTest.addTest('API连接测试', async () => {
    const response = await apiClient.request('GET', '/health');
    if (!response.success) {
        throw new Error('API健康检查失败');
    }
});

integrationTest.addTest('WebSocket连接测试', async () => {
    return new Promise((resolve, reject) => {
        if (wsClient.isConnected) {
            resolve();
        } else {
            const timeout = setTimeout(() => {
                reject(new Error('WebSocket连接超时'));
            }, 5000);
            
            wsClient.onConnected = () => {
                clearTimeout(timeout);
                resolve();
            };
        }
    });
});

integrationTest.addTest('任务创建测试', async () => {
    const testTask = {
        name: '集成测试任务',
        description: '这是一个集成测试任务',
        priority: '低',
        deadline: '2024-12-31',
        assignee: '测试用户'
    };
    
    const response = await apiClient.createTask(testTask);
    if (!response.success) {
        throw new Error('任务创建失败');
    }
});

integrationTest.addTest('数据同步测试', async () => {
    await mvp2App.components.dataManager.syncData();
    // 验证数据是否同步成功
});

// 在控制台中运行测试
// integrationTest.runAllTests();
```

## 总结

通过以上集成方案，MVP2前端可以：

1. **无缝对接**：通过适配层实现与LangGraph后端的完美集成
2. **实时通信**：WebSocket提供实时状态更新和通知
3. **离线支持**：在网络异常时自动切换到离线模式
4. **错误恢复**：智能错误处理和用户友好的错误提示
5. **用户反馈**：完整的反馈收集和处理系统
6. **性能优化**：数据缓存、自动同步和连接管理

这个集成方案确保了MVP2前端能够充分利用LangGraph多智能体系统的强大功能，同时保持良好的用户体验和系统稳定性。

## 部署和配置指南

### 1. 环境准备

#### 前端环境要求
```bash
# Node.js环境
Node.js >= 16.0.0
npm >= 8.0.0 或 yarn >= 1.22.0

# 浏览器支持
Chrome >= 90
Firefox >= 88
Safari >= 14
Edge >= 90
```

#### 后端环境配置
```bash
# 确保LangGraph多智能体系统已部署
kubectl get pods -n langgraph-multi-agent

# 验证API服务可用
curl -f http://your-domain.com/api/v1/mvp2/health
```

### 2. MVP2前端部署

#### Docker部署方式
```dockerfile
# Dockerfile.mvp2
FROM nginx:alpine

# 复制前端文件
COPY mvp2-frontend/ /usr/share/nginx/html/

# 复制Nginx配置
COPY nginx.conf /etc/nginx/nginx.conf

# 暴露端口
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

```yaml
# docker-compose.mvp2.yml
version: '3.8'
services:
  mvp2-frontend:
    build:
      context: .
      dockerfile: Dockerfile.mvp2
    ports:
      - "80:80"
    environment:
      - API_BASE_URL=http://langgraph-backend:8000/api/v1/mvp2
      - WS_URL=ws://langgraph-backend:8000/api/v1/mvp2/ws
    depends_on:
      - langgraph-backend
    networks:
      - langgraph-network

networks:
  langgraph-network:
    external: true
```

#### Kubernetes部署
```yaml
# k8s/mvp2-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mvp2-frontend
  namespace: langgraph-multi-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mvp2-frontend
  template:
    metadata:
      labels:
        app: mvp2-frontend
    spec:
      containers:
      - name: mvp2-frontend
        image: mvp2-frontend:latest
        ports:
        - containerPort: 80
        env:
        - name: API_BASE_URL
          value: "http://langgraph-multi-agent-service:8000/api/v1/mvp2"
        - name: WS_URL
          value: "ws://langgraph-multi-agent-service:8000/api/v1/mvp2/ws"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"

---
apiVersion: v1
kind: Service
metadata:
  name: mvp2-frontend-service
  namespace: langgraph-multi-agent
spec:
  selector:
    app: mvp2-frontend
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mvp2-frontend-ingress
  namespace: langgraph-multi-agent
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: mvp2.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mvp2-frontend-service
            port:
              number: 80
```

### 3. 配置管理

#### 环境变量配置
```javascript
// config/environment.js
const environments = {
  development: {
    API_BASE_URL: 'http://localhost:8000/api/v1/mvp2',
    WS_URL: 'ws://localhost:8000/api/v1/mvp2/ws',
    DEBUG: true,
    LOG_LEVEL: 'debug'
  },
  staging: {
    API_BASE_URL: 'https://staging-api.your-domain.com/api/v1/mvp2',
    WS_URL: 'wss://staging-api.your-domain.com/api/v1/mvp2/ws',
    DEBUG: false,
    LOG_LEVEL: 'info'
  },
  production: {
    API_BASE_URL: 'https://api.your-domain.com/api/v1/mvp2',
    WS_URL: 'wss://api.your-domain.com/api/v1/mvp2/ws',
    DEBUG: false,
    LOG_LEVEL: 'error'
  }
};

const currentEnv = process.env.NODE_ENV || 'development';
export default environments[currentEnv];
```

#### Nginx配置
```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    server {
        listen 80;
        server_name mvp2.your-domain.com;
        root /usr/share/nginx/html;
        index index.html;

        # 静态文件缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # API代理
        location /api/ {
            proxy_pass http://langgraph-backend:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket代理
        location /api/v1/mvp2/ws {
            proxy_pass http://langgraph-backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # SPA路由支持
        location / {
            try_files $uri $uri/ /index.html;
        }

        # 健康检查
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
```

### 4. 集成测试

#### 自动化测试脚本
```bash
#!/bin/bash
# mvp2-integration-test.sh

BASE_URL="http://mvp2.your-domain.com"
API_URL="http://your-domain.com/api/v1/mvp2"

echo "=== MVP2前端集成测试 ==="

# 1. 前端可访问性测试
echo "1. 测试前端可访问性..."
if curl -f -s "$BASE_URL" > /dev/null; then
    echo "✅ 前端页面可访问"
else
    echo "❌ 前端页面不可访问"
    exit 1
fi

# 2. API连接测试
echo "2. 测试API连接..."
if curl -f -s "$API_URL/health" > /dev/null; then
    echo "✅ API连接正常"
else
    echo "❌ API连接失败"
    exit 1
fi

# 3. 功能测试
echo "3. 测试核心功能..."

# 创建测试任务
TASK_DATA='{"name":"集成测试任务","description":"自动化测试","priority":"中","deadline":"2024-12-31","assignee":"测试用户"}'
TASK_RESPONSE=$(curl -s -X POST "$API_URL/tasks" \
    -H "Content-Type: application/json" \
    -d "$TASK_DATA")

if echo "$TASK_RESPONSE" | grep -q "success.*true"; then
    echo "✅ 任务创建功能正常"
    TASK_ID=$(echo "$TASK_RESPONSE" | jq -r '.data.id')
else
    echo "❌ 任务创建功能异常"
    exit 1
fi

# 获取任务列表
TASKS_RESPONSE=$(curl -s "$API_URL/tasks")
if echo "$TASKS_RESPONSE" | grep -q "success.*true"; then
    echo "✅ 任务列表功能正常"
else
    echo "❌ 任务列表功能异常"
    exit 1
fi

# 更新任务
UPDATE_DATA='{"status":"进行中","progress":50}'
UPDATE_RESPONSE=$(curl -s -X PUT "$API_URL/tasks/$TASK_ID" \
    -H "Content-Type: application/json" \
    -d "$UPDATE_DATA")

if echo "$UPDATE_RESPONSE" | grep -q "success.*true"; then
    echo "✅ 任务更新功能正常"
else
    echo "❌ 任务更新功能异常"
fi

# 删除测试任务
DELETE_RESPONSE=$(curl -s -X DELETE "$API_URL/tasks/$TASK_ID")
if echo "$DELETE_RESPONSE" | grep -q "success.*true"; then
    echo "✅ 任务删除功能正常"
else
    echo "❌ 任务删除功能异常"
fi

# 4. WebSocket连接测试
echo "4. 测试WebSocket连接..."
# 使用wscat测试WebSocket连接
if command -v wscat &> /dev/null; then
    timeout 10s wscat -c "ws://your-domain.com/api/v1/mvp2/ws" -x '{"type":"ping"}' > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ WebSocket连接正常"
    else
        echo "⚠️  WebSocket连接测试超时（可能正常）"
    fi
else
    echo "⚠️  wscat未安装，跳过WebSocket测试"
fi

echo "=== 集成测试完成 ==="
```

#### 性能测试
```bash
#!/bin/bash
# mvp2-performance-test.sh

API_URL="http://your-domain.com/api/v1/mvp2"
CONCURRENT_USERS=10
TEST_DURATION=60

echo "=== MVP2性能测试 ==="

# 使用Apache Bench进行压力测试
if command -v ab &> /dev/null; then
    echo "执行API性能测试..."
    ab -n 1000 -c $CONCURRENT_USERS -t $TEST_DURATION "$API_URL/tasks" > performance_results.txt
    
    # 分析结果
    echo "性能测试结果:"
    grep "Requests per second" performance_results.txt
    grep "Time per request" performance_results.txt
    grep "Transfer rate" performance_results.txt
else
    echo "Apache Bench未安装，跳过性能测试"
fi

# 使用curl测试响应时间
echo "测试API响应时间..."
for endpoint in "/health" "/tasks" "/tasks/stats"; do
    response_time=$(curl -o /dev/null -s -w "%{time_total}" "$API_URL$endpoint")
    echo "$endpoint: ${response_time}s"
done

echo "=== 性能测试完成 ==="
```

### 5. 监控和日志

#### 前端监控配置
```javascript
// monitoring/frontend-monitoring.js
class FrontendMonitoring {
    constructor() {
        this.metrics = {
            pageViews: 0,
            apiCalls: 0,
            errors: 0,
            loadTime: 0
        };
        
        this.setupPerformanceMonitoring();
        this.setupErrorTracking();
    }

    setupPerformanceMonitoring() {
        // 页面加载时间监控
        window.addEventListener('load', () => {
            const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
            this.metrics.loadTime = loadTime;
            this.sendMetric('page_load_time', loadTime);
        });

        // API调用监控
        const originalFetch = window.fetch;
        window.fetch = (...args) => {
            this.metrics.apiCalls++;
            const startTime = Date.now();
            
            return originalFetch(...args)
                .then(response => {
                    const duration = Date.now() - startTime;
                    this.sendMetric('api_call_duration', duration, {
                        url: args[0],
                        status: response.status
                    });
                    return response;
                })
                .catch(error => {
                    this.metrics.errors++;
                    this.sendMetric('api_call_error', 1, {
                        url: args[0],
                        error: error.message
                    });
                    throw error;
                });
        };
    }

    setupErrorTracking() {
        window.addEventListener('error', (event) => {
            this.metrics.errors++;
            this.sendMetric('javascript_error', 1, {
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno
            });
        });

        window.addEventListener('unhandledrejection', (event) => {
            this.metrics.errors++;
            this.sendMetric('promise_rejection', 1, {
                reason: event.reason
            });
        });
    }

    sendMetric(name, value, tags = {}) {
        // 发送指标到监控系统
        fetch('/api/v1/metrics', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                metric: name,
                value: value,
                tags: {
                    ...tags,
                    component: 'mvp2-frontend',
                    timestamp: new Date().toISOString()
                }
            })
        }).catch(error => {
            console.error('Failed to send metric:', error);
        });
    }

    getMetrics() {
        return this.metrics;
    }
}

// 初始化监控
const frontendMonitoring = new FrontendMonitoring();
window.frontendMonitoring = frontendMonitoring;
```

#### 日志配置
```javascript
// logging/frontend-logger.js
class FrontendLogger {
    constructor(config = {}) {
        this.config = {
            level: config.level || 'info',
            endpoint: config.endpoint || '/api/v1/logs',
            batchSize: config.batchSize || 10,
            flushInterval: config.flushInterval || 5000,
            ...config
        };
        
        this.logBuffer = [];
        this.setupAutoFlush();
    }

    log(level, message, context = {}) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            level: level,
            message: message,
            context: {
                ...context,
                userAgent: navigator.userAgent,
                url: window.location.href,
                component: 'mvp2-frontend'
            }
        };

        // 添加到缓冲区
        this.logBuffer.push(logEntry);

        // 如果是错误级别，立即发送
        if (level === 'error' || level === 'critical') {
            this.flush();
        }

        // 如果缓冲区满了，发送日志
        if (this.logBuffer.length >= this.config.batchSize) {
            this.flush();
        }

        // 同时输出到控制台（开发环境）
        if (this.config.level === 'debug') {
            console[level] || console.log(logEntry);
        }
    }

    debug(message, context) {
        this.log('debug', message, context);
    }

    info(message, context) {
        this.log('info', message, context);
    }

    warn(message, context) {
        this.log('warn', message, context);
    }

    error(message, context) {
        this.log('error', message, context);
    }

    critical(message, context) {
        this.log('critical', message, context);
    }

    flush() {
        if (this.logBuffer.length === 0) {
            return;
        }

        const logs = [...this.logBuffer];
        this.logBuffer = [];

        fetch(this.config.endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ logs })
        }).catch(error => {
            console.error('Failed to send logs:', error);
            // 重新添加到缓冲区
            this.logBuffer.unshift(...logs);
        });
    }

    setupAutoFlush() {
        setInterval(() => {
            this.flush();
        }, this.config.flushInterval);

        // 页面卸载时发送剩余日志
        window.addEventListener('beforeunload', () => {
            this.flush();
        });
    }
}

// 初始化日志器
const logger = new FrontendLogger({
    level: window.location.hostname === 'localhost' ? 'debug' : 'info'
});

window.logger = logger;
```

### 6. 故障排查

#### 常见问题和解决方案

**问题1: 前端无法连接到后端API**
```bash
# 检查网络连接
curl -v http://your-domain.com/api/v1/mvp2/health

# 检查DNS解析
nslookup your-domain.com

# 检查防火墙规则
iptables -L | grep 8000

# 解决方案
# 1. 检查后端服务状态
kubectl get pods -n langgraph-multi-agent
# 2. 检查服务配置
kubectl get svc -n langgraph-multi-agent
# 3. 检查Ingress配置
kubectl get ingress -n langgraph-multi-agent
```

**问题2: WebSocket连接失败**
```bash
# 检查WebSocket端点
wscat -c ws://your-domain.com/api/v1/mvp2/ws

# 检查Nginx配置
kubectl exec deployment/nginx -n langgraph-multi-agent -- nginx -t

# 解决方案
# 1. 确认WebSocket代理配置正确
# 2. 检查防火墙是否允许WebSocket连接
# 3. 验证SSL证书配置（如果使用HTTPS）
```

**问题3: 前端页面加载缓慢**
```bash
# 检查静态资源大小
du -sh /usr/share/nginx/html/*

# 检查Nginx压缩配置
kubectl exec deployment/nginx -n langgraph-multi-agent -- nginx -T | grep gzip

# 解决方案
# 1. 启用Gzip压缩
# 2. 优化静态资源缓存
# 3. 使用CDN加速
# 4. 压缩JavaScript和CSS文件
```

### 7. 维护和更新

#### 前端更新流程
```bash
#!/bin/bash
# update-mvp2-frontend.sh

NEW_VERSION=$1
NAMESPACE="langgraph-multi-agent"

if [ -z "$NEW_VERSION" ]; then
    echo "用法: $0 <new_version>"
    exit 1
fi

echo "开始更新MVP2前端到版本: $NEW_VERSION"

# 1. 构建新版本镜像
docker build -t mvp2-frontend:$NEW_VERSION .

# 2. 推送到镜像仓库
docker push mvp2-frontend:$NEW_VERSION

# 3. 更新Kubernetes部署
kubectl set image deployment/mvp2-frontend \
    mvp2-frontend=mvp2-frontend:$NEW_VERSION \
    -n $NAMESPACE

# 4. 等待部署完成
kubectl rollout status deployment/mvp2-frontend -n $NAMESPACE

# 5. 验证更新
echo "验证前端更新..."
sleep 30
curl -f http://mvp2.your-domain.com/health

echo "MVP2前端更新完成"
```

#### 配置热更新
```bash
#!/bin/bash
# hot-reload-config.sh

NAMESPACE="langgraph-multi-agent"

# 更新ConfigMap
kubectl create configmap mvp2-config \
    --from-file=config/ \
    --dry-run=client -o yaml | kubectl apply -f -

# 重启前端Pod以应用新配置
kubectl rollout restart deployment/mvp2-frontend -n $NAMESPACE

echo "配置热更新完成"
```

这个综合的部署和配置指南确保了MVP2前端能够成功集成到LangGraph多智能体系统中，并提供了完整的监控、日志、故障排查和维护流程。