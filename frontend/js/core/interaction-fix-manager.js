/**
 * 交互修复管理器 - 统一的前端交互问题诊断和修复系统
 * 负责检测和修复各种前端交互问题，包括对话、智能体管理、LLM配置等
 */

class InteractionFixManager {
    constructor() {
        this.fixers = new Map();
        this.diagnostics = null;
        this.autoFix = null;
        this.monitoring = null;
        this.initialized = false;
        this.fixHistory = [];
        
        this.init();
    }
    
    async init() {
        try {
            // 动态导入子系统类
            const DiagnosticEngine = (await import('./diagnostic-engine.js')).default;
            const AutoFixEngine = (await import('./auto-fix-engine.js')).default;
            const InteractionMonitoring = (await import('./interaction-monitoring.js')).default;
            
            // 初始化子系统
            this.diagnostics = new DiagnosticEngine();
            this.autoFix = new AutoFixEngine();
            this.monitoring = new InteractionMonitoring();
            
            // 注册各种修复器
            await this.initializeFixers();
            
            this.initialized = true;
            console.log('交互修复管理器初始化完成');
            
        } catch (error) {
            console.error('交互修复管理器初始化失败:', error);
            throw error;
        }
    }
    
    async initializeFixers() {
        // 注册各种专门的修复器
        try {
            // 对话交互修复器
            const DialogInteractionFixer = (await import('../fixers/dialog-interaction-fixer.js')).default;
            this.fixers.set('dialog', new DialogInteractionFixer());
            
            // 智能体管理修复器
            const AgentManagementFixer = (await import('../fixers/agent-management-fixer.js')).default;
            this.fixers.set('agent_management', new AgentManagementFixer());
            
            // LLM配置修复器
            const LLMConfigFixer = (await import('../fixers/llm-config-fixer.js')).default;
            this.fixers.set('llm_config', new LLMConfigFixer());
            
            // 任务依赖关系修复器
            const TaskDependencyFixer = (await import('../fixers/task-dependency-fixer.js')).default;
            this.fixers.set('task_dependency', new TaskDependencyFixer());
            
            // 元智能体对话修复器
            const MetaAgentChatFixer = (await import('../fixers/meta-agent-chat-fixer.js')).default;
            this.fixers.set('meta_agent_chat', new MetaAgentChatFixer());
            
            console.log(`已注册 ${this.fixers.size} 个修复器`);
            
        } catch (error) {
            console.error('修复器初始化失败:', error);
            // 如果修复器加载失败，创建占位符
            this.createPlaceholderFixers();
        }
    }
    
    createPlaceholderFixers() {
        // 创建占位符修复器，防止系统崩溃
        const placeholderFixer = {
            diagnose: async () => [{ type: 'fixer_not_loaded', severity: 'warning', message: '修复器未加载' }],
            fix: async () => [{ issue: 'fixer_not_loaded', status: 'skipped' }],
            verify: async () => ({ allPassed: false, results: [{ name: '修复器验证', passed: false, error: '修复器未加载' }] })
        };
        
        this.fixers.set('dialog', placeholderFixer);
        this.fixers.set('agent_management', placeholderFixer);
        this.fixers.set('llm_config', placeholderFixer);
        this.fixers.set('task_dependency', placeholderFixer);
        this.fixers.set('meta_agent_chat', placeholderFixer);
    }
    
    /**
     * 诊断并修复特定组件的交互问题
     * @param {string} component - 组件名称
     * @returns {Promise<Object>} 修复结果
     */
    async diagnoseAndFix(component) {
        if (!this.initialized) {
            throw new Error('交互修复管理器未初始化');
        }
        
        const fixer = this.fixers.get(component);
        if (!fixer) {
            throw new Error(`未找到组件 ${component} 的修复器`);
        }
        
        const startTime = Date.now();
        
        try {
            console.log(`开始诊断组件: ${component}`);
            
            // 1. 诊断问题
            const issues = await fixer.diagnose();
            console.log(`发现 ${issues.length} 个问题:`, issues);
            
            // 2. 执行修复
            const results = await fixer.fix(issues);
            console.log(`修复结果:`, results);
            
            // 3. 验证修复效果
            const verification = await fixer.verify();
            console.log(`验证结果:`, verification);
            
            const endTime = Date.now();
            const duration = endTime - startTime;
            
            // 4. 记录修复历史
            const fixRecord = {
                component,
                issues,
                results,
                verification,
                success: verification.allPassed,
                duration,
                timestamp: new Date().toISOString()
            };
            
            this.monitoring.recordFix(fixRecord);
            this.fixHistory.push(fixRecord);
            
            return fixRecord;
            
        } catch (error) {
            console.error(`修复组件 ${component} 时发生错误:`, error);
            
            const errorRecord = {
                component,
                error: error.message,
                success: false,
                duration: Date.now() - startTime,
                timestamp: new Date().toISOString()
            };
            
            this.fixHistory.push(errorRecord);
            return errorRecord;
        }
    }
    
    /**
     * 修复所有交互问题
     * @returns {Promise<Array>} 所有组件的修复结果
     */
    async fixAllInteractions() {
        if (!this.initialized) {
            throw new Error('交互修复管理器未初始化');
        }
        
        console.log('开始修复所有交互问题...');
        const results = [];
        
        // 按优先级顺序修复
        const fixOrder = ['llm_config', 'dialog', 'meta_agent_chat', 'agent_management', 'task_dependency'];
        
        for (const component of fixOrder) {
            try {
                console.log(`正在修复: ${component}`);
                const result = await this.diagnoseAndFix(component);
                results.push(result);
                
                // 如果关键组件修复失败，记录但继续
                if (!result.success && ['llm_config', 'dialog'].includes(component)) {
                    console.warn(`关键组件 ${component} 修复失败，但继续处理其他组件`);
                }
                
            } catch (error) {
                console.error(`修复组件 ${component} 失败:`, error);
                results.push({
                    component,
                    error: error.message,
                    success: false,
                    timestamp: new Date().toISOString()
                });
            }
        }
        
        // 生成修复报告
        const report = this.generateFixReport(results);
        console.log('修复完成，报告:', report);
        
        return results;
    }
    
    /**
     * 获取特定组件的修复器
     * @param {string} component - 组件名称
     * @returns {Object} 修复器实例
     */
    getFixer(component) {
        return this.fixers.get(component);
    }
    
    /**
     * 获取所有已注册的修复器
     * @returns {Array} 修复器列表
     */
    getAvailableFixers() {
        return Array.from(this.fixers.keys());
    }
    
    /**
     * 获取修复历史
     * @param {string} component - 可选，特定组件的历史
     * @returns {Array} 修复历史记录
     */
    getFixHistory(component = null) {
        if (component) {
            return this.fixHistory.filter(record => record.component === component);
        }
        return [...this.fixHistory];
    }
    
    /**
     * 生成修复报告
     * @param {Array} results - 修复结果
     * @returns {Object} 修复报告
     */
    generateFixReport(results) {
        const totalComponents = results.length;
        const successfulFixes = results.filter(r => r.success).length;
        const failedFixes = results.filter(r => !r.success).length;
        
        const criticalIssues = results.reduce((count, result) => {
            if (result.issues) {
                return count + result.issues.filter(issue => issue.severity === 'critical').length;
            }
            return count;
        }, 0);
        
        const totalDuration = results.reduce((sum, result) => sum + (result.duration || 0), 0);
        
        return {
            summary: {
                totalComponents,
                successfulFixes,
                failedFixes,
                successRate: totalComponents > 0 ? (successfulFixes / totalComponents * 100).toFixed(1) + '%' : '0%',
                criticalIssues,
                totalDuration: totalDuration + 'ms'
            },
            details: results,
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * 清除修复历史
     */
    clearHistory() {
        this.fixHistory = [];
        console.log('修复历史已清除');
    }
    
    /**
     * 获取系统状态
     * @returns {Object} 系统状态信息
     */
    getStatus() {
        return {
            initialized: this.initialized,
            availableFixers: this.getAvailableFixers(),
            historyCount: this.fixHistory.length,
            lastFix: this.fixHistory.length > 0 ? this.fixHistory[this.fixHistory.length - 1] : null
        };
    }
}

// 导出类
export default InteractionFixManager;

// 创建全局实例
window.InteractionFixManager = InteractionFixManager;