/**
 * 增强的WebSocket连接管理器
 * 处理连接断开重连、消息队列和数据完整性
 */
class EnhancedWebSocketManager {
    constructor() {
        this.ws = null;
        this.url = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = CONFIG.WEBSOCKET.MAX_RECONNECT_ATTEMPTS || 10;
        this.reconnectInterval = CONFIG.WEBSOCKET.RECONNECT_INTERVAL || 5000;
        this.heartbeatInterval = CONFIG.WEBSOCKET.HEARTBEAT_INTERVAL || 30000;
        this.heartbeatTimer = null;
        this.connectionTimeout = 10000;
        this.connectionTimer = null;
        
        // 消息处理
        this.messageHandlers = new Map();
        this.messageQueue = [];
        this.pendingMessages = new Map();
        this.messageId = 0;
        
        // 状态管理
        this.connectionState = 'disconnected';
        this.lastPingTime = null;
        this.lastPongTime = null;
        this.connectionQuality = 'unknown';
        
        // 数据完整性
        this.sequenceNumber = 0;
        this.expectedSequence = 0;
        this.missedMessages = new Set();
        
        this.init();
    }
    
    /**
     * 初始化WebSocket管理器
     */
    init() {
        this.setupEventHandlers();
        this.setupHeartbeat();
        this.setupMessageQueue();
    }
    
    /**
     * 设置事件处理器
     */
    setupEventHandlers() {
        // 监听网络状态变化
        window.addEventListener('online', () => {
            if (this.connectionState === 'disconnected') {
                this.connect();
            }
        });
        
        window.addEventListener('offline', () => {
            this.handleNetworkDisconnect();
        });
        
        // 监听页面可见性变化
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.handlePageVisible();
            } else {
                this.handlePageHidden();
            }
        });
    }
    
    /**
     * 连接WebSocket
     */
    connect(url = null) {
        if (url) {
            this.url = url;
        }
        
        if (!this.url) {
            this.url = `ws://localhost:8000${CONFIG.API.ENDPOINTS.MVP2_WEBSOCKET}`;
        }
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return Promise.resolve();
        }
        
        return new Promise((resolve, reject) => {
            try {
                console.log(`Connecting to WebSocket: ${this.url}`);
                this.connectionState = 'connecting';
                this.ws = new WebSocket(this.url);
                
                // 连接超时处理
                this.connectionTimer = setTimeout(() => {
                    if (this.ws.readyState === WebSocket.CONNECTING) {
                        this.ws.close();
                        reject(new Error('Connection timeout'));
                    }
                }, this.connectionTimeout);
                
                this.ws.onopen = (event) => {
                    clearTimeout(this.connectionTimer);
                    this.onOpen(event);
                    resolve();
                };
                
                this.ws.onmessage = (event) => {
                    this.onMessage(event);
                };
                
                this.ws.onclose = (event) => {
                    clearTimeout(this.connectionTimer);
                    this.onClose(event);
                    if (this.reconnectAttempts === 0) {
                        reject(new Error('Connection closed'));
                    }
                };
                
                this.ws.onerror = (event) => {
                    clearTimeout(this.connectionTimer);
                    this.onError(event);
                    reject(new Error('Connection error'));
                };
                
            } catch (error) {
                console.error('Failed to create WebSocket connection:', error);
                this.connectionState = 'disconnected';
                reject(error);
            }
        });
    }
    
    /**
     * 连接打开处理
     */
    onOpen(event) {
        console.log('WebSocket connection established');
        this.connectionState = 'connected';
        this.reconnectAttempts = 0;
        this.connectionQuality = 'good';
        
        // 开始心跳
        this.startHeartbeat();
        
        // 发送队列中的消息
        this.flushMessageQueue();
        
        // 请求重传丢失的消息
        this.requestMissedMessages();
        
        // 触发连接事件
        this.triggerEvent('connected', { timestamp: Date.now() });
        
        // 通知用户
        if (window.feedbackManager && this.reconnectAttempts > 0) {
            window.feedbackManager.showSuccess('连接恢复', 'WebSocket连接已恢复');
        }
    }
    
    /**
     * 消息接收处理
     */
    onMessage(event) {
        try {
            const message = JSON.parse(event.data);
            this.handleIncomingMessage(message);
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }
    
    /**
     * 处理接收到的消息
     */
    handleIncomingMessage(message) {
        const { type, data, id, sequence, timestamp } = message;
        
        // 处理心跳响应
        if (type === 'pong') {
            this.handlePong(timestamp);
            return;
        }
        
        // 处理消息确认
        if (type === 'ack') {
            this.handleMessageAck(id);
            return;
        }
        
        // 处理序列号
        if (sequence !== undefined) {
            this.handleSequenceNumber(sequence, message);
        }
        
        // 发送确认
        if (id) {
            this.sendAck(id);
        }
        
        // 分发消息给处理器
        if (this.messageHandlers.has(type)) {
            try {
                this.messageHandlers.get(type)(data, message);
            } catch (error) {
                console.error(`Message handler error for type ${type}:`, error);
            }
        } else {
            console.log('Unhandled WebSocket message:', message);
        }
        
        // 触发消息事件
        this.triggerEvent('message', { type, data, message });
    }
    
    /**
     * 处理序列号
     */
    handleSequenceNumber(sequence, message) {
        if (sequence === this.expectedSequence) {
            // 正确的序列号
            this.expectedSequence++;
            
            // 检查是否有等待的消息
            this.processWaitingMessages();
        } else if (sequence > this.expectedSequence) {
            // 跳过了一些消息，标记为丢失
            for (let i = this.expectedSequence; i < sequence; i++) {
                this.missedMessages.add(i);
            }
            this.expectedSequence = sequence + 1;
            
            // 请求重传丢失的消息
            this.requestMissedMessages();
        } else {
            // 重复或过期的消息，忽略
            console.log(`Ignoring duplicate/old message with sequence ${sequence}`);
            return false;
        }
        
        return true;
    }
    
    /**
     * 处理等待的消息
     */
    processWaitingMessages() {
        // 这里可以实现消息重排序逻辑
        // 暂时简单处理
    }
    
    /**
     * 请求重传丢失的消息
     */
    requestMissedMessages() {
        if (this.missedMessages.size > 0) {
            const missedArray = Array.from(this.missedMessages);
            this.send({
                type: 'request_retransmission',
                sequences: missedArray
            });
            
            console.log(`Requesting retransmission for sequences: ${missedArray.join(', ')}`);
        }
    }
    
    /**
     * 连接关闭处理
     */
    onClose(event) {
        console.log('WebSocket connection closed:', event.code, event.reason);
        this.connectionState = 'disconnected';
        
        // 停止心跳
        this.stopHeartbeat();
        
        // 触发断开事件
        this.triggerEvent('disconnected', { 
            code: event.code, 
            reason: event.reason,
            timestamp: Date.now()
        });
        
        // 尝试重连
        if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.triggerEvent('maxReconnectAttemptsReached');
            
            if (window.feedbackManager) {
                window.feedbackManager.showError(
                    '连接失败', 
                    '无法连接到服务器，请检查网络连接或刷新页面重试'
                );
            }
        }
    }
    
    /**
     * 连接错误处理
     */
    onError(event) {
        console.error('WebSocket error:', event);
        this.connectionState = 'error';
        this.connectionQuality = 'poor';
        
        this.triggerEvent('error', { 
            error: event,
            timestamp: Date.now()
        });
    }
    
    /**
     * 尝试重连
     */
    attemptReconnect() {
        this.reconnectAttempts++;
        const delay = Math.min(
            this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
            30000 // 最大30秒
        );
        
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`);
        
        this.connectionState = 'reconnecting';
        this.triggerEvent('reconnecting', { 
            attempt: this.reconnectAttempts,
            delay,
            timestamp: Date.now()
        });
        
        setTimeout(() => {
            if (this.connectionState === 'reconnecting') {
                this.connect().catch(error => {
                    console.error('Reconnection failed:', error);
                });
            }
        }, delay);
    }
    
    /**
     * 发送消息
     */
    send(message, options = {}) {
        const {
            requireAck = false,
            timeout = 5000,
            priority = 'normal'
        } = options;
        
        // 添加消息ID和序列号
        const messageWithMeta = {
            ...message,
            id: requireAck ? this.generateMessageId() : undefined,
            sequence: this.sequenceNumber++,
            timestamp: Date.now()
        };
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify(messageWithMeta));
                
                // 如果需要确认，添加到待确认列表
                if (requireAck) {
                    this.pendingMessages.set(messageWithMeta.id, {
                        message: messageWithMeta,
                        timestamp: Date.now(),
                        timeout: setTimeout(() => {
                            this.handleMessageTimeout(messageWithMeta.id);
                        }, timeout)
                    });
                }
                
                return messageWithMeta.id;
            } catch (error) {
                console.error('Failed to send WebSocket message:', error);
                this.queueMessage(messageWithMeta, options);
                throw error;
            }
        } else {
            // 连接未建立，加入队列
            this.queueMessage(messageWithMeta, options);
            
            // 如果未连接，尝试连接
            if (this.connectionState === 'disconnected') {
                this.connect().catch(error => {
                    console.error('Failed to connect for sending message:', error);
                });
            }
            
            return messageWithMeta.id;
        }
    }
    
    /**
     * 消息加入队列
     */
    queueMessage(message, options) {
        const queueItem = {
            message,
            options,
            timestamp: Date.now()
        };
        
        // 根据优先级插入队列
        if (options.priority === 'high') {
            this.messageQueue.unshift(queueItem);
        } else {
            this.messageQueue.push(queueItem);
        }
        
        // 限制队列大小
        if (this.messageQueue.length > 100) {
            this.messageQueue.splice(50); // 保留前50条消息
        }
    }
    
    /**
     * 刷新消息队列
     */
    flushMessageQueue() {
        while (this.messageQueue.length > 0) {
            const item = this.messageQueue.shift();
            try {
                this.send(item.message, item.options);
            } catch (error) {
                // 发送失败，重新加入队列
                this.messageQueue.unshift(item);
                break;
            }
        }
    }
    
    /**
     * 处理消息确认
     */
    handleMessageAck(messageId) {
        const pending = this.pendingMessages.get(messageId);
        if (pending) {
            clearTimeout(pending.timeout);
            this.pendingMessages.delete(messageId);
            
            this.triggerEvent('messageAcknowledged', { messageId });
        }
    }
    
    /**
     * 处理消息超时
     */
    handleMessageTimeout(messageId) {
        const pending = this.pendingMessages.get(messageId);
        if (pending) {
            this.pendingMessages.delete(messageId);
            
            console.warn(`Message ${messageId} timed out`);
            this.triggerEvent('messageTimeout', { messageId, message: pending.message });
            
            // 可以选择重发消息
            this.queueMessage(pending.message, { requireAck: true });
        }
    }
    
    /**
     * 发送确认
     */
    sendAck(messageId) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify({
                    type: 'ack',
                    id: messageId,
                    timestamp: Date.now()
                }));
            } catch (error) {
                console.error('Failed to send ack:', error);
            }
        }
    }
    
    /**
     * 设置心跳
     */
    setupHeartbeat() {
        // 心跳逻辑在startHeartbeat中实现
    }
    
    /**
     * 开始心跳
     */
    startHeartbeat() {
        this.stopHeartbeat();
        
        this.heartbeatTimer = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.lastPingTime = Date.now();
                this.send({
                    type: 'ping',
                    timestamp: this.lastPingTime
                });
                
                // 检查连接质量
                this.checkConnectionQuality();
            }
        }, this.heartbeatInterval);
    }
    
    /**
     * 停止心跳
     */
    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    
    /**
     * 处理心跳响应
     */
    handlePong(serverTimestamp) {
        this.lastPongTime = Date.now();
        
        if (this.lastPingTime) {
            const latency = this.lastPongTime - this.lastPingTime;
            this.updateConnectionQuality(latency);
            
            this.triggerEvent('heartbeat', { 
                latency,
                serverTimestamp,
                timestamp: this.lastPongTime
            });
        }
    }
    
    /**
     * 检查连接质量
     */
    checkConnectionQuality() {
        if (this.lastPingTime && this.lastPongTime) {
            const timeSinceLastPong = Date.now() - this.lastPongTime;
            
            if (timeSinceLastPong > this.heartbeatInterval * 2) {
                this.connectionQuality = 'poor';
                console.warn('Poor connection quality detected');
            }
        }
    }
    
    /**
     * 更新连接质量
     */
    updateConnectionQuality(latency) {
        if (latency < 100) {
            this.connectionQuality = 'excellent';
        } else if (latency < 300) {
            this.connectionQuality = 'good';
        } else if (latency < 1000) {
            this.connectionQuality = 'fair';
        } else {
            this.connectionQuality = 'poor';
        }
    }
    
    /**
     * 设置消息队列处理
     */
    setupMessageQueue() {
        // 定期清理过期的队列消息
        setInterval(() => {
            const now = Date.now();
            this.messageQueue = this.messageQueue.filter(item => {
                return (now - item.timestamp) < 300000; // 5分钟过期
            });
        }, 60000);
    }
    
    /**
     * 处理网络断开
     */
    handleNetworkDisconnect() {
        console.log('Network disconnected');
        this.connectionQuality = 'offline';
        
        if (this.ws) {
            this.ws.close();
        }
    }
    
    /**
     * 处理页面可见
     */
    handlePageVisible() {
        // 页面重新可见时，检查连接状态
        if (this.connectionState === 'disconnected') {
            this.connect().catch(error => {
                console.error('Failed to reconnect on page visible:', error);
            });
        }
    }
    
    /**
     * 处理页面隐藏
     */
    handlePageHidden() {
        // 页面隐藏时可以降低心跳频率
        // 这里暂时不做处理
    }
    
    /**
     * 注册消息处理器
     */
    onMessage(type, handler) {
        this.messageHandlers.set(type, handler);
        return () => this.messageHandlers.delete(type);
    }
    
    /**
     * 注册事件处理器
     */
    on(event, handler) {
        if (!this.eventHandlers) {
            this.eventHandlers = new Map();
        }
        
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, new Set());
        }
        
        this.eventHandlers.get(event).add(handler);
        
        return () => {
            const handlers = this.eventHandlers.get(event);
            if (handlers) {
                handlers.delete(handler);
            }
        };
    }
    
    /**
     * 触发事件
     */
    triggerEvent(event, data = null) {
        if (this.eventHandlers && this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Event handler error for ${event}:`, error);
                }
            });
        }
        
        // 也触发DOM事件
        window.dispatchEvent(new CustomEvent(`websocket:${event}`, {
            detail: data
        }));
    }
    
    /**
     * 生成消息ID
     */
    generateMessageId() {
        return `msg_${++this.messageId}_${Date.now()}`;
    }
    
    /**
     * 获取连接状态
     */
    getConnectionStatus() {
        return {
            state: this.connectionState,
            quality: this.connectionQuality,
            reconnectAttempts: this.reconnectAttempts,
            queueLength: this.messageQueue.length,
            pendingMessages: this.pendingMessages.size,
            lastPingTime: this.lastPingTime,
            lastPongTime: this.lastPongTime,
            missedMessages: this.missedMessages.size
        };
    }
    
    /**
     * 关闭连接
     */
    close() {
        this.stopHeartbeat();
        
        if (this.ws) {
            this.ws.close(1000, 'Client closing');
            this.ws = null;
        }
        
        this.connectionState = 'disconnected';
        this.messageQueue = [];
        this.pendingMessages.clear();
        this.missedMessages.clear();
    }
    
    /**
     * 销毁管理器
     */
    destroy() {
        this.close();
        this.messageHandlers.clear();
        
        if (this.eventHandlers) {
            this.eventHandlers.clear();
        }
    }
}

// 替换原有的WebSocket管理器
if (window.wsManager) {
    window.wsManager.destroy();
}

window.wsManager = new EnhancedWebSocketManager();

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnhancedWebSocketManager;
}