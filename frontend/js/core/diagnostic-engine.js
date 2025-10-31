/**
 * 问题诊断引擎 - 自动检测各种前端交互问题
 * 负责DOM结构检查、事件绑定验证、API连接测试等诊断功能
 */

class DiagnosticEngine {
    constructor() {
        this.diagnosticTests = new Map();
        this.severityLevels = {
            CRITICAL: 'critical',
            HIGH: 'high',
            MEDIUM: 'medium',
            LOW: 'low',
            INFO: 'info'
        };
        
        this.initializeDiagnosticTests();
    }
    
    initializeDiagnosticTests() {
        // 注册各种诊断测试
        this.diagnosticTests.set('dom_structure', this.checkDOMStructure.bind(this));
        this.diagnosticTests.set('event_bindings', this.checkEventBindings.bind(this));
        this.diagnosticTests.set('api_connectivity', this.checkAPIConnectivity.bind(this));
        this.diagnosticTests.set('websocket_connection', this.checkWebSocketConnection.bind(this));
        this.diagnosticTests.set('local_storage', this.checkLocalStorage.bind(this));
        this.diagnosticTests.set('console_errors', this.checkConsoleErrors.bind(this));
        this.diagnosticTests.set('network_status', this.checkNetworkStatus.bind(this));
        this.diagnosticTests.set('browser_compatibility', this.checkBrowserCompatibility.bind(this));
    }
    
    /**
     * 运行所有诊断测试
     * @returns {Promise<Array>} 诊断结果列表
     */
    async runAllDiagnostics() {
        const results = [];
        
        for (const [testName, testFunction] of this.diagnosticTests) {
            try {
                console.log(`运行诊断测试: ${testName}`);
                const testResults = await testFunction();
                
                if (Array.isArray(testResults)) {
                    results.push(...testResults);
                } else if (testResults) {
                    results.push(testResults);
                }
                
            } catch (error) {
                console.error(`诊断测试 ${testName} 失败:`, error);
                results.push({
                    type: 'diagnostic_test_failed',
                    testName,
                    severity: this.severityLevels.HIGH,
                    message: `诊断测试失败: ${error.message}`,
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
            }
        }
        
        return this.prioritizeIssues(results);
    }
    
    /**
     * 运行特定的诊断测试
     * @param {string} testName - 测试名称
     * @returns {Promise<Array>} 诊断结果
     */
    async runDiagnostic(testName) {
        const testFunction = this.diagnosticTests.get(testName);
        if (!testFunction) {
            throw new Error(`未找到诊断测试: ${testName}`);
        }
        
        try {
            const results = await testFunction();
            return Array.isArray(results) ? results : [results];
        } catch (error) {
            return [{
                type: 'diagnostic_test_failed',
                testName,
                severity: this.severityLevels.HIGH,
                message: `诊断测试失败: ${error.message}`,
                error: error.message,
                timestamp: new Date().toISOString()
            }];
        }
    }
    
    /**
     * 检查DOM结构完整性
     * @returns {Promise<Array>} DOM问题列表
     */
    async checkDOMStructure() {
        const issues = [];
        
        // 检查关键容器元素
        const criticalElements = [
            { selector: '#main-content', name: '主内容容器' },
            { selector: '#agent-management', name: '智能体管理容器' },
            { selector: '#llm-config', name: 'LLM配置容器' },
            { selector: '#task-dependencies', name: '任务依赖容器' },
            { selector: '#meta-agent-chat', name: '元智能体对话容器' }
        ];
        
        for (const element of criticalElements) {
            const domElement = document.querySelector(element.selector);
            if (!domElement) {
                issues.push({
                    type: 'dom_element_missing',
                    severity: this.severityLevels.HIGH,
                    message: `关键DOM元素缺失: ${element.name} (${element.selector})`,
                    selector: element.selector,
                    elementName: element.name,
                    timestamp: new Date().toISOString()
                });
            } else {
                // 检查元素是否可见
                const isVisible = this.isElementVisible(domElement);
                if (!isVisible) {
                    issues.push({
                        type: 'dom_element_hidden',
                        severity: this.severityLevels.MEDIUM,
                        message: `DOM元素不可见: ${element.name}`,
                        selector: element.selector,
                        elementName: element.name,
                        timestamp: new Date().toISOString()
                    });
                }
            }
        }
        
        // 检查模态框结构
        const modals = document.querySelectorAll('.modal');
        modals.forEach((modal, index) => {
            const closeBtn = modal.querySelector('.close');
            const modalContent = modal.querySelector('.modal-content');
            
            if (!closeBtn) {
                issues.push({
                    type: 'modal_close_button_missing',
                    severity: this.severityLevels.MEDIUM,
                    message: `模态框 ${index + 1} 缺少关闭按钮`,
                    modalIndex: index,
                    timestamp: new Date().toISOString()
                });
            }
            
            if (!modalContent) {
                issues.push({
                    type: 'modal_content_missing',
                    severity: this.severityLevels.HIGH,
                    message: `模态框 ${index + 1} 缺少内容容器`,
                    modalIndex: index,
                    timestamp: new Date().toISOString()
                });
            }
        });
        
        return issues;
    }
    
    /**
     * 检查事件绑定状态
     * @returns {Promise<Array>} 事件绑定问题列表
     */
    async checkEventBindings() {
        const issues = [];
        
        // 检查关键按钮的事件绑定
        const criticalButtons = [
            { selector: '#refresh-agents', name: '刷新智能体按钮' },
            { selector: '#add-agent', name: '添加智能体按钮' },
            { selector: '#save-llm-config', name: '保存LLM配置按钮' },
            { selector: '#test-llm-connection', name: '测试LLM连接按钮' },
            { selector: '#start-meta-chat', name: '开始元智能体对话按钮' }
        ];
        
        for (const button of criticalButtons) {
            const element = document.querySelector(button.selector);
            if (element) {
                const hasClickListener = this.hasEventListener(element, 'click');
                if (!hasClickListener) {
                    issues.push({
                        type: 'event_binding_missing',
                        severity: this.severityLevels.HIGH,
                        message: `按钮缺少点击事件: ${button.name}`,
                        selector: button.selector,
                        buttonName: button.name,
                        timestamp: new Date().toISOString()
                    });
                }
            }
        }
        
        // 检查表单事件绑定
        const forms = document.querySelectorAll('form');
        forms.forEach((form, index) => {
            const hasSubmitListener = this.hasEventListener(form, 'submit');
            if (!hasSubmitListener) {
                issues.push({
                    type: 'form_submit_binding_missing',
                    severity: this.severityLevels.MEDIUM,
                    message: `表单 ${index + 1} 缺少提交事件绑定`,
                    formIndex: index,
                    timestamp: new Date().toISOString()
                });
            }
        });
        
        // 检查输入框事件绑定
        const inputs = document.querySelectorAll('input[type="text"], textarea');
        let unboundInputs = 0;
        inputs.forEach(input => {
            const hasInputListener = this.hasEventListener(input, 'input') || 
                                   this.hasEventListener(input, 'change');
            if (!hasInputListener) {
                unboundInputs++;
            }
        });
        
        if (unboundInputs > 0) {
            issues.push({
                type: 'input_binding_missing',
                severity: this.severityLevels.LOW,
                message: `${unboundInputs} 个输入框缺少事件绑定`,
                unboundCount: unboundInputs,
                timestamp: new Date().toISOString()
            });
        }
        
        return issues;
    }
    
    /**
     * 检查API连接状态
     * @returns {Promise<Array>} API连接问题列表
     */
    async checkAPIConnectivity() {
        const issues = [];
        
        // 定义关键API端点
        const apiEndpoints = [
            { url: '/api/v1/health', name: '健康检查', critical: true },
            { url: '/api/v1/agents', name: '智能体API', critical: true },
            { url: '/api/v1/llm-configs', name: 'LLM配置API', critical: true },
            { url: '/api/v1/tasks', name: '任务API', critical: false },
            { url: '/api/v1/meta-agent/chat', name: '元智能体对话API', critical: true }
        ];
        
        for (const endpoint of apiEndpoints) {
            try {
                const response = await fetch(endpoint.url, {
                    method: 'GET',
                    timeout: 5000
                });
                
                if (!response.ok) {
                    issues.push({
                        type: 'api_endpoint_error',
                        severity: endpoint.critical ? this.severityLevels.CRITICAL : this.severityLevels.HIGH,
                        message: `API端点错误: ${endpoint.name} (${response.status})`,
                        url: endpoint.url,
                        status: response.status,
                        statusText: response.statusText,
                        timestamp: new Date().toISOString()
                    });
                }
                
            } catch (error) {
                issues.push({
                    type: 'api_endpoint_unreachable',
                    severity: endpoint.critical ? this.severityLevels.CRITICAL : this.severityLevels.HIGH,
                    message: `API端点不可达: ${endpoint.name}`,
                    url: endpoint.url,
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
            }
        }
        
        return issues;
    }
    
    /**
     * 检查WebSocket连接状态
     * @returns {Promise<Array>} WebSocket问题列表
     */
    async checkWebSocketConnection() {
        const issues = [];
        
        // 检查WebSocket管理器是否存在
        if (!window.websocketManager) {
            issues.push({
                type: 'websocket_manager_missing',
                severity: this.severityLevels.HIGH,
                message: 'WebSocket管理器未初始化',
                timestamp: new Date().toISOString()
            });
            return issues;
        }
        
        // 检查WebSocket连接状态
        const wsStatus = window.websocketManager.getConnectionStatus();
        if (wsStatus !== 'connected') {
            issues.push({
                type: 'websocket_not_connected',
                severity: this.severityLevels.HIGH,
                message: `WebSocket未连接，当前状态: ${wsStatus}`,
                status: wsStatus,
                timestamp: new Date().toISOString()
            });
        }
        
        return issues;
    }
    
    /**
     * 检查本地存储功能
     * @returns {Promise<Array>} 本地存储问题列表
     */
    async checkLocalStorage() {
        const issues = [];
        
        try {
            // 测试localStorage可用性
            const testKey = 'diagnostic_test_' + Date.now();
            const testValue = 'test_value';
            
            localStorage.setItem(testKey, testValue);
            const retrievedValue = localStorage.getItem(testKey);
            localStorage.removeItem(testKey);
            
            if (retrievedValue !== testValue) {
                issues.push({
                    type: 'local_storage_malfunction',
                    severity: this.severityLevels.HIGH,
                    message: 'localStorage功能异常',
                    timestamp: new Date().toISOString()
                });
            }
            
        } catch (error) {
            issues.push({
                type: 'local_storage_unavailable',
                severity: this.severityLevels.HIGH,
                message: 'localStorage不可用',
                error: error.message,
                timestamp: new Date().toISOString()
            });
        }
        
        // 检查关键配置是否存在
        const criticalKeys = ['llm_configs', 'agent_settings', 'user_preferences'];
        for (const key of criticalKeys) {
            const value = localStorage.getItem(key);
            if (!value) {
                issues.push({
                    type: 'critical_config_missing',
                    severity: this.severityLevels.MEDIUM,
                    message: `关键配置缺失: ${key}`,
                    configKey: key,
                    timestamp: new Date().toISOString()
                });
            }
        }
        
        return issues;
    }
    
    /**
     * 检查控制台错误
     * @returns {Promise<Array>} 控制台错误列表
     */
    async checkConsoleErrors() {
        const issues = [];
        
        // 这里我们检查是否有全局错误处理器
        if (!window.onerror && !window.addEventListener) {
            issues.push({
                type: 'error_handler_missing',
                severity: this.severityLevels.MEDIUM,
                message: '缺少全局错误处理器',
                timestamp: new Date().toISOString()
            });
        }
        
        // 检查是否有未捕获的Promise拒绝处理器
        if (!window.onunhandledrejection) {
            issues.push({
                type: 'promise_rejection_handler_missing',
                severity: this.severityLevels.MEDIUM,
                message: '缺少未捕获Promise拒绝处理器',
                timestamp: new Date().toISOString()
            });
        }
        
        return issues;
    }
    
    /**
     * 检查网络状态
     * @returns {Promise<Array>} 网络状态问题列表
     */
    async checkNetworkStatus() {
        const issues = [];
        
        if (!navigator.onLine) {
            issues.push({
                type: 'network_offline',
                severity: this.severityLevels.CRITICAL,
                message: '网络连接已断开',
                timestamp: new Date().toISOString()
            });
        }
        
        // 检查网络连接质量
        if (navigator.connection) {
            const connection = navigator.connection;
            if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
                issues.push({
                    type: 'slow_network',
                    severity: this.severityLevels.MEDIUM,
                    message: `网络连接较慢: ${connection.effectiveType}`,
                    effectiveType: connection.effectiveType,
                    timestamp: new Date().toISOString()
                });
            }
        }
        
        return issues;
    }
    
    /**
     * 检查浏览器兼容性
     * @returns {Promise<Array>} 浏览器兼容性问题列表
     */
    async checkBrowserCompatibility() {
        const issues = [];
        
        // 检查关键API支持
        const requiredAPIs = [
            { name: 'fetch', check: () => typeof fetch !== 'undefined' },
            { name: 'Promise', check: () => typeof Promise !== 'undefined' },
            { name: 'WebSocket', check: () => typeof WebSocket !== 'undefined' },
            { name: 'localStorage', check: () => typeof Storage !== 'undefined' },
            { name: 'addEventListener', check: () => typeof EventTarget !== 'undefined' }
        ];
        
        for (const api of requiredAPIs) {
            if (!api.check()) {
                issues.push({
                    type: 'browser_api_unsupported',
                    severity: this.severityLevels.CRITICAL,
                    message: `浏览器不支持 ${api.name} API`,
                    apiName: api.name,
                    timestamp: new Date().toISOString()
                });
            }
        }
        
        // 检查ES6特性支持
        try {
            eval('const test = () => {}; class Test {}');
        } catch (error) {
            issues.push({
                type: 'es6_unsupported',
                severity: this.severityLevels.HIGH,
                message: '浏览器不支持ES6特性',
                timestamp: new Date().toISOString()
            });
        }
        
        return issues;
    }
    
    /**
     * 检查元素是否可见
     * @param {Element} element - DOM元素
     * @returns {boolean} 是否可见
     */
    isElementVisible(element) {
        const style = window.getComputedStyle(element);
        return style.display !== 'none' && 
               style.visibility !== 'hidden' && 
               style.opacity !== '0' &&
               element.offsetWidth > 0 && 
               element.offsetHeight > 0;
    }
    
    /**
     * 检查元素是否有特定事件监听器
     * @param {Element} element - DOM元素
     * @param {string} eventType - 事件类型
     * @returns {boolean} 是否有监听器
     */
    hasEventListener(element, eventType) {
        // 这是一个简化的检查，实际实现可能需要更复杂的逻辑
        const listeners = element.getEventListeners ? element.getEventListeners() : {};
        return listeners[eventType] && listeners[eventType].length > 0;
    }
    
    /**
     * 按严重程度排序问题
     * @param {Array} issues - 问题列表
     * @returns {Array} 排序后的问题列表
     */
    prioritizeIssues(issues) {
        const severityOrder = {
            [this.severityLevels.CRITICAL]: 0,
            [this.severityLevels.HIGH]: 1,
            [this.severityLevels.MEDIUM]: 2,
            [this.severityLevels.LOW]: 3,
            [this.severityLevels.INFO]: 4
        };
        
        return issues.sort((a, b) => {
            const aPriority = severityOrder[a.severity] || 5;
            const bPriority = severityOrder[b.severity] || 5;
            return aPriority - bPriority;
        });
    }
    
    /**
     * 生成诊断报告
     * @param {Array} issues - 问题列表
     * @returns {Object} 诊断报告
     */
    generateDiagnosticReport(issues) {
        const severityCounts = {
            critical: 0,
            high: 0,
            medium: 0,
            low: 0,
            info: 0
        };
        
        issues.forEach(issue => {
            if (severityCounts.hasOwnProperty(issue.severity)) {
                severityCounts[issue.severity]++;
            }
        });
        
        const totalIssues = issues.length;
        const criticalAndHigh = severityCounts.critical + severityCounts.high;
        
        return {
            summary: {
                totalIssues,
                criticalAndHigh,
                severityCounts,
                healthScore: totalIssues === 0 ? 100 : Math.max(0, 100 - (criticalAndHigh * 20) - (severityCounts.medium * 5) - (severityCounts.low * 1))
            },
            issues: issues,
            recommendations: this.generateRecommendations(issues),
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * 生成修复建议
     * @param {Array} issues - 问题列表
     * @returns {Array} 建议列表
     */
    generateRecommendations(issues) {
        const recommendations = [];
        
        // 按问题类型生成建议
        const issueTypes = [...new Set(issues.map(issue => issue.type))];
        
        for (const type of issueTypes) {
            const typeIssues = issues.filter(issue => issue.type === type);
            const recommendation = this.getRecommendationForIssueType(type, typeIssues);
            if (recommendation) {
                recommendations.push(recommendation);
            }
        }
        
        return recommendations;
    }
    
    /**
     * 获取特定问题类型的建议
     * @param {string} issueType - 问题类型
     * @param {Array} issues - 该类型的问题列表
     * @returns {Object} 建议
     */
    getRecommendationForIssueType(issueType, issues) {
        const recommendationMap = {
            'dom_element_missing': {
                title: '修复缺失的DOM元素',
                description: '重新创建或修复缺失的关键DOM元素',
                priority: 'high',
                action: 'recreate_dom'
            },
            'event_binding_missing': {
                title: '重新绑定事件监听器',
                description: '为缺失事件绑定的元素重新添加监听器',
                priority: 'high',
                action: 'rebind_events'
            },
            'api_endpoint_unreachable': {
                title: '修复API连接问题',
                description: '检查后端服务状态或使用备用方案',
                priority: 'critical',
                action: 'fix_api_connection'
            },
            'websocket_not_connected': {
                title: '重新建立WebSocket连接',
                description: '重新初始化WebSocket连接',
                priority: 'high',
                action: 'reconnect_websocket'
            },
            'local_storage_unavailable': {
                title: '启用替代存储方案',
                description: '使用内存存储或其他替代方案',
                priority: 'medium',
                action: 'enable_fallback_storage'
            }
        };
        
        const recommendation = recommendationMap[issueType];
        if (recommendation) {
            return {
                ...recommendation,
                affectedCount: issues.length,
                issues: issues.map(issue => issue.message)
            };
        }
        
        return null;
    }
}

// 导出类
export default DiagnosticEngine;

// 创建全局实例
window.DiagnosticEngine = DiagnosticEngine;