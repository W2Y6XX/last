# LangGraph多智能体系统

基于LangGraph框架的多智能体任务管理系统，集成现有智能体架构。

## 项目结构

```
langgraph_multi_agent/
├── __init__.py                 # 主模块入口
├── README.md                   # 项目说明
├── core/                       # 核心模块
│   ├── __init__.py
│   ├── state.py               # LangGraph状态定义
│   └── workflow.py            # 工作流引擎
├── agents/                     # 智能体模块
│   ├── __init__.py
│   ├── wrappers.py            # 基础包装器
│   ├── meta_agent_wrapper.py  # MetaAgent包装器
│   ├── coordinator_wrapper.py # Coordinator包装器
│   └── task_decomposer_wrapper.py # TaskDecomposer包装器
├── api/                        # API接口模块
│   ├── __init__.py
│   ├── main.py                # FastAPI应用
│   ├── models.py              # 数据模型
│   └── websocket.py           # WebSocket管理
├── utils/                      # 工具模块
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   ├── logging.py             # 日志配置
│   └── helpers.py             # 辅助函数
├── legacy/                     # 兼容模块
│   ├── __init__.py
│   └── task_state.py          # 现有状态定义
└── tests/                      # 测试模块
    ├── __init__.py
    └── test_basic_setup.py     # 基础设置测试
```

## 已完成功能

✅ **项目基础设置**
- 创建了完整的项目目录结构
- 配置了依赖管理和构建系统
- 实现了配置管理和日志系统
- 创建了扩展的LangGraph状态模型

✅ **状态管理**
- 定义了LangGraphTaskState状态结构
- 实现了工作流上下文和检查点数据
- 添加了智能体消息和协调状态管理
- 创建了状态操作的辅助函数

✅ **基础测试**
- 实现了基础设置的单元测试
- 验证了配置创建和状态管理功能
- 测试了工作流阶段更新和消息添加

## 下一步任务

接下来将实施：
1. 状态管理和数据模型的完整实现
2. 智能体节点包装器的具体实现
3. LangGraph工作流引擎的核心逻辑
4. 错误处理和恢复机制
5. 前端API接口层

## 运行测试

```bash
# 运行所有测试
python -m pytest langgraph_multi_agent/tests/ -v

# 运行特定测试
python -m pytest langgraph_multi_agent/tests/test_basic_setup.py -v
```

## 启动应用

```bash
# 启动API服务器
python main.py
```

## 配置

系统支持通过环境变量进行配置：

- `REDIS_URL`: Redis连接URL
- `SQLITE_PATH`: SQLite数据库路径
- `API_HOST`: API服务器主机
- `API_PORT`: API服务器端口
- `LOG_LEVEL`: 日志级别
- `CHECKPOINT_STORAGE`: 检查点存储类型
- `ENABLE_TRACING`: 是否启用追踪