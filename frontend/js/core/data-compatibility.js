/**
 * 数据格式兼容性处理器
 * 负责处理不同版本间的数据格式兼容性，确保向后兼容
 */
class DataCompatibilityHandler {
    constructor() {
        this.schemaVersions = new Map();
        this.migrationRules = new Map();
        this.validators = new Map();
        this.currentVersion = '2.0.0';
        this.supportedVersions = ['1.0.0', '1.1.0', '1.2.0', '2.0.0'];
        
        // 初始化数据模式和迁移规则
        this._initializeSchemas();
        this._initializeMigrationRules();
        this._initializeValidators();
    }
    
    /**
     * 初始化数据模式
     * @private
     */
    _initializeSchemas() {
        // 任务数据模式
        this.schemaVersions.set('task', {
            '1.0.0': {
                id: 'string',
                title: 'string',
                description: 'string',
                status: 'string',
                priority: 'number',
                created_at: 'string'
            },
            '1.1.0': {
                id: 'string',
                title: 'string',
                description: 'string',
                status: 'string',
                priority: 'number',
                type: 'string',
                created_at: 'string',
                updated_at: 'string'
            },
            '1.2.0': {
                id: 'string',
                title: 'string',
                description: 'string',
                status: 'string',
                priority: 'number',
                type: 'string',
                tags: 'array',
                assignee: 'string',
                created_at: 'string',
                updated_at: 'string'
            },
            '2.0.0': {
                id: 'string',
                title: 'string',
                description: 'string',
                status: 'string',
                priority: 'number',
                type: 'string',
                tags: 'array',
                assignee: 'string',
                metadata: 'object',
                dependencies: 'array',
                subtasks: 'array',
                created_at: 'string',
                updated_at: 'string',
                completed_at: 'string'
            }
        });
        
        // 智能体数据模式
        this.schemaVersions.set('agent', {
            '1.0.0': {
                id: 'string',
                name: 'string',
                type: 'string',
                status: 'string'
            },
            '1.1.0': {
                id: 'string',
                name: 'string',
                type: 'string',
                status: 'string',
                capabilities: 'array',
                description: 'string'
            },
            '2.0.0': {
                agentId: 'string',
                agentType: 'string',
                name: 'string',
                description: 'string',
                capabilities: 'array',
                status: 'string',
                currentTask: 'string',
                configuration: 'object',
                executionStats: 'object',
                healthStatus: 'object',
                createdAt: 'string',
                updatedAt: 'string'
            }
        });
        
        // 大模型配置数据模式
        this.schemaVersions.set('llm_config', {
            '2.0.0': {
                id: 'string',
                name: 'string',
                provider: 'string',
                settings: 'object',
                isActive: 'boolean',
                testResult: 'object',
                usage: 'object',
                createdAt: 'string',
                updatedAt: 'string'
            }
        });
        
        // 对话数据模式
        this.schemaVersions.set('conversation', {
            '2.0.0': {
                conversationId: 'string',
                taskContext: 'object',
                messages: 'array',
                currentPhase: 'string',
                progress: 'number',
                canDecompose: 'boolean',
                decompositionResult: 'object',
                createdAt: 'string',
                updatedAt: 'string'
            }
        });
    }
    
    /**
     * 初始化迁移规则
     * @private
     */
    _initializeMigrationRules() {
        // 任务数据迁移规则
        this.migrationRules.set('task', {
            '1.0.0->1.1.0': (data) => ({
                ...data,
                type: 'general',
                updated_at: data.created_at
            }),
            '1.1.0->1.2.0': (data) => ({
                ...data,
                tags: [],
                assignee: null
            }),
            '1.2.0->2.0.0': (data) => ({
                ...data,
                metadata: {},
                dependencies: [],
                subtasks: [],
                completed_at: data.status === 'completed' ? data.updated_at : null
            })
        });
        
        // 智能体数据迁移规则
        this.migrationRules.set('agent', {
            '1.0.0->1.1.0': (data) => ({
                ...data,
                capabilities: [],
                description: `${data.type} 智能体`
            }),
            '1.1.0->2.0.0': (data) => ({
                agentId: data.id,
                agentType: data.type,
                name: data.name,
                description: data.description,
                capabilities: data.capabilities,
                status: data.status,
                currentTask: null,
                configuration: {
                    llmConfig: null,
                    parameters: {},
                    constraints: []
                },
                executionStats: {
                    totalExecutions: 0,
                    successfulExecutions: 0,
                    failedExecutions: 0,
                    averageExecutionTime: 0,
                    lastExecutionTime: null
                },
                healthStatus: {
                    isHealthy: data.status !== 'error',
                    lastHealthCheck: new Date().toISOString(),
                    issues: []
                },
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            })
        });
    }
    
    /**
     * 初始化验证器
     * @private
     */
    _initializeValidators() {
        this.validators.set('string', (value) => typeof value === 'string');
        this.validators.set('number', (value) => typeof value === 'number' && !isNaN(value));
        this.validators.set('boolean', (value) => typeof value === 'boolean');
        this.validators.set('array', (value) => Array.isArray(value));
        this.validators.set('object', (value) => value !== null && typeof value === 'object' && !Array.isArray(value));
    }
    
    /**
     * 检测数据版本
     * @param {Object} data 数据对象
     * @param {string} dataType 数据类型
     * @returns {string|null} 检测到的版本
     */
    detectVersion(data, dataType) {
        if (!data || typeof data !== 'object') {
            return null;
        }
        
        const schemas = this.schemaVersions.get(dataType);
        if (!schemas) {
            return null;
        }
        
        // 从最新版本开始检测
        const versions = Object.keys(schemas).sort((a, b) => {
            return this._compareVersions(b, a); // 降序排列
        });
        
        for (const version of versions) {
            if (this._matchesSchema(data, schemas[version])) {
                return version;
            }
        }
        
        return null;
    }
    
    /**
     * 检查数据是否匹配模式
     * @private
     */
    _matchesSchema(data, schema) {
        const dataKeys = Object.keys(data);
        const schemaKeys = Object.keys(schema);
        
        // 检查必需字段是否存在
        const requiredFields = schemaKeys.filter(key => !key.endsWith('?'));
        const missingFields = requiredFields.filter(field => !dataKeys.includes(field));
        
        if (missingFields.length > 0) {
            return false;
        }
        
        // 检查字段类型
        for (const key of dataKeys) {
            if (schemaKeys.includes(key)) {
                const expectedType = schema[key];
                const validator = this.validators.get(expectedType);
                
                if (validator && !validator(data[key])) {
                    return false;
                }
            }
        }
        
        return true;
    }
    
    /**
     * 比较版本号
     * @private
     */
    _compareVersions(version1, version2) {
        const v1Parts = version1.split('.').map(Number);
        const v2Parts = version2.split('.').map(Number);
        
        for (let i = 0; i < Math.max(v1Parts.length, v2Parts.length); i++) {
            const v1Part = v1Parts[i] || 0;
            const v2Part = v2Parts[i] || 0;
            
            if (v1Part > v2Part) return 1;
            if (v1Part < v2Part) return -1;
        }
        
        return 0;
    }
    
    /**
     * 迁移数据到指定版本
     * @param {Object} data 原始数据
     * @param {string} dataType 数据类型
     * @param {string} targetVersion 目标版本
     * @returns {Object} 迁移结果
     */
    migrateData(data, dataType, targetVersion = null) {
        try {
            if (!data || typeof data !== 'object') {
                return {
                    success: false,
                    error: '无效的数据对象',
                    data: null
                };
            }
            
            const currentVersion = this.detectVersion(data, dataType);
            if (!currentVersion) {
                return {
                    success: false,
                    error: '无法检测数据版本',
                    data: null
                };
            }
            
            const target = targetVersion || this.currentVersion;
            
            // 如果已经是目标版本，直接返回
            if (currentVersion === target) {
                return {
                    success: true,
                    data: { ...data },
                    fromVersion: currentVersion,
                    toVersion: target,
                    migrated: false
                };
            }
            
            // 检查是否支持迁移路径
            const migrationPath = this._findMigrationPath(currentVersion, target);
            if (!migrationPath) {
                return {
                    success: false,
                    error: `不支持从版本 ${currentVersion} 迁移到 ${target}`,
                    data: null
                };
            }
            
            // 执行迁移
            let migratedData = { ...data };
            const migrationRules = this.migrationRules.get(dataType);
            
            for (let i = 0; i < migrationPath.length - 1; i++) {
                const fromVersion = migrationPath[i];
                const toVersion = migrationPath[i + 1];
                const ruleKey = `${fromVersion}->${toVersion}`;
                
                if (migrationRules && migrationRules[ruleKey]) {
                    migratedData = migrationRules[ruleKey](migratedData);
                } else {
                    return {
                        success: false,
                        error: `缺少迁移规则: ${ruleKey}`,
                        data: null
                    };
                }
            }
            
            // 验证迁移结果
            const finalVersion = this.detectVersion(migratedData, dataType);
            if (finalVersion !== target) {
                return {
                    success: false,
                    error: '迁移后数据版本验证失败',
                    data: null
                };
            }
            
            return {
                success: true,
                data: migratedData,
                fromVersion: currentVersion,
                toVersion: target,
                migrated: true,
                migrationPath
            };
            
        } catch (error) {
            return {
                success: false,
                error: `迁移过程中发生错误: ${error.message}`,
                data: null
            };
        }
    }
    
    /**
     * 查找迁移路径
     * @private
     */
    _findMigrationPath(fromVersion, toVersion) {
        const supportedVersions = this.supportedVersions.sort(this._compareVersions);
        
        const fromIndex = supportedVersions.indexOf(fromVersion);
        const toIndex = supportedVersions.indexOf(toVersion);
        
        if (fromIndex === -1 || toIndex === -1) {
            return null;
        }
        
        if (fromIndex <= toIndex) {
            // 向前迁移
            return supportedVersions.slice(fromIndex, toIndex + 1);
        } else {
            // 向后迁移（通常不支持）
            return null;
        }
    }
    
    /**
     * 批量迁移数据
     * @param {Array} dataArray 数据数组
     * @param {string} dataType 数据类型
     * @param {string} targetVersion 目标版本
     * @returns {Object} 批量迁移结果
     */
    migrateBatch(dataArray, dataType, targetVersion = null) {
        if (!Array.isArray(dataArray)) {
            return {
                success: false,
                error: '输入必须是数组',
                results: []
            };
        }
        
        const results = [];
        let successCount = 0;
        let failureCount = 0;
        
        dataArray.forEach((data, index) => {
            const result = this.migrateData(data, dataType, targetVersion);
            results.push({
                index,
                ...result
            });
            
            if (result.success) {
                successCount++;
            } else {
                failureCount++;
            }
        });
        
        return {
            success: failureCount === 0,
            total: dataArray.length,
            successCount,
            failureCount,
            results
        };
    }
    
    /**
     * 验证数据格式
     * @param {Object} data 数据对象
     * @param {string} dataType 数据类型
     * @param {string} version 版本
     * @returns {Object} 验证结果
     */
    validateData(data, dataType, version = null) {
        try {
            const targetVersion = version || this.currentVersion;
            const schemas = this.schemaVersions.get(dataType);
            
            if (!schemas || !schemas[targetVersion]) {
                return {
                    valid: false,
                    errors: [`不支持的数据类型或版本: ${dataType}@${targetVersion}`]
                };
            }
            
            const schema = schemas[targetVersion];
            const errors = [];
            
            // 检查必需字段
            const requiredFields = Object.keys(schema).filter(key => !key.endsWith('?'));
            const dataKeys = Object.keys(data || {});
            
            requiredFields.forEach(field => {
                if (!dataKeys.includes(field)) {
                    errors.push(`缺少必需字段: ${field}`);
                }
            });
            
            // 检查字段类型
            dataKeys.forEach(key => {
                if (schema[key]) {
                    const expectedType = schema[key];
                    const validator = this.validators.get(expectedType);
                    
                    if (validator && !validator(data[key])) {
                        errors.push(`字段 ${key} 类型错误，期望: ${expectedType}`);
                    }
                }
            });
            
            return {
                valid: errors.length === 0,
                errors,
                version: targetVersion
            };
            
        } catch (error) {
            return {
                valid: false,
                errors: [`验证过程中发生错误: ${error.message}`]
            };
        }
    }
    
    /**
     * 获取数据类型的所有支持版本
     * @param {string} dataType 数据类型
     * @returns {Array} 支持的版本列表
     */
    getSupportedVersions(dataType) {
        const schemas = this.schemaVersions.get(dataType);
        return schemas ? Object.keys(schemas).sort(this._compareVersions) : [];
    }
    
    /**
     * 获取数据模式
     * @param {string} dataType 数据类型
     * @param {string} version 版本
     * @returns {Object|null} 数据模式
     */
    getSchema(dataType, version) {
        const schemas = this.schemaVersions.get(dataType);
        return schemas && schemas[version] ? schemas[version] : null;
    }
    
    /**
     * 添加自定义数据类型
     * @param {string} dataType 数据类型
     * @param {string} version 版本
     * @param {Object} schema 数据模式
     */
    addDataType(dataType, version, schema) {
        if (!this.schemaVersions.has(dataType)) {
            this.schemaVersions.set(dataType, {});
        }
        
        this.schemaVersions.get(dataType)[version] = schema;
    }
    
    /**
     * 添加迁移规则
     * @param {string} dataType 数据类型
     * @param {string} fromVersion 源版本
     * @param {string} toVersion 目标版本
     * @param {Function} migrationFn 迁移函数
     */
    addMigrationRule(dataType, fromVersion, toVersion, migrationFn) {
        if (!this.migrationRules.has(dataType)) {
            this.migrationRules.set(dataType, {});
        }
        
        const ruleKey = `${fromVersion}->${toVersion}`;
        this.migrationRules.get(dataType)[ruleKey] = migrationFn;
    }
    
    /**
     * 获取兼容性报告
     * @param {Array} dataArray 数据数组
     * @param {string} dataType 数据类型
     * @returns {Object} 兼容性报告
     */
    getCompatibilityReport(dataArray, dataType) {
        const report = {
            dataType,
            total: dataArray.length,
            versionDistribution: {},
            compatibilityIssues: [],
            migrationRequired: 0,
            fullyCompatible: 0
        };
        
        dataArray.forEach((data, index) => {
            const version = this.detectVersion(data, dataType);
            
            if (version) {
                report.versionDistribution[version] = (report.versionDistribution[version] || 0) + 1;
                
                if (version === this.currentVersion) {
                    report.fullyCompatible++;
                } else {
                    report.migrationRequired++;
                }
            } else {
                report.compatibilityIssues.push({
                    index,
                    issue: '无法检测数据版本',
                    data: data
                });
            }
        });
        
        return report;
    }
    
    /**
     * 自动修复数据
     * @param {Object} data 数据对象
     * @param {string} dataType 数据类型
     * @returns {Object} 修复结果
     */
    autoFixData(data, dataType) {
        // 首先尝试迁移
        const migrationResult = this.migrateData(data, dataType);
        
        if (migrationResult.success) {
            return {
                success: true,
                data: migrationResult.data,
                fixes: ['数据版本迁移'],
                fromVersion: migrationResult.fromVersion,
                toVersion: migrationResult.toVersion
            };
        }
        
        // 如果迁移失败，尝试基本修复
        const fixes = [];
        let fixedData = { ...data };
        
        // 添加缺失的必需字段
        const schema = this.getSchema(dataType, this.currentVersion);
        if (schema) {
            Object.keys(schema).forEach(field => {
                if (!fixedData.hasOwnProperty(field)) {
                    fixedData[field] = this._getDefaultValue(schema[field]);
                    fixes.push(`添加缺失字段: ${field}`);
                }
            });
        }
        
        // 修复字段类型
        if (schema) {
            Object.keys(fixedData).forEach(key => {
                if (schema[key]) {
                    const expectedType = schema[key];
                    const validator = this.validators.get(expectedType);
                    
                    if (validator && !validator(fixedData[key])) {
                        fixedData[key] = this._convertType(fixedData[key], expectedType);
                        fixes.push(`修复字段类型: ${key}`);
                    }
                }
            });
        }
        
        return {
            success: fixes.length > 0,
            data: fixedData,
            fixes,
            fromVersion: 'unknown',
            toVersion: this.currentVersion
        };
    }
    
    /**
     * 获取默认值
     * @private
     */
    _getDefaultValue(type) {
        switch (type) {
            case 'string': return '';
            case 'number': return 0;
            case 'boolean': return false;
            case 'array': return [];
            case 'object': return {};
            default: return null;
        }
    }
    
    /**
     * 转换类型
     * @private
     */
    _convertType(value, targetType) {
        try {
            switch (targetType) {
                case 'string':
                    return String(value);
                case 'number':
                    const num = Number(value);
                    return isNaN(num) ? 0 : num;
                case 'boolean':
                    return Boolean(value);
                case 'array':
                    return Array.isArray(value) ? value : [value];
                case 'object':
                    return (value && typeof value === 'object') ? value : {};
                default:
                    return value;
            }
        } catch (error) {
            return this._getDefaultValue(targetType);
        }
    }
}

// 导出类
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DataCompatibilityHandler;
} else {
    window.DataCompatibilityHandler = DataCompatibilityHandler;
}