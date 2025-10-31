// MVP2前端配置文件
const CONFIG = {
    // 后端API配置
    API: {
        BASE_URL: 'http://localhost:8000',
        ENDPOINTS: {
            // 基础端点
            HEALTH: '/health',
            VERSION: '/version',
            
            // 任务管理
            TASKS: '/api/v1/tasks',
            TASK_CREATE: '/api/v1/tasks',
            TASK_DETAIL: '/api/v1/tasks/{id}',
            TASK_UPDATE: '/api/v1/tasks/{id}',
            TASK_DELETE: '/api/v1/tasks/{id}',
            TASK_STATISTICS: '/api/v1/tasks/statistics',
            
            // 智能体管理
            AGENTS: '/api/v1/agents',
            AGENT_STATUS: '/api/v1/agents/status',
            AGENT_DETAIL: '/api/v1/agents/{id}',
            
            // 系统管理
            SYSTEM_STATUS: '/api/v1/system/status',
            SYSTEM_HEALTH: '/api/v1/system/health',
            SYSTEM_METRICS: '/api/v1/system/metrics',
            
            // WebSocket
            WEBSOCKET: '/api/v1/ws',
            MVP2_WEBSOCKET: '/api/v1/mvp2/ws'
        }
    },
    
    // WebSocket配置
    WEBSOCKET: {
        RECONNECT_INTERVAL: 5000,
        MAX_RECONNECT_ATTEMPTS: 10,
        HEARTBEAT_INTERVAL: 30000
    },
    
    // UI配置
    UI: {
        THEME: 'dark',
        LANGUAGE: 'zh-CN',
        AUTO_REFRESH_INTERVAL: 30000,
        NOTIFICATION_DURATION: 5000
    },
    
    // 功能开关
    FEATURES: {
        REAL_TIME_UPDATES: true,
        AUTO_SAVE: true,
        OFFLINE_MODE: false,
        DEBUG_MODE: false
    },
    
    // 任务配置
    TASKS: {
        DEFAULT_PRIORITY: 2,
        DEFAULT_TYPE: 'general',
        MAX_TITLE_LENGTH: 200,
        MAX_DESCRIPTION_LENGTH: 2000,
        REFRESH_INTERVAL: 10000
    },
    
    // 智能体配置
    AGENTS: {
        TYPES: {
            META_AGENT: 'meta_agent',
            TASK_DECOMPOSER: 'task_decomposer',
            COORDINATOR: 'coordinator',
            GENERIC: 'generic'
        },
        STATUS_COLORS: {
            active: '#10b981',
            idle: '#6b7280',
            busy: '#f59e0b',
            error: '#ef4444'
        }
    }
};

// API请求工具类
class APIClient {
    constructor() {
        this.baseURL = CONFIG.API.BASE_URL;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
    }
    
    // 构建完整URL
    buildURL(endpoint, params = {}) {
        let url = this.baseURL + endpoint;
        
        // 替换路径参数
        Object.keys(params).forEach(key => {
            url = url.replace(`{${key}}`, params[key]);
        });
        
        return url;
    }
    
    // 通用请求方法
    async request(method, endpoint, data = null, params = {}) {
        const url = this.buildURL(endpoint, params);
        
        const options = {
            method: method.toUpperCase(),
            headers: { ...this.defaultHeaders },
            mode: 'cors'
        };
        
        if (data && (method.toUpperCase() === 'POST' || method.toUpperCase() === 'PUT')) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error(`API请求失败 [${method.toUpperCase()} ${url}]:`, error);
            throw error;
        }
    }
    
    // GET请求
    async get(endpoint, params = {}) {
        return this.request('GET', endpoint, null, params);
    }
    
    // POST请求
    async post(endpoint, data, params = {}) {
        return this.request('POST', endpoint, data, params);
    }
    
    // PUT请求
    async put(endpoint, data, params = {}) {
        return this.request('PUT', endpoint, data, params);
    }
    
    // DELETE请求
    async delete(endpoint, params = {}) {
        return this.request('DELETE', endpoint, null, params);
    }
    
    // 健康检查
    async healthCheck() {
        try {
            const response = await this.get(CONFIG.API.ENDPOINTS.HEALTH);
            return response;
        } catch (error) {
            console.error('健康检查失败:', error);
            return null;
        }
    }
    
    // 获取任务列表
    async getTasks(page = 1, pageSize = 20) {
        const url = `${CONFIG.API.ENDPOINTS.TASKS}?page=${page}&page_size=${pageSize}`;
        return this.get(url);
    }
    
    // 创建任务
    async createTask(taskData) {
        return this.post(CONFIG.API.ENDPOINTS.TASK_CREATE, taskData);
    }
    
    // 获取智能体列表
    async getAgents() {
        return this.get(CONFIG.API.ENDPOINTS.AGENTS);
    }
    
    // 获取系统状态
    async getSystemStatus() {
        return this.get(CONFIG.API.ENDPOINTS.SYSTEM_STATUS);
    }
}

// WebSocket管理类
class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = CONFIG.WEBSOCKET.MAX_RECONNECT_ATTEMPTS;
        this.reconnectInterval = CONFIG.WEBSOCKET.RECONNECT_INTERVAL;
        this.heartbeatInterval = null;
        this.messageHandlers = new Map();
    }
    
    // 连接WebSocket
    connect() {
        const wsURL = `ws://localhost:8000${CONFIG.API.ENDPOINTS.MVP2_WEBSOCKET}`;
        
        try {
            this.ws = new WebSocket(wsURL);
            
            this.ws.onopen = () => {
                console.log('WebSocket连接已建立');
                this.reconnectAttempts = 0;
                this.startHeartbeat();
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('WebSocket消息解析失败:', error);
                }
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket连接已关闭');
                this.stopHeartbeat();
                this.attemptReconnect();
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket错误:', error);
            };
            
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.attemptReconnect();
        }
    }
    
    // 处理消息
    handleMessage(message) {
        const { type, data } = message;
        
        if (this.messageHandlers.has(type)) {
            this.messageHandlers.get(type)(data);
        } else {
            console.log('收到未处理的WebSocket消息:', message);
        }
    }
    
    // 注册消息处理器
    onMessage(type, handler) {
        this.messageHandlers.set(type, handler);
    }
    
    // 发送消息
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket未连接，无法发送消息');
        }
    }
    
    // 尝试重连
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`尝试重连WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectInterval);
        } else {
            console.error('WebSocket重连次数已达上限');
        }
    }
    
    // 开始心跳
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            this.send({ type: 'ping', timestamp: Date.now() });
        }, CONFIG.WEBSOCKET.HEARTBEAT_INTERVAL);
    }
    
    // 停止心跳
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    // 关闭连接
    close() {
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// 全局实例
window.apiClient = new APIClient();
window.wsManager = new WebSocketManager();
window.CONFIG = CONFIG;

// 导出配置和工具类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CONFIG, APIClient, WebSocketManager };
}