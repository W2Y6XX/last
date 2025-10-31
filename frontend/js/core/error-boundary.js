/**
 * 错误边界组件
 * 防止新功能错误影响现有功能的正常运行
 */
class ErrorBoundary {
    constructor(options = {}) {
        this.componentName = options.componentName || 'Unknown';
        this.fallbackUI = options.fallbackUI || null;
        this.onError = options.onError || null;
        this.isolateErrors = options.isolateErrors !== false;
        this.retryable = options.retryable !== false;
        this.maxRetries = options.maxRetries || 3;
        this.retryDelay = options.retryDelay || 1000;
        
        this.errorState = {
            hasError: false,
            error: null,
            errorInfo: null,
            retryCount: 0,
            lastErrorTime: null
        };
        
        this.boundMethods = new Map();
        this.wrappedElements = new WeakMap();
        this.errorLog = [];
        
        // 绑定错误处理
        this._setupErrorHandling();
    }
    
    /**
     * 设置错误处理
     * @private
     */
    _setupErrorHandling() {
        // 如果有全局错误处理器，注册组件级错误处理
        if (window.errorHandler) {
            window.errorHandler.registerHandler('component', (error) => {
                this._handleComponentError(error);
            });
        }
    }
    
    /**
     * 包装函数以捕获错误
     * @param {Function} fn 要包装的函数
     * @param {string} methodName 方法名称
     * @returns {Function} 包装后的函数
     */
    wrapMethod(fn, methodName = 'anonymous') {
        if (typeof fn !== 'function') {
            return fn;
        }
        
        // 如果已经包装过，直接返回
        if (this.boundMethods.has(fn)) {
            return this.boundMethods.get(fn);
        }
        
        const wrappedFn = (...args) => {
            try {
                // 如果组件处于错误状态且不可重试，返回安全值
                if (this.errorState.hasError && !this.retryable) {
                    console.warn(`${this.componentName}.${methodName} 因错误状态被跳过`);
                    return this._getSafeReturnValue(methodName);
                }
                
                const result = fn.apply(this, args);
                
                // 如果是Promise，包装错误处理
                if (result && typeof result.then === 'function') {
                    return result.catch(error => {
                        this._handleError(error, methodName, args);
                        throw error;
                    });
                }
                
                // 如果执行成功且之前有错误，清除错误状态
                if (this.errorState.hasError && this.errorState.retryCount > 0) {
                    this._clearError();
                }
                
                return result;
                
            } catch (error) {
                this._handleError(error, methodName, args);
                
                // 根据配置决定是否重新抛出错误
                if (this.isolateErrors) {
                    return this._getSafeReturnValue(methodName);
                } else {
                    throw error;
                }
            }
        };
        
        // 保存包装关系
        this.boundMethods.set(fn, wrappedFn);
        
        return wrappedFn;
    }
    
    /**
     * 包装对象的所有方法
     * @param {Object} obj 要包装的对象
     * @param {Array} methodNames 要包装的方法名列表，如果不提供则包装所有方法
     * @returns {Object} 包装后的对象
     */
    wrapObject(obj, methodNames = null) {
        if (!obj || typeof obj !== 'object') {
            return obj;
        }
        
        // 如果已经包装过，直接返回
        if (this.wrappedElements.has(obj)) {
            return this.wrappedElements.get(obj);
        }
        
        const wrappedObj = {};
        const methods = methodNames || Object.getOwnPropertyNames(obj);
        
        methods.forEach(key => {
            const value = obj[key];
            if (typeof value === 'function') {
                wrappedObj[key] = this.wrapMethod(value.bind(obj), key);
            } else {
                wrappedObj[key] = value;
            }
        });
        
        // 保存包装关系
        this.wrappedElements.set(obj, wrappedObj);
        
        return wrappedObj;
    }
    
    /**
     * 包装DOM元素的事件处理器
     * @param {HTMLElement} element DOM元素
     * @param {string} eventType 事件类型
     * @param {Function} handler 事件处理器
     * @param {Object} options 事件选项
     */
    wrapEventHandler(element, eventType, handler, options = {}) {
        if (!element || typeof handler !== 'function') {
            return;
        }
        
        const wrappedHandler = this.wrapMethod(handler, `${eventType}Handler`);
        
        element.addEventListener(eventType, wrappedHandler, options);
        
        // 保存原始处理器的引用，以便后续移除
        if (!element._errorBoundaryHandlers) {
            element._errorBoundaryHandlers = new Map();
        }
        element._errorBoundaryHandlers.set(handler, wrappedHandler);
    }
    
    /**
     * 移除包装的事件处理器
     * @param {HTMLElement} element DOM元素
     * @param {string} eventType 事件类型
     * @param {Function} handler 原始事件处理器
     */
    unwrapEventHandler(element, eventType, handler) {
        if (!element || !element._errorBoundaryHandlers) {
            return;
        }
        
        const wrappedHandler = element._errorBoundaryHandlers.get(handler);
        if (wrappedHandler) {
            element.removeEventListener(eventType, wrappedHandler);
            element._errorBoundaryHandlers.delete(handler);
        }
    }
    
    /**
     * 处理错误
     * @private
     */
    _handleError(error, methodName, args) {
        const errorInfo = {
            componentName: this.componentName,
            methodName,
            error: error.message,
            stack: error.stack,
            args: args ? args.map(arg => this._serializeArg(arg)) : [],
            timestamp: new Date().toISOString(),
            retryCount: this.errorState.retryCount
        };
        
        // 记录错误
        this.errorLog.push(errorInfo);
        this._limitErrorLog();
        
        // 更新错误状态
        this.errorState = {
            hasError: true,
            error,
            errorInfo,
            retryCount: this.errorState.retryCount + 1,
            lastErrorTime: new Date()
        };
        
        // 调用自定义错误处理器
        if (typeof this.onError === 'function') {
            try {
                this.onError(error, errorInfo);
            } catch (handlerError) {
                console.error('错误处理器执行失败:', handlerError);
            }
        }
        
        // 报告到全局错误处理器
        if (window.errorHandler) {
            window.errorHandler.handleError({
                type: 'component',
                message: `${this.componentName}.${methodName}: ${error.message}`,
                error,
                context: 'error_boundary',
                additionalData: errorInfo
            });
        }
        
        // 尝试自动重试
        if (this.retryable && this.errorState.retryCount <= this.maxRetries) {
            this._scheduleRetry(methodName, args);
        }
        
        console.error(`[ErrorBoundary:${this.componentName}] ${methodName} 执行失败:`, error);
    }
    
    /**
     * 处理组件级错误
     * @private
     */
    _handleComponentError(error) {
        if (error.context === 'error_boundary' && 
            error.additionalData?.componentName === this.componentName) {
            // 这是我们自己报告的错误，避免循环处理
            return;
        }
        
        // 处理其他组件错误
        this._handleError(error.error || new Error(error.message), 'componentError', []);
    }
    
    /**
     * 序列化参数用于日志记录
     * @private
     */
    _serializeArg(arg) {
        try {
            if (arg === null || arg === undefined) {
                return arg;
            }
            
            if (typeof arg === 'function') {
                return '[Function]';
            }
            
            if (arg instanceof HTMLElement) {
                return `[HTMLElement:${arg.tagName}]`;
            }
            
            if (typeof arg === 'object') {
                // 避免循环引用
                return JSON.parse(JSON.stringify(arg));
            }
            
            return arg;
        } catch (error) {
            return '[Unserializable]';
        }
    }
    
    /**
     * 限制错误日志大小
     * @private
     */
    _limitErrorLog() {
        const maxLogSize = 100;
        if (this.errorLog.length > maxLogSize) {
            this.errorLog = this.errorLog.slice(-maxLogSize);
        }
    }
    
    /**
     * 获取安全的返回值
     * @private
     */
    _getSafeReturnValue(methodName) {
        // 根据方法名推断合适的返回值
        if (methodName.includes('get') || methodName.includes('find')) {
            return null;
        }
        
        if (methodName.includes('is') || methodName.includes('has') || methodName.includes('can')) {
            return false;
        }
        
        if (methodName.includes('list') || methodName.includes('all')) {
            return [];
        }
        
        if (methodName.includes('count') || methodName.includes('length')) {
            return 0;
        }
        
        return undefined;
    }
    
    /**
     * 安排重试
     * @private
     */
    _scheduleRetry(methodName, args) {
        const delay = this.retryDelay * Math.pow(2, this.errorState.retryCount - 1); // 指数退避
        
        setTimeout(() => {
            console.log(`[ErrorBoundary:${this.componentName}] 重试 ${methodName} (第${this.errorState.retryCount}次)`);
            
            try {
                // 这里应该重新执行原始方法，但由于我们无法直接访问，
                // 只能清除错误状态，让下次调用时重试
                this._clearError();
            } catch (retryError) {
                console.error(`[ErrorBoundary:${this.componentName}] 重试失败:`, retryError);
            }
        }, delay);
    }
    
    /**
     * 清除错误状态
     * @private
     */
    _clearError() {
        this.errorState = {
            hasError: false,
            error: null,
            errorInfo: null,
            retryCount: 0,
            lastErrorTime: null
        };
        
        console.log(`[ErrorBoundary:${this.componentName}] 错误状态已清除`);
    }
    
    /**
     * 检查是否有错误
     * @returns {boolean} 是否有错误
     */
    hasError() {
        return this.errorState.hasError;
    }
    
    /**
     * 获取错误信息
     * @returns {Object|null} 错误信息
     */
    getError() {
        return this.errorState.hasError ? {
            error: this.errorState.error,
            errorInfo: this.errorState.errorInfo,
            retryCount: this.errorState.retryCount,
            lastErrorTime: this.errorState.lastErrorTime
        } : null;
    }
    
    /**
     * 手动清除错误
     */
    clearError() {
        this._clearError();
    }
    
    /**
     * 手动重试
     * @returns {boolean} 是否可以重试
     */
    retry() {
        if (this.errorState.hasError && this.retryable && 
            this.errorState.retryCount <= this.maxRetries) {
            this._clearError();
            return true;
        }
        return false;
    }
    
    /**
     * 获取错误日志
     * @param {number} limit 限制数量
     * @returns {Array} 错误日志
     */
    getErrorLog(limit = 10) {
        return this.errorLog.slice(-limit);
    }
    
    /**
     * 清除错误日志
     */
    clearErrorLog() {
        this.errorLog = [];
    }
    
    /**
     * 渲染降级UI
     * @param {HTMLElement} container 容器元素
     */
    renderFallbackUI(container) {
        if (!container || !this.errorState.hasError) {
            return;
        }
        
        // 如果有自定义降级UI
        if (typeof this.fallbackUI === 'function') {
            try {
                this.fallbackUI(container, this.errorState);
                return;
            } catch (error) {
                console.error('渲染自定义降级UI失败:', error);
            }
        }
        
        // 默认降级UI
        container.innerHTML = `
            <div class="error-boundary-fallback">
                <div class="error-icon">⚠️</div>
                <div class="error-message">
                    <h4>组件暂时不可用</h4>
                    <p>${this.componentName} 遇到了问题，正在尝试恢复。</p>
                    ${this.retryable ? `
                        <button class="retry-button" onclick="this.parentElement.parentElement.parentElement.errorBoundary?.retry()">
                            重试 (${this.errorState.retryCount}/${this.maxRetries})
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
        
        // 保存错误边界引用到DOM元素
        container.errorBoundary = this;
        
        // 添加样式
        this._addFallbackStyles();
    }
    
    /**
     * 添加降级UI样式
     * @private
     */
    _addFallbackStyles() {
        const styleId = 'error-boundary-styles';
        if (document.getElementById(styleId)) {
            return;
        }
        
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .error-boundary-fallback {
                display: flex;
                align-items: center;
                padding: 20px;
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                margin: 10px 0;
            }
            
            .error-boundary-fallback .error-icon {
                font-size: 24px;
                margin-right: 15px;
            }
            
            .error-boundary-fallback .error-message h4 {
                margin: 0 0 8px 0;
                color: #dc2626;
                font-size: 16px;
            }
            
            .error-boundary-fallback .error-message p {
                margin: 0 0 12px 0;
                color: #7f1d1d;
                font-size: 14px;
            }
            
            .error-boundary-fallback .retry-button {
                background-color: #dc2626;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }
            
            .error-boundary-fallback .retry-button:hover {
                background-color: #b91c1c;
            }
        `;
        
        document.head.appendChild(style);
    }
    
    /**
     * 获取统计信息
     * @returns {Object} 统计信息
     */
    getStats() {
        return {
            componentName: this.componentName,
            hasError: this.errorState.hasError,
            totalErrors: this.errorLog.length,
            retryCount: this.errorState.retryCount,
            maxRetries: this.maxRetries,
            lastErrorTime: this.errorState.lastErrorTime,
            wrappedMethods: this.boundMethods.size,
            wrappedObjects: this.wrappedElements.size || 0
        };
    }
    
    /**
     * 销毁错误边界
     */
    destroy() {
        this.boundMethods.clear();
        this.errorLog = [];
        this._clearError();
        
        // 移除全局错误处理器
        if (window.errorHandler) {
            window.errorHandler.unregisterHandler('component');
        }
    }
}

/**
 * 创建错误边界装饰器
 * @param {Object} options 选项
 * @returns {Function} 装饰器函数
 */
function withErrorBoundary(options = {}) {
    return function(target) {
        const errorBoundary = new ErrorBoundary({
            componentName: target.name || 'Component',
            ...options
        });
        
        // 包装类的所有方法
        const prototype = target.prototype;
        const methodNames = Object.getOwnPropertyNames(prototype);
        
        methodNames.forEach(methodName => {
            if (methodName !== 'constructor' && typeof prototype[methodName] === 'function') {
                const originalMethod = prototype[methodName];
                prototype[methodName] = errorBoundary.wrapMethod(originalMethod, methodName);
            }
        });
        
        // 添加错误边界实例到类
        target.prototype._errorBoundary = errorBoundary;
        
        return target;
    };
}

// 导出类和装饰器
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ErrorBoundary, withErrorBoundary };
} else {
    window.ErrorBoundary = ErrorBoundary;
    window.withErrorBoundary = withErrorBoundary;
}