/**
 * UX和性能优化模块初始化脚本
 * 按正确顺序加载和初始化所有UX和性能相关模块
 */
(function() {
    'use strict';
    
    // 检查必要的依赖
    if (typeof CONFIG === 'undefined') {
        console.error('CONFIG is not defined. Please load config.js first.');
        return;
    }
    
    // 模块加载状态
    const moduleLoadStatus = {
        responsive: false,
        performance: false,
        feedback: false,
        help: false,
        sync: false,
        websocket: false,
        integration: false
    };
    
    // 加载完成回调队列
    const loadCallbacks = [];
    
    /**
     * 动态加载脚本
     */
    function loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    
    /**
     * 动态加载CSS
     */
    function loadCSS(href) {
        return new Promise((resolve, reject) => {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = href;
            link.onload = resolve;
            link.onerror = reject;
            document.head.appendChild(link);
        });
    }
    
    /**
     * 检查模块是否已加载
     */
    function checkModuleLoaded(moduleName, globalVar) {
        return new Promise((resolve) => {
            const checkInterval = setInterval(() => {
                if (window[globalVar]) {
                    clearInterval(checkInterval);
                    moduleLoadStatus[moduleName] = true;
                    console.log(`✓ ${moduleName} module loaded`);
                    resolve();
                }
            }, 100);
            
            // 超时处理
            setTimeout(() => {
                clearInterval(checkInterval);
                console.warn(`⚠ ${moduleName} module load timeout`);
                resolve();
            }, 5000);
        });
    }
    
    /**
     * 初始化UX和性能模块
     */
    async function initializeUXPerformance() {
        console.log('🚀 Starting UX Performance modules initialization...');
        
        try {
            // 1. 加载CSS样式
            console.log('📄 Loading CSS styles...');
            await loadCSS('css/responsive.css');
            
            // 2. 按依赖顺序加载核心模块
            console.log('📦 Loading core modules...');
            
            // 响应式管理器（最先加载，其他模块可能依赖）
            await loadScript('js/core/responsive-manager.js');
            await checkModuleLoaded('responsive', 'responsiveManager');
            
            // 性能管理器
            await loadScript('js/core/performance-manager.js');
            await checkModuleLoaded('performance', 'performanceManager');
            
            // 反馈管理器
            await loadScript('js/core/feedback-manager.js');
            await checkModuleLoaded('feedback', 'feedbackManager');
            
            // 帮助系统
            await loadScript('js/core/help-system.js');
            await checkModuleLoaded('help', 'helpSystem');
            
            // 3. 加载数据同步相关模块
            console.log('🔄 Loading sync modules...');
            
            // 同步管理器
            await loadScript('js/core/sync-manager.js');
            await checkModuleLoaded('sync', 'syncManager');
            
            // 增强的WebSocket管理器
            await loadScript('js/core/websocket-manager.js');
            await checkModuleLoaded('websocket', 'wsManager');
            
            // 4. 加载集成模块
            console.log('🔗 Loading integration module...');
            await loadScript('js/core/ux-performance-integration.js');
            await checkModuleLoaded('integration', 'uxPerformanceIntegration');
            
            // 5. 等待所有模块初始化完成
            console.log('⏳ Waiting for modules to initialize...');
            await waitForModulesReady();
            
            // 6. 设置全局快捷方式
            setupGlobalShortcuts();
            
            // 7. 设置开发者工具
            if (CONFIG.FEATURES.DEBUG_MODE) {
                setupDeveloperTools();
            }
            
            console.log('✅ UX Performance modules initialization completed!');
            
            // 触发初始化完成事件
            window.dispatchEvent(new CustomEvent('uxPerformanceReady', {
                detail: {
                    modules: moduleLoadStatus,
                    timestamp: Date.now()
                }
            }));
            
            // 执行回调
            loadCallbacks.forEach(callback => {
                try {
                    callback();
                } catch (error) {
                    console.error('Load callback error:', error);
                }
            });
            
        } catch (error) {
            console.error('❌ UX Performance initialization failed:', error);
            handleInitializationFailure(error);
        }
    }
    
    /**
     * 等待模块准备就绪
     */
    function waitForModulesReady() {
        return new Promise((resolve) => {
            const checkReady = () => {
                const allReady = Object.values(moduleLoadStatus).every(status => status);
                
                if (allReady) {
                    resolve();
                } else {
                    setTimeout(checkReady, 100);
                }
            };
            
            checkReady();
            
            // 超时处理
            setTimeout(resolve, 10000);
        });
    }
    
    /**
     * 设置全局快捷方式
     */
    function setupGlobalShortcuts() {
        // 添加全局UX工具快捷方式
        window.UX = {
            // 显示系统状态
            status: () => {
                if (window.uxPerformanceIntegration) {
                    console.table(window.uxPerformanceIntegration.getSystemStatus());
                }
            },
            
            // 显示性能报告
            performance: () => {
                if (window.performanceManager) {
                    console.table(window.performanceManager.getPerformanceMetrics());
                }
            },
            
            // 显示分析报告
            analytics: () => {
                if (window.uxPerformanceIntegration) {
                    console.log(window.uxPerformanceIntegration.getAnalyticsReport());
                }
            },
            
            // 强制同步
            sync: () => {
                if (window.syncManager) {
                    return window.syncManager.forceSync();
                }
            },
            
            // WebSocket状态
            websocket: () => {
                if (window.wsManager) {
                    console.table(window.wsManager.getConnectionStatus());
                }
            },
            
            // 显示帮助
            help: () => {
                if (window.helpSystem) {
                    window.helpSystem.showHelpModal();
                }
            },
            
            // 测试通知
            notify: (type = 'info', title = 'Test', message = 'This is a test notification') => {
                if (window.feedbackManager) {
                    window.feedbackManager.showNotification({ type, title, message });
                }
            },
            
            // 清理所有模块
            cleanup: () => {
                if (window.uxPerformanceIntegration) {
                    window.uxPerformanceIntegration.cleanup();
                }
            }
        };
        
        console.log('🔧 Global UX shortcuts available: window.UX');
    }
    
    /**
     * 设置开发者工具
     */
    function setupDeveloperTools() {
        // 添加开发者面板
        const devPanel = document.createElement('div');
        devPanel.id = 'ux-dev-panel';
        devPanel.style.cssText = `
            position: fixed;
            top: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            z-index: 10000;
            max-width: 300px;
            display: none;
        `;
        
        document.body.appendChild(devPanel);
        
        // 切换开发者面板的快捷键
        document.addEventListener('keydown', (event) => {
            if (event.ctrlKey && event.shiftKey && event.key === 'D') {
                event.preventDefault();
                const panel = document.getElementById('ux-dev-panel');
                if (panel) {
                    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
                    if (panel.style.display === 'block') {
                        updateDevPanel();
                    }
                }
            }
        });
        
        // 更新开发者面板
        function updateDevPanel() {
            const panel = document.getElementById('ux-dev-panel');
            if (!panel || panel.style.display === 'none') return;
            
            const status = window.uxPerformanceIntegration ? 
                window.uxPerformanceIntegration.getSystemStatus() : {};
            
            panel.innerHTML = `
                <div><strong>UX Performance Dev Panel</strong></div>
                <div>Modules: ${Object.keys(status.modules || {}).length}</div>
                <div>Initialized: ${status.initialized ? '✅' : '❌'}</div>
                <div>Breakpoint: ${window.responsiveManager ? window.responsiveManager.currentBreakpoint : 'unknown'}</div>
                <div>Online: ${navigator.onLine ? '✅' : '❌'}</div>
                <div>WebSocket: ${window.wsManager ? window.wsManager.connectionState : 'unknown'}</div>
                <div style="margin-top: 5px; font-size: 10px;">Ctrl+Shift+D to toggle</div>
            `;
        }
        
        // 定期更新开发者面板
        setInterval(updateDevPanel, 1000);
        
        console.log('🛠 Developer tools enabled. Press Ctrl+Shift+D to toggle dev panel.');
    }
    
    /**
     * 处理初始化失败
     */
    function handleInitializationFailure(error) {
        console.error('UX Performance initialization failed:', error);
        
        // 尝试启用基本功能
        document.body.classList.add('ux-fallback-mode');
        
        // 显示错误通知（如果可能）
        if (window.feedbackManager) {
            window.feedbackManager.showError(
                '系统初始化失败',
                '部分功能可能无法正常工作，请刷新页面重试'
            );
        } else {
            // 使用原生alert作为后备
            alert('系统初始化失败，部分功能可能无法正常工作');
        }
        
        // 触发失败事件
        window.dispatchEvent(new CustomEvent('uxPerformanceInitFailed', {
            detail: { error, timestamp: Date.now() }
        }));
    }
    
    /**
     * 添加加载完成回调
     */
    function onReady(callback) {
        if (typeof callback === 'function') {
            loadCallbacks.push(callback);
        }
    }
    
    /**
     * 检查是否已准备就绪
     */
    function isReady() {
        return Object.values(moduleLoadStatus).every(status => status);
    }
    
    // 暴露公共API
    window.UXPerformanceInit = {
        onReady,
        isReady,
        moduleLoadStatus: () => ({ ...moduleLoadStatus })
    };
    
    // 自动初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeUXPerformance);
    } else {
        // DOM已加载，延迟一点时间确保其他脚本加载完成
        setTimeout(initializeUXPerformance, 100);
    }
    
})();