/**
 * 用户反馈和状态指示管理器
 * 处理操作反馈、加载状态、进度指示和确认对话框
 */
class FeedbackManager {
    constructor() {
        this.notifications = new Map();
        this.loadingStates = new Map();
        this.progressBars = new Map();
        this.confirmDialogs = new Map();
        this.toastContainer = null;
        this.modalContainer = null;
        
        this.init();
    }
    
    /**
     * 初始化反馈管理器
     */
    init() {
        this.createToastContainer();
        this.createModalContainer();
        this.setupGlobalStyles();
        this.setupKeyboardHandlers();
    }
    
    /**
     * 创建通知容器
     */
    createToastContainer() {
        this.toastContainer = document.createElement('div');
        this.toastContainer.id = 'toast-container';
        this.toastContainer.className = 'toast-container';
        this.toastContainer.setAttribute('aria-live', 'polite');
        this.toastContainer.setAttribute('aria-atomic', 'true');
        
        document.body.appendChild(this.toastContainer);
    }
    
    /**
     * 创建模态框容器
     */
    createModalContainer() {
        this.modalContainer = document.createElement('div');
        this.modalContainer.id = 'modal-container';
        this.modalContainer.className = 'modal-container';
        
        document.body.appendChild(this.modalContainer);
    }
    
    /**
     * 设置全局样式
     */
    setupGlobalStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* 通知样式 */
            .toast-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1050;
                max-width: 400px;
                pointer-events: none;
            }
            
            .toast {
                background: var(--toast-bg, #1f2937);
                border: 1px solid var(--toast-border, #374151);
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 12px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
                pointer-events: auto;
                transform: translateX(100%);
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            
            .toast.show {
                transform: translateX(0);
            }
            
            .toast.hide {
                transform: translateX(100%);
                opacity: 0;
            }
            
            .toast::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 4px;
                height: 100%;
                background: var(--toast-accent, #3b82f6);
            }
            
            .toast.success::before { background: #10b981; }
            .toast.error::before { background: #ef4444; }
            .toast.warning::before { background: #f59e0b; }
            .toast.info::before { background: #3b82f6; }
            
            .toast-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 8px;
            }
            
            .toast-title {
                font-weight: 600;
                color: var(--toast-title-color, #f3f4f6);
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .toast-icon {
                width: 20px;
                height: 20px;
                flex-shrink: 0;
            }
            
            .toast-close {
                background: none;
                border: none;
                color: var(--toast-close-color, #9ca3af);
                cursor: pointer;
                padding: 4px;
                border-radius: 4px;
                transition: all 0.2s ease;
            }
            
            .toast-close:hover {
                background: var(--toast-close-hover, #374151);
                color: var(--toast-close-hover-color, #f3f4f6);
            }
            
            .toast-body {
                color: var(--toast-body-color, #d1d5db);
                line-height: 1.5;
            }
            
            .toast-progress {
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background: var(--toast-accent, #3b82f6);
                transition: width 0.1s linear;
            }
            
            /* 加载指示器样式 */
            .loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1040;
                backdrop-filter: blur(2px);
            }
            
            .loading-spinner {
                width: 40px;
                height: 40px;
                border: 3px solid var(--spinner-track, #374151);
                border-top: 3px solid var(--spinner-color, #3b82f6);
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            .loading-content {
                background: var(--loading-bg, #1f2937);
                border-radius: 12px;
                padding: 32px;
                text-align: center;
                max-width: 300px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            }
            
            .loading-text {
                margin-top: 16px;
                color: var(--loading-text-color, #f3f4f6);
                font-weight: 500;
            }
            
            /* 进度条样式 */
            .progress-bar {
                width: 100%;
                height: 8px;
                background: var(--progress-track, #374151);
                border-radius: 4px;
                overflow: hidden;
                position: relative;
            }
            
            .progress-fill {
                height: 100%;
                background: var(--progress-color, #3b82f6);
                border-radius: 4px;
                transition: width 0.3s ease;
                position: relative;
            }
            
            .progress-fill::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                bottom: 0;
                right: 0;
                background: linear-gradient(
                    90deg,
                    transparent,
                    rgba(255, 255, 255, 0.2),
                    transparent
                );
                animation: shimmer 2s infinite;
            }
            
            .progress-text {
                margin-top: 8px;
                font-size: 14px;
                color: var(--progress-text-color, #9ca3af);
                text-align: center;
            }
            
            /* 确认对话框样式 */
            .confirm-dialog {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.75);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1060;
                padding: 20px;
            }
            
            .confirm-content {
                background: var(--confirm-bg, #1f2937);
                border-radius: 12px;
                padding: 24px;
                max-width: 400px;
                width: 100%;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
                animation: confirmSlideIn 0.3s ease;
            }
            
            .confirm-header {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 16px;
            }
            
            .confirm-icon {
                width: 24px;
                height: 24px;
                flex-shrink: 0;
            }
            
            .confirm-title {
                font-size: 18px;
                font-weight: 600;
                color: var(--confirm-title-color, #f3f4f6);
            }
            
            .confirm-body {
                color: var(--confirm-body-color, #d1d5db);
                line-height: 1.5;
                margin-bottom: 24px;
            }
            
            .confirm-actions {
                display: flex;
                gap: 12px;
                justify-content: flex-end;
            }
            
            .confirm-btn {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
                min-width: 80px;
            }
            
            .confirm-btn-primary {
                background: var(--primary-color, #3b82f6);
                color: white;
            }
            
            .confirm-btn-primary:hover {
                background: var(--primary-hover, #2563eb);
            }
            
            .confirm-btn-secondary {
                background: var(--secondary-color, #6b7280);
                color: white;
            }
            
            .confirm-btn-secondary:hover {
                background: var(--secondary-hover, #4b5563);
            }
            
            /* 动画 */
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            @keyframes shimmer {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
            }
            
            @keyframes confirmSlideIn {
                from {
                    opacity: 0;
                    transform: scale(0.9) translateY(-20px);
                }
                to {
                    opacity: 1;
                    transform: scale(1) translateY(0);
                }
            }
            
            /* 响应式适配 */
            @media (max-width: 768px) {
                .toast-container {
                    top: 10px;
                    right: 10px;
                    left: 10px;
                    max-width: none;
                }
                
                .toast {
                    margin-bottom: 8px;
                }
                
                .loading-content {
                    padding: 24px;
                    margin: 0 20px;
                }
                
                .confirm-content {
                    margin: 0 20px;
                }
                
                .confirm-actions {
                    flex-direction: column;
                }
                
                .confirm-btn {
                    width: 100%;
                }
            }
        `;
        
        document.head.appendChild(style);
    }
    
    /**
     * 设置键盘处理器
     */
    setupKeyboardHandlers() {
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                // 关闭最新的确认对话框
                const dialogs = Array.from(this.confirmDialogs.values());
                if (dialogs.length > 0) {
                    const latestDialog = dialogs[dialogs.length - 1];
                    if (latestDialog.onCancel) {
                        latestDialog.onCancel();
                    }
                }
            }
        });
    }
    
    /**
     * 显示通知
     */
    showNotification(options) {
        const {
            type = 'info',
            title = '',
            message = '',
            duration = 5000,
            persistent = false,
            actions = []
        } = options;
        
        const id = this.generateId();
        const toast = this.createToast(id, type, title, message, actions);
        
        this.toastContainer.appendChild(toast);
        
        // 触发显示动画
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        // 自动隐藏
        if (!persistent && duration > 0) {
            const progressBar = toast.querySelector('.toast-progress');
            if (progressBar) {
                progressBar.style.width = '100%';
                progressBar.style.transition = `width ${duration}ms linear`;
                setTimeout(() => {
                    progressBar.style.width = '0%';
                }, 10);
            }
            
            setTimeout(() => {
                this.hideNotification(id);
            }, duration);
        }
        
        this.notifications.set(id, {
            element: toast,
            type,
            title,
            message,
            duration,
            persistent
        });
        
        return id;
    }
    
    /**
     * 创建通知元素
     */
    createToast(id, type, title, message, actions) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.dataset.toastId = id;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        
        const icon = this.getIcon(type);
        
        toast.innerHTML = `
            <div class="toast-header">
                <div class="toast-title">
                    ${icon}
                    ${title}
                </div>
                <button class="toast-close" aria-label="关闭通知">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                    </svg>
                </button>
            </div>
            <div class="toast-body">${message}</div>
            ${actions.length > 0 ? this.createActionButtons(actions) : ''}
            <div class="toast-progress"></div>
        `;
        
        // 绑定关闭事件
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => {
            this.hideNotification(id);
        });
        
        // 绑定动作按钮事件
        actions.forEach((action, index) => {
            const btn = toast.querySelector(`[data-action-index="${index}"]`);
            if (btn && action.handler) {
                btn.addEventListener('click', () => {
                    action.handler();
                    if (action.closeOnClick !== false) {
                        this.hideNotification(id);
                    }
                });
            }
        });
        
        return toast;
    }
    
    /**
     * 创建动作按钮
     */
    createActionButtons(actions) {
        const buttonsHtml = actions.map((action, index) => `
            <button class="toast-action-btn" data-action-index="${index}">
                ${action.text}
            </button>
        `).join('');
        
        return `<div class="toast-actions">${buttonsHtml}</div>`;
    }
    
    /**
     * 获取图标
     */
    getIcon(type) {
        const icons = {
            success: `<svg class="toast-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
            </svg>`,
            error: `<svg class="toast-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>`,
            warning: `<svg class="toast-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/>
            </svg>`,
            info: `<svg class="toast-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
            </svg>`
        };
        
        return icons[type] || icons.info;
    }
    
    /**
     * 隐藏通知
     */
    hideNotification(id) {
        const notification = this.notifications.get(id);
        if (notification) {
            const toast = notification.element;
            toast.classList.add('hide');
            
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
                this.notifications.delete(id);
            }, 300);
        }
    }
    
    /**
     * 显示成功通知
     */
    showSuccess(title, message, options = {}) {
        return this.showNotification({
            type: 'success',
            title,
            message,
            ...options
        });
    }
    
    /**
     * 显示错误通知
     */
    showError(title, message, options = {}) {
        return this.showNotification({
            type: 'error',
            title,
            message,
            duration: 8000, // 错误通知显示更长时间
            ...options
        });
    }
    
    /**
     * 显示警告通知
     */
    showWarning(title, message, options = {}) {
        return this.showNotification({
            type: 'warning',
            title,
            message,
            ...options
        });
    }
    
    /**
     * 显示信息通知
     */
    showInfo(title, message, options = {}) {
        return this.showNotification({
            type: 'info',
            title,
            message,
            ...options
        });
    }
    
    /**
     * 显示加载状态
     */
    showLoading(message = '加载中...', options = {}) {
        const {
            overlay = true,
            spinner = true,
            cancellable = false
        } = options;
        
        const id = this.generateId();
        const loadingElement = this.createLoadingElement(id, message, spinner, cancellable);
        
        if (overlay) {
            document.body.appendChild(loadingElement);
        }
        
        this.loadingStates.set(id, {
            element: loadingElement,
            message,
            overlay
        });
        
        return id;
    }
    
    /**
     * 创建加载元素
     */
    createLoadingElement(id, message, spinner, cancellable) {
        const loading = document.createElement('div');
        loading.className = 'loading-overlay';
        loading.dataset.loadingId = id;
        loading.setAttribute('role', 'status');
        loading.setAttribute('aria-live', 'polite');
        
        loading.innerHTML = `
            <div class="loading-content">
                ${spinner ? '<div class="loading-spinner"></div>' : ''}
                <div class="loading-text">${message}</div>
                ${cancellable ? '<button class="loading-cancel">取消</button>' : ''}
            </div>
        `;
        
        if (cancellable) {
            const cancelBtn = loading.querySelector('.loading-cancel');
            cancelBtn.addEventListener('click', () => {
                this.hideLoading(id);
            });
        }
        
        return loading;
    }
    
    /**
     * 隐藏加载状态
     */
    hideLoading(id) {
        const loading = this.loadingStates.get(id);
        if (loading) {
            const element = loading.element;
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
            this.loadingStates.delete(id);
        }
    }
    
    /**
     * 更新加载消息
     */
    updateLoadingMessage(id, message) {
        const loading = this.loadingStates.get(id);
        if (loading) {
            const textElement = loading.element.querySelector('.loading-text');
            if (textElement) {
                textElement.textContent = message;
            }
        }
    }
    
    /**
     * 显示进度条
     */
    showProgress(container, options = {}) {
        const {
            value = 0,
            max = 100,
            text = '',
            color = '#3b82f6'
        } = options;
        
        const id = this.generateId();
        const progressElement = this.createProgressElement(id, value, max, text, color);
        
        if (typeof container === 'string') {
            container = document.querySelector(container);
        }
        
        if (container) {
            container.appendChild(progressElement);
        }
        
        this.progressBars.set(id, {
            element: progressElement,
            container,
            value,
            max
        });
        
        return id;
    }
    
    /**
     * 创建进度条元素
     */
    createProgressElement(id, value, max, text, color) {
        const progress = document.createElement('div');
        progress.className = 'progress-container';
        progress.dataset.progressId = id;
        
        const percentage = Math.round((value / max) * 100);
        
        progress.innerHTML = `
            <div class="progress-bar" role="progressbar" aria-valuenow="${value}" aria-valuemin="0" aria-valuemax="${max}">
                <div class="progress-fill" style="width: ${percentage}%; background-color: ${color};"></div>
            </div>
            ${text ? `<div class="progress-text">${text}</div>` : ''}
        `;
        
        return progress;
    }
    
    /**
     * 更新进度条
     */
    updateProgress(id, value, text = null) {
        const progress = this.progressBars.get(id);
        if (progress) {
            const percentage = Math.round((value / progress.max) * 100);
            const fillElement = progress.element.querySelector('.progress-fill');
            const textElement = progress.element.querySelector('.progress-text');
            
            if (fillElement) {
                fillElement.style.width = `${percentage}%`;
            }
            
            if (text && textElement) {
                textElement.textContent = text;
            }
            
            // 更新ARIA属性
            const progressBar = progress.element.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.setAttribute('aria-valuenow', value);
            }
            
            progress.value = value;
        }
    }
    
    /**
     * 隐藏进度条
     */
    hideProgress(id) {
        const progress = this.progressBars.get(id);
        if (progress) {
            const element = progress.element;
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
            this.progressBars.delete(id);
        }
    }
    
    /**
     * 显示确认对话框
     */
    showConfirm(options) {
        const {
            title = '确认操作',
            message = '您确定要执行此操作吗？',
            confirmText = '确认',
            cancelText = '取消',
            type = 'warning',
            onConfirm = null,
            onCancel = null
        } = options;
        
        return new Promise((resolve) => {
            const id = this.generateId();
            const dialog = this.createConfirmDialog(id, title, message, confirmText, cancelText, type);
            
            this.modalContainer.appendChild(dialog);
            
            // 焦点管理
            const confirmBtn = dialog.querySelector('.confirm-btn-primary');
            if (confirmBtn) {
                confirmBtn.focus();
            }
            
            const handleConfirm = () => {
                this.hideConfirm(id);
                if (onConfirm) onConfirm();
                resolve(true);
            };
            
            const handleCancel = () => {
                this.hideConfirm(id);
                if (onCancel) onCancel();
                resolve(false);
            };
            
            this.confirmDialogs.set(id, {
                element: dialog,
                onConfirm: handleConfirm,
                onCancel: handleCancel
            });
            
            // 绑定事件
            const confirmBtnEl = dialog.querySelector('.confirm-btn-primary');
            const cancelBtnEl = dialog.querySelector('.confirm-btn-secondary');
            
            if (confirmBtnEl) {
                confirmBtnEl.addEventListener('click', handleConfirm);
            }
            
            if (cancelBtnEl) {
                cancelBtnEl.addEventListener('click', handleCancel);
            }
            
            // 点击背景关闭
            dialog.addEventListener('click', (event) => {
                if (event.target === dialog) {
                    handleCancel();
                }
            });
        });
    }
    
    /**
     * 创建确认对话框
     */
    createConfirmDialog(id, title, message, confirmText, cancelText, type) {
        const dialog = document.createElement('div');
        dialog.className = 'confirm-dialog';
        dialog.dataset.confirmId = id;
        dialog.setAttribute('role', 'dialog');
        dialog.setAttribute('aria-modal', 'true');
        dialog.setAttribute('aria-labelledby', `confirm-title-${id}`);
        
        const icon = this.getIcon(type);
        
        dialog.innerHTML = `
            <div class="confirm-content">
                <div class="confirm-header">
                    ${icon}
                    <div class="confirm-title" id="confirm-title-${id}">${title}</div>
                </div>
                <div class="confirm-body">${message}</div>
                <div class="confirm-actions">
                    <button class="confirm-btn confirm-btn-secondary">${cancelText}</button>
                    <button class="confirm-btn confirm-btn-primary">${confirmText}</button>
                </div>
            </div>
        `;
        
        return dialog;
    }
    
    /**
     * 隐藏确认对话框
     */
    hideConfirm(id) {
        const dialog = this.confirmDialogs.get(id);
        if (dialog) {
            const element = dialog.element;
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
            this.confirmDialogs.delete(id);
        }
    }
    
    /**
     * 生成唯一ID
     */
    generateId() {
        return Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * 清理所有反馈元素
     */
    cleanup() {
        // 清理通知
        this.notifications.forEach((notification, id) => {
            this.hideNotification(id);
        });
        
        // 清理加载状态
        this.loadingStates.forEach((loading, id) => {
            this.hideLoading(id);
        });
        
        // 清理进度条
        this.progressBars.forEach((progress, id) => {
            this.hideProgress(id);
        });
        
        // 清理确认对话框
        this.confirmDialogs.forEach((dialog, id) => {
            this.hideConfirm(id);
        });
    }
}

// 创建全局实例
window.feedbackManager = new FeedbackManager();

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FeedbackManager;
}