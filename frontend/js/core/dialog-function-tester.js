/**
 * 对话功能测试系统
 * 负责测试对话是否返回固定回复，实现多轮对话测试，验证回复的多样性
 */

class DialogFunctionTester {
    constructor() {
        this.apiEndpoints = {
            dialogTest: '/api/v1/dialog/test',
            dialogChat: '/api/v1/dialog/chat',
            dialogHistory: '/api/v1/dialog/history'
        };
        
        // 测试消息集合，用于检测固定回复
        this.testMessages = {
            greetings: [
                '你好',
                'Hello',
                '早上好',
                '下午好',
                '晚上好'
            ],
            questions: [
                '你是谁？',
                '你能做什么？',
                '请介绍一下自己',
                '你有什么功能？',
                '你是什么？'
            ],
            requests: [
                '请帮我分析一个问题',
                '给我一些建议',
                '帮我写一段代码',
                '解释一下这个概念',
                '请总结一下'
            ],
            casual: [
                '今天天气怎么样？',
                '你觉得这个想法如何？',
                '有什么新闻吗？',
                '推荐一本书',
                '聊聊天吧'
            ],
            technical: [
                '什么是机器学习？',
                '如何优化数据库性能？',
                '解释一下REST API',
                'JavaScript和Python的区别',
                '什么是微服务架构？'
            ]
        };
        
        // 固定回复模式检测
        this.fixedResponsePatterns = [
            {
                name: '通用拒绝',
                pattern: /^(很抱歉|抱歉|对不起).*?(无法|不能|无法提供)/i,
                severity: 'high'
            },
            {
                name: '功能限制',
                pattern: /^我(只是|仅仅是|是一个).*?(助手|AI|机器人).*?(无法|不能)/i,
                severity: 'high'
            },
            {
                name: '重复介绍',
                pattern: /^我是.*?(助手|AI|智能助手).*?可以帮助/i,
                severity: 'medium'
            },
            {
                name: '标准回复',
                pattern: /^(我理解|我明白).*?(但是|不过|然而).*?(无法|不能)/i,
                severity: 'medium'
            },
            {
                name: '空洞回复',
                pattern: /^(这是一个|这个问题|关于这个).*?(很复杂|需要考虑|因人而异)/i,
                severity: 'low'
            }
        ];
        
        this.testResults = [];
        this.conversationHistory = [];
        this.qualityMetrics = {
            diversity: 0,
            relevance: 0,
            coherence: 0,
            engagement: 0
        };
    }
    
    /**
     * 测试对话功能
     * @param {Object} options - 测试选项
     * @returns {Promise<Object>} 测试结果
     */
    async testDialogFunction(options = {}) {
        const testConfig = {
            includeMultiTurn: true,
            testAllCategories: true,
            maxMessagesPerCategory: 3,
            delayBetweenMessages: 1000,
            timeoutPerMessage: 15000,
            ...options
        };
        
        console.log('开始对话功能测试...', testConfig);
        
        try {
            const testResults = {
                startTime: new Date().toISOString(),
                config: testConfig,
                results: {
                    singleTurn: [],
                    multiTurn: [],
                    fixedResponseAnalysis: null,
                    qualityAssessment: null
                },
                summary: {
                    totalMessages: 0,
                    successfulResponses: 0,
                    failedResponses: 0,
                    fixedResponses: 0,
                    diversityScore: 0,
                    overallScore: 0
                }
            };
            
            // 1. 单轮对话测试
            console.log('执行单轮对话测试...');
            testResults.results.singleTurn = await this.runSingleTurnTests(testConfig);
            
            // 2. 多轮对话测试
            if (testConfig.includeMultiTurn) {
                console.log('执行多轮对话测试...');
                testResults.results.multiTurn = await this.runMultiTurnTests(testConfig);
            }
            
            // 3. 分析固定回复模式
            console.log('分析回复模式...');
            testResults.results.fixedResponseAnalysis = this.analyzeFixedResponses(testResults);
            
            // 4. 评估对话质量
            console.log('评估对话质量...');
            testResults.results.qualityAssessment = this.assessDialogQuality(testResults);
            
            // 5. 生成测试摘要
            testResults.summary = this.generateTestSummary(testResults);
            testResults.endTime = new Date().toISOString();
            testResults.duration = new Date(testResults.endTime) - new Date(testResults.startTime);
            
            // 保存测试结果
            this.testResults.push(testResults);
            
            console.log('对话功能测试完成:', testResults.summary);
            return testResults;
            
        } catch (error) {
            console.error('对话功能测试失败:', error);
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }
    
    /**
     * 运行单轮对话测试
     * @param {Object} config - 测试配置
     * @returns {Promise<Array>} 单轮测试结果
     */
    async runSingleTurnTests(config) {
        const results = [];
        
        for (const [category, messages] of Object.entries(this.testMessages)) {
            if (!config.testAllCategories && category !== 'questions') {
                continue; // 如果不测试所有类别，只测试问题类别
            }
            
            const categoryResults = {
                category: category,
                messages: [],
                summary: {
                    total: 0,
                    successful: 0,
                    failed: 0,
                    avgResponseTime: 0
                }
            };
            
            const testMessages = messages.slice(0, config.maxMessagesPerCategory);
            
            for (const message of testMessages) {
                try {
                    const startTime = Date.now();
                    
                    const response = await this.sendSingleMessage(message, {
                        timeout: config.timeoutPerMessage
                    });
                    
                    const endTime = Date.now();
                    const responseTime = endTime - startTime;
                    
                    const messageResult = {
                        message: message,
                        response: response.content,
                        responseTime: responseTime,
                        success: true,
                        timestamp: new Date().toISOString(),
                        metadata: response.metadata || {}
                    };
                    
                    categoryResults.messages.push(messageResult);
                    categoryResults.summary.successful++;
                    
                    // 延迟避免请求过快
                    if (config.delayBetweenMessages > 0) {
                        await new Promise(resolve => setTimeout(resolve, config.delayBetweenMessages));
                    }
                    
                } catch (error) {
                    console.error(`单轮测试失败 [${category}] "${message}":`, error);
                    
                    const messageResult = {
                        message: message,
                        response: null,
                        responseTime: 0,
                        success: false,
                        error: error.message,
                        timestamp: new Date().toISOString()
                    };
                    
                    categoryResults.messages.push(messageResult);
                    categoryResults.summary.failed++;
                }
                
                categoryResults.summary.total++;
            }
            
            // 计算平均响应时间
            const successfulMessages = categoryResults.messages.filter(m => m.success);
            if (successfulMessages.length > 0) {
                categoryResults.summary.avgResponseTime = 
                    successfulMessages.reduce((sum, m) => sum + m.responseTime, 0) / successfulMessages.length;
            }
            
            results.push(categoryResults);
        }
        
        return results;
    }
    
    /**
     * 运行多轮对话测试
     * @param {Object} config - 测试配置
     * @returns {Promise<Array>} 多轮测试结果
     */
    async runMultiTurnTests(config) {
        const results = [];
        
        // 定义多轮对话场景
        const multiTurnScenarios = [
            {
                name: '问题深入',
                messages: [
                    '什么是人工智能？',
                    '它有哪些应用领域？',
                    '在医疗领域具体如何应用？',
                    '有什么挑战和限制吗？'
                ]
            },
            {
                name: '技术讨论',
                messages: [
                    '我想学习编程',
                    '推荐什么语言开始？',
                    'Python适合初学者吗？',
                    '有什么好的学习资源？'
                ]
            },
            {
                name: '问题解决',
                messages: [
                    '我的网站加载很慢',
                    '可能是什么原因？',
                    '如何优化图片加载？',
                    '还有其他优化建议吗？'
                ]
            }
        ];
        
        for (const scenario of multiTurnScenarios) {
            try {
                console.log(`执行多轮对话场景: ${scenario.name}`);
                
                const scenarioResult = {
                    name: scenario.name,
                    messages: [],
                    conversationFlow: [],
                    coherenceScore: 0,
                    contextRetention: 0,
                    success: true
                };
                
                let conversationContext = [];
                
                for (let i = 0; i < scenario.messages.length; i++) {
                    const message = scenario.messages[i];
                    
                    try {
                        const startTime = Date.now();
                        
                        const response = await this.sendMessageWithContext(message, conversationContext, {
                            timeout: config.timeoutPerMessage
                        });
                        
                        const endTime = Date.now();
                        const responseTime = endTime - startTime;
                        
                        const messageResult = {
                            turn: i + 1,
                            message: message,
                            response: response.content,
                            responseTime: responseTime,
                            success: true,
                            timestamp: new Date().toISOString(),
                            contextUsed: response.contextUsed || false
                        };
                        
                        scenarioResult.messages.push(messageResult);
                        
                        // 更新对话上下文
                        conversationContext.push({
                            role: 'user',
                            content: message
                        });
                        conversationContext.push({
                            role: 'assistant',
                            content: response.content
                        });
                        
                        // 分析对话流
                        if (i > 0) {
                            const flowAnalysis = this.analyzeConversationFlow(
                                scenarioResult.messages[i - 1],
                                messageResult
                            );
                            scenarioResult.conversationFlow.push(flowAnalysis);
                        }
                        
                        // 延迟
                        if (config.delayBetweenMessages > 0) {
                            await new Promise(resolve => setTimeout(resolve, config.delayBetweenMessages));
                        }
                        
                    } catch (error) {
                        console.error(`多轮测试失败 [${scenario.name}] 第${i + 1}轮:`, error);
                        
                        scenarioResult.messages.push({
                            turn: i + 1,
                            message: message,
                            response: null,
                            success: false,
                            error: error.message,
                            timestamp: new Date().toISOString()
                        });
                        
                        scenarioResult.success = false;
                        break; // 如果某轮失败，停止该场景
                    }
                }
                
                // 计算场景指标
                if (scenarioResult.success) {
                    scenarioResult.coherenceScore = this.calculateCoherenceScore(scenarioResult);
                    scenarioResult.contextRetention = this.calculateContextRetention(scenarioResult);
                }
                
                results.push(scenarioResult);
                
            } catch (error) {
                console.error(`多轮对话场景 ${scenario.name} 失败:`, error);
                results.push({
                    name: scenario.name,
                    success: false,
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
            }
        }
        
        return results;
    }
    
    /**
     * 发送单条消息
     * @param {string} message - 消息内容
     * @param {Object} options - 选项
     * @returns {Promise<Object>} 响应结果
     */
    async sendSingleMessage(message, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), options.timeout || 15000);
        
        try {
            const response = await fetch(this.apiEndpoints.dialogTest, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    timestamp: new Date().toISOString(),
                    testMode: true
                }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (!result.content) {
                throw new Error('响应内容为空');
            }
            
            return result;
            
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('请求超时');
            }
            
            throw error;
        }
    }
    
    /**
     * 发送带上下文的消息
     * @param {string} message - 消息内容
     * @param {Array} context - 对话上下文
     * @param {Object} options - 选项
     * @returns {Promise<Object>} 响应结果
     */
    async sendMessageWithContext(message, context, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), options.timeout || 15000);
        
        try {
            const response = await fetch(this.apiEndpoints.dialogChat, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    context: context,
                    timestamp: new Date().toISOString(),
                    testMode: true
                }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (!result.content) {
                throw new Error('响应内容为空');
            }
            
            return result;
            
        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('请求超时');
            }
            
            throw error;
        }
    }
    
    /**
     * 分析固定回复模式
     * @param {Object} testResults - 测试结果
     * @returns {Object} 固定回复分析结果
     */
    analyzeFixedResponses(testResults) {
        const analysis = {
            detectedPatterns: [],
            fixedResponseCount: 0,
            totalResponseCount: 0,
            fixedResponseRate: 0,
            severityDistribution: {
                high: 0,
                medium: 0,
                low: 0
            },
            examples: []
        };
        
        // 收集所有响应
        const allResponses = [];
        
        // 从单轮测试收集响应
        if (testResults.results.singleTurn) {
            for (const category of testResults.results.singleTurn) {
                for (const message of category.messages) {
                    if (message.success && message.response) {
                        allResponses.push({
                            message: message.message,
                            response: message.response,
                            category: category.category,
                            type: 'single-turn'
                        });
                    }
                }
            }
        }
        
        // 从多轮测试收集响应
        if (testResults.results.multiTurn) {
            for (const scenario of testResults.results.multiTurn) {
                for (const message of scenario.messages) {
                    if (message.success && message.response) {
                        allResponses.push({
                            message: message.message,
                            response: message.response,
                            scenario: scenario.name,
                            turn: message.turn,
                            type: 'multi-turn'
                        });
                    }
                }
            }
        }
        
        analysis.totalResponseCount = allResponses.length;
        
        // 检测固定回复模式
        for (const pattern of this.fixedResponsePatterns) {
            const matches = allResponses.filter(resp => 
                pattern.pattern.test(resp.response)
            );
            
            if (matches.length > 0) {
                analysis.detectedPatterns.push({
                    name: pattern.name,
                    pattern: pattern.pattern.toString(),
                    severity: pattern.severity,
                    matchCount: matches.length,
                    matchRate: matches.length / allResponses.length,
                    examples: matches.slice(0, 3).map(m => ({
                        message: m.message,
                        response: m.response,
                        type: m.type
                    }))
                });
                
                analysis.fixedResponseCount += matches.length;
                analysis.severityDistribution[pattern.severity] += matches.length;
            }
        }
        
        // 检测完全相同的回复
        const responseGroups = {};
        for (const resp of allResponses) {
            const key = resp.response.trim().toLowerCase();
            if (!responseGroups[key]) {
                responseGroups[key] = [];
            }
            responseGroups[key].push(resp);
        }
        
        const duplicateResponses = Object.entries(responseGroups)
            .filter(([_, responses]) => responses.length > 1)
            .map(([response, responses]) => ({
                response: responses[0].response,
                count: responses.length,
                examples: responses.slice(0, 3)
            }));
        
        if (duplicateResponses.length > 0) {
            analysis.detectedPatterns.push({
                name: '完全重复回复',
                severity: 'high',
                matchCount: duplicateResponses.reduce((sum, dup) => sum + dup.count, 0),
                duplicates: duplicateResponses
            });
        }
        
        analysis.fixedResponseRate = analysis.totalResponseCount > 0 ? 
            analysis.fixedResponseCount / analysis.totalResponseCount : 0;
        
        return analysis;
    }
    
    /**
     * 评估对话质量
     * @param {Object} testResults - 测试结果
     * @returns {Object} 质量评估结果
     */
    assessDialogQuality(testResults) {
        const assessment = {
            diversity: this.calculateDiversityScore(testResults),
            relevance: this.calculateRelevanceScore(testResults),
            coherence: this.calculateCoherenceScore(testResults),
            engagement: this.calculateEngagementScore(testResults),
            overallScore: 0,
            grade: 'F',
            recommendations: []
        };
        
        // 计算总分
        assessment.overallScore = (
            assessment.diversity * 0.3 +
            assessment.relevance * 0.3 +
            assessment.coherence * 0.2 +
            assessment.engagement * 0.2
        );
        
        // 确定等级
        if (assessment.overallScore >= 0.9) {
            assessment.grade = 'A';
        } else if (assessment.overallScore >= 0.8) {
            assessment.grade = 'B';
        } else if (assessment.overallScore >= 0.7) {
            assessment.grade = 'C';
        } else if (assessment.overallScore >= 0.6) {
            assessment.grade = 'D';
        } else {
            assessment.grade = 'F';
        }
        
        // 生成建议
        assessment.recommendations = this.generateQualityRecommendations(assessment);
        
        return assessment;
    }
    
    /**
     * 计算多样性分数
     * @param {Object} testResults - 测试结果
     * @returns {number} 多样性分数 (0-1)
     */
    calculateDiversityScore(testResults) {
        const allResponses = this.extractAllResponses(testResults);
        
        if (allResponses.length === 0) {
            return 0;
        }
        
        // 计算唯一响应的比例
        const uniqueResponses = new Set(allResponses.map(r => r.response.trim().toLowerCase()));
        const uniqueRatio = uniqueResponses.size / allResponses.length;
        
        // 计算平均响应长度变化
        const responseLengths = allResponses.map(r => r.response.length);
        const avgLength = responseLengths.reduce((sum, len) => sum + len, 0) / responseLengths.length;
        const lengthVariance = responseLengths.reduce((sum, len) => sum + Math.pow(len - avgLength, 2), 0) / responseLengths.length;
        const lengthDiversity = Math.min(1, lengthVariance / (avgLength * avgLength));
        
        return (uniqueRatio * 0.7 + lengthDiversity * 0.3);
    }
    
    /**
     * 计算相关性分数
     * @param {Object} testResults - 测试结果
     * @returns {number} 相关性分数 (0-1)
     */
    calculateRelevanceScore(testResults) {
        // 简化的相关性评估，基于响应是否包含问题相关的关键词
        const allResponses = this.extractAllResponses(testResults);
        
        if (allResponses.length === 0) {
            return 0;
        }
        
        let relevantCount = 0;
        
        for (const resp of allResponses) {
            const messageWords = resp.message.toLowerCase().split(/\s+/);
            const responseWords = resp.response.toLowerCase().split(/\s+/);
            
            // 检查响应是否包含问题中的关键词
            const keywordOverlap = messageWords.filter(word => 
                word.length > 2 && responseWords.includes(word)
            ).length;
            
            // 检查是否为通用拒绝回复
            const isGenericRefusal = this.fixedResponsePatterns.some(pattern => 
                pattern.pattern.test(resp.response)
            );
            
            if (keywordOverlap > 0 && !isGenericRefusal) {
                relevantCount++;
            }
        }
        
        return relevantCount / allResponses.length;
    }
    
    /**
     * 计算连贯性分数
     * @param {Object} testResults - 测试结果
     * @returns {number} 连贯性分数 (0-1)
     */
    calculateCoherenceScore(testResults) {
        if (!testResults.results.multiTurn) {
            return 0.5; // 如果没有多轮测试，给中等分数
        }
        
        let totalCoherence = 0;
        let scenarioCount = 0;
        
        for (const scenario of testResults.results.multiTurn) {
            if (scenario.success && scenario.messages.length > 1) {
                let scenarioCoherence = 0;
                
                for (let i = 1; i < scenario.messages.length; i++) {
                    const prevMessage = scenario.messages[i - 1];
                    const currMessage = scenario.messages[i];
                    
                    if (prevMessage.success && currMessage.success) {
                        // 简化的连贯性检查：响应是否延续了对话主题
                        const coherence = this.checkResponseCoherence(
                            prevMessage.response,
                            currMessage.message,
                            currMessage.response
                        );
                        scenarioCoherence += coherence;
                    }
                }
                
                if (scenario.messages.length > 1) {
                    totalCoherence += scenarioCoherence / (scenario.messages.length - 1);
                    scenarioCount++;
                }
            }
        }
        
        return scenarioCount > 0 ? totalCoherence / scenarioCount : 0.5;
    }
    
    /**
     * 计算参与度分数
     * @param {Object} testResults - 测试结果
     * @returns {number} 参与度分数 (0-1)
     */
    calculateEngagementScore(testResults) {
        const allResponses = this.extractAllResponses(testResults);
        
        if (allResponses.length === 0) {
            return 0;
        }
        
        let engagementScore = 0;
        
        for (const resp of allResponses) {
            let score = 0;
            
            // 响应长度（适中的长度表示更好的参与）
            const length = resp.response.length;
            if (length > 20 && length < 500) {
                score += 0.3;
            }
            
            // 是否包含问题或进一步的互动
            if (/[？?]/.test(resp.response)) {
                score += 0.2;
            }
            
            // 是否提供具体信息而非通用回复
            if (!/^(我是|很抱歉|对不起|我无法)/.test(resp.response)) {
                score += 0.3;
            }
            
            // 是否使用积极的语言
            if (/(可以|能够|帮助|建议|推荐)/.test(resp.response)) {
                score += 0.2;
            }
            
            engagementScore += Math.min(1, score);
        }
        
        return engagementScore / allResponses.length;
    }
    
    /**
     * 生成测试摘要
     * @param {Object} testResults - 测试结果
     * @returns {Object} 测试摘要
     */
    generateTestSummary(testResults) {
        const summary = {
            totalMessages: 0,
            successfulResponses: 0,
            failedResponses: 0,
            fixedResponses: 0,
            diversityScore: 0,
            overallScore: 0,
            grade: 'F',
            issues: [],
            recommendations: []
        };
        
        // 统计消息数量
        if (testResults.results.singleTurn) {
            for (const category of testResults.results.singleTurn) {
                summary.totalMessages += category.summary.total;
                summary.successfulResponses += category.summary.successful;
                summary.failedResponses += category.summary.failed;
            }
        }
        
        if (testResults.results.multiTurn) {
            for (const scenario of testResults.results.multiTurn) {
                summary.totalMessages += scenario.messages.length;
                summary.successfulResponses += scenario.messages.filter(m => m.success).length;
                summary.failedResponses += scenario.messages.filter(m => !m.success).length;
            }
        }
        
        // 从分析结果获取指标
        if (testResults.results.fixedResponseAnalysis) {
            summary.fixedResponses = testResults.results.fixedResponseAnalysis.fixedResponseCount;
        }
        
        if (testResults.results.qualityAssessment) {
            summary.diversityScore = testResults.results.qualityAssessment.diversity;
            summary.overallScore = testResults.results.qualityAssessment.overallScore;
            summary.grade = testResults.results.qualityAssessment.grade;
        }
        
        // 识别问题
        if (summary.failedResponses > 0) {
            summary.issues.push(`${summary.failedResponses} 个消息发送失败`);
        }
        
        if (summary.fixedResponses > summary.totalMessages * 0.3) {
            summary.issues.push('检测到大量固定回复模式');
        }
        
        if (summary.diversityScore < 0.5) {
            summary.issues.push('回复多样性不足');
        }
        
        // 生成建议
        if (summary.issues.length > 0) {
            summary.recommendations.push('需要检查和修复LLM配置');
            summary.recommendations.push('考虑调整模型参数以提高回复质量');
        }
        
        if (summary.overallScore < 0.7) {
            summary.recommendations.push('建议重新训练或更换对话模型');
        }
        
        return summary;
    }
    
    // 辅助方法
    
    extractAllResponses(testResults) {
        const responses = [];
        
        if (testResults.results.singleTurn) {
            for (const category of testResults.results.singleTurn) {
                for (const message of category.messages) {
                    if (message.success && message.response) {
                        responses.push({
                            message: message.message,
                            response: message.response,
                            type: 'single-turn',
                            category: category.category
                        });
                    }
                }
            }
        }
        
        if (testResults.results.multiTurn) {
            for (const scenario of testResults.results.multiTurn) {
                for (const message of scenario.messages) {
                    if (message.success && message.response) {
                        responses.push({
                            message: message.message,
                            response: message.response,
                            type: 'multi-turn',
                            scenario: scenario.name,
                            turn: message.turn
                        });
                    }
                }
            }
        }
        
        return responses;
    }
    
    analyzeConversationFlow(prevMessage, currMessage) {
        return {
            coherent: true, // 简化实现
            contextUsed: currMessage.contextUsed || false,
            topicContinuity: 0.5 // 简化实现
        };
    }
    
    checkResponseCoherence(prevResponse, currMessage, currResponse) {
        // 简化的连贯性检查
        return 0.7; // 返回固定值，实际实现会更复杂
    }
    
    generateQualityRecommendations(assessment) {
        const recommendations = [];
        
        if (assessment.diversity < 0.5) {
            recommendations.push('增加回复的多样性，避免重复回复');
        }
        
        if (assessment.relevance < 0.6) {
            recommendations.push('提高回复的相关性，确保回答用户问题');
        }
        
        if (assessment.coherence < 0.6) {
            recommendations.push('改善多轮对话的连贯性和上下文理解');
        }
        
        if (assessment.engagement < 0.5) {
            recommendations.push('增强对话的参与度和互动性');
        }
        
        return recommendations;
    }
    
    /**
     * 获取测试历史
     * @param {number} limit - 限制数量
     * @returns {Array} 测试历史
     */
    getTestHistory(limit = 10) {
        return this.testResults.slice(-limit);
    }
    
    /**
     * 清除测试历史
     */
    clearTestHistory() {
        this.testResults = [];
        this.conversationHistory = [];
        console.log('测试历史已清除');
    }
    
    /**
     * 获取最新测试结果
     * @returns {Object|null} 最新测试结果
     */
    getLatestTestResult() {
        return this.testResults.length > 0 ? this.testResults[this.testResults.length - 1] : null;
    }
}

// 导出类
export default DialogFunctionTester;

// 创建全局实例
window.DialogFunctionTester = DialogFunctionTester;