/**
 * 响应式交互管理器
 * 处理不同设备的交互优化和响应式行为
 */
class ResponsiveManager {
    constructor() {
        this.breakpoints = {
            mobile: 768,
            tablet: 1024,
            desktop: 1200
        };
        
        this.currentBreakpoint = this.getCurrentBreakpoint();
        this.touchDevice = this.isTouchDevice();
        this.resizeHandlers = new Set();
        this.orientationHandlers = new Set();
        
        this.init();
    }
    
    /**
     * 初始化响应式管理器
     */
    init() {
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.optimizeForDevice();
        this.setupAccessibility();
    }
    
    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 窗口大小变化监听
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.handleResize();
            }, 150);
        });
        
        // 设备方向变化监听
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.handleOrientationChange();
            }, 100);
        });
        
        // 触摸事件优化
        if (this.touchDevice) {
            this.setupTouchOptimizations();
        }
    }
    
    /**
     * 处理窗口大小变化
     */
    handleResize() {
        const newBreakpoint = this.getCurrentBreakpoint();
        
        if (newBreakpoint !== this.currentBreakpoint) {
            const oldBreakpoint = this.currentBreakpoint;
            this.currentBreakpoint = newBreakpoint;
            
            // 触发断点变化事件
            this.triggerBreakpointChange(oldBreakpoint, newBreakpoint);
        }
        
        // 触发所有注册的resize处理器
        this.resizeHandlers.forEach(handler => {
            try {
                handler(this.currentBreakpoint);
            } catch (error) {
                console.error('Resize handler error:', error);
            }
        });
        
        // 更新CSS自定义属性
        this.updateCSSProperties();
    }
    
    /**
     * 处理设备方向变化
     */
    handleOrientationChange() {
        const orientation = this.getOrientation();
        
        // 触发方向变化处理器
        this.orientationHandlers.forEach(handler => {
            try {
                handler(orientation);
            } catch (error) {
                console.error('Orientation handler error:', error);
            }
        });
        
        // 重新计算布局
        this.recalculateLayout();
    }
    
    /**
     * 获取当前断点
     */
    getCurrentBreakpoint() {
        const width = window.innerWidth;
        
        if (width < this.breakpoints.mobile) {
            return 'mobile';
        } else if (width < this.breakpoints.tablet) {
            return 'tablet';
        } else if (width < this.breakpoints.desktop) {
            return 'desktop';
        } else {
            return 'large';
        }
    }
    
    /**
     * 检测是否为触摸设备
     */
    isTouchDevice() {
        return 'ontouchstart' in window || 
               navigator.maxTouchPoints > 0 || 
               navigator.msMaxTouchPoints > 0;
    }
    
    /**
     * 获取设备方向
     */
    getOrientation() {
        if (screen.orientation) {
            return screen.orientation.angle === 0 || screen.orientation.angle === 180 
                ? 'portrait' : 'landscape';
        }
        return window.innerHeight > window.innerWidth ? 'portrait' : 'landscape';
    }
    
    /**
     * 设置触摸优化
     */
    setupTouchOptimizations() {
        // 防止双击缩放
        let lastTouchEnd = 0;
        document.addEventListener('touchend', (event) => {
            const now = Date.now();
            if (now - lastTouchEnd <= 300) {
                event.preventDefault();
            }
            lastTouchEnd = now;
        }, false);
        
        // 优化滚动性能
        document.addEventListener('touchstart', (event) => {
            if (event.touches.length > 1) {
                event.preventDefault();
            }
        }, { passive: false });
        
        // 添加触摸反馈类
        document.body.classList.add('touch-device');
    }
    
    /**
     * 设置键盘快捷键
     */
    setupKeyboardShortcuts() {
        const shortcuts = {
            // ESC键关闭模态框
            'Escape': () => this.closeTopModal(),
            // Ctrl+/ 显示快捷键帮助
            'ctrl+/': () => this.showKeyboardHelp(),
            // Alt+1-9 快速导航
            'alt+1': () => this.navigateToSection('agents'),
            'alt+2': () => this.navigateToSection('tasks'),
            'alt+3': () => this.navigateToSection('config'),
        };
        
        document.addEventListener('keydown', (event) => {
            const key = this.getKeyCombo(event);
            
            if (shortcuts[key]) {
                event.preventDefault();
                shortcuts[key]();
            }
        });
    }
    
    /**
     * 获取按键组合
     */
    getKeyCombo(event) {
        const parts = [];
        
        if (event.ctrlKey) parts.push('ctrl');
        if (event.altKey) parts.push('alt');
        if (event.shiftKey) parts.push('shift');
        if (event.metaKey) parts.push('meta');
        
        parts.push(event.key.toLowerCase());
        
        return parts.join('+');
    }
    
    /**
     * 设备优化
     */
    optimizeForDevice() {
        const deviceClass = this.getDeviceClass();
        document.body.classList.add(`device-${deviceClass}`);
        
        // 移动设备优化
        if (this.currentBreakpoint === 'mobile') {
            this.optimizeForMobile();
        }
        
        // 触摸设备优化
        if (this.touchDevice) {
            this.optimizeForTouch();
        }
    }
    
    /**
     * 移动设备优化
     */
    optimizeForMobile() {
        // 设置视口元标签
        let viewport = document.querySelector('meta[name="viewport"]');
        if (!viewport) {
            viewport = document.createElement('meta');
            viewport.name = 'viewport';
            document.head.appendChild(viewport);
        }
        viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
        
        // 优化表单输入
        this.optimizeMobileInputs();
        
        // 优化滚动
        this.optimizeMobileScrolling();
    }
    
    /**
     * 触摸设备优化
     */
    optimizeForTouch() {
        // 增大触摸目标
        const style = document.createElement('style');
        style.textContent = `
            .touch-device button,
            .touch-device .btn,
            .touch-device input,
            .touch-device select {
                min-height: 44px;
                min-width: 44px;
            }
            
            .touch-device .clickable {
                cursor: pointer;
                -webkit-tap-highlight-color: rgba(0, 0, 0, 0.1);
            }
        `;
        document.head.appendChild(style);
    }
    
    /**
     * 优化移动端输入
     */
    optimizeMobileInputs() {
        const inputs = document.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            // 防止iOS缩放
            if (input.type === 'text' || input.tagName === 'TEXTAREA') {
                input.style.fontSize = '16px';
            }
            
            // 添加适当的输入类型
            if (input.name && input.name.includes('email')) {
                input.type = 'email';
            }
            if (input.name && input.name.includes('phone')) {
                input.type = 'tel';
            }
        });
    }
    
    /**
     * 优化移动端滚动
     */
    optimizeMobileScrolling() {
        // 启用平滑滚动
        document.documentElement.style.scrollBehavior = 'smooth';
        
        // 优化滚动容器
        const scrollContainers = document.querySelectorAll('.scroll-container, .chat-messages');
        scrollContainers.forEach(container => {
            container.style.webkitOverflowScrolling = 'touch';
            container.style.overflowScrolling = 'touch';
        });
    }
    
    /**
     * 设置无障碍功能
     */
    setupAccessibility() {
        // 检测用户偏好
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            document.body.classList.add('reduce-motion');
        }
        
        if (window.matchMedia('(prefers-contrast: high)').matches) {
            document.body.classList.add('high-contrast');
        }
        
        // 焦点管理
        this.setupFocusManagement();
        
        // 屏幕阅读器支持
        this.setupScreenReaderSupport();
    }
    
    /**
     * 设置焦点管理
     */
    setupFocusManagement() {
        // 跳过链接
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.textContent = '跳转到主内容';
        skipLink.className = 'skip-link';
        skipLink.style.cssText = `
            position: absolute;
            top: -40px;
            left: 6px;
            background: #000;
            color: #fff;
            padding: 8px;
            text-decoration: none;
            z-index: 1001;
        `;
        
        skipLink.addEventListener('focus', () => {
            skipLink.style.top = '6px';
        });
        
        skipLink.addEventListener('blur', () => {
            skipLink.style.top = '-40px';
        });
        
        document.body.insertBefore(skipLink, document.body.firstChild);
        
        // 焦点陷阱（用于模态框）
        this.setupFocusTrap();
    }
    
    /**
     * 设置焦点陷阱
     */
    setupFocusTrap() {
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Tab') {
                const modal = document.querySelector('.modal:not([style*="display: none"])');
                if (modal) {
                    this.trapFocus(event, modal);
                }
            }
        });
    }
    
    /**
     * 陷阱焦点在模态框内
     */
    trapFocus(event, container) {
        const focusableElements = container.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        
        if (event.shiftKey) {
            if (document.activeElement === firstElement) {
                lastElement.focus();
                event.preventDefault();
            }
        } else {
            if (document.activeElement === lastElement) {
                firstElement.focus();
                event.preventDefault();
            }
        }
    }
    
    /**
     * 设置屏幕阅读器支持
     */
    setupScreenReaderSupport() {
        // 动态内容更新通知
        const liveRegion = document.createElement('div');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'sr-only';
        liveRegion.style.cssText = `
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        `;
        document.body.appendChild(liveRegion);
        
        this.liveRegion = liveRegion;
    }
    
    /**
     * 通知屏幕阅读器
     */
    announceToScreenReader(message) {
        if (this.liveRegion) {
            this.liveRegion.textContent = message;
            setTimeout(() => {
                this.liveRegion.textContent = '';
            }, 1000);
        }
    }
    
    /**
     * 获取设备类别
     */
    getDeviceClass() {
        const userAgent = navigator.userAgent.toLowerCase();
        
        if (/iphone|ipod/.test(userAgent)) return 'ios';
        if (/ipad/.test(userAgent)) return 'ipad';
        if (/android/.test(userAgent)) return 'android';
        if (/windows phone/.test(userAgent)) return 'windows-phone';
        
        return 'desktop';
    }
    
    /**
     * 更新CSS自定义属性
     */
    updateCSSProperties() {
        const root = document.documentElement;
        
        root.style.setProperty('--viewport-width', `${window.innerWidth}px`);
        root.style.setProperty('--viewport-height', `${window.innerHeight}px`);
        root.style.setProperty('--current-breakpoint', `"${this.currentBreakpoint}"`);
    }
    
    /**
     * 重新计算布局
     */
    recalculateLayout() {
        // 强制重新计算布局
        document.body.offsetHeight;
        
        // 触发自定义事件
        window.dispatchEvent(new CustomEvent('layoutRecalculated', {
            detail: {
                breakpoint: this.currentBreakpoint,
                orientation: this.getOrientation()
            }
        }));
    }
    
    /**
     * 触发断点变化事件
     */
    triggerBreakpointChange(oldBreakpoint, newBreakpoint) {
        window.dispatchEvent(new CustomEvent('breakpointChange', {
            detail: {
                from: oldBreakpoint,
                to: newBreakpoint
            }
        }));
        
        console.log(`Breakpoint changed: ${oldBreakpoint} -> ${newBreakpoint}`);
    }
    
    /**
     * 注册resize处理器
     */
    onResize(handler) {
        this.resizeHandlers.add(handler);
        return () => this.resizeHandlers.delete(handler);
    }
    
    /**
     * 注册方向变化处理器
     */
    onOrientationChange(handler) {
        this.orientationHandlers.add(handler);
        return () => this.orientationHandlers.delete(handler);
    }
    
    /**
     * 关闭顶层模态框
     */
    closeTopModal() {
        const modals = document.querySelectorAll('.modal:not([style*="display: none"])');
        if (modals.length > 0) {
            const topModal = modals[modals.length - 1];
            const closeBtn = topModal.querySelector('.modal-close, .btn-close');
            if (closeBtn) {
                closeBtn.click();
            }
        }
    }
    
    /**
     * 显示键盘快捷键帮助
     */
    showKeyboardHelp() {
        // 实现快捷键帮助模态框
        console.log('Keyboard shortcuts help');
    }
    
    /**
     * 导航到指定区域
     */
    navigateToSection(section) {
        const element = document.querySelector(`#${section}, [data-section="${section}"]`);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
            element.focus();
        }
    }
    
    /**
     * 检查是否为移动设备
     */
    isMobile() {
        return this.currentBreakpoint === 'mobile';
    }
    
    /**
     * 检查是否为平板设备
     */
    isTablet() {
        return this.currentBreakpoint === 'tablet';
    }
    
    /**
     * 检查是否为桌面设备
     */
    isDesktop() {
        return this.currentBreakpoint === 'desktop' || this.currentBreakpoint === 'large';
    }
    
    /**
     * 销毁管理器
     */
    destroy() {
        this.resizeHandlers.clear();
        this.orientationHandlers.clear();
        
        // 移除事件监听器
        window.removeEventListener('resize', this.handleResize);
        window.removeEventListener('orientationchange', this.handleOrientationChange);
    }
}

// 创建全局实例
window.responsiveManager = new ResponsiveManager();

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ResponsiveManager;
}