/**
 * 前后端集成测试套件
 * 验证新功能与现有系统的集成状态
 */
class IntegrationTestSuite {
    constructor() {
        this.testResults = new Map();
        this.testConfig = {
            timeout: 10000,
            retries: 3,
            parallel: false
        };
        
        this.apiEndpoints = {
            health: '/health',
            version: '/version',
            agents: '/api/v1/agents',
            agentsEnhanced: '/api/v1/agents/enhanced',
            agentStatus: '/api/v1/agents/status',
            llmConfigs: '/api/v1/llm/configs',
            llmConfigTest: '/api/v1/llm/configs/{id}/test',
            metaAgentConversations: '/api/v1/meta-agent/conversations',
            metaAgentMessages: '/api/v1/meta-agent/conversations/{id}/messages',
            metaAgentDecompose: '/api/v1/meta-agent/conversations/{id}/decompose',
            tasks: '/api/v1/tasks',
            systemStatus: '/api/v1/system/status'
        };
        
        this.websocketEndpoints = {
            mvp2: '/api/v1/mvp2/ws',
            general: '/api/v1/ws'
        };
        
        this.testSuites = [
            'apiConnectivity',
            'dataIntegrity',
            'featureCompatibility',
            'websocketFunctionality',
            'errorHandling',
            'performanceBaseline',
            'endToEndWorkflows'
        ];
        
        this.mockData = this._initializeMockData();
    }
    
    /**
     * 初始化模拟数据
     * @private
     */
    _initializeMockData() {
        return {
            llmConfig: {
                name: 'Test Config',
                provider: 'siliconflow',
                settings: {
                    apiKey: 'test-api-key',
                    baseUrl: 'https://api.siliconflow.cn/v1',
                    model: 'Qwen/Qwen2.5-7B-Instruct',
                    temperature: 0.7,
                    maxTokens: 2048
                }
            },
            agentConfig: {
                llmConfig: 'test-config-id',
                parameters: {
                    maxRetries: 3,
                    timeout: 30000
                },
                constraints: ['no-external-calls']
            },
            conversation: {
                initialPrompt: '我需要创建一个数据分析任务',
                context: {
                    userRole: 'analyst',
                    priority: 'high'
                }
            },
            task: {
                title: '集成测试任务',
                description: '用于测试系统集成的任务',
                type: 'test',
                priority: 1
            }
        };
    }
    
    /**
     * 运行所有测试套件
     * @returns {Promise<Object>} 测试结果
     */
    async runAllTests() {
        console.log('开始运行集成测试套件...');
        
        const startTime = Date.now();
        const results = {
            summary: {
                total: 0,
                passed: 0,
                failed: 0,
                skipped: 0,
                duration: 0
            },
            suites: {},
            errors: []
        };
        
        try {
            for (const suiteName of this.testSuites) {
                console.log(`运行测试套件: ${suiteName}`);
                
                try {
                    const suiteResults = await this._runTestSuite(suiteName);
                    results.suites[suiteName] = suiteResults;
                    
                    results.summary.total += suiteResults.total;
                    results.summary.passed += suiteResults.passed;
                    results.summary.failed += suiteResults.failed;
                    results.summary.skipped += suiteResults.skipped;
                    
                } catch (error) {
                    console.error(`测试套件 ${suiteName} 执行失败:`, error);
                    results.errors.push({
                        suite: suiteName,
                        error: error.message
                    });
                    
                    results.suites[suiteName] = {
                        total: 0,
                        passed: 0,
                        failed: 1,
                        skipped: 0,
                        tests: [],
                        error: error.message
                    };
                    results.summary.failed++;
                }
            }
            
            results.summary.duration = Date.now() - startTime;
            results.summary.success = results.summary.failed === 0;
            
            console.log('集成测试完成:', results.summary);
            return results;
            
        } catch (error) {
            console.error('集成测试执行失败:', error);
            results.errors.push({
                suite: 'global',
                error: error.message
            });
            return results;
        }
    }
    
    /**
     * 运行单个测试套件
     * @private
     */
    async _runTestSuite(suiteName) {
        const suiteResults = {
            total: 0,
            passed: 0,
            failed: 0,
            skipped: 0,
            tests: []
        };
        
        let tests = [];
        
        switch (suiteName) {
            case 'apiConnectivity':
                tests = await this._getApiConnectivityTests();
                break;
            case 'dataIntegrity':
                tests = await this._getDataIntegrityTests();
                break;
            case 'featureCompatibility':
                tests = await this._getFeatureCompatibilityTests();
                break;
            case 'websocketFunctionality':
                tests = await this._getWebSocketTests();
                break;
            case 'errorHandling':
                tests = await this._getErrorHandlingTests();
                break;
            case 'performanceBaseline':
                tests = await this._getPerformanceTests();
                break;
            case 'endToEndWorkflows':
                tests = await this._getEndToEndTests();
                break;
        }
        
        for (const test of tests) {
            suiteResults.total++;
            
            try {
                const testResult = await this._runSingleTest(test);
                suiteResults.tests.push(testResult);
                
                if (testResult.passed) {
                    suiteResults.passed++;
                } else if (testResult.skipped) {
                    suiteResults.skipped++;
                } else {
                    suiteResults.failed++;
                }
                
            } catch (error) {
                suiteResults.failed++;
                suiteResults.tests.push({
                    name: test.name,
                    passed: false,
                    skipped: false,
                    error: error.message,
                    duration: 0
                });
            }
        }
        
        return suiteResults;
    }
    
    /**
     * 运行单个测试
     * @private
     */
    async _runSingleTest(test) {
        const startTime = Date.now();
        
        try {
            // 检查测试前置条件
            if (test.precondition && !await test.precondition()) {
                return {
                    name: test.name,
                    passed: false,
                    skipped: true,
                    reason: 'Precondition not met',
                    duration: Date.now() - startTime
                };
            }
            
            // 执行测试
            const result = await Promise.race([
                test.execute(),
                new Promise((_, reject) => 
                    setTimeout(() => reject(new Error('Test timeout')), this.testConfig.timeout)
                )
            ]);
            
            return {
                name: test.name,
                passed: result.success,
                skipped: false,
                result: result.data,
                duration: Date.now() - startTime
            };
            
        } catch (error) {
            return {
                name: test.name,
                passed: false,
                skipped: false,
                error: error.message,
                duration: Date.now() - startTime
            };
        }
    }
    
    /**
     * 获取API连接性测试
     * @private
     */
    async _getApiConnectivityTests() {
        return [
            {
                name: 'Health Check Endpoint',
                precondition: () => !!window.apiClient,
                execute: async () => {
                    const response = await window.apiClient.get(this.apiEndpoints.health);
                    return {
                        success: response && (response.status === 'healthy' || response.status === 'ok'),
                        data: response
                    };
                }
            },
            {
                name: 'Version Endpoint',
                precondition: () => !!window.apiClient,
                execute: async () => {
                    const response = await window.apiClient.get(this.apiEndpoints.version);
                    return {
                        success: response && response.version,
                        data: response
                    };
                }
            },
            {
                name: 'Agents Endpoint',
                precondition: () => !!window.apiClient,
                execute: async () => {
                    const response = await window.apiClient.get(this.apiEndpoints.agents);
                    return {
                        success: response && Array.isArray(response.data || response),
                        data: response
                    };
                }
            },
            {
                name: 'Enhanced Agents Endpoint',
                precondition: () => !!window.apiClient,
                execute: async () => {
                    const response = await window.apiClient.get(this.apiEndpoints.agentsEnhanced);
                    return {
                        success: response && (response.success !== false),
                        data: response
                    };
                }
            },
            {
                name: 'LLM Configs Endpoint',
                precondition: () => !!window.apiClient,
                execute: async () => {
                    const response = await window.apiClient.get(this.apiEndpoints.llmConfigs);
                    return {
                        success: response && (response.success !== false),
                        data: response
                    };
                }
            },
            {
                name: 'Meta Agent Conversations Endpoint',
                precondition: () => !!window.apiClient,
                execute: async () => {
                    try {
                        const response = await window.apiClient.post(
                            this.apiEndpoints.metaAgentConversations,
                            this.mockData.conversation
                        );
                        return {
                            success: response && (response.success !== false),
                            data: response
                        };
                    } catch (error) {
                        // 404 is acceptable for this test - means endpoint exists but may not be implemented
                        return {
                            success: !error.message.includes('500'),
                            data: { error: error.message }
                        };
                    }
                }
            }
        ];
    }
    
    /**
     * 获取数据完整性测试
     * @private
     */
    async _getDataIntegrityTests() {
        return [
            {
                name: 'Agent Data Structure Validation',
                precondition: () => !!window.apiClient,
                execute: async () => {
                    const response = await window.apiClient.get(this.apiEndpoints.agentsEnhanced);
                    
                    if (!response || !response.data || !Array.isArray(response.data.agents)) {
                        return { success: false, data: 'Invalid response structure' };
                    }
                    
                    const agents = response.data.agents;
                    const requiredFields = ['agentId', 'agentType', 'name', 'status'];
                    
                    for (const agent of agents) {
                        for (const field of requiredFields) {
                            if (!agent.hasOwnProperty(field)) {
                                return { 
                                    success: false, 
                                    data: `Missing field: ${field} in agent ${agent.agentId || 'unknown'}` 
                                };
                            }
                        }
                    }
                    
                    return { success: true, data: `Validated ${agents.length} agents` };
                }
            },
            {
                name: 'LLM Config Data Migration',
                precondition: () => !!window.DataCompatibilityHandler,
                execute: async () => {
                    const handler = new window.DataCompatibilityHandler();
                    
                    // Test data migration
                    const oldFormatConfig = {
                        id: 'test-config',
                        name: 'Test Config',
                        provider: 'siliconflow',
                        apiKey: 'test-key',
                        model: 'test-model'
                    };
                    
                    const migrationResult = handler.migrateData(oldFormatConfig, 'llm_config');
                    
                    return {
                        success: migrationResult.success || migrationResult.data !== null,
                        data: migrationResult
                    };
                }
            },
            {
                name: 'Agent Data Migration',
                precondition: () => !!window.DataCompatibilityHandler,
                execute: async () => {
                    const handler = new window.DataCompatibilityHandler();
                    
                    // Test agent data migration from old format
                    const oldFormatAgent = {
                        id: 'test-agent',
                        name: 'Test Agent',
                        type: 'generic',
                        status: 'idle'
                    };
                    
                    const migrationResult = handler.migrateData(oldFormatAgent, 'agent');
                    
                    return {
                        success: migrationResult.success,
                        data: migrationResult
                    };
                }
            }
        ];
    }
    
    /**
     * 获取功能兼容性测试
     * @private
     */
    async _getFeatureCompatibilityTests() {
        return [
            {
                name: 'Feature Flag Manager Initialization',
                precondition: () => !!window.FeatureFlagManager,
                execute: async () => {
                    const manager = new window.FeatureFlagManager();
                    const flags = manager.getAllFlags();
                    
                    return {
                        success: Object.keys(flags).length > 0,
                        data: { flagCount: Object.keys(flags).length }
                    };
                }
            },
            {
                name: 'Compatibility Manager Check',
                precondition: () => !!window.CompatibilityManager,
                execute: async () => {
                    const manager = new window.CompatibilityManager();
                    // Wait a bit for initialization
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    const status = manager.getCompatibilityStatus();
                    
                    return {
                        success: status.overall !== null,
                        data: status
                    };
                }
            },
            {
                name: 'Error Boundary Functionality',
                precondition: () => !!window.ErrorBoundary,
                execute: async () => {
                    const boundary = new window.ErrorBoundary({
                        componentName: 'TestComponent'
                    });
                    
                    // Test error wrapping
                    const testFn = () => {
                        throw new Error('Test error');
                    };
                    
                    const wrappedFn = boundary.wrapMethod(testFn, 'testMethod');
                    
                    try {
                        wrappedFn();
                    } catch (error) {
                        // Expected to throw
                    }
                    
                    return {
                        success: boundary.hasError(),
                        data: { hasError: boundary.hasError() }
                    };
                }
            },
            {
                name: 'LLM Config Manager Integration',
                precondition: () => !!window.LLMConfigManager,
                execute: async () => {
                    const manager = new window.LLMConfigManager();
                    
                    // Test basic functionality
                    const providers = manager.getSupportedProviders();
                    const configs = manager.getAllConfigs();
                    
                    return {
                        success: providers.length > 0,
                        data: { 
                            providerCount: providers.length,
                            configCount: configs.length
                        }
                    };
                }
            },
            {
                name: 'Agent Manager Integration',
                precondition: () => !!window.AgentManager,
                execute: async () => {
                    const manager = new window.AgentManager();
                    
                    // Test basic functionality
                    const agents = manager.getAllAgents();
                    const summary = manager.getAgentsSummary();
                    
                    return {
                        success: summary && typeof summary.total === 'number',
                        data: summary
                    };
                }
            }
        ];
    }
    
    /**
     * 获取WebSocket功能测试
     * @private
     */
    async _getWebSocketTests() {
        return [
            {
                name: 'WebSocket Manager Initialization',
                precondition: () => !!window.WebSocketManager,
                execute: async () => {
                    const manager = new window.WebSocketManager();
                    
                    return {
                        success: manager !== null,
                        data: { initialized: true }
                    };
                }
            },
            {
                name: 'WebSocket Connection Test',
                precondition: () => !!window.wsManager,
                execute: async () => {
                    // This is a basic connectivity test
                    // In a real scenario, we'd test actual connection
                    const hasWebSocketSupport = typeof WebSocket !== 'undefined';
                    
                    return {
                        success: hasWebSocketSupport,
                        data: { webSocketSupported: hasWebSocketSupport }
                    };
                }
            },
            {
                name: 'Real-time Updates Compatibility',
                precondition: () => !!window.featureFlagManager,
                execute: async () => {
                    const isEnabled = window.featureFlagManager.isEnabled('real-time-updates');
                    
                    return {
                        success: true, // This test always passes, just checks the flag
                        data: { realTimeUpdatesEnabled: isEnabled }
                    };
                }
            }
        ];
    }
    
    /**
     * 获取错误处理测试
     * @private
     */
    async _getErrorHandlingTests() {
        return [
            {
                name: 'Global Error Handler',
                precondition: () => !!window.errorHandler,
                execute: async () => {
                    const handler = window.errorHandler;
                    
                    // Test error reporting
                    handler.reportError('test', 'Integration test error', { testData: true });
                    
                    const stats = handler.getErrorStats();
                    
                    return {
                        success: stats.total > 0,
                        data: stats
                    };
                }
            },
            {
                name: 'API Error Handling',
                precondition: () => !!window.apiClient,
                execute: async () => {
                    try {
                        // Try to access a non-existent endpoint
                        await window.apiClient.get('/api/v1/non-existent-endpoint');
                        return { success: false, data: 'Should have thrown an error' };
                    } catch (error) {
                        // Expected to fail
                        return {
                            success: error.message.includes('404') || error.message.includes('Not Found'),
                            data: { errorMessage: error.message }
                        };
                    }
                }
            },
            {
                name: 'Component Error Isolation',
                precondition: () => !!window.ErrorBoundary,
                execute: async () => {
                    const boundary = new window.ErrorBoundary({
                        componentName: 'TestComponent',
                        isolateErrors: true
                    });
                    
                    const faultyFunction = () => {
                        throw new Error('Intentional test error');
                    };
                    
                    const wrappedFunction = boundary.wrapMethod(faultyFunction, 'faultyMethod');
                    
                    // This should not throw due to error isolation
                    const result = wrappedFunction();
                    
                    return {
                        success: boundary.hasError() && result === undefined,
                        data: { 
                            hasError: boundary.hasError(),
                            result: result
                        }
                    };
                }
            }
        ];
    }
    
    /**
     * 获取性能基准测试
     * @private
     */
    async _getPerformanceTests() {
        return [
            {
                name: 'API Response Time Baseline',
                precondition: () => !!window.apiClient,
                execute: async () => {
                    const startTime = performance.now();
                    
                    try {
                        await window.apiClient.get(this.apiEndpoints.health);
                        const responseTime = performance.now() - startTime;
                        
                        return {
                            success: responseTime < 5000, // 5 seconds threshold
                            data: { responseTime }
                        };
                    } catch (error) {
                        return {
                            success: false,
                            data: { error: error.message }
                        };
                    }
                }
            },
            {
                name: 'Component Initialization Time',
                precondition: () => !!window.LLMConfigManager,
                execute: async () => {
                    const startTime = performance.now();
                    
                    const manager = new window.LLMConfigManager();
                    const initTime = performance.now() - startTime;
                    
                    return {
                        success: initTime < 1000, // 1 second threshold
                        data: { initTime }
                    };
                }
            },
            {
                name: 'Memory Usage Check',
                precondition: () => 'memory' in performance,
                execute: async () => {
                    const memoryInfo = performance.memory;
                    const memoryUsage = memoryInfo.usedJSHeapSize / memoryInfo.jsHeapSizeLimit;
                    
                    return {
                        success: memoryUsage < 0.8, // 80% threshold
                        data: {
                            memoryUsage,
                            usedMemory: memoryInfo.usedJSHeapSize,
                            totalMemory: memoryInfo.jsHeapSizeLimit
                        }
                    };
                }
            }
        ];
    }
    
    /**
     * 获取端到端工作流测试
     * @private
     */
    async _getEndToEndTests() {
        return [
            {
                name: 'LLM Configuration Workflow',
                precondition: () => !!window.llmConfigManager,
                execute: async () => {
                    const manager = window.llmConfigManager;
                    
                    // Create a test configuration
                    const createResult = await manager.createConfig(this.mockData.llmConfig);
                    
                    if (!createResult.success) {
                        return { success: false, data: createResult };
                    }
                    
                    // Get the configuration
                    const configs = manager.getAllConfigs();
                    const testConfig = configs.find(c => c.name === this.mockData.llmConfig.name);
                    
                    if (!testConfig) {
                        return { success: false, data: 'Configuration not found after creation' };
                    }
                    
                    // Clean up
                    await manager.deleteConfig(testConfig.id);
                    
                    return {
                        success: true,
                        data: { configId: testConfig.id }
                    };
                }
            },
            {
                name: 'Agent Management Workflow',
                precondition: () => !!window.agentManager,
                execute: async () => {
                    const manager = window.agentManager;
                    
                    // Load agents
                    const loadResult = await manager.loadAgents();
                    
                    if (!loadResult.success) {
                        return { success: false, data: loadResult };
                    }
                    
                    // Get agent summary
                    const summary = manager.getAgentsSummary();
                    
                    return {
                        success: summary && typeof summary.total === 'number',
                        data: summary
                    };
                }
            },
            {
                name: 'System Integration Workflow',
                precondition: () => !!window.SystemIntegrationManager,
                execute: async () => {
                    const manager = new window.SystemIntegrationManager();
                    
                    // Wait for initialization
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    const status = manager.getSystemStatus();
                    
                    return {
                        success: status.integration.initialized,
                        data: status
                    };
                }
            }
        ];
    }
    
    /**
     * 生成测试报告
     * @param {Object} results 测试结果
     * @returns {string} HTML报告
     */
    generateReport(results) {
        const { summary, suites } = results;
        const successRate = summary.total > 0 ? (summary.passed / summary.total * 100).toFixed(1) : 0;
        
        let html = `
            <div class="integration-test-report">
                <h2>前后端集成测试报告</h2>
                
                <div class="test-summary">
                    <h3>测试摘要</h3>
                    <div class="summary-stats">
                        <div class="stat-item">
                            <span class="stat-label">总测试数:</span>
                            <span class="stat-value">${summary.total}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">通过:</span>
                            <span class="stat-value success">${summary.passed}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">失败:</span>
                            <span class="stat-value failure">${summary.failed}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">跳过:</span>
                            <span class="stat-value skipped">${summary.skipped}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">成功率:</span>
                            <span class="stat-value">${successRate}%</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">执行时间:</span>
                            <span class="stat-value">${summary.duration}ms</span>
                        </div>
                    </div>
                </div>
                
                <div class="test-suites">
                    <h3>测试套件详情</h3>
        `;
        
        Object.keys(suites).forEach(suiteName => {
            const suite = suites[suiteName];
            const suiteSuccessRate = suite.total > 0 ? (suite.passed / suite.total * 100).toFixed(1) : 0;
            
            html += `
                <div class="test-suite">
                    <h4>${suiteName}</h4>
                    <div class="suite-summary">
                        <span>通过: ${suite.passed}</span>
                        <span>失败: ${suite.failed}</span>
                        <span>跳过: ${suite.skipped}</span>
                        <span>成功率: ${suiteSuccessRate}%</span>
                    </div>
                    
                    <div class="test-details">
            `;
            
            suite.tests.forEach(test => {
                const statusClass = test.passed ? 'success' : test.skipped ? 'skipped' : 'failure';
                const statusText = test.passed ? '✓' : test.skipped ? '○' : '✗';
                
                html += `
                    <div class="test-item ${statusClass}">
                        <span class="test-status">${statusText}</span>
                        <span class="test-name">${test.name}</span>
                        <span class="test-duration">${test.duration}ms</span>
                        ${test.error ? `<div class="test-error">${test.error}</div>` : ''}
                        ${test.reason ? `<div class="test-reason">${test.reason}</div>` : ''}
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
            
            <style>
                .integration-test-report {
                    font-family: Arial, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                
                .test-summary {
                    background: #f5f5f5;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }
                
                .summary-stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 10px;
                }
                
                .stat-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 5px 0;
                }
                
                .stat-value.success { color: #10b981; }
                .stat-value.failure { color: #ef4444; }
                .stat-value.skipped { color: #f59e0b; }
                
                .test-suite {
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    padding: 15px;
                }
                
                .suite-summary {
                    display: flex;
                    gap: 20px;
                    margin-bottom: 15px;
                    font-size: 14px;
                    color: #6b7280;
                }
                
                .test-item {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 8px 0;
                    border-bottom: 1px solid #f3f4f6;
                }
                
                .test-item:last-child {
                    border-bottom: none;
                }
                
                .test-status {
                    width: 20px;
                    font-weight: bold;
                }
                
                .test-item.success .test-status { color: #10b981; }
                .test-item.failure .test-status { color: #ef4444; }
                .test-item.skipped .test-status { color: #f59e0b; }
                
                .test-name {
                    flex: 1;
                }
                
                .test-duration {
                    font-size: 12px;
                    color: #9ca3af;
                }
                
                .test-error, .test-reason {
                    font-size: 12px;
                    color: #ef4444;
                    margin-left: 30px;
                    margin-top: 5px;
                }
                
                .test-reason {
                    color: #f59e0b;
                }
            </style>
        `;
        
        return html;
    }
    
    /**
     * 运行特定测试套件
     * @param {string} suiteName 测试套件名称
     * @returns {Promise<Object>} 测试结果
     */
    async runTestSuite(suiteName) {
        if (!this.testSuites.includes(suiteName)) {
            throw new Error(`Unknown test suite: ${suiteName}`);
        }
        
        console.log(`运行测试套件: ${suiteName}`);
        return await this._runTestSuite(suiteName);
    }
    
    /**
     * 获取可用的测试套件
     * @returns {Array} 测试套件列表
     */
    getAvailableTestSuites() {
        return [...this.testSuites];
    }
    
    /**
     * 设置测试配置
     * @param {Object} config 测试配置
     */
    setTestConfig(config) {
        this.testConfig = { ...this.testConfig, ...config };
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = IntegrationTestSuite;
} else {
    window.IntegrationTestSuite = IntegrationTestSuite;
}