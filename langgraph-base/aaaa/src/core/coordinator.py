"""
系统协调器 - 集成和管理所有系统组件
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass

from .base_agent import BaseAgent
from ..agents.meta_agent import MetaAgent
from ..communication.message_bus import MessageBus
from ..communication.registry import AgentRegistry
from ..communication.messaging import MessagingService
from ..task_management.task_manager import TaskManager
from ..task_management.lifecycle import TaskLifecycle
from ..task_management.planning import TaskPlanner, PlanningStrategy
from ..task_management.resource_manager import ResourceManager
from ..core.types import AgentType, TaskId, AgentId
from ..core.exceptions import AgentSystemError
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SystemStatus:
    """系统状态"""
    total_agents: int
    active_agents: int
    total_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    system_load: float
    message_stats: Dict[str, int]
    uptime: datetime


class SystemCoordinator:
    """系统协调器 - 统一管理所有组件"""

    def __init__(self):
        # 核心组件
        self.message_bus = MessageBus()
        self.messaging_service = MessagingService(self.message_bus)
        self.agent_registry = AgentRegistry()
        self.task_manager = TaskManager()
        self.task_lifecycle = TaskLifecycle(self.task_manager)
        self.task_planner = TaskPlanner(self.task_manager)
        self.resource_manager = ResourceManager(self.agent_registry)

        # 智能体存储
        self._agents: Dict[AgentId, BaseAgent] = {}
        self._meta_agent: Optional[MetaAgent] = None

        # 系统状态
        self._is_running = False
        self._start_time: Optional[datetime] = None
        self._background_tasks: Set[asyncio.Task] = set()

        # 事件处理器
        self._system_event_handlers: Dict[str, List[callable]] = {}

    async def initialize(self) -> None:
        """初始化系统协调器"""
        try:
            logger.info("Initializing SystemCoordinator...")

            # 启动所有组件
            await self.message_bus.start()
            await self.agent_registry.start()
            await self.task_manager.start()
            await self.resource_manager.start()

            # 创建和注册 MetaAgent
            await self._create_meta_agent()

            # 注册事件处理器
            self._register_event_handlers()

            self._start_time = datetime.now()
            logger.info("SystemCoordinator initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize SystemCoordinator: {e}")
            raise AgentSystemError(f"System initialization failed: {str(e)}")

    async def start(self) -> None:
        """启动系统"""
        if self._is_running:
            logger.warning("System already running")
            return

        try:
            await self.initialize()

            # 启动所有智能体
            for agent in self._agents.values():
                await agent.start()

            # 启动后台任务
            await self._start_background_tasks()

            self._is_running = True
            logger.info("System started successfully")

            # 触发系统启动事件
            await self._trigger_system_event("system_started", {
                "start_time": self._start_time,
                "agents_count": len(self._agents)
            })

        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            await self.stop()
            raise AgentSystemError(f"System start failed: {str(e)}")

    async def stop(self) -> None:
        """停止系统"""
        if not self._is_running:
            return

        try:
            logger.info("Stopping system...")

            self._is_running = False

            # 停止后台任务
            await self._stop_background_tasks()

            # 停止所有智能体
            for agent in self._agents.values():
                await agent.stop()

            # 停止所有组件
            await self.resource_manager.stop()
            await self.task_manager.stop()
            await self.agent_registry.stop()
            await self.message_bus.stop()

            logger.info("System stopped successfully")

            # 触发系统停止事件
            await self._trigger_system_event("system_stopped", {
                "stop_time": datetime.now(),
                "uptime": datetime.now() - self._start_time if self._start_time else None
            })

        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")

    async def register_agent(self, agent: BaseAgent) -> bool:
        """注册智能体"""
        try:
            agent_id = agent.agent_id

            # 检查是否已注册
            if agent_id in self._agents:
                logger.warning(f"Agent already registered: {agent_id}")
                return False

            # 注册到智能体注册表
            from ..core.types import AgentInfo, AgentCapability
            agent_info = AgentInfo(
                agent_id=agent_id,
                agent_type=agent.agent_type,
                name=agent.name,
                description=agent.description,
                capabilities=[
                    AgentCapability(
                        name=cap,
                        description=f"Capability: {cap}",
                        parameters={}
                    )
                    for cap in agent.capabilities
                ]
            )

            success = await self.agent_registry.register_agent(agent_info)
            if not success:
                logger.error(f"Failed to register agent in registry: {agent_id}")
                return False

            # 注册到消息总线
            await self.message_bus.register_agent(agent_id, self._create_agent_message_handler(agent))

            # 存储智能体
            self._agents[agent_id] = agent

            # 启动智能体（如果系统正在运行）
            if self._is_running:
                await agent.start()

            logger.info(f"Agent registered: {agent_id} ({agent.agent_type.value})")

            # 触发智能体注册事件
            await self._trigger_system_event("agent_registered", {
                "agent_id": agent_id,
                "agent_type": agent.agent_type.value,
                "capabilities": agent.capabilities
            })

            return True

        except Exception as e:
            logger.error(f"Failed to register agent {agent.agent_id}: {e}")
            return False

    async def unregister_agent(self, agent_id: AgentId) -> bool:
        """注销智能体"""
        try:
            if agent_id not in self._agents:
                logger.warning(f"Agent not found for unregistration: {agent_id}")
                return False

            agent = self._agents[agent_id]

            # 停止智能体
            await agent.stop()

            # 从注册表注销
            await self.agent_registry.unregister_agent(agent_id)

            # 从消息总线注销
            await self.message_bus.unregister_agent(agent_id)

            # 从存储中移除
            del self._agents[agent_id]

            logger.info(f"Agent unregistered: {agent_id}")

            # 触发智能体注销事件
            await self._trigger_system_event("agent_unregistered", {
                "agent_id": agent_id,
                "agent_type": agent.agent_type.value
            })

            return True

        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False

    async def submit_task(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        requester_id: str = "user"
    ) -> Optional[TaskId]:
        """提交任务到系统"""
        try:
            # 通过 MetaAgent 处理任务
            if not self._meta_agent:
                logger.error("MetaAgent not available")
                return None

            # 处理任务请求
            result = await self._meta_agent.process_task_request(description)

            if result.get("success"):
                # 从 MetaAgent 响应中提取任务信息
                assignments = result.get("agent_assignments", {})
                decomposition = result.get("task_decomposition", {})

                # 创建实际的任务记录
                task_ids = []
                for subtask in decomposition.get("subtasks", []):
                    task_id = await self.task_lifecycle.create_task(
                        title=subtask["title"],
                        description=subtask["description"],
                        priority=priority,
                        metadata={
                            "requester_id": requester_id,
                            "original_request": description,
                            "subtask_of": title
                        }
                    )
                    task_ids.append(task_id)

                logger.info(f"Task submitted and decomposed: {len(task_ids)} subtasks created")
                return task_ids[0] if task_ids else None

            else:
                logger.error(f"MetaAgent failed to process task: {result.get('error')}")
                return None

        except Exception as e:
            logger.error(f"Failed to submit task: {e}")
            return None

    async def get_system_status(self) -> SystemStatus:
        """获取系统状态"""
        try:
            # 获取各种统计信息
            agent_stats = self.agent_registry.get_registry_stats()
            task_stats = await self.task_manager.get_statistics()
            message_stats = self.message_bus.get_statistics()
            system_load = await self.resource_manager.get_system_load()

            uptime = datetime.now() - self._start_time if self._start_time else None

            return SystemStatus(
                total_agents=agent_stats.get("active_agents", 0),
                active_agents=len([agent for agent in self._agents.values() if agent.is_running]),
                total_tasks=task_stats.get("total_tasks", 0),
                running_tasks=task_stats.get("running_tasks", 0),
                completed_tasks=task_stats.get("completed_tasks", 0),
                failed_tasks=task_stats.get("failed_tasks", 0),
                system_load=system_load.get("average_load", 0.0),
                message_stats=message_stats,
                uptime=uptime or datetime.min
            )

        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return SystemStatus(
                total_agents=0, active_agents=0, total_tasks=0,
                running_tasks=0, completed_tasks=0, failed_tasks=0,
                system_load=0.0, message_stats={}, uptime=datetime.min
            )

    async def get_agent_info(self, agent_id: AgentId) -> Optional[Dict[str, Any]]:
        """获取智能体信息"""
        try:
            # 从注册表获取基本信息
            registry_info = self.agent_registry.get_agent_info(agent_id)
            if not registry_info:
                return None

            # 从本地存储获取运行时信息
            agent = self._agents.get(agent_id)
            runtime_info = {
                "is_running": agent.is_running if agent else False,
                "is_initialized": agent.is_initialized if agent else False,
                "capabilities": agent.capabilities if agent else []
            }

            # 合并信息
            return {
                **registry_info.dict(),
                **runtime_info
            }

        except Exception as e:
            logger.error(f"Failed to get agent info for {agent_id}: {e}")
            return None

    async def broadcast_system_message(
        self,
        content: str,
        message_type: str = "info",
        sender_id: str = "system"
    ) -> Dict[str, bool]:
        """广播系统消息"""
        try:
            result = await self.messaging_service.broadcast_to_all(
                sender_id=sender_id,
                content=content,
                exclude_agents=[]
            )

            logger.info(f"System message broadcasted to {len(result)} agents")
            return result

        except Exception as e:
            logger.error(f"Failed to broadcast system message: {e}")
            return {}

    async def perform_health_check(self) -> Dict[str, Any]:
        """执行系统健康检查"""
        try:
            health_status = {
                "overall": "healthy",
                "components": {},
                "agents": {},
                "timestamp": datetime.now().isoformat()
            }

            # 检查各个组件
            components = {
                "message_bus": self.message_bus._is_running,
                "agent_registry": self.agent_registry._is_running,
                "task_manager": self.task_manager._scheduler_running,
                "resource_manager": self.resource_manager._is_monitoring
            }

            for component, is_healthy in components.items():
                health_status["components"][component] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "running": is_healthy
                }
                if not is_healthy:
                    health_status["overall"] = "degraded"

            # 检查智能体
            for agent_id, agent in self._agents.items():
                agent_health = {
                    "status": "healthy" if agent.is_running else "unhealthy",
                    "running": agent.is_running,
                    "initialized": agent.is_initialized
                }
                health_status["agents"][agent_id] = agent_health

                if not agent.is_running:
                    health_status["overall"] = "degraded"

            return health_status

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "overall": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    # 私有方法
    async def _create_meta_agent(self) -> None:
        """创建 MetaAgent"""
        self._meta_agent = MetaAgent()
        await self.register_agent(self._meta_agent)

    async def _create_agent_message_handler(self, agent: BaseAgent):
        """创建智能体消息处理器"""
        async def message_handler(message):
            try:
                # 转发消息给智能体处理
                response = await agent.process_message(message)

                # 发送响应
                if response and hasattr(message, 'sender_id'):
                    await self.messaging_service.send_point_to_point(
                        sender_id=agent.agent_id,
                        receiver_id=message.sender_id,
                        content=response.content,
                        require_acknowledgment=False
                    )

            except Exception as e:
                logger.error(f"Error handling message for agent {agent.agent_id}: {e}")

        return message_handler

    def _register_event_handlers(self) -> None:
        """注册事件处理器"""
        # 任务管理器事件
        self.task_manager.add_event_handler("tasks_ready", self._on_tasks_ready)
        self.task_manager.add_event_handler("task_assigned", self._on_task_assigned)
        self.task_manager.add_event_handler("task_created", self._on_task_created)

        # 生命周期事件
        self.task_lifecycle.add_transition_handler(
            self.task_lifecycle.LifecycleEvent.COMPLETED,
            self._on_task_completed
        )
        self.task_lifecycle.add_transition_handler(
            self.task_lifecycle.LifecycleEvent.FAILED,
            self._on_task_failed
        )

    async def _start_background_tasks(self) -> None:
        """启动后台任务"""
        # 定期健康检查
        health_task = asyncio.create_task(self._periodic_health_check())
        self._background_tasks.add(health_task)
        health_task.add_done_callback(self._background_tasks.discard)

        # 负载均衡
        balance_task = asyncio.create_task(self._periodic_load_balancing())
        self._background_tasks.add(balance_task)
        balance_task.add_done_callback(self._background_tasks.discard)

    async def _stop_background_tasks(self) -> None:
        """停止后台任务"""
        for task in self._background_tasks:
            task.cancel()

        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        self._background_tasks.clear()

    async def _periodic_health_check(self) -> None:
        """定期健康检查"""
        while self._is_running:
            try:
                await asyncio.sleep(300)  # 每5分钟检查一次
                health = await self.perform_health_check()

                if health["overall"] != "healthy":
                    logger.warning(f"System health degraded: {health}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _periodic_load_balancing(self) -> None:
        """定期负载均衡"""
        while self._is_running:
            try:
                await asyncio.sleep(600)  # 每10分钟检查一次
                result = await self.resource_manager.rebalance_load()

                if result.get("actions_taken", 0) > 0:
                    logger.info(f"Load balancing performed: {result}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Load balancing error: {e}")

    async def _trigger_system_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """触发系统事件"""
        if event_type in self._system_event_handlers:
            for handler in self._system_event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"System event handler error: {e}")

    # 事件处理器
    async def _on_tasks_ready(self, data: Dict[str, Any]) -> None:
        """任务就绪事件处理器"""
        ready_tasks = data.get("tasks", [])
        logger.info(f"Tasks ready for execution: {len(ready_tasks)}")

    async def _on_task_assigned(self, data: Dict[str, Any]) -> None:
        """任务分配事件处理器"""
        task_id = data.get("task_id")
        agent_id = data.get("agent_id")
        logger.info(f"Task assigned: {task_id} -> {agent_id}")

    async def _on_task_created(self, data: Dict[str, Any]) -> None:
        """任务创建事件处理器"""
        task_id = data.get("task_id")
        task_info = data.get("task_info")
        logger.info(f"Task created: {task_id}")

    async def _on_task_completed(self, transition) -> None:
        """任务完成事件处理器"""
        logger.info(f"Task completed: {transition.task_id}")

    async def _on_task_failed(self, transition) -> None:
        """任务失败事件处理器"""
        logger.warning(f"Task failed: {transition.task_id} - {transition.reason}")

    # 系统事件处理器管理
    def add_system_event_handler(self, event_type: str, handler: callable) -> None:
        """添加系统事件处理器"""
        if event_type not in self._system_event_handlers:
            self._system_event_handlers[event_type] = []
        self._system_event_handlers[event_type].append(handler)

    def remove_system_event_handler(self, event_type: str, handler: callable) -> None:
        """移除系统事件处理器"""
        if event_type in self._system_event_handlers:
            if handler in self._system_event_handlers[event_type]:
                self._system_event_handlers[event_type].remove(handler)