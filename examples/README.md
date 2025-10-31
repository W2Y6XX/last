# LangGraph多智能体系统示例

本目录包含了LangGraph多智能体系统的各种使用示例和演示案例。

## 示例列表

### 1. 基础示例
- `basic_workflow.py` - 基本工作流使用示例
- `simple_task.py` - 简单任务处理示例
- `agent_interaction.py` - 智能体交互示例

### 2. 业务场景示例
- `data_analysis_workflow.py` - 数据分析工作流
- `content_generation.py` - 内容生成任务
- `research_assistant.py` - 研究助手工作流
- `project_planning.py` - 项目规划示例

### 3. 高级功能示例
- `parallel_processing.py` - 并行处理示例
- `error_recovery.py` - 错误恢复机制示例
- `checkpoint_resume.py` - 检查点恢复示例
- `performance_optimization.py` - 性能优化示例

### 4. 集成示例
- `api_integration.py` - API集成示例
- `database_integration.py` - 数据库集成示例
- `external_service.py` - 外部服务集成示例

### 5. MVP2前端集成
- `frontend_demo/` - 前端集成演示
- `websocket_demo.py` - WebSocket实时通信示例
- `rest_api_demo.py` - REST API使用示例

## 运行示例

### 环境准备

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的配置
```

3. 启动系统：
```bash
python -m langgraph_multi_agent.main
```

### 运行单个示例

```bash
# 运行基础工作流示例
python examples/basic_workflow.py

# 运行数据分析示例
python examples/data_analysis_workflow.py

# 运行并行处理示例
python examples/parallel_processing.py
```

### 运行演示服务器

```bash
# 启动演示API服务器
python examples/demo_server.py

# 访问演示界面
# http://localhost:8080/demo
```

## 示例说明

每个示例都包含：
- 详细的代码注释
- 使用说明
- 预期输出
- 常见问题解答

## 自定义示例

您可以基于现有示例创建自己的工作流：

1. 复制相似的示例文件
2. 修改智能体配置
3. 调整工作流逻辑
4. 测试和优化

## 故障排除

如果遇到问题，请检查：
1. 环境变量配置是否正确
2. 依赖是否完整安装
3. 系统是否正常启动
4. 日志文件中的错误信息

更多帮助请参考主文档或提交Issue。