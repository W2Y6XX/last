/**
 * 交互修复系统初始化脚本
 * 负责初始化和启动交互修复管理器
 */

(async function initializeInteractionFixSystem() {
    try {
        console.log('正在初始化交互修复系统...');
        
        // 动态导入InteractionFixManager
        const InteractionFixManager = (await import('../core/interaction-fix-manager.js')).default;
        
        // 创建全局实例
        window.interactionFixManager = new InteractionFixManager();
        
        // 等待初始化完成
        await new Promise((resolve) => {
            const checkInit = () => {
                if (window.interactionFixManager.initialized) {
                    resolve();
                } else {
                    setTimeout(checkInit, 100);
                }
            };
            checkInit();
        });
        
        console.log('交互修复系统初始化完成');
        
        // 添加全局快捷方法
        window.fixAllInteractions = () => window.interactionFixManager.fixAllInteractions();
        window.diagnoseComponent = (component) => window.interactionFixManager.diagnoseAndFix(component);
        window.getFixStatus = () => window.interactionFixManager.getStatus();
        
        // 监听页面加载完成事件，自动执行一次诊断
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', performInitialDiagnosis);
        } else {
            performInitialDiagnosis();
        }
        
        // 添加监控事件监听器
        setupMonitoringEventListeners();
        
    } catch (error) {
        console.error('交互修复系统初始化失败:', error);
        
        // 创建简化的备用系统
        createFallbackSystem();
    }
})();

/**
 * 执行初始诊断
 */
async function performInitialDiagnosis() {
    try {
        console.log('执行初始系统诊断...');
        
        // 延迟执行，确保页面完全加载
        setTimeout(async () => {
            if (window.interactionFixManager) {
                const results = await window.interactionFixManager.fixAllInteractions();
                console.log('初始诊断完成:', results);
                
                // 显示诊断结果摘要
                displayDiagnosticSummary(results);
            }
        }, 2000);
        
    } catch (error) {
        console.error('初始诊断失败:', error);
    }
}

/**
 * 设置监控事件监听器
 */
function setupMonitoringEventListeners() {
    // 监听修复记录事件
    window.addEventListener('monitoring:fix_recorded', (event) => {
        console.log('修复记录:', event.detail);
    });
    
    // 监听警报事件
    window.addEventListener('monitoring:alert_created', (event) => {
        console.warn('系统警报:', event.detail);
        showAlert(event.detail);
    });
    
    // 监听错误记录事件
    window.addEventListener('monitoring:error_recorded', (event) => {
        console.error('错误记录:', event.detail);
    });
}

/**
 * 显示诊断结果摘要
 * @param {Array} results - 诊断结果
 */
function displayDiagnosticSummary(results) {
    const summary = {
        total: results.length,
        successful: results.filter(r => r.success).length,
        failed: results.filter(r => !r.success).length
    };
    
    console.log(`诊断摘要: 总计 ${summary.total} 个组件，成功修复 ${summary.successful} 个，失败 ${summary.failed} 个`);
    
    // 如果有失败的修复，显示详细信息
    const failedResults = results.filter(r => !r.success);
    if (failedResults.length > 0) {
        console.warn('修复失败的组件:', failedResults.map(r => r.component));
    }
    
    // 在页面上显示简单的状态指示器
    createStatusIndicator(summary);
}

/**
 * 创建状态指示器
 * @param {Object} summary - 诊断摘要
 */
function createStatusIndicator(summary) {
    // 移除现有的状态指示器
    const existingIndicator = document.querySelector('#fix-status-indicator');
    if (existingIndicator) {
        existingIndicator.remove();
    }
    
    // 创建新的状态指示器
    const indicator = document.createElement('div');
    indicator.id = 'fix-status-indicator';
    indicator.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        z-index: 10000;
        cursor: pointer;
        transition: opacity 0.3s ease;
    `;
    
    // 根据修复结果设置样式和内容
    if (summary.failed === 0) {
        indicator.style.backgroundColor = '#4CAF50';
        indicator.style.color = 'white';
        indicator.textContent = `✓ 系统正常 (${summary.successful}/${summary.total})`;
    } else if (summary.successful > summary.failed) {
        indicator.style.backgroundColor = '#FF9800';
        indicator.style.color = 'white';
        indicator.textContent = `⚠ 部分问题 (${summary.failed} 个问题)`;
    } else {
        indicator.style.backgroundColor = '#F44336';
        indicator.style.color = 'white';
        indicator.textContent = `✗ 系统异常 (${summary.failed} 个问题)`;
    }
    
    // 添加点击事件显示详细信息
    indicator.addEventListener('click', () => {
        showDetailedStatus();
    });
    
    // 添加到页面
    document.body.appendChild(indicator);
    
    // 5秒后自动隐藏
    setTimeout(() => {
        indicator.style.opacity = '0.7';
    }, 5000);
}

/**
 * 显示详细状态
 */
function showDetailedStatus() {
    if (window.interactionFixManager) {
        const status = window.interactionFixManager.getStatus();
        const history = window.interactionFixManager.getFixHistory();
        
        console.group('系统状态详情');
        console.log('初始化状态:', status.initialized);
        console.log('可用修复器:', status.availableFixers);
        console.log('修复历史数量:', status.historyCount);
        console.log('最近修复:', status.lastFix);
        console.log('完整修复历史:', history);
        console.groupEnd();
        
        // 可以在这里添加更复杂的状态显示UI
        alert(`系统状态:\n初始化: ${status.initialized ? '是' : '否'}\n可用修复器: ${status.availableFixers.length} 个\n修复历史: ${status.historyCount} 条记录`);
    }
}

/**
 * 显示警报
 * @param {Object} alert - 警报对象
 */
function showAlert(alert) {
    // 创建警报通知
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 50px;
        right: 10px;
        max-width: 300px;
        padding: 12px;
        background-color: #F44336;
        color: white;
        border-radius: 4px;
        font-size: 14px;
        z-index: 10001;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    `;
    
    notification.innerHTML = `
        <div style="font-weight: bold; margin-bottom: 4px;">系统警报</div>
        <div>${alert.message}</div>
        <div style="font-size: 12px; margin-top: 4px; opacity: 0.8;">
            ${new Date(alert.timestamp).toLocaleTimeString()}
        </div>
    `;
    
    // 添加关闭按钮
    const closeBtn = document.createElement('span');
    closeBtn.innerHTML = '×';
    closeBtn.style.cssText = `
        position: absolute;
        top: 4px;
        right: 8px;
        cursor: pointer;
        font-size: 18px;
        font-weight: bold;
    `;
    closeBtn.addEventListener('click', () => {
        notification.remove();
    });
    
    notification.appendChild(closeBtn);
    document.body.appendChild(notification);
    
    // 10秒后自动移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 10000);
}

/**
 * 创建备用系统
 */
function createFallbackSystem() {
    console.log('创建备用交互修复系统...');
    
    window.interactionFixManager = {
        initialized: false,
        fixAllInteractions: () => {
            console.warn('交互修复系统不可用，使用备用方案');
            return Promise.resolve([]);
        },
        diagnoseAndFix: (component) => {
            console.warn(`无法修复组件 ${component}，交互修复系统不可用`);
            return Promise.resolve({ component, success: false, error: '系统不可用' });
        },
        getStatus: () => ({
            initialized: false,
            availableFixers: [],
            historyCount: 0,
            lastFix: null,
            error: '交互修复系统初始化失败'
        }),
        getFixHistory: () => []
    };
    
    // 添加全局快捷方法
    window.fixAllInteractions = window.interactionFixManager.fixAllInteractions;
    window.diagnoseComponent = window.interactionFixManager.diagnoseAndFix;
    window.getFixStatus = window.interactionFixManager.getStatus;
}

// 导出初始化函数供其他模块使用
window.initializeInteractionFixSystem = initializeInteractionFixSystem;