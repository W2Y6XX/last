/**
 * 数据同步管理器
 * 处理前后端数据同步、状态一致性检查和离线处理
 */
class SyncManager {
    constructor() {
        this.syncQueue = [];
        this.retryQueue = [];
        this.syncStates = new Map();
        this.conflictResolver = null;
        this.isOnline = navigator.onLine;
        this.lastSyncTime = null;
        this.syncInterval = null;
        this.maxRetries = 3;
        this.retryDelay = 1000;
        
        this.init();
    }
    
    /**
     * 初始化同步管理器
     */
    init() {
        this.setupOnlineStatusMonitoring();
        this.setupPeriodicSync();
        this.setupConflictResolution();
        this.loadSyncState();
        this.startSyncWorker();
    }
    
    /**
     * 设置在线状态监控
     */
    setupOnlineStatusMonitoring() {
        window.addEventListener('online', () => {
            console.log('网络连接已恢复');
            this.isOnline = true;
            this.onNetworkReconnect();
            
            // 通知用户
            if (window.feedbackManager) {
                window.feedbackManager.showSuccess('网络连接', '网络连接已恢复，正在同步数据...');
            }
        });
        
        window.addEventListener('offline', () => {
            console.log('网络连接已断开');
            this.isOnline = false;
            this.onNetworkDisconnect();
            
            // 通知用户
            if (window.feedbackManager) {
                window.feedbackManager.showWarning('网络连接', '网络连接已断开，数据将在连接恢复后同步');
            }
        });
        
        // 定期检查网络状态
        setInterval(() => {
            this.checkNetworkStatus();
        }, 30000);
    }
    
    /**
     * 检查网络状态
     */
    async checkNetworkStatus() {
        try {
            const response = await fetch('/api/v1/health', {
                method: 'HEAD',
                cache: 'no-cache'
            });
            
            const wasOnline = this.isOnline;
            this.isOnline = response.ok;
            
            if (!wasOnline && this.isOnline) {
                this.onNetworkReconnect();
            } else if (wasOnline && !this.isOnline) {
                this.onNetworkDisconnect();
            }
        } catch (error) {
            if (this.isOnline) {
                this.isOnline = false;
                this.onNetworkDisconnect();
            }
        }
    }
    
    /**
     * 网络重连处理
     */
    async onNetworkReconnect() {
        // 处理重试队列
        await this.processRetryQueue();
        
        // 执行完整同步
        await this.performFullSync();
        
        // 恢复定期同步
        this.startPeriodicSync();
        
        // 触发事件
        window.dispatchEvent(new CustomEvent('networkReconnected'));
    }
    
    /**
     * 网络断开处理
     */
    onNetworkDisconnect() {
        // 停止定期同步
        this.stopPeriodicSync();
        
        // 启用离线模式
        this.enableOfflineMode();
        
        // 触发事件
        window.dispatchEvent(new CustomEvent('networkDisconnected'));
    }
    
    /**
     * 设置定期同步
     */
    setupPeriodicSync() {
        this.startPeriodicSync();
    }
    
    /**
     * 开始定期同步
     */
    startPeriodicSync() {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
        }
        
        this.syncInterval = setInterval(() => {
            if (this.isOnline) {
                this.performIncrementalSync();
            }
        }, CONFIG.UI.AUTO_REFRESH_INTERVAL || 30000);
    }
    
    /**
     * 停止定期同步
     */
    stopPeriodicSync() {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
        }
    }
    
    /**
     * 设置冲突解决
     */
    setupConflictResolution() {
        this.conflictResolver = {
            // 智能体状态冲突：服务器优先
            agentStatus: (local, remote) => remote,
            
            // 配置冲突：最新修改时间优先
            configuration: (local, remote) => {
                return new Date(local.updatedAt) > new Date(remote.updatedAt) ? local : remote;
            },
            
            // 任务状态冲突：服务器优先
            taskStatus: (local, remote) => remote,
            
            // 用户设置冲突：本地优先
            userSettings: (local, remote) => local
        };
    }
    
    /**
     * 加载同步状态
     */
    loadSyncState() {
        try {
            const savedState = localStorage.getItem('sync_state');
            if (savedState) {
                const state = JSON.parse(savedState);
                this.lastSyncTime = new Date(state.lastSyncTime);
                this.syncStates = new Map(state.syncStates || []);
            }
        } catch (error) {
            console.error('Failed to load sync state:', error);
        }
    }
    
    /**
     * 保存同步状态
     */
    saveSyncState() {
        try {
            const state = {
                lastSyncTime: this.lastSyncTime,
                syncStates: Array.from(this.syncStates.entries())
            };
            localStorage.setItem('sync_state', JSON.stringify(state));
        } catch (error) {
            console.error('Failed to save sync state:', error);
        }
    }
    
    /**
     * 启动同步工作器
     */
    startSyncWorker() {
        // 处理同步队列
        setInterval(() => {
            this.processSyncQueue();
        }, 1000);
        
        // 处理重试队列
        setInterval(() => {
            this.processRetryQueue();
        }, 5000);
    }
    
    /**
     * 添加同步任务
     */
    addSyncTask(task) {
        const syncTask = {
            id: this.generateId(),
            type: task.type,
            action: task.action,
            data: task.data,
            timestamp: Date.now(),
            retries: 0,
            priority: task.priority || 'normal'
        };
        
        // 根据优先级插入队列
        if (syncTask.priority === 'high') {
            this.syncQueue.unshift(syncTask);
        } else {
            this.syncQueue.push(syncTask);
        }
        
        // 立即处理高优先级任务
        if (syncTask.priority === 'high' && this.isOnline) {
            this.processSyncQueue();
        }
        
        return syncTask.id;
    }
    
    /**
     * 处理同步队列
     */
    async processSyncQueue() {
        if (!this.isOnline || this.syncQueue.length === 0) {
            return;
        }
        
        const task = this.syncQueue.shift();
        
        try {
            await this.executeSyncTask(task);
            this.updateSyncState(task.type, 'success', task.timestamp);
        } catch (error) {
            console.error('Sync task failed:', error);
            this.handleSyncFailure(task, error);
        }
    }
    
    /**
     * 执行同步任务
     */
    async executeSyncTask(task) {
        const { type, action, data } = task;
        
        switch (type) {
            case 'agent':
                return await this.syncAgentData(action, data);
            case 'llmConfig':
                return await this.syncLLMConfig(action, data);
            case 'task':
                return await this.syncTaskData(action, data);
            case 'userSettings':
                return await this.syncUserSettings(action, data);
            default:
                throw new Error(`Unknown sync task type: ${type}`);
        }
    }
    
    /**
     * 同步智能体数据
     */
    async syncAgentData(action, data) {
        switch (action) {
            case 'update':
                return await window.apiClient.put(CONFIG.API.ENDPOINTS.AGENT_DETAIL, data, { id: data.agentId });
            case 'fetch':
                return await window.apiClient.get(CONFIG.API.ENDPOINTS.AGENTS);
            case 'status':
                return await window.apiClient.get(CONFIG.API.ENDPOINTS.AGENT_STATUS);
            default:
                throw new Error(`Unknown agent sync action: ${action}`);
        }
    }
    
    /**
     * 同步大模型配置
     */
    async syncLLMConfig(action, data) {
        const endpoint = '/api/v1/llm/configs';
        
        switch (action) {
            case 'create':
                return await window.apiClient.post(endpoint, data);
            case 'update':
                return await window.apiClient.put(`${endpoint}/${data.id}`, data);
            case 'delete':
                return await window.apiClient.delete(`${endpoint}/${data.id}`);
            case 'fetch':
                return await window.apiClient.get(endpoint);
            default:
                throw new Error(`Unknown LLM config sync action: ${action}`);
        }
    }
    
    /**
     * 同步任务数据
     */
    async syncTaskData(action, data) {
        switch (action) {
            case 'create':
                return await window.apiClient.post(CONFIG.API.ENDPOINTS.TASK_CREATE, data);
            case 'update':
                return await window.apiClient.put(CONFIG.API.ENDPOINTS.TASK_UPDATE, data, { id: data.id });
            case 'delete':
                return await window.apiClient.delete(CONFIG.API.ENDPOINTS.TASK_DELETE, { id: data.id });
            case 'fetch':
                return await window.apiClient.get(CONFIG.API.ENDPOINTS.TASKS);
            default:
                throw new Error(`Unknown task sync action: ${action}`);
        }
    }
    
    /**
     * 同步用户设置
     */
    async syncUserSettings(action, data) {
        const endpoint = '/api/v1/user/settings';
        
        switch (action) {
            case 'update':
                return await window.apiClient.put(endpoint, data);
            case 'fetch':
                return await window.apiClient.get(endpoint);
            default:
                throw new Error(`Unknown user settings sync action: ${action}`);
        }
    }
    
    /**
     * 处理同步失败
     */
    handleSyncFailure(task, error) {
        task.retries++;
        task.lastError = error.message;
        task.nextRetry = Date.now() + (this.retryDelay * Math.pow(2, task.retries - 1));
        
        if (task.retries < this.maxRetries) {
            this.retryQueue.push(task);
        } else {
            console.error(`Sync task failed permanently:`, task);
            this.updateSyncState(task.type, 'failed', task.timestamp, error.message);
            
            // 通知用户
            if (window.feedbackManager) {
                window.feedbackManager.showError(
                    '同步失败',
                    `${task.type} 数据同步失败: ${error.message}`
                );
            }
        }
    }
    
    /**
     * 处理重试队列
     */
    async processRetryQueue() {
        if (!this.isOnline || this.retryQueue.length === 0) {
            return;
        }
        
        const now = Date.now();
        const readyTasks = this.retryQueue.filter(task => task.nextRetry <= now);
        
        for (const task of readyTasks) {
            this.retryQueue = this.retryQueue.filter(t => t.id !== task.id);
            
            try {
                await this.executeSyncTask(task);
                this.updateSyncState(task.type, 'success', task.timestamp);
            } catch (error) {
                this.handleSyncFailure(task, error);
            }
        }
    }
    
    /**
     * 执行完整同步
     */
    async performFullSync() {
        console.log('Performing full sync...');
        
        const syncTasks = [
            { type: 'agent', action: 'fetch', priority: 'high' },
            { type: 'llmConfig', action: 'fetch', priority: 'high' },
            { type: 'task', action: 'fetch', priority: 'normal' },
            { type: 'userSettings', action: 'fetch', priority: 'low' }
        ];
        
        for (const task of syncTasks) {
            this.addSyncTask(task);
        }
        
        this.lastSyncTime = new Date();
        this.saveSyncState();
    }
    
    /**
     * 执行增量同步
     */
    async performIncrementalSync() {
        if (!this.lastSyncTime) {
            return this.performFullSync();
        }
        
        console.log('Performing incremental sync...');
        
        // 只同步可能变化的数据
        const syncTasks = [
            { type: 'agent', action: 'status', priority: 'high' },
            { type: 'task', action: 'fetch', priority: 'normal' }
        ];
        
        for (const task of syncTasks) {
            this.addSyncTask(task);
        }
        
        this.lastSyncTime = new Date();
        this.saveSyncState();
    }
    
    /**
     * 更新同步状态
     */
    updateSyncState(type, status, timestamp, error = null) {
        this.syncStates.set(type, {
            status,
            timestamp,
            error
        });
        
        this.saveSyncState();
        
        // 触发状态更新事件
        window.dispatchEvent(new CustomEvent('syncStateChanged', {
            detail: { type, status, timestamp, error }
        }));
    }
    
    /**
     * 启用离线模式
     */
    enableOfflineMode() {
        document.body.classList.add('offline-mode');
        
        // 显示离线指示器
        this.showOfflineIndicator();
        
        // 启用本地缓存
        this.enableLocalCache();
    }
    
    /**
     * 禁用离线模式
     */
    disableOfflineMode() {
        document.body.classList.remove('offline-mode');
        
        // 隐藏离线指示器
        this.hideOfflineIndicator();
    }
    
    /**
     * 显示离线指示器
     */
    showOfflineIndicator() {
        let indicator = document.querySelector('.offline-indicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'offline-indicator';
            indicator.innerHTML = `
                <div class="offline-content">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M23.64 7c-.45-.34-4.93-4-11.64-4-1.5 0-2.89.19-4.15.48L18.18 13.8 23.64 7zm-6.6 8.22L3.27 1.44 2 2.72l2.05 2.06C1.91 5.76.59 6.82.36 7l11.63 14.49.01.01.01-.01L16.17 16l1.42 1.42 1.41-1.42-.96-.78z"/>
                    </svg>
                    <span>离线模式</span>
                </div>
            `;
            
            indicator.style.cssText = `
                position: fixed;
                top: 10px;
                left: 50%;
                transform: translateX(-50%);
                background: #f59e0b;
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 14px;
                z-index: 1100;
                display: flex;
                align-items: center;
                gap: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            `;
            
            document.body.appendChild(indicator);
        }
        
        indicator.style.display = 'flex';
    }
    
    /**
     * 隐藏离线指示器
     */
    hideOfflineIndicator() {
        const indicator = document.querySelector('.offline-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }
    
    /**
     * 启用本地缓存
     */
    enableLocalCache() {
        // 实现本地数据缓存逻辑
        this.cacheEnabled = true;
    }
    
    /**
     * 检查数据一致性
     */
    async checkDataConsistency(type, localData, remoteData) {
        const conflicts = [];
        
        if (Array.isArray(localData) && Array.isArray(remoteData)) {
            // 数组数据比较
            const localMap = new Map(localData.map(item => [item.id, item]));
            const remoteMap = new Map(remoteData.map(item => [item.id, item]));
            
            // 检查冲突
            for (const [id, localItem] of localMap) {
                const remoteItem = remoteMap.get(id);
                if (remoteItem && this.hasConflict(localItem, remoteItem)) {
                    conflicts.push({
                        id,
                        type,
                        local: localItem,
                        remote: remoteItem
                    });
                }
            }
        } else if (localData && remoteData) {
            // 单个对象比较
            if (this.hasConflict(localData, remoteData)) {
                conflicts.push({
                    type,
                    local: localData,
                    remote: remoteData
                });
            }
        }
        
        return conflicts;
    }
    
    /**
     * 检查是否有冲突
     */
    hasConflict(local, remote) {
        // 比较更新时间
        const localTime = new Date(local.updatedAt || local.timestamp || 0);
        const remoteTime = new Date(remote.updatedAt || remote.timestamp || 0);
        
        // 如果时间差超过阈值且内容不同，则认为有冲突
        const timeDiff = Math.abs(localTime - remoteTime);
        const hasTimeDiff = timeDiff > 1000; // 1秒阈值
        
        if (!hasTimeDiff) {
            return false;
        }
        
        // 简单的内容比较
        const localStr = JSON.stringify(local);
        const remoteStr = JSON.stringify(remote);
        
        return localStr !== remoteStr;
    }
    
    /**
     * 解决数据冲突
     */
    resolveConflicts(conflicts) {
        const resolved = [];
        
        for (const conflict of conflicts) {
            const resolver = this.conflictResolver[conflict.type];
            if (resolver) {
                const resolvedData = resolver(conflict.local, conflict.remote);
                resolved.push({
                    ...conflict,
                    resolved: resolvedData
                });
            } else {
                // 默认使用远程数据
                resolved.push({
                    ...conflict,
                    resolved: conflict.remote
                });
            }
        }
        
        return resolved;
    }
    
    /**
     * 获取同步状态
     */
    getSyncStatus() {
        return {
            isOnline: this.isOnline,
            lastSyncTime: this.lastSyncTime,
            syncStates: Object.fromEntries(this.syncStates),
            queueLength: this.syncQueue.length,
            retryQueueLength: this.retryQueue.length
        };
    }
    
    /**
     * 强制同步
     */
    async forceSync() {
        if (!this.isOnline) {
            throw new Error('Cannot sync while offline');
        }
        
        // 清空队列
        this.syncQueue = [];
        this.retryQueue = [];
        
        // 执行完整同步
        await this.performFullSync();
        
        return this.getSyncStatus();
    }
    
    /**
     * 生成唯一ID
     */
    generateId() {
        return Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * 销毁同步管理器
     */
    destroy() {
        this.stopPeriodicSync();
        this.syncQueue = [];
        this.retryQueue = [];
        this.syncStates.clear();
        
        // 移除事件监听器
        window.removeEventListener('online', this.onNetworkReconnect);
        window.removeEventListener('offline', this.onNetworkDisconnect);
    }
}

// 创建全局实例
window.syncManager = new SyncManager();

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SyncManager;
}