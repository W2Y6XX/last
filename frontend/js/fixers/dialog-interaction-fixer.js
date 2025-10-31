/**
 * 对话交互修复器 - 专门处理对话相关问题
 * 负责修复对话回复固定化问题，配置大模型连接，实现对话后端LLM配置同步机制
 */

class DialogInteractionFixer {
    constructor() {
        this.apiEndpoints = {
            health: '/api/v1/health',
            llmConfigs: '/api/v1/llm-configs',
            dialogTest: '/api/v1/dialog/test',
            dialogConfig: '/api/v1/dialog/config'
        };
        
        this.testMessages = [
            '你好，请介绍一下自己',
            '今天天气怎么样？',
            '请帮我分析一个问题',
            '你能做什么？',
            '请给我一些建议'
        ];
        
        this.fixedResponsePatterns = [
            /^我是.*助手$/,
            /^很抱歉.*无法.*$/,
            /^我无法.*$/,
            /^抱歉.*不能.*$/,
            /^对不起.*$/
        ];
    }
    
    /**
     * 诊断对话系统问题
     * @returns {Promise<Array>} 问题列表
     */
    async diagnose() {
        const issues = [];
        
        try {
            console.log('开始诊断对话系统...');
            
            // 1. 检查LLM配置状态
            const llmConfigIssues = await this.checkLLMConfiguration();
            issues.push(...llmConfigIssues);
            
            // 2. 检查对话后端连接
            const backendIssues = await this.checkDialogBackendConnection();
            issues.push(...backendIssues);
            
            // 3. 测试对话功能
            const dialogIssues = await this.testDialogFunction();
            issues.push(...dialogIssues);
            
            // 4. 检查对话配置同步状态
            const syncIssues = await this.checkConfigurationSync();
            issues.push(...syncIssues);
            
            console.log(`对话系统诊断完成，发现 ${issues.length} 个问题`);
            
        } catch (error) {
            console.error('对话系统诊断失败:', error);
            issues.push({
                type: 'dialog_diagnosis_failed',
                severity: 'high',
                message: `对话系统诊断失败: ${error.message}`,
                error: error.message,
                timestamp: new Date().toISOString()
            });
        }
        
        return this.prioritizeIssues(issues);
    }
    
    /**
     * 检查LLM配置状态
     * @returns {Promise<Array>} LLM配置问题列表
     */
    async checkLLMConfiguration() {
        const issues = [];
        
        try {
            // 检查本地LLM配置
            const localConfig = this.getLocalLLMConfig();
            if (!localConfig) {
                issues.push({
                    type: 'llm_config_missing',
                    severity: 'critical',
                    message: '本地LLM配置缺失',
                    timestamp: new Date().toISOString()
                });
                return issues;
            }
            
            // 验证配置完整性
            const configValidation = this.validateLLMConfig(localConfig);
            if (!configValidation.valid) {
                issues.push({
                    type: 'llm_config_invalid',
                    severity: 'high',
                    message: `LLM配置无效: ${configValidation.errors.join(', ')}`,
                    errors: configValidation.errors,
                    timestamp: new Date().toISOString()
                });
            }
            
            // 测试LLM连接
            const connectionTest = await this.testLLMConnection(localConfig);
            if (!connectionTest.success) {
                issues.push({
                    type: 'llm_connection_failed',
                    severity: 'critical',
                    message: `LLM连接失败: ${connectionTest.error}`,
                    error: connectionTest.error,
                    config: localConfig,
                    timestamp: new Date().toISOString()
                });
            }
            
        } catch (error) {
            issues.push({
                type: 'llm_config_check_failed',
                severity: 'high',
                message: `LLM配置检查失败: ${error.message}`,
                error: error.message,
                timestamp: new Date().toISOString()
            });
        }
        
        return issues;
    }
    
    /**
     * 检查对话后端连接
     * @returns {Promise<Array>} 后端连接问题列表
     */
    async checkDialogBackendConnection() {
        const issues = [];
        
        try {
            // 检查健康状态端点
            const healthResponse = await fetch(this.apiEndpoints.health, {
                method: 'GET',
                timeout: 5000
            });
            
            if (!healthResponse.ok) {
                issues.push({
                    type: 'dialog_backend_unhealthy',
                    severity: 'critical',
                    message: `对话后端健康检查失败: ${healthResponse.status}`,
                    status: healthResponse.status,
                    statusText: healthResponse.statusText,
                    timestamp: new Date().toISOString()
                });
            }
            
            // 检查对话配置端点
            const configResponse = await fetch(this.apiEndpoints.dialogConfig, {
                method: 'GET',
                timeout: 5000
            });
            
            if (!configResponse.ok) {
                issues.push({
                    type: 'dialog_config_endpoint_failed',
                    severity: 'high',
                    message: `对话配置端点不可用: ${configResponse.status}`,
                    status: configResponse.status,
                    timestamp: new Date().toISOString()
                });
            }
            
        } catch (error) {
            issues.push({
                type: 'dialog_backend_unreachable',
                severity: 'critical',
                message: `对话后端不可达: ${error.message}`,
                error: error.message,
                timestamp: new Date().toISOString()
            });
        }
        
        return issues;
    }
    
    /**
     * 测试对话功能
     * @returns {Promise<Array>} 对话功能问题列表
     */
    async testDialogFunction() {
        const issues = [];
        
        try {
            console.log('开始测试对话功能...');
            
            const responses = [];
            
            // 发送多个测试消息
            for (const message of this.testMessages) {
                try {
                    const response = await this.sendTestMessage(message);
                    responses.push({
                        message,
                        response: response.content,
                        timestamp: response.timestamp
                    });
                    
                    // 短暂延迟避免请求过快
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                } catch (error) {
                    issues.push({
                        type: 'dialog_test_message_failed',
                        severity: 'high',
                        message: `测试消息发送失败: ${message}`,
                        testMessage: message,
                        error: error.message,
                        timestamp: new Date().toISOString()
                    });
                }
            }
            
            // 分析回复模式
            const analysisResult = this.analyzeDialogResponses(responses);
            
            if (analysisResult.hasFixedResponses) {
                issues.push({
                    type: 'dialog_fixed_responses',
                    severity: 'critical',
                    message: '检测到对话回复固定化问题',
                    fixedPatterns: analysisResult.fixedPatterns,
                    responses: responses,
                    timestamp: new Date().toISOString()
                });
            }
            
            if (analysisResult.lowDiversity) {
                issues.push({
                    type: 'dialog_low_diversity',
                    severity: 'medium',
                    message: '对话回复多样性不足',
                    diversityScore: analysisResult.diversityScore,
                    responses: responses,
                    timestamp: new Date().toISOString()
                });
            }
            
            if (responses.length === 0) {
                issues.push({
                    type: 'dialog_no_responses',
                    severity: 'critical',
                    message: '对话系统无法产生任何回复',
                    timestamp: new Date().toISOString()
                });
            }
            
        } catch (error) {
            issues.push({
                type: 'dialog_function_test_failed',
                severity: 'high',
                message: `对话功能测试失败: ${error.message}`,
                error: error.message,
                timestamp: new Date().toISOString()
            });
        }
        
        return issues;
    }
    
    /**
     * 检查配置同步状态
     * @returns {Promise<Array>} 配置同步问题列表
     */
    async checkConfigurationSync() {
        const issues = [];
        
        try {
            const localConfig = this.getLocalLLMConfig();
            if (!localConfig) {
                return issues; // 已在其他检查中处理
            }
            
            // 获取后端配置
            const backendConfig = await this.getBackendLLMConfig();
            
            if (!backendConfig) {
                issues.push({
                    type: 'backend_config_missing',
                    severity: 'high',
                    message: '后端LLM配置缺失',
                    timestamp: new Date().toISOString()
                });
                return issues;
            }
            
            // 比较配置差异
            const configDiff = this.compareConfigurations(localConfig, backendConfig);
            
            if (configDiff.hasDifferences) {
                issues.push({
                    type: 'config_sync_mismatch',
                    severity: 'medium',
                    message: '前后端LLM配置不同步',
                    differences: configDiff.differences,
                    localConfig: localConfig,
                    backendConfig: backendConfig,
                    timestamp: new Date().toISOString()
                });
            }
            
        } catch (error) {
            issues.push({
                type: 'config_sync_check_failed',
                severity: 'medium',
                message: `配置同步检查失败: ${error.message}`,
                error: error.message,
                timestamp: new Date().toISOString()
            });
        }
        
        return issues;
    }
    
    /**
     * 修复对话系统问题
     * @param {Array} issues - 问题列表
     * @returns {Promise<Array>} 修复结果列表
     */
    async fix(issues) {
        const results = [];
        
        for (const issue of issues) {
            try {
                console.log(`正在修复问题: ${issue.type}`);
                
                let result;
                switch (issue.type) {
                    case 'llm_config_missing':
                        result = await this.fixMissingLLMConfig(issue);
                        break;
                    case 'llm_config_invalid':
                        result = await this.fixInvalidLLMConfig(issue);
                        break;
                    case 'llm_connection_failed':
                        result = await this.fixLLMConnection(issue);
                        break;
                    case 'dialog_backend_unreachable':
                        result = await this.fixBackendConnection(issue);
                        break;
                    case 'dialog_fixed_responses':
                        result = await this.fixFixedResponses(issue);
                        break;
                    case 'config_sync_mismatch':
                        result = await this.fixConfigurationSync(issue);
                        break;
                    case 'backend_config_missing':
                        result = await this.fixMissingBackendConfig(issue);
                        break;
                    default:
                        result = {
                            issue: issue.type,
                            status: 'skipped',
                            message: '未找到对应的修复策略'
                        };
                }
                
                results.push(result);
                
            } catch (error) {
                console.error(`修复问题 ${issue.type} 失败:`, error);
                results.push({
                    issue: issue.type,
                    status: 'failed',
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
            }
        }
        
        return results;
    }
    
    /**
     * 验证修复效果
     * @returns {Promise<Object>} 验证结果
     */
    async verify() {
        const results = [];
        
        try {
            // 重新运行诊断检查修复效果
            const issues = await this.diagnose();
            
            // 检查关键功能
            results.push(await this.verifyLLMConfiguration());
            results.push(await this.verifyDialogBackendConnection());
            results.push(await this.verifyDialogFunction());
            results.push(await this.verifyConfigurationSync());
            
            const allPassed = results.every(result => result.passed) && issues.length === 0;
            
            return {
                allPassed,
                results,
                remainingIssues: issues.length,
                issues: issues.filter(issue => issue.severity === 'critical' || issue.severity === 'high')
            };
            
        } catch (error) {
            return {
                allPassed: false,
                results: [{
                    name: '对话系统验证',
                    passed: false,
                    error: error.message
                }],
                error: error.message
            };
        }
    }
    
    // 辅助方法实现
    
    getLocalLLMConfig() {
        try {
            const config = localStorage.getItem('llm_configs');
            return config ? JSON.parse(config) : null;
        } catch (error) {
            console.error('获取本地LLM配置失败:', error);
            return null;
        }
    }
    
    validateLLMConfig(config) {
        const errors = [];
        
        if (!config.apiKey) {
            errors.push('API密钥缺失');
        }
        
        if (!config.baseUrl) {
            errors.push('基础URL缺失');
        }
        
        if (!config.model) {
            errors.push('模型名称缺失');
        }
        
        if (config.maxTokens && (config.maxTokens < 1 || config.maxTokens > 32000)) {
            errors.push('最大令牌数设置无效');
        }
        
        if (config.temperature && (config.temperature < 0 || config.temperature > 2)) {
            errors.push('温度参数设置无效');
        }
        
        return {
            valid: errors.length === 0,
            errors
        };
    }
    
    async testLLMConnection(config) {
        try {
            const response = await fetch(`${config.baseUrl}/v1/models`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${config.apiKey}`,
                    'Content-Type': 'application/json'
                },
                timeout: 10000
            });
            
            if (response.ok) {
                return { success: true };
            } else {
                return { 
                    success: false, 
                    error: `HTTP ${response.status}: ${response.statusText}` 
                };
            }
            
        } catch (error) {
            return { 
                success: false, 
                error: error.message 
            };
        }
    }
    
    async sendTestMessage(message) {
        const response = await fetch(this.apiEndpoints.dialogTest, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                timestamp: new Date().toISOString()
            }),
            timeout: 15000
        });
        
        if (!response.ok) {
            throw new Error(`对话测试请求失败: ${response.status}`);
        }
        
        return await response.json();
    }
    
    analyzeDialogResponses(responses) {
        if (responses.length === 0) {
            return {
                hasFixedResponses: false,
                lowDiversity: true,
                diversityScore: 0,
                fixedPatterns: []
            };
        }
        
        const contents = responses.map(r => r.response);
        const fixedPatterns = [];
        
        // 检查固定回复模式
        for (const pattern of this.fixedResponsePatterns) {
            const matches = contents.filter(content => pattern.test(content));
            if (matches.length > 0) {
                fixedPatterns.push({
                    pattern: pattern.toString(),
                    matches: matches.length,
                    examples: matches.slice(0, 3)
                });
            }
        }
        
        // 计算多样性分数
        const uniqueResponses = new Set(contents);
        const diversityScore = uniqueResponses.size / contents.length;
        
        return {
            hasFixedResponses: fixedPatterns.length > 0,
            lowDiversity: diversityScore < 0.7,
            diversityScore,
            fixedPatterns
        };
    }
    
    async getBackendLLMConfig() {
        try {
            const response = await fetch(this.apiEndpoints.dialogConfig, {
                method: 'GET',
                timeout: 5000
            });
            
            if (response.ok) {
                return await response.json();
            }
            
            return null;
        } catch (error) {
            console.error('获取后端LLM配置失败:', error);
            return null;
        }
    }
    
    compareConfigurations(localConfig, backendConfig) {
        const differences = [];
        
        const compareFields = ['apiKey', 'baseUrl', 'model', 'maxTokens', 'temperature'];
        
        for (const field of compareFields) {
            if (localConfig[field] !== backendConfig[field]) {
                differences.push({
                    field,
                    local: localConfig[field],
                    backend: backendConfig[field]
                });
            }
        }
        
        return {
            hasDifferences: differences.length > 0,
            differences
        };
    }
    
    // 修复方法实现
    
    async fixMissingLLMConfig(issue) {
        // 尝试从默认配置或环境变量创建配置
        const defaultConfig = {
            apiKey: 'your-api-key-here',
            baseUrl: 'https://api.openai.com',
            model: 'gpt-3.5-turbo',
            maxTokens: 2000,
            temperature: 0.7
        };
        
        localStorage.setItem('llm_configs', JSON.stringify(defaultConfig));
        
        return {
            issue: issue.type,
            status: 'fixed',
            message: '已创建默认LLM配置，请更新API密钥',
            config: defaultConfig,
            timestamp: new Date().toISOString()
        };
    }
    
    async fixInvalidLLMConfig(issue) {
        const config = this.getLocalLLMConfig();
        
        // 修复配置中的问题
        if (!config.maxTokens || config.maxTokens < 1) {
            config.maxTokens = 2000;
        }
        
        if (!config.temperature || config.temperature < 0 || config.temperature > 2) {
            config.temperature = 0.7;
        }
        
        localStorage.setItem('llm_configs', JSON.stringify(config));
        
        return {
            issue: issue.type,
            status: 'fixed',
            message: '已修复LLM配置中的无效参数',
            fixedConfig: config,
            timestamp: new Date().toISOString()
        };
    }
    
    async fixLLMConnection(issue) {
        // 尝试重新测试连接
        const config = this.getLocalLLMConfig();
        const connectionTest = await this.testLLMConnection(config);
        
        if (connectionTest.success) {
            return {
                issue: issue.type,
                status: 'fixed',
                message: 'LLM连接已恢复',
                timestamp: new Date().toISOString()
            };
        } else {
            return {
                issue: issue.type,
                status: 'failed',
                message: `LLM连接仍然失败: ${connectionTest.error}`,
                error: connectionTest.error,
                timestamp: new Date().toISOString()
            };
        }
    }
    
    async fixBackendConnection(issue) {
        // 尝试重新连接后端
        try {
            const response = await fetch(this.apiEndpoints.health, {
                method: 'GET',
                timeout: 5000
            });
            
            if (response.ok) {
                return {
                    issue: issue.type,
                    status: 'fixed',
                    message: '后端连接已恢复',
                    timestamp: new Date().toISOString()
                };
            } else {
                return {
                    issue: issue.type,
                    status: 'failed',
                    message: `后端仍然不可用: ${response.status}`,
                    timestamp: new Date().toISOString()
                };
            }
        } catch (error) {
            return {
                issue: issue.type,
                status: 'failed',
                message: `后端连接修复失败: ${error.message}`,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }
    
    async fixFixedResponses(issue) {
        // 尝试重新配置对话后端以解决固定回复问题
        const config = this.getLocalLLMConfig();
        
        if (!config) {
            return {
                issue: issue.type,
                status: 'failed',
                message: '无法修复固定回复：LLM配置缺失',
                timestamp: new Date().toISOString()
            };
        }
        
        try {
            // 同步配置到后端
            const syncResult = await this.syncConfigurationToBackend(config);
            
            if (syncResult.success) {
                return {
                    issue: issue.type,
                    status: 'fixed',
                    message: '已重新配置对话后端，固定回复问题应该得到解决',
                    timestamp: new Date().toISOString()
                };
            } else {
                return {
                    issue: issue.type,
                    status: 'failed',
                    message: `配置同步失败: ${syncResult.error}`,
                    error: syncResult.error,
                    timestamp: new Date().toISOString()
                };
            }
        } catch (error) {
            return {
                issue: issue.type,
                status: 'failed',
                message: `修复固定回复失败: ${error.message}`,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }
    
    async fixConfigurationSync(issue) {
        const localConfig = this.getLocalLLMConfig();
        
        try {
            const syncResult = await this.syncConfigurationToBackend(localConfig);
            
            if (syncResult.success) {
                return {
                    issue: issue.type,
                    status: 'fixed',
                    message: '配置同步已完成',
                    timestamp: new Date().toISOString()
                };
            } else {
                return {
                    issue: issue.type,
                    status: 'failed',
                    message: `配置同步失败: ${syncResult.error}`,
                    error: syncResult.error,
                    timestamp: new Date().toISOString()
                };
            }
        } catch (error) {
            return {
                issue: issue.type,
                status: 'failed',
                message: `配置同步修复失败: ${error.message}`,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }
    
    async fixMissingBackendConfig(issue) {
        const localConfig = this.getLocalLLMConfig();
        
        if (!localConfig) {
            return {
                issue: issue.type,
                status: 'failed',
                message: '无法修复后端配置：本地配置也缺失',
                timestamp: new Date().toISOString()
            };
        }
        
        try {
            const syncResult = await this.syncConfigurationToBackend(localConfig);
            
            if (syncResult.success) {
                return {
                    issue: issue.type,
                    status: 'fixed',
                    message: '已将本地配置同步到后端',
                    timestamp: new Date().toISOString()
                };
            } else {
                return {
                    issue: issue.type,
                    status: 'failed',
                    message: `后端配置创建失败: ${syncResult.error}`,
                    error: syncResult.error,
                    timestamp: new Date().toISOString()
                };
            }
        } catch (error) {
            return {
                issue: issue.type,
                status: 'failed',
                message: `后端配置修复失败: ${error.message}`,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }
    
    async syncConfigurationToBackend(config) {
        try {
            const response = await fetch(this.apiEndpoints.dialogConfig, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config),
                timeout: 10000
            });
            
            if (response.ok) {
                return { success: true };
            } else {
                const errorData = await response.json().catch(() => ({}));
                return { 
                    success: false, 
                    error: errorData.message || `HTTP ${response.status}` 
                };
            }
        } catch (error) {
            return { 
                success: false, 
                error: error.message 
            };
        }
    }
    
    // 验证方法实现
    
    async verifyLLMConfiguration() {
        try {
            const config = this.getLocalLLMConfig();
            if (!config) {
                return {
                    name: 'LLM配置验证',
                    passed: false,
                    message: 'LLM配置缺失'
                };
            }
            
            const validation = this.validateLLMConfig(config);
            if (!validation.valid) {
                return {
                    name: 'LLM配置验证',
                    passed: false,
                    message: `配置无效: ${validation.errors.join(', ')}`
                };
            }
            
            const connectionTest = await this.testLLMConnection(config);
            if (!connectionTest.success) {
                return {
                    name: 'LLM配置验证',
                    passed: false,
                    message: `连接测试失败: ${connectionTest.error}`
                };
            }
            
            return {
                name: 'LLM配置验证',
                passed: true,
                message: 'LLM配置正常'
            };
        } catch (error) {
            return {
                name: 'LLM配置验证',
                passed: false,
                error: error.message
            };
        }
    }
    
    async verifyDialogBackendConnection() {
        try {
            const response = await fetch(this.apiEndpoints.health, {
                method: 'GET',
                timeout: 5000
            });
            
            return {
                name: '对话后端连接验证',
                passed: response.ok,
                message: response.ok ? '后端连接正常' : `后端连接失败: ${response.status}`
            };
        } catch (error) {
            return {
                name: '对话后端连接验证',
                passed: false,
                error: error.message
            };
        }
    }
    
    async verifyDialogFunction() {
        try {
            const testMessage = '这是一个验证测试消息';
            const response = await this.sendTestMessage(testMessage);
            
            if (!response || !response.content) {
                return {
                    name: '对话功能验证',
                    passed: false,
                    message: '对话系统无响应'
                };
            }
            
            // 检查是否为固定回复
            const isFixed = this.fixedResponsePatterns.some(pattern => 
                pattern.test(response.content)
            );
            
            return {
                name: '对话功能验证',
                passed: !isFixed,
                message: isFixed ? '检测到固定回复模式' : '对话功能正常',
                response: response.content
            };
        } catch (error) {
            return {
                name: '对话功能验证',
                passed: false,
                error: error.message
            };
        }
    }
    
    async verifyConfigurationSync() {
        try {
            const localConfig = this.getLocalLLMConfig();
            const backendConfig = await this.getBackendLLMConfig();
            
            if (!localConfig || !backendConfig) {
                return {
                    name: '配置同步验证',
                    passed: false,
                    message: '配置缺失，无法验证同步状态'
                };
            }
            
            const configDiff = this.compareConfigurations(localConfig, backendConfig);
            
            return {
                name: '配置同步验证',
                passed: !configDiff.hasDifferences,
                message: configDiff.hasDifferences ? 
                    `配置不同步，差异: ${configDiff.differences.length} 项` : 
                    '配置同步正常'
            };
        } catch (error) {
            return {
                name: '配置同步验证',
                passed: false,
                error: error.message
            };
        }
    }
    
    prioritizeIssues(issues) {
        const severityOrder = {
            'critical': 0,
            'high': 1,
            'medium': 2,
            'low': 3,
            'info': 4
        };
        
        return issues.sort((a, b) => {
            const aPriority = severityOrder[a.severity] || 5;
            const bPriority = severityOrder[b.severity] || 5;
            return aPriority - bPriority;
        });
    }
}

export default DialogInteractionFixer;