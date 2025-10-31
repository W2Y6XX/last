# LangGraph 多智能体任务管理系统

基于 LangGraph 框架的多智能体协作系统，提供任务分析、分解、执行和协调的完整解决方案。

## 🚀 快速开始

### 环境要求

- Python 3.9+
- pip 或 poetry
- 可选：Docker 和 Docker Compose

### 安装

1. **克隆项目**
```bash
git clone <repository-url>
cd langgraph-agent-system
```

2. **安装依赖**
```bash
# 使用 pip
pip install -e .

# 或使用 poetry
poetry install
```

3. **配置系统**
```bash
# 复制配置文件模板
cp config/default.yaml config/local.yaml

# 编辑配置文件
nano config/local.yaml
```

### 运行系统

1. **开发环境**
```bash
python scripts/start_system.py --env development
```

2. **生产环境**
```bash
python scripts/start_system.py --env production --mode daemon
```

3. **使用自定义配置**
```bash
python scripts/start_system.py --config config/local.yaml
```

## 📋 系统架构

### 核心组件

1. **MetaAgent** - 元智能体
   - 任务分析和需求澄清
   - 任务分解和智能体分配
   - 工作流协调

2. **消息总线** - 通信基础设施
   - 点对点和广播消息
   - 消息优先级和重试机制
   - 可靠性保证

3. **任务管理器** - 任务生命周期管理
   - 任务创建、分配、跟踪
   - 依赖关系管理
   - 执行计划生成

4. **资源管理器** - 智能体资源协调
   - 负载均衡
   - 资源分配
   - 性能监控

5. **系统协调器** - 统一管理
   - 组件集成
   - 事件处理
   - 状态同步

## 🛠️ 使用指南

### 基本操作

1. **提交任务**
```python
from src.core.interface import LangGraphAgentSystem, TaskRequest

# 创建系统实例
system = LangGraphAgentSystem()
await system.start()

# 提交任务
request = TaskRequest(
    title="开发用户管理系统",
    description="实现用户注册、登录、权限管理等功能",
    priority="high"
)

response = await system.submit_task(request)
if response.success:
    print(f"任务提交成功，ID: {response.task_id}")
```

2. **查询任务状态**
```python
# 获取任务状态
task_status = await system.get_task_status(task_id)
print(f"任务状态: {task_status['status']}")
print(f"进度: {task_status['progress']}%")
```

3. **取消任务**
```python
# 取消任务
result = await system.cancel_task(task_id, "用户取消")
print(f"取消结果: {result['success']}")
```

4. **获取系统状态**
```python
# 获取系统状态
status = await system.get_system_status()
print(f"活跃智能体: {status.active_agents}")
print(f"运行中任务: {status.running_tasks}")
print(f"系统负载: {status.system_load}%")
```

### 高级功能

1. **智能体通信**
```python
# 发送消息给特定智能体
response = await system.send_message_to_agent(
    sender_id="user",
    receiver_id="meta-agent",
    content="请分析这个任务",
    message_type="task_request"
)
```

2. **广播消息**
```python
# 向所有智能体广播消息
response = await system.broadcast_message(
    sender_id="system",
    content="系统维护通知",
    message_type="broadcast"
)
```

3. **性能监控**
```python
# 获取系统指标
metrics = await system.get_system_metrics()
print(f"任务完成率: {metrics['tasks']['completed_tasks'] / metrics['tasks']['total_tasks'] * 100:.1f}%")
```

## 📊 监控和健康检查

### 健康检查端点

- `GET /health` - 基本健康检查
- `GET /health/ready` - 就绪检查
- `GET /health/live` - 存活检查
- `GET /health/metrics` - 系统指标
- `GET /health/alerts` - 告警信息

### 使用示例

```bash
# 基本健康检查
curl http://localhost:8000/health

# 详细健康检查
curl http://localhost:8000/health?detailed=true

# 获取系统指标
curl http://localhost:8000/health/metrics

# 获取告警信息
curl http://localhost:8000/health/alerts
```

## 🔧 配置说明

### 配置文件结构

系统使用 YAML 配置文件，支持环境继承：

```yaml
# 系统配置
system:
  name: "LangGraph Agent System"
  version: "0.1.0"
  debug: false

# 服务器配置
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4

# 消息总线配置
message_bus:
  max_queue_size: 1000
  processing_interval_seconds: 0.01

# 任务管理配置
task_manager:
  max_concurrent_tasks: 100
  default_timeout_seconds: 3600
```

### 环境变量

支持在配置中使用环境变量：

```yaml
security:
  secret_key: "${SECRET_KEY}"
database:
  connection_string: "${DATABASE_URL:sqlite:///default.db}"
```

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_integration.py

# 运行测试并生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 测试类型

1. **单元测试** - 测试单个组件
2. **集成测试** - 测试组件间协作
3. **端到端测试** - 测试完整工作流

## 🚀 部署

### Docker 部署

1. **构建镜像**
```bash
docker build -t langgraph-agent-system .
```

2. **运行容器**
```bash
docker run -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e SECRET_KEY=your-secret-key \
  langgraph-agent-system
```

### Docker Compose

```yaml
version: '3.8'
services:
  agent-system:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    restart: unless-stopped
```

### 生产部署建议

1. **使用反向代理** (Nginx/Apache)
2. **启用 SSL/TLS**
3. **配置日志轮转**
4. **设置监控和告警**
5. **定期备份**

## 📖 API 文档

启动系统后，访问以下地址查看 API 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🔍 故障排除

### 常见问题

1. **系统启动失败**
   - 检查配置文件语法
   - 确认端口未被占用
   - 查看日志文件

2. **智能体不响应**
   - 检查智能体注册状态
   - 验证消息总线连接
   - 查看智能体日志

3. **任务执行失败**
   - 检查任务依赖关系
   - 验证智能体能力
   - 查看错误日志

### 日志位置

- 应用日志: `logs/agent_system.log`
- 错误日志: `logs/error.log`
- 审计日志: `logs/audit.log`

## 🤝 贡献

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 🆘 支持

- 📧 Email: support@example.com
- 💬 讨论: [GitHub Discussions](https://github.com/your-repo/discussions)
- 🐛 问题报告: [GitHub Issues](https://github.com/your-repo/issues)

## 📚 更多资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [项目架构设计](docs/architecture.md)
- [API 参考文档](docs/api.md)
- [开发指南](docs/development.md)