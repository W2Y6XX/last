# 智能体系统集成指南

## 快速开始

### 环境要求
- Python 3.11+
- Redis 6.0+
- PostgreSQL 12+
- 消息队列 (RabbitMQ 或 Apache Kafka)

### 基础安装
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置数据库
python scripts/setup_database.py

# 3. 初始化消息队列
python scripts/setup_message_bus.py

# 4. 启动基础服务
python start_system.py
```

## 智能体注册和配置

### 1. 创建智能体配置文件
```yaml
# config/my_agent.yaml
agent:
  name: "MyCustomAgent"
  id: "my-agent-001"
  type: "custom"
  version: "1.0.0"

capabilities:
  name: "MyCustomAgent"
  description: "自定义智能体，专门处理特定任务"
  input_types: ["custom_task", "data_processing"]
  output_types: ["processed_data", "analysis_result"]
  max_concurrent_tasks: 5
  specializations: ["data_analysis", "report_generation"]

configuration:
  # 智能体特定配置
  processing_timeout: 300
  retry_attempts: 3
  custom_settings:
    parameter1: "value1"
    parameter2: 42

dependencies:
  - "redis"
  - "postgresql"
  - "message_bus"

resources:
  memory_mb: 512
  cpu_cores: 2
  storage_gb: 10
```

### 2. 实现智能体类
```python
# agents/my_custom_agent.py
from agents.base_agent import BaseAgent
from communication.message_bus import get_message_bus
from typing import Dict, Any

class MyCustomAgent(BaseAgent):
    """自定义智能体实现"""

    def __init__(self, agent_id: str, config: Dict[str, Any] = None):
        capabilities = AgentCapabilities(
            name="MyCustomAgent",
            description="自定义智能体",
            input_types=["custom_task", "data_processing"],
            output_types=["processed_data", "analysis_result"],
            max_concurrent_tasks=5,
            specializations=["data_analysis", "report_generation"]
        )

        super().__init__(
            agent_id=agent_id,
            name=f"MyCustomAgent {agent_id}",
            capabilities=capabilities,
            config=config or {}
        )

        # 自定义初始化
        self.processing_timeout = self.config.get("processing_timeout", 300)
        self.retry_attempts = self.config.get("retry_attempts", 3)

    async def on_start(self) -> None:
        """启动时的初始化逻辑"""
        self.logger.info(f"Starting MyCustomAgent {self.agent_id}")

        # 获取消息总线
        self.message_bus = get_message_bus()
        await self.message_bus.subscribe(f"agent.{self.agent_id}.tasks", self.agent_id)

        # 注册自定义消息处理器
        await self.register_message_handler(
            MessageType.CUSTOM_TASK,
            self._handle_custom_task
        )

        self.logger.info("MyCustomAgent started successfully")

    async def on_stop(self) -> None:
        """停止时的清理逻辑"""
        self.logger.info(f"Stopping MyCustomAgent {self.agent_id}")

        # 清理资源
        if hasattr(self, 'message_bus'):
            await self.message_bus.unsubscribe(f"agent.{self.agent_id}.tasks", self.agent_id)

        self.logger.info("MyCustomAgent stopped")

    async def process_task(self, task: Task) -> Dict[str, Any]:
        """处理任务的实现"""
        try:
            if task.type == "custom_task":
                return await self._process_custom_task(task)
            elif task.type == "data_processing":
                return await self._process_data(task)
            else:
                raise ValueError(f"Unknown task type: {task.type}")

        except Exception as e:
            self.logger.error(f"Error processing task {task.id}: {e}")
            raise

    async def _process_custom_task(self, task: Task) -> Dict[str, Any]:
        """处理自定义任务"""
        # 实现具体的业务逻辑
        input_data = task.parameters.get("input_data", {})

        # 处理逻辑
        result = await self._perform_custom_processing(input_data)

        return {
            "success": True,
            "task_id": task.id,
            "result": result,
            "processing_time": self._get_processing_time()
        }

    async def _process_data(self, task: Task) -> Dict[str, Any]:
        """处理数据任务"""
        data = task.parameters.get("data", [])

        # 数据处理逻辑
        processed_data = await self._analyze_data(data)

        return {
            "success": True,
            "task_id": task.id,
            "processed_data": processed_data,
            "statistics": self._calculate_statistics(data)
        }

    # 自定义业务方法
    async def _perform_custom_processing(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """自定义处理逻辑"""
        # 实现具体的处理逻辑
        pass

    async def _analyze_data(self, data: List[Any]) -> Dict[str, Any]:
        """数据分析逻辑"""
        # 实现数据分析
        pass

    def _calculate_statistics(self, data: List[Any]) -> Dict[str, Any]:
        """计算统计信息"""
        # 实现统计计算
        pass

    def _get_processing_time(self) -> float:
        """获取处理时间"""
        # 返回处理耗时
        pass
```

### 3. 注册智能体到系统
```python
# scripts/register_agent.py
import asyncio
from backend.src.agents.my_custom_agent import MyCustomAgent
from communication.message_bus import get_message_bus

async def register_agent():
    """注册自定义智能体"""

    # 创建智能体实例
    agent = MyCustomAgent(
        agent_id="my-agent-001",
        config={
            "processing_timeout": 300,
            "retry_attempts": 3,
            "custom_settings": {
                "parameter1": "value1",
                "parameter2": 42
            }
        }
    )

    # 启动智能体
    success = await agent.start()
    if success:
        print("智能体注册成功")

        # 向元智能体注册能力
        message_bus = get_message_bus()
        await message_bus.send_message(
            recipient_id="meta-agent-001",
            message_type=MessageType.AGENT_REGISTER,
            content={
                "agent_id": agent.agent_id,
                "agent_type": agent.agent_type,
                "capabilities": agent.capabilities.__dict__,
                "max_concurrent_tasks": agent.capabilities.max_concurrent_tasks,
                "specializations": agent.capabilities.specializations
            }
        )
    else:
        print("智能体注册失败")

if __name__ == "__main__":
    asyncio.run(register_agent())
```

## 任务提交和处理

### 1. 提交任务到系统
```python
# examples/submit_task.py
import asyncio
from communication.message_bus import get_message_bus
from communication.protocol import MessageType

async def submit_task():
    """提交任务到多智能体系统"""

    message_bus = get_message_bus()

    # 创建任务数据
    task_data = {
        "task_id": "task-001",
        "task_type": "data_analysis",
        "priority": 5,
        "input_data": {
            "data_source": "database",
            "query": "SELECT * FROM analytics WHERE date > '2024-01-01'",
            "analysis_type": "trend_analysis"
        },
        "requirements": [
            "data_processing",
            "statistical_analysis",
            "report_generation"
        ],
        "deadline": "2024-01-31T23:59:59Z",
        "requester_id": "user-001"
    }

    # 提交任务
    response = await message_bus.send_message(
        recipient_id="meta-agent-001",
        message_type=MessageType.TASK_REQUEST,
        content=task_data,
        requires_response=True,
        timeout_seconds=30
    )

    if response:
        print("任务提交成功")
        print(f"分配的智能体: {response.content.get('assigned_agents', [])}")
        print(f"预计完成时间: {response.content.get('estimated_completion')}")
    else:
        print("任务提交失败")

if __name__ == "__main__":
    asyncio.run(submit_task())
```

### 2. 处理任务结果
```python
# examples/handle_task_result.py
import asyncio
from communication.message_bus import get_message_bus
from communication.protocol import MessageType

class TaskResultHandler:
    def __init__(self):
        self.message_bus = get_message_bus()

    async def start_listening(self):
        """开始监听任务结果"""

        await self.message_bus.subscribe(
            "task.results",
            self._handle_task_result
        )

        print("开始监听任务结果...")

        # 保持监听状态
        while True:
            await asyncio.sleep(1)

    async def _handle_task_result(self, message):
        """处理任务结果消息"""
        result_data = message.content

        task_id = result_data.get("task_id")
        success = result_data.get("success", False)
        result = result_data.get("result", {})
        error = result_data.get("error")

        if success:
            print(f"任务 {task_id} 执行成功")
            print(f"结果: {result}")

            # 处理成功结果
            await self._process_successful_result(task_id, result)
        else:
            print(f"任务 {task_id} 执行失败: {error}")

            # 处理失败结果
            await self._process_failed_result(task_id, error)

    async def _process_successful_result(self, task_id: str, result: Dict[str, Any]):
        """处理成功结果"""
        # 实现成功结果的处理逻辑
        pass

    async def _process_failed_result(self, task_id: str, error: str):
        """处理失败结果"""
        # 实现失败结果的处理逻辑
        pass

if __name__ == "__main__":
    handler = TaskResultHandler()
    asyncio.run(handler.start_listening())
```

## 智能体协作

### 1. 建立协作会话
```python
# examples/collaboration_example.py
import asyncio
from communication.message_bus import get_message_bus
from communication.protocol import MessageType

async def establish_collaboration():
    """建立智能体协作会话"""

    message_bus = get_message_bus()

    # 创建协作请求
    collaboration_data = {
        "coordination_type": "establish_collaboration",
        "participants": ["agent-001", "agent-002", "agent-003"],
        "collaboration_type": "data_processing_pipeline",
        "context": {
            "project": "analytics_dashboard",
            "deadline": "2024-02-15T23:59:59Z",
            "shared_resources": ["database_connection", "cache"]
        }
    }

    # 向协调智能体发送协作请求
    response = await message_bus.send_message(
        recipient_id="coordinator-001",
        message_type=MessageType.COORDINATION_REQUEST,
        content=collaboration_data,
        requires_response=True,
        timeout_seconds=30
    )

    if response and response.content.get("success"):
        session_id = response.content["result"]["session_id"]
        print(f"协作会话已建立: {session_id}")

        # 开始协作执行
        await start_collaborative_execution(session_id)
    else:
        print("协作会话建立失败")

async def start_collaborative_execution(session_id: str):
    """开始协作执行"""

    message_bus = get_message_bus()

    # 创建执行计划
    execution_data = {
        "coordination_type": "coordinate_execution",
        "session_id": session_id,
        "execution_plan": {
            "steps": [
                {
                    "name": "data_extraction",
                    "assignee": "agent-001",
                    "estimated_duration": 300,
                    "dependencies": []
                },
                {
                    "name": "data_processing",
                    "assignee": "agent-002",
                    "estimated_duration": 600,
                    "dependencies": ["data_extraction"]
                },
                {
                    "name": "report_generation",
                    "assignee": "agent-003",
                    "estimated_duration": 300,
                    "dependencies": ["data_processing"]
                }
            ],
            "timeline": {
                "start_time": "2024-02-01T09:00:00Z",
                "end_time": "2024-02-01T10:30:00Z"
            },
            "resource_requirements": {
                "database_connections": 2,
                "memory_gb": 8
            }
        }
    }

    # 发送执行请求
    response = await message_bus.send_message(
        recipient_id="coordinator-001",
        message_type=MessageType.COORDINATION_REQUEST,
        content=execution_data,
        requires_response=True,
        timeout_seconds=30
    )

    if response and response.content.get("success"):
        print("协作执行已开始")
        print(f"执行详情: {response.content['result']}")
    else:
        print("协作执行启动失败")

if __name__ == "__main__":
    asyncio.run(establish_collaboration())
```

### 2. 处理协作冲突
```python
# examples/conflict_resolution.py
import asyncio
from communication.message_bus import get_message_bus
from communication.protocol import MessageType

async def handle_conflict():
    """处理协作冲突"""

    message_bus = get_message_bus()

    # 创建冲突报告
    conflict_data = {
        "coordination_type": "resolve_conflict",
        "conflict": {
            "conflict_type": "resource_conflict",
            "involved_agents": ["agent-001", "agent-002"],
            "description": "两个智能体同时需要访问同一数据库资源",
            "resource": "database_connection_pool",
            "impact": "high",
            "priority": 8
        }
    }

    # 向协调智能体报告冲突
    response = await message_bus.send_message(
        recipient_id="coordinator-001",
        message_type=MessageType.CONFLICT_REPORT,
        content=conflict_data,
        requires_response=True,
        timeout_seconds=30
    )

    if response and response.content.get("success"):
        resolution = response.content["result"]
        print(f"冲突已解决: {resolution['conflict_id']}")
        print(f"解决策略: {resolution['resolution_strategy']}")
        print(f"解决结果: {resolution['resolution_result']}")

        # 应用解决方案
        await apply_conflict_resolution(resolution)
    else:
        print("冲突解决失败")

async def apply_conflict_resolution(resolution: Dict[str, Any]):
    """应用冲突解决方案"""

    strategy = resolution.get("resolution_strategy")
    result = resolution.get("resolution_result")

    if strategy == "resource_reallocation":
        # 实现资源重新分配
        print("正在应用资源重新分配方案...")

    elif strategy == "priority_negotiation":
        # 实现优先级协商
        print("正在执行优先级协商...")

    elif strategy == "time_sharing":
        # 实现时间分片
        print("正在配置时间分片方案...")

    print("冲突解决方案已应用")

if __name__ == "__main__":
    asyncio.run(handle_conflict())
```

## 监控和管理

### 1. 系统状态监控
```python
# examples/monitoring.py
import asyncio
import time
from communication.message_bus import get_message_bus
from communication.protocol import MessageType

class SystemMonitor:
    def __init__(self):
        self.message_bus = get_message_bus()
        self.monitoring_interval = 60  # 60秒

    async def start_monitoring(self):
        """开始系统监控"""

        print("开始系统监控...")

        while True:
            try:
                # 获取系统状态
                await self._collect_system_metrics()

                # 检查异常情况
                await self._check_for_anomalies()

                # 等待下次监控
                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                print(f"监控错误: {e}")
                await asyncio.sleep(10)

    async def _collect_system_metrics(self):
        """收集系统指标"""

        # 向元智能体请求系统状态
        response = await self.message_bus.send_message(
            recipient_id="meta-agent-001",
            message_type=MessageType.SYSTEM_STATUS_REQUEST,
            content={},
            requires_response=True,
            timeout_seconds=10
        )

        if response:
            system_status = response.content

            # 显示关键指标
            self._display_metrics(system_status)

            # 保存指标数据
            await self._save_metrics(system_status)

    def _display_metrics(self, system_status: Dict[str, Any]):
        """显示系统指标"""

        print(f"\n=== 系统状态 ({time.strftime('%Y-%m-%d %H:%M:%S')}) ===")

        # 基础指标
        print(f"注册智能体: {system_status.get('registered_agents_count', 0)}")
        print(f"活跃任务: {system_status.get('active_tasks_count', 0)}")
        print(f"系统健康度: {system_status.get('system_health', 0):.2%}")

        # 性能指标
        metrics = system_status.get('metrics', {})
        print(f"任务处理数: {metrics.get('tasks_processed', 0)}")
        print(f"成功率: {metrics.get('success_rate', 0):.2%}")
        print(f"平均响应时间: {metrics.get('average_response_time', 0):.2f}s")

        # 智能体详情
        agents = system_status.get('registered_agents', [])
        print(f"\n智能体状态:")
        for agent in agents[:5]:  # 显示前5个智能体
            print(f"  - {agent['agent_id']}: {agent['status']} (负载: {agent['current_load']}/{agent['max_capacity']})")

        if len(agents) > 5:
            print(f"  ... 还有 {len(agents) - 5} 个智能体")

    async def _save_metrics(self, system_status: Dict[str, Any]):
        """保存指标数据"""
        # 实现指标数据保存逻辑
        pass

    async def _check_for_anomalies(self):
        """检查异常情况"""

        # 向协调智能体查询异常
        response = await self.message_bus.send_message(
            recipient_id="coordinator-001",
            message_type=MessageType.STATUS_REQUEST,
            content={"check_anomalies": True},
            requires_response=True,
            timeout_seconds=10
        )

        if response:
            anomalies = response.content.get("anomalies", [])

            if anomalies:
                print(f"\n⚠️  发现 {len(anomalies)} 个异常:")
                for anomaly in anomalies:
                    print(f"  - {anomaly['type']}: {anomaly['description']}")
                    print(f"    严重程度: {anomaly['severity']}")
                    print(f"    建议措施: {anomaly['recommended_action']}")

            # 检查系统健康度
            system_health = response.content.get("coordination_health", "good")
            if system_health != "good":
                print(f"\n系统健康状态: {system_health}")

if __name__ == "__main__":
    monitor = SystemMonitor()
    asyncio.run(monitor.start_monitoring())
```

### 2. 性能优化
```python
# examples/performance_optimization.py
import asyncio
from communication.message_bus import get_message_bus
from communication.protocol import MessageType

async def optimize_system_performance():
    """优化系统性能"""

    message_bus = get_message_bus()

    # 分析当前性能
    performance_analysis = await analyze_performance()

    if performance_analysis["needs_optimization"]:
        print("系统需要性能优化")

        # 应用优化策略
        optimization_strategies = performance_analysis["recommended_strategies"]

        for strategy in optimization_strategies:
            print(f"应用优化策略: {strategy['name']}")
            await apply_optimization_strategy(strategy)
            print(f"优化策略 {strategy['name']} 已应用")

        # 验证优化效果
        await verify_optimization_results()
    else:
        print("系统性能正常，无需优化")

async def analyze_performance() -> Dict[str, Any]:
    """分析系统性能"""

    message_bus = get_message_bus()

    # 收集性能数据
    performance_data = {}

    # 从元智能体获取性能指标
    meta_response = await message_bus.send_message(
        recipient_id="meta-agent-001",
        message_type=MessageType.SYSTEM_STATUS_REQUEST,
        content={"include_metrics": True},
        requires_response=True,
        timeout_seconds=10
    )

    if meta_response:
        performance_data["meta_agent"] = meta_response.content

    # 从协调智能体获取协调性能
    coord_response = await message_bus.send_message(
        recipient_id="coordinator-001",
        message_type=MessageType.STATUS_REQUEST,
        content={"include_performance": True},
        requires_response=True,
        timeout_seconds=10
    )

    if coord_response:
        performance_data["coordinator"] = coord_response.content

    # 分析性能瓶颈
    return analyze_performance_bottlenecks(performance_data)

def analyze_performance_bottlenecks(data: Dict[str, Any]) -> Dict[str, Any]:
    """分析性能瓶颈"""

    bottlenecks = []
    strategies = []

    # 分析元智能体性能
    meta_metrics = data.get("meta_agent", {}).get("metrics", {})
    if meta_metrics.get("average_response_time", 0) > 5.0:
        bottlenecks.append("元智能体响应时间过长")
        strategies.append({
            "name": "optimize_meta_agent",
            "description": "优化元智能体的任务分配算法",
            "expected_improvement": "响应时间减少30%"
        })

    # 分析协调性能
    coord_stats = data.get("coordinator", {}).get("coordination_stats", {})
    if coord_stats.get("average_response_time", 0) > 3.0:
        bottlenecks.append("协调智能体处理延迟")
        strategies.append({
            "name": "optimize_coordination",
            "description": "优化协调智能体的消息处理流程",
            "expected_improvement": "协调延迟减少40%"
        })

    # 分析负载均衡
    active_agents = data.get("meta_agent", {}).get("registered_agents_count", 0)
    active_tasks = data.get("meta_agent", {}).get("active_tasks_count", 0)

    if active_tasks > active_agents * 10:
        bottlenecks.append("系统负载过高")
        strategies.append({
            "name": "scale_agents",
            "description": "增加智能体实例以提高处理能力",
            "expected_improvement": "处理能力提升50%"
        })

    return {
        "needs_optimization": len(bottlenecks) > 0,
        "bottlenecks": bottlenecks,
        "recommended_strategies": strategies
    }

async def apply_optimization_strategy(strategy: Dict[str, Any]):
    """应用优化策略"""

    message_bus = get_message_bus()
    strategy_name = strategy["name"]

    if strategy_name == "optimize_meta_agent":
        # 优化元智能体
        await message_bus.send_message(
            recipient_id="meta-agent-001",
            message_type=MessageType.OPTIMIZATION_REQUEST,
            content={
                "optimization_type": "allocation_algorithm",
                "parameters": {
                    "enable_load_balancing": True,
                    "enable_priority_queue": True,
                    "allocation_strategy": "capability_matched"
                }
            }
        )

    elif strategy_name == "optimize_coordination":
        # 优化协调智能体
        await message_bus.send_message(
            recipient_id="coordinator-001",
            message_type=MessageType.OPTIMIZATION_REQUEST,
            content={
                "optimization_type": "message_processing",
                "parameters": {
                    "enable_async_processing": True,
                    "batch_size": 100,
                    "processing_threads": 4
                }
            }
        )

    elif strategy_name == "scale_agents":
        # 扩展智能体
        print("正在启动额外的智能体实例...")
        # 这里可以实现动态启动智能体的逻辑

        # 等待新智能体注册
        await asyncio.sleep(10)

async def verify_optimization_results():
    """验证优化效果"""

    print("正在验证优化效果...")

    # 等待优化生效
    await asyncio.sleep(30)

    # 重新分析性能
    new_performance = await analyze_performance()

    if not new_performance["needs_optimization"]:
        print("✅ 优化成功，系统性能已改善")
    else:
        print("⚠️  优化效果有限，可能需要进一步调整")
        print(f"剩余瓶颈: {new_performance['bottlenecks']}")

if __name__ == "__main__":
    asyncio.run(optimize_system_performance())
```

## 故障处理和恢复

### 1. 智能体故障检测
```python
# examples/fault_detection.py
import asyncio
import time
from communication.message_bus import get_message_bus
from communication.protocol import MessageType

class FaultDetector:
    def __init__(self):
        self.message_bus = get_message_bus()
        self.health_check_interval = 30  # 30秒
        self.unhealthy_agents = {}

    async def start_detection(self):
        """开始故障检测"""

        print("开始智能体故障检测...")

        while True:
            try:
                # 检查所有注册的智能体
                await self._check_agent_health()

                # 处理不健康的智能体
                await self._handle_unhealthy_agents()

                # 等待下次检查
                await asyncio.sleep(self.health_check_interval)

            except Exception as e:
                print(f"故障检测错误: {e}")
                await asyncio.sleep(10)

    async def _check_agent_health(self):
        """检查智能体健康状态"""

        # 获取所有智能体列表
        response = await self.message_bus.send_message(
            recipient_id="meta-agent-001",
            message_type=MessageType.SYSTEM_STATUS_REQUEST,
            content={},
            requires_response=True,
            timeout_seconds=10
        )

        if response:
            agents = response.content.get("registered_agents", [])

            for agent in agents:
                agent_id = agent["agent_id"]

                # 检查智能体响应
                is_healthy = await self._ping_agent(agent_id)

                if not is_healthy:
                    if agent_id not in self.unhealthy_agents:
                        self.unhealthy_agents[agent_id] = {
                            "first_detected": time.time(),
                            "last_check": time.time(),
                            "failure_count": 1
                        }
                        print(f"⚠️  智能体 {agent_id} 健康检查失败")
                    else:
                        self.unhealthy_agents[agent_id]["last_check"] = time.time()
                        self.unhealthy_agents[agent_id]["failure_count"] += 1
                else:
                    if agent_id in self.unhealthy_agents:
                        del self.unhealthy_agents[agent_id]
                        print(f"✅ 智能体 {agent_id} 已恢复健康")

    async def _ping_agent(self, agent_id: str) -> bool:
        """检查单个智能体的健康状态"""

        try:
            response = await self.message_bus.send_message(
                recipient_id=agent_id,
                message_type=MessageType.HEARTBEAT_REQUEST,
                content={},
                requires_response=True,
                timeout_seconds=5
            )

            return response is not None

        except Exception:
            return False

    async def _handle_unhealthy_agents(self):
        """处理不健康的智能体"""

        current_time = time.time()

        for agent_id, health_info in list(self.unhealthy_agents.items()):
            failure_count = health_info["failure_count"]
            time_since_first = current_time - health_info["first_detected"]

            # 根据失败次数和时间采取不同措施
            if failure_count >= 3 and time_since_first >= 60:
                # 超过3次失败且超过1分钟，尝试重启
                print(f"尝试重启智能体 {agent_id}...")
                await self._restart_agent(agent_id)

            elif failure_count >= 5 and time_since_first >= 300:
                # 超过5次失败且超过5分钟，通知管理员
                print(f"智能体 {agent_id} 长时间无响应，需要人工干预")
                await self._alert_administrator(agent_id, health_info)

    async def _restart_agent(self, agent_id: str):
        """重启智能体"""

        # 发送重启命令
        response = await self.message_bus.send_message(
            recipient_id=agent_id,
            message_type=MessageType.SHUTDOWN_REQUEST,
            content={"restart": True},
            requires_response=True,
            timeout_seconds=10
        )

        if response:
            print(f"智能体 {agent_id} 重启命令已发送")
            # 从不健康列表中移除，等待下次检查
            if agent_id in self.unhealthy_agents:
                del self.unhealthy_agents[agent_id]
        else:
            print(f"无法向智能体 {agent_id} 发送重启命令")

    async def _alert_administrator(self, agent_id: str, health_info: Dict[str, Any]):
        """通知管理员"""

        alert_data = {
            "alert_type": "agent_failure",
            "agent_id": agent_id,
            "failure_count": health_info["failure_count"],
            "time_since_first": int(time.time() - health_info["first_detected"]),
            "severity": "high",
            "message": f"智能体 {agent_id} 长时间无响应，需要人工干预"
        }

        # 发送告警消息
        await self.message_bus.broadcast(
            MessageType.EMERGENCY_ALERT,
            alert_data
        )

        print(f"已发送管理员告警: {alert_data['message']}")

if __name__ == "__main__":
    detector = FaultDetector()
    asyncio.run(detector.start_detection())
```

## 部署和运维

### 1. Docker 部署
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 设置环境变量
ENV PYTHONPATH=/app
ENV AGENT_CONFIG_PATH=/app/config

# 暴露端口
EXPOSE 8000 8001 8002

# 启动命令
CMD ["python", "start_system.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 消息队列
  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # 数据库
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: multi_agent
      POSTGRES_USER: agent_user
      POSTGRES_PASSWORD: agent_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # 元智能体
  meta-agent:
    build: .
    environment:
      - AGENT_TYPE=meta_agent
      - AGENT_ID=meta-agent-001
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://agent_user:agent_password@postgres:5432/multi_agent
    depends_on:
      - redis
      - postgres
    ports:
      - "8000:8000"

  # 协调智能体
  coordinator:
    build: .
    environment:
      - AGENT_TYPE=coordinator
      - AGENT_ID=coordinator-001
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://agent_user:agent_password@postgres:5432/multi_agent
    depends_on:
      - redis
      - postgres
      - meta-agent
    ports:
      - "8001:8000"

  # 任务拆解智能体
  task-decomposer:
    build: .
    environment:
      - AGENT_TYPE=task_decomposer
      - AGENT_ID=task-decomposer-001
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://agent_user:agent_password@postgres:5432/multi_agent
    depends_on:
      - redis
      - postgres
      - meta-agent
    ports:
      - "8002:8000"

volumes:
  redis_data:
  postgres_data:
```

### 2. 生产环境配置
```yaml
# config/production.yaml
database:
  host: "prod-db.example.com"
  port: 5432
  name: "multi_agent_prod"
  user: "agent_user"
  password: "${DB_PASSWORD}"
  pool_size: 20
  max_overflow: 10

redis:
  host: "prod-redis.example.com"
  port: 6379
  password: "${REDIS_PASSWORD}"
  db: 0
  ssl: true

message_bus:
  type: "rabbitmq"
  host: "prod-rabbitmq.example.com"
  port: 5672
  username: "agent_user"
  password: "${RABBITMQ_PASSWORD}"
  virtual_host: "/multi_agent"

monitoring:
  enabled: true
  metrics_endpoint: "http://prometheus:9090"
  log_level: "INFO"
  alert_webhook: "${ALERT_WEBHOOK_URL}"

security:
  encryption_key: "${ENCRYPTION_KEY}"
  jwt_secret: "${JWT_SECRET}"
  ssl_cert_path: "/etc/ssl/certs/server.crt"
  ssl_key_path: "/etc/ssl/certs/server.key"

performance:
  max_concurrent_tasks: 100
  task_timeout: 300
  message_retry_attempts: 3
  health_check_interval: 30
```

这个集成指南提供了：
- ✅ **完整的安装配置**：从基础环境到生产部署
- ✅ **详细的代码示例**：涵盖所有主要功能的使用
- ✅ **实际应用场景**：协作、监控、故障处理等
- ✅ **运维指导**：Docker部署、性能优化、故障恢复
- ✅ **最佳实践**：安全配置、性能调优、监控告警

通过这个指南，开发者可以快速集成和使用多智能体系统，并根据具体需求进行定制和扩展。