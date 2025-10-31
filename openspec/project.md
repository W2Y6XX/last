# Project Context

## Purpose
基于LangGraph的多智能体协作系统，提供智能任务分解、智能体协调和错误恢复能力。系统旨在构建一个能够自动处理复杂任务的多智能体协作平台，支持任务的智能分析、分解、协调执行和结果汇总。

## Tech Stack

### 后端技术栈
- **Python 3.8+** - 主要开发语言
- **LangGraph** - 工作流编排框架（>=1.0.1）
- **LangChain** - LLM集成框架（>=1.0.0）
- **FastAPI** - 现代Web框架（>=0.104.0）
- **Uvicorn** - ASGI服务器（>=0.24.0）
- **Pydantic** - 数据验证库（>=2.5.0）
- **SQLAlchemy** - ORM框架（>=2.0.0）
- **Redis** - 缓存和会话存储（>=5.0.0）
- **WebSockets** - 实时通信协议
- **SQLite/PostgreSQL** - 数据持久化

### 前端技术栈
- **原生JavaScript** - 前端开发语言
- **HTML5/CSS3** - 网页结构和样式
- **WebSocket API** - 实时通信
- **Fetch API** - HTTP请求

### 基础设施
- **Docker** - 容器化部署
- **Docker Compose** - 服务编排
- **Nginx** - 反向代理和静态文件服务
- **Prometheus** - 监控指标收集
- **Grafana** - 数据可视化
- **Elasticsearch** - 日志存储和搜索
- **Kibana** - 日志可视化

### LLM服务
- **硅基流动** - LLM服务提供商
- **DeepSeek-R1-Distill-Qwen-7B** - 主要使用的LLM模型

## Project Conventions

### Code Style
- **Python**: 遵循PEP 8规范，使用Black格式化工具（行长度88字符）
- **JavaScript**: 使用ES6+语法，遵循现代JavaScript最佳实践
- **命名规范**:
  - Python: snake_case（变量和函数），PascalCase（类）
  - JavaScript: camelCase（变量和函数），PascalCase（类）
- **文件命名**: 使用下划线分隔的文件名
- **注释**: 中文注释为主，关键逻辑添加详细说明

### Architecture Patterns
- **分层架构**: API层、业务逻辑层、数据访问层
- **智能体模式**: MetaAgent、TaskDecomposer、Coordinator、GenericAgent
- **工作流模式**: 基于LangGraph StateGraph的工作流编排
- **状态管理**: 扩展的TaskState模型，支持工作流上下文
- **错误处理**: 统一的错误分类和恢复策略
- **异步处理**: 大量使用async/await模式

### Testing Strategy
- **测试框架**: pytest + pytest-asyncio（异步测试）
- **测试类型**:
  - 单元测试：测试单个函数和类
  - 集成测试：测试组件间交互
  - 系统测试：测试完整工作流
- **测试覆盖率**: 目标80%以上
- **测试文件命名**: test_*.py
- **测试目录**: langgraph_multi_agent/tests/

### Git Workflow
- **分支策略**: GitFlow（主分支main、开发分支develop、功能分支feature/*）
- **提交规范**:
  - feat: 新功能
  - fix: 错误修复
  - docs: 文档更新
  - style: 代码格式调整
  - refactor: 代码重构
  - test: 测试相关
  - chore: 构建/工具相关
- **代码审查**: 所有PR需要代码审查
- **合并策略**: 使用squash merge保持历史清晰

## Domain Context

### 智能体类型和职责
- **MetaAgent**: 任务分析和复杂度评估，决定任务是否需要分解
- **TaskDecomposer**: 智能任务分解和依赖分析，将复杂任务分解为子任务
- **Coordinator**: 智能体协调和冲突解决，管理多个智能体的协作
- **GenericAgent**: 通用任务执行智能体，负责具体任务的执行

### 工作流阶段
- **INITIALIZATION**: 工作流初始化
- **ANALYSIS**: 任务分析和复杂度评估
- **DECOMPOSITION**: 任务分解（如需要）
- **COORDINATION**: 智能体协调
- **EXECUTION**: 任务执行
- **REVIEW**: 结果审查
- **COMPLETION**: 完成
- **ERROR_HANDLING**: 错误处理

### 任务状态
- **PENDING**: 待处理
- **IN_PROGRESS**: 执行中
- **PAUSED**: 已暂停
- **COMPLETED**: 已完成
- **FAILED**: 执行失败
- **CANCELLED**: 已取消

### 执行模式
- **顺序执行**: 按依赖关系依次执行
- **并行执行**: 同时执行无依赖关系的任务
- **自适应执行**: 根据任务复杂度和系统状态动态选择执行策略

## Important Constraints

### 性能约束
- **任务处理时间**: 单个任务处理时间不超过1小时
- **并发限制**: 最大并发任务数100个
- **内存使用**: 单个容器内存使用不超过2GB
- **响应时间**: API响应时间不超过5秒

### 安全约束
- **API密钥管理**: LLM API密钥通过环境变量管理
- **数据加密**: 敏感数据在传输和存储时加密
- **访问控制**: 实现适当的API访问控制
- **审计日志**: 记录所有关键操作的审计日志

### 可靠性约束
- **错误恢复**: 支持自动错误检测和恢复
- **重试机制**: 最大重试次数3次
- **健康检查**: 实现服务和依赖的健康检查
- **数据备份**: 定期备份重要数据

### 业务约束
- **任务优先级**: 支持1-5级任务优先级
- **任务依赖**: 支持复杂的任务依赖关系
- **结果一致性**: 确保任务执行结果的一致性
- **监控告警**: 关键指标异常时自动告警

## External Dependencies

### LLM服务依赖
- **硅基流动API**: https://api.siliconflow.cn
- **API密钥**: sk-wmxxamqdqsmscgrrmweqsqcieowsmqpxqwvenlelrxtkvmms
- **模型**: deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
- **限流**: 根据API提供商限制进行调用

### 数据存储依赖
- **Redis**: 缓存和会话存储（端口6379）
- **PostgreSQL**: 主数据库（端口5432）
- **SQLite**: 轻量级数据库选项

### 监控和日志依赖
- **Prometheus**: 指标收集（端口9090）
- **Grafana**: 数据可视化（端口3000）
- **Elasticsearch**: 日志存储（端口9200）
- **Kibana**: 日志可视化（端口5601）

### 网络依赖
- **Nginx**: 反向代理（端口80/443）
- **应用服务**: FastAPI应用（端口8000）
- **WebSocket**: 实时通信端点

### 系统依赖
- **Docker**: 容器运行时
- **Python 3.8+**: 运行环境
- **现代浏览器**: 前端界面支持
