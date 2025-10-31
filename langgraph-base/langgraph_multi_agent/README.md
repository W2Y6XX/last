# 基于LangGraph的多智能体任务管理系统

## 🎯 项目概述

本项目将现有的多智能体任务管理系统重构为基于LangGraph的现代架构，结合LangGraph的强大状态管理和工作流编排能力，构建更高效、可扩展的多智能体协作系统。

## 🏗️ 系统架构

### 核心设计原则
- **状态驱动**: 利用LangGraph的StateGraph进行统一状态管理
- **工具集成**: 将原有智能体能力封装为LangGraph工具节点
- **工作流编排**: 使用LangGraph的预构建组件简化复杂流程
- **可扩展性**: 保持原有系统的智能体扩展机制

### 智能体架构
```
用户输入 → MetaAgent → Coordinator → SpecialistAgents → 结果整合 → 用户
    ↓         ↓            ↓              ↓             ↓
  任务分析   任务拆解     任务协调       专业执行       结果汇总
```

## 📁 项目结构

```
langgraph_multi_agent/
├── agents/                    # 智能体实现
│   ├── __init__.py
│   ├── meta_agent.py         # 元智能体（任务分析）
│   ├── coordinator_agent.py  # 协调智能体
│   ├── task_decomposer.py   # 任务拆解智能体
│   └── specialist/          # 专门化智能体
│       ├── __init__.py
│       ├── analyst_agent.py
│       ├── developer_agent.py
│       └── architect_agent.py
├── tools/                    # 工具集成
│   ├── __init__.py
│   ├── communication_tools.py
│   ├── analysis_tools.py
│   └── execution_tools.py
├── workflows/               # 工作流定义
│   ├── __init__.py
│   ├── main_workflow.py    # 主工作流
│   ├── analysis_workflow.py # 分析工作流
│   └── execution_workflow.py # 执行工作流
├── state/                   # 状态管理
│   ├── __init__.py
│   ├── message_state.py    # 消息状态
│   └── task_state.py        # 任务状态
├── utils/                   # 工具函数
│   ├── __init__.py
│   └── helpers.py
├── config/                  # 配置文件
│   ├── __init__.py
│   └── agent_config.py
└── main.py                 # 主程序入口
```

## 🚀 快速开始

### 安装依赖
```bash
pip install langgraph langchain langchain-core
```

### 基础使用示例
```python
from langgraph_multi_agent import MultiAgentSystem

# 初始化系统
system = MultiAgentSystem()

# 处理用户任务
result = system.process_task("开发一个用户管理系统")
print(result)
```

## 🔧 核心特性

1. **智能任务分析**: MetaAgent自动分析和拆解复杂任务
2. **动态智能体协作**: 基于任务需求动态选择和协调智能体
3. **状态持久化**: 支持任务执行过程中的状态保存和恢复
4. **工具集成**: 轻松集成外部API和工具
5. **监控和日志**: 完整的执行过程监控和日志记录

## 🎯 核心智能体

### MetaAgent (元智能体)
- **职责**: 任务分析、需求澄清、规格生成、智能体推荐
- **能力**: 深度任务理解、结构化分析、质量保证

### CoordinatorAgent (协调智能体)
- **职责**: 智能体间通信、协作协调、冲突解决、状态同步
- **能力**: 系统架构协调、产品策略协调、进度监控

### TaskDecomposer (任务拆解智能体)
- **职责**: 复杂任务拆解、子任务定义、依赖关系分析
- **能力**: 任务层次化、优先级管理、资源评估

### SpecialistAgents (专门化智能体)
- **AnalystAgent**: 业务分析、需求分析、数据分析
- **DeveloperAgent**: 代码开发、技术实现、测试
- **ArchitectAgent**: 系统设计、架构规划、技术选型

## 📊 与原系统的优势对比

| 特性 | 原系统 | LangGraph系统 |
|------|--------|---------------|
| 状态管理 | 自定义实现 | StateGraph统一管理 |
| 工作流编排 | 手动协调 | 自动化工作流 |
| 工具集成 | 自定义接口 | ToolNode标准集成 |
| 持久化 | 需要手动实现 | 内置检查点支持 |
| 错误处理 | 分散处理 | 统一错误恢复机制 |
| 监控调试 | 自定义日志 | LangSmith集成 |

## 🔄 迁移指南

本项目保持与原有系统的API兼容性，可以平滑迁移：

1. **状态兼容**: 保持原有的任务和消息数据结构
2. **接口兼容**: 维持核心智能体的调用接口
3. **配置兼容**: 支持原有的智能体配置格式
4. **渐进迁移**: 支持逐步迁移原有功能