# Project Context

## Purpose
本项目是一个基于 LangGraph 框架的多智能体任务管理系统，旨在构建一个高度可扩展、模块化的智能协作平台。系统通过多个专门化智能体的协作，为用户提供从任务分析、需求澄清到执行规划和协调管理的全流程支持。

### 主要目标
- **智能任务管理**: 通过多智能体协作实现复杂任务的自动化分解、规划和执行
- **模块化架构**: 基于 LangGraph 的图形化工作流，支持灵活的智能体组合和扩展
- **质量保证**: 多层验证和质量检查机制，确保输出结果的可靠性和准确性
- **用户友好**: 提供多种交互方式（CLI、GUI、API），满足不同用户的需求

## Tech Stack

### 核心框架
- **LangGraph**: 主要的图形化工作流和状态管理框架
- **Python 3.9+**: 主要开发语言
- **langchain_core**: LangChain 核心功能，提供基础的 AI 能力支持
- **pydantic**: 数据验证和类型定义
- **asyncio**: 异步编程支持

### 通信和存储
- **Redis**: 消息队列和缓存系统（可选）
- **PostgreSQL**: 主要关系型数据库（可选）
- **MongoDB**: 文档存储（可选）
- **httpx/urllib3**: HTTP 客户端库

### 开发和部署
- **Docker**: 容器化部署
- **pytest**: 单元测试框架
- **black/flake8**: 代码格式化和检查
- **pre-commit**: Git 钩子管理

## Project Conventions

### Code Style
- **Python 风格**: 遵循 PEP 8 规范，使用 Black 进行代码格式化
- **类型注解**: 所有公共函数和方法必须包含完整的类型注解
- **文档字符串**: 使用 Google 风格的文档字符串，描述参数、返回值和异常
- **命名约定**:
  - 类名: PascalCase (如 `MetaAgent`, `TaskDecomposer`)
  - 函数/变量名: snake_case (如 `process_task`, `agent_state`)
  - 常量: UPPER_SNAKE_CASE (如 `MAX_RETRY_COUNT`)
  - 私有成员: 以下划线开头 (如 `_internal_method`)

### Architecture Patterns
- **图状工作流**: 基于 LangGraph 的 StateGraph 构建智能体工作流
- **状态管理**: 使用 MessagesState 和 add_messages 进行状态管理
- **依赖注入**: 通过配置和依赖注入实现组件解耦
- **异步编程**: 使用 asyncio 进行异步任务处理和智能体通信
- **插件化**: 智能体采用插件化设计，支持动态加载和配置

### Testing Strategy
- **单元测试**: 每个智能体和组件都有对应的单元测试
- **集成测试**: 测试智能体间的协作和消息传递
- **端到端测试**: 测试完整的任务执行流程
- **模拟测试**: 使用 mock 对象模拟外部依赖
- **覆盖率要求**: 代码覆盖率不低于 80%

### Git Workflow
- **分支策略**: 采用 GitFlow 模型
  - `main`: 主分支，包含生产环境代码
  - `develop`: 开发分支，集成最新功能
  - `feature/*`: 功能分支
  - `hotfix/*`: 紧急修复分支
- **提交规范**: 使用约定式提交 (Conventional Commits)
  - `feat:` 新功能
  - `fix:` 错误修复
  - `docs:` 文档更新
  - `style:` 代码格式调整
  - `refactor:` 代码重构
  - `test:` 测试相关
  - `chore:` 构建/工具相关

## Domain Context

### 智能体生态系统
本项目基于 D:\agent 10.20\aaa 项目的智能体架构，包含以下核心智能体：

1. **MetaAgent (元智能体)**: 负责任务分析、需求澄清和规格生成
2. **Coordinator (协调智能体)**: 负责智能体间协调、通信和冲突解决
3. **TaskDecomposer (任务拆解智能体)**: 负责复杂任务分解和执行规划
4. **HumanAgent (人类智能体)**: 负责人机交互和用户体验

### BMAD-METHOD 集成
系统融合了 BMAD-METHOD 框架的多种角色能力：
- **Analyst**: 深度分析和需求澄清
- **PM**: 产品策略和优先级管理
- **Scrum Master**: 任务准备和流程优化
- **Architect**: 系统设计和架构规划

### LangGraph 工作流特性
- **状态图**: 使用 StateGraph 构建复杂的状态转换逻辑
- **消息传递**: 基于消息的智能体间通信机制
- **检查点**: 支持工作流的持久化和恢复
- **条件路由**: 根据状态和条件动态路由任务

## Important Constraints

### 性能约束
- **响应时间**: 简单查询 < 2秒，复杂任务 < 5分钟
- **并发处理**: 支持至少 10 个并发任务请求
- **内存使用**: 单个智能体内存占用不超过 1GB
- **可用性**: 系统可用性目标 > 99.5%

### 安全约束
- **数据隐私**: 敏感数据必须加密存储和传输
- **访问控制**: 实施基于角色的访问控制 (RBAC)
- **审计日志**: 记录所有关键操作的审计日志
- **输入验证**: 严格验证所有外部输入，防止注入攻击

### 扩展性约束
- **智能体扩展**: 支持动态添加新的智能体类型
- **水平扩展**: 支持多实例部署和负载均衡
- **配置驱动**: 智能体行为通过配置文件控制，无需修改代码
- **向后兼容**: 新版本必须保持与现有配置和接口的向后兼容

## External Dependencies

### AI 和语言模型
- **OpenAI API**: GPT 系列模型接口 (可选)
- **Anthropic Claude**: Claude 系列模型接口 (可选)
- **本地模型**: 支持本地部署的开源模型 (可选)

### 基础设施服务
- **Redis**: 消息队列和缓存服务
- **PostgreSQL**: 主数据库，存储任务和智能体状态
- **Elasticsearch**: 日志搜索和分析 (可选)
- **Prometheus**: 监控指标收集 (可选)

### 开发工具
- **Docker Hub**: 容器镜像仓库
- **GitHub**: 源代码管理和 CI/CD
- **PyPI**: Python 包管理
- **Pre-commit**: 代码质量检查钩子

### 通信协议
- **HTTP/HTTPS**: RESTful API 接口
- **WebSocket**: 实时通信支持
- **gRPC**: 高性能 RPC 通信 (可选)
- **Message Queue**: 异步消息传递
