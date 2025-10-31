# 交互修复器目录

这个目录包含各种专门的交互修复器，每个修复器负责修复特定类型的前端交互问题。

## 修复器列表

以下修复器将在后续任务中实现：

### 1. DialogInteractionFixer (对话交互修复器)
- **文件**: `dialog-interaction-fixer.js`
- **功能**: 修复时光回音对话回复固定化问题
- **任务**: 2.1 创建对话交互修复器

### 2. AgentManagementFixer (智能体管理修复器)
- **文件**: `agent-management-fixer.js`
- **功能**: 修复智能体管理界面无法交互的问题
- **任务**: 3.1 创建智能体管理修复器

### 3. LLMConfigFixer (LLM配置修复器)
- **文件**: `llm-config-fixer.js`
- **功能**: 修复大模型配置无法保存的问题
- **任务**: 5.1 修复LLM配置保存机制

### 4. TaskDependencyFixer (任务依赖关系修复器)
- **文件**: `task-dependency-fixer.js`
- **功能**: 修复任务依赖关系无法交互的问题
- **任务**: 6.1 创建任务依赖关系修复器

### 5. MetaAgentChatFixer (元智能体对话修复器)
- **文件**: `meta-agent-chat-fixer.js`
- **功能**: 修复元智能体对话无法交互的问题
- **任务**: 7.1 修复元智能体会话初始化

## 修复器接口

每个修复器都应该实现以下接口：

```javascript
class FixerInterface {
    /**
     * 诊断问题
     * @returns {Promise<Array>} 问题列表
     */
    async diagnose() {
        // 返回问题列表，每个问题包含：
        // - type: 问题类型
        // - severity: 严重程度 (critical, high, medium, low, info)
        // - message: 问题描述
        // - 其他相关信息
    }
    
    /**
     * 修复问题
     * @param {Array} issues - 问题列表
     * @returns {Promise<Array>} 修复结果列表
     */
    async fix(issues) {
        // 返回修复结果列表，每个结果包含：
        // - issue: 问题类型
        // - status: 修复状态 (fixed, failed, skipped)
        // - 其他修复信息
    }
    
    /**
     * 验证修复效果
     * @returns {Promise<Object>} 验证结果
     */
    async verify() {
        // 返回验证结果：
        // - allPassed: 是否全部通过
        // - results: 详细验证结果列表
    }
}
```

## 使用说明

修复器会被 `InteractionFixManager` 自动加载和管理。每个修复器都应该：

1. 继承或实现上述接口
2. 提供详细的问题诊断功能
3. 实现相应的修复逻辑
4. 包含修复效果验证
5. 处理各种异常情况
6. 提供清晰的日志输出

## 开发指南

在开发新的修复器时，请遵循以下原则：

1. **单一职责**: 每个修复器只负责特定类型的问题
2. **幂等性**: 多次执行修复应该是安全的
3. **可回滚**: 提供修复失败时的回滚机制
4. **详细日志**: 记录详细的诊断和修复过程
5. **错误处理**: 优雅地处理各种异常情况
6. **性能考虑**: 避免阻塞主线程的长时间操作