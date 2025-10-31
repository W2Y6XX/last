/**
 * 性能优化管理器
 * 处理界面加载和渲染性能优化
 */
class PerformanceManager {
    constructor() {
        this.observers = new Map();
        this.loadingStates = new Map();
        this.renderQueue = [];
        this.isProcessingQueue = false;
        this.performanceMetrics = {
            loadTime: 0,
            renderTime: 0,
            interactionTime: 0
        };
        
        this.init();
    }
    
    /**
     * 初始化性能管理器
     */
    init() {
        this.setupIntersectionObserver();
        this.setupPerformanceMonitoring();
        this.setupLazyLoading();
        this.setupImageOptimization();
        this.measureInitialLoad();
    }
    
    /**
     * 设置交叉观察器（用于懒加载）
     */
    setupIntersectionObserver() {
        if ('IntersectionObserver' in window) {
            // 懒加载观察器
            this.lazyObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.loadLazyElement(entry.target);
                        this.lazyObserver.unobserve(entry.target);
                    }
                });
            }, {
                rootMargin: '50px 0px',
                threshold: 0.1
            });
            
            // 动画观察器
            this.animationObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('animate-in');
                    }
                });
            }, {
                threshold: 0.2
            });
        }
    }
    
    /**
     * 设置性能监控
     */
    setupPerformanceMonitoring() {
        // 监控页面加载性能
        if ('performance' in window) {
            window.addEventListener('load', () => {
                setTimeout(() => {
                    this.collectPerformanceMetrics();
                }, 0);
            });
        }
        
        // 监控长任务
        if ('PerformanceObserver' in window) {
            try {
                const longTaskObserver = new PerformanceObserver((list) => {
                    list.getEntries().forEach(entry => {
                        if (entry.duration > 50) {
                            console.warn(`Long task detected: ${entry.duration}ms`);
                        }
                    });
                });
                longTaskObserver.observe({ entryTypes: ['longtask'] });
            } catch (e) {
                // 某些浏览器可能不支持longtask
            }
        }
    }
    
    /**
     * 收集性能指标
     */
    collectPerformanceMetrics() {
        const navigation = performance.getEntriesByType('navigation')[0];
        if (navigation) {
            this.performanceMetrics = {
                loadTime: navigation.loadEventEnd - navigation.loadEventStart,
                domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
                firstPaint: this.getFirstPaint(),
                firstContentfulPaint: this.getFirstContentfulPaint(),
                largestContentfulPaint: this.getLargestContentfulPaint()
            };
            
            console.log('Performance Metrics:', this.performanceMetrics);
        }
    }
    
    /**
     * 获取首次绘制时间
     */
    getFirstPaint() {
        const paintEntries = performance.getEntriesByType('paint');
        const firstPaint = paintEntries.find(entry => entry.name === 'first-paint');
        return firstPaint ? firstPaint.startTime : 0;
    }
    
    /**
     * 获取首次内容绘制时间
     */
    getFirstContentfulPaint() {
        const paintEntries = performance.getEntriesByType('paint');
        const fcp = paintEntries.find(entry => entry.name === 'first-contentful-paint');
        return fcp ? fcp.startTime : 0;
    }
    
    /**
     * 获取最大内容绘制时间
     */
    getLargestContentfulPaint() {
        return new Promise((resolve) => {
            if ('PerformanceObserver' in window) {
                try {
                    const observer = new PerformanceObserver((list) => {
                        const entries = list.getEntries();
                        const lastEntry = entries[entries.length - 1];
                        resolve(lastEntry.startTime);
                    });
                    observer.observe({ entryTypes: ['largest-contentful-paint'] });
                    
                    // 超时处理
                    setTimeout(() => resolve(0), 5000);
                } catch (e) {
                    resolve(0);
                }
            } else {
                resolve(0);
            }
        });
    }
    
    /**
     * 设置懒加载
     */
    setupLazyLoading() {
        // 为所有懒加载元素添加观察
        this.observeLazyElements();
        
        // 监听DOM变化，为新添加的元素设置懒加载
        if ('MutationObserver' in window) {
            const mutationObserver = new MutationObserver((mutations) => {
                mutations.forEach(mutation => {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            this.observeLazyElements(node);
                        }
                    });
                });
            });
            
            mutationObserver.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    }
    
    /**
     * 观察懒加载元素
     */
    observeLazyElements(container = document) {
        if (!this.lazyObserver) return;
        
        const lazyElements = container.querySelectorAll('[data-lazy], .lazy-load');
        lazyElements.forEach(element => {
            this.lazyObserver.observe(element);
        });
        
        const animateElements = container.querySelectorAll('.animate-on-scroll');
        animateElements.forEach(element => {
            if (this.animationObserver) {
                this.animationObserver.observe(element);
            }
        });
    }
    
    /**
     * 加载懒加载元素
     */
    loadLazyElement(element) {
        const src = element.dataset.lazy || element.dataset.src;
        
        if (element.tagName === 'IMG' && src) {
            // 图片懒加载
            const img = new Image();
            img.onload = () => {
                element.src = src;
                element.classList.add('loaded');
                element.removeAttribute('data-lazy');
            };
            img.onerror = () => {
                element.classList.add('error');
            };
            img.src = src;
        } else if (element.dataset.component) {
            // 组件懒加载
            this.loadLazyComponent(element);
        } else if (element.dataset.content) {
            // 内容懒加载
            this.loadLazyContent(element);
        }
    }
    
    /**
     * 懒加载组件
     */
    async loadLazyComponent(element) {
        const componentName = element.dataset.component;
        const componentData = element.dataset.componentData ? 
            JSON.parse(element.dataset.componentData) : {};
        
        try {
            // 显示加载状态
            this.showLoadingState(element);
            
            // 动态加载组件
            const component = await this.loadComponent(componentName);
            if (component) {
                await component.render(element, componentData);
                element.classList.add('loaded');
            }
        } catch (error) {
            console.error(`Failed to load component ${componentName}:`, error);
            element.classList.add('error');
        } finally {
            this.hideLoadingState(element);
        }
    }
    
    /**
     * 懒加载内容
     */
    async loadLazyContent(element) {
        const contentUrl = element.dataset.content;
        
        try {
            this.showLoadingState(element);
            
            const response = await fetch(contentUrl);
            if (response.ok) {
                const content = await response.text();
                element.innerHTML = content;
                element.classList.add('loaded');
            }
        } catch (error) {
            console.error(`Failed to load content from ${contentUrl}:`, error);
            element.classList.add('error');
        } finally {
            this.hideLoadingState(element);
        }
    }
    
    /**
     * 动态加载组件
     */
    async loadComponent(componentName) {
        try {
            const module = await import(`../components/${componentName}.js`);
            return module.default || module;
        } catch (error) {
            console.error(`Failed to import component ${componentName}:`, error);
            return null;
        }
    }
    
    /**
     * 设置图片优化
     */
    setupImageOptimization() {
        // 为所有图片添加加载优化
        const images = document.querySelectorAll('img');
        images.forEach(img => this.optimizeImage(img));
        
        // 监听新添加的图片
        if ('MutationObserver' in window) {
            const imageObserver = new MutationObserver((mutations) => {
                mutations.forEach(mutation => {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            if (node.tagName === 'IMG') {
                                this.optimizeImage(node);
                            } else {
                                const images = node.querySelectorAll('img');
                                images.forEach(img => this.optimizeImage(img));
                            }
                        }
                    });
                });
            });
            
            imageObserver.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    }
    
    /**
     * 优化图片
     */
    optimizeImage(img) {
        // 添加加载状态
        img.addEventListener('load', () => {
            img.classList.add('loaded');
        });
        
        img.addEventListener('error', () => {
            img.classList.add('error');
            // 设置默认图片
            if (!img.dataset.fallback) {
                img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIE5vdCBGb3VuZDwvdGV4dD48L3N2Zz4=';
            }
        });
        
        // 设置合适的loading属性
        if ('loading' in HTMLImageElement.prototype) {
            img.loading = 'lazy';
        }
    }
    
    /**
     * 显示加载状态
     */
    showLoadingState(element, message = '加载中...') {
        const loadingId = this.generateId();
        this.loadingStates.set(element, loadingId);
        
        // 创建加载指示器
        const loader = document.createElement('div');
        loader.className = 'loading-indicator';
        loader.dataset.loadingId = loadingId;
        loader.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-text">${message}</div>
        `;
        
        // 添加样式
        loader.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            z-index: 10;
        `;
        
        // 设置容器为相对定位
        if (getComputedStyle(element).position === 'static') {
            element.style.position = 'relative';
        }
        
        element.appendChild(loader);
        element.classList.add('loading');
    }
    
    /**
     * 隐藏加载状态
     */
    hideLoadingState(element) {
        const loadingId = this.loadingStates.get(element);
        if (loadingId) {
            const loader = element.querySelector(`[data-loading-id="${loadingId}"]`);
            if (loader) {
                loader.remove();
            }
            this.loadingStates.delete(element);
            element.classList.remove('loading');
        }
    }
    
    /**
     * 批量渲染优化
     */
    batchRender(renderFunction) {
        this.renderQueue.push(renderFunction);
        
        if (!this.isProcessingQueue) {
            this.processRenderQueue();
        }
    }
    
    /**
     * 处理渲染队列
     */
    processRenderQueue() {
        if (this.renderQueue.length === 0) {
            this.isProcessingQueue = false;
            return;
        }
        
        this.isProcessingQueue = true;
        
        requestAnimationFrame(() => {
            const startTime = performance.now();
            
            // 处理队列中的渲染任务，但限制执行时间
            while (this.renderQueue.length > 0 && (performance.now() - startTime) < 16) {
                const renderFunction = this.renderQueue.shift();
                try {
                    renderFunction();
                } catch (error) {
                    console.error('Render function error:', error);
                }
            }
            
            // 继续处理剩余任务
            this.processRenderQueue();
        });
    }
    
    /**
     * 防抖函数
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    /**
     * 节流函数
     */
    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
    
    /**
     * 测量初始加载时间
     */
    measureInitialLoad() {
        const startTime = performance.now();
        
        window.addEventListener('load', () => {
            const loadTime = performance.now() - startTime;
            console.log(`Initial load time: ${loadTime.toFixed(2)}ms`);
            
            // 发送性能数据（如果需要）
            this.reportPerformance({
                loadTime,
                timestamp: Date.now(),
                userAgent: navigator.userAgent,
                viewport: {
                    width: window.innerWidth,
                    height: window.innerHeight
                }
            });
        });
    }
    
    /**
     * 报告性能数据
     */
    reportPerformance(data) {
        // 这里可以发送到分析服务
        console.log('Performance data:', data);
        
        // 存储到本地存储用于调试
        if (CONFIG.FEATURES.DEBUG_MODE) {
            const perfData = JSON.parse(localStorage.getItem('performance_data') || '[]');
            perfData.push(data);
            
            // 只保留最近50条记录
            if (perfData.length > 50) {
                perfData.splice(0, perfData.length - 50);
            }
            
            localStorage.setItem('performance_data', JSON.stringify(perfData));
        }
    }
    
    /**
     * 生成唯一ID
     */
    generateId() {
        return Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * 获取性能指标
     */
    getPerformanceMetrics() {
        return { ...this.performanceMetrics };
    }
    
    /**
     * 清理资源
     */
    cleanup() {
        if (this.lazyObserver) {
            this.lazyObserver.disconnect();
        }
        
        if (this.animationObserver) {
            this.animationObserver.disconnect();
        }
        
        this.observers.clear();
        this.loadingStates.clear();
        this.renderQueue = [];
    }
}

// 创建全局实例
window.performanceManager = new PerformanceManager();

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PerformanceManager;
}