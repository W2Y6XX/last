"""
系统接口 - 提供统一的外部访问接口
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field

from .coordinator import SystemCoordinator
from ..core.types import TaskId, AgentId, Priority, TaskStatus
from ..utils.logging import get_logger

logger = get_logger(__name__)


class TaskRequest(BaseModel):
    """任务请求模型"""
    title: str = Field(..., description="任务标题")
    description: str = Field(..., description="任务描述")
    priority: str = Field(default="medium", description="优先级")
    requester_id: str = Field(default="user", description="请求者ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class TaskResponse(BaseModel):
    """任务响应模型"""
    success: bool
    task_id: Optional[str] = None
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentInfo(BaseModel):
    """智能体信息模型"""
    agent_id: str
    agent_type: str
    name: str
    description: str
    status: str
    capabilities: List[str]
    current_tasks: int = 0
    load_percentage: float = 0.0


class SystemStatus(BaseModel):
    """系统状态模型"""
    total_agents: int
    active_agents: int
    total_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    system_load: float
    uptime_seconds: int
    is_healthy: bool


class LangGraphAgentSystem:
    """LangGraph 多智能体系统接口"""

    def __init__(self):
        self.coordinator = SystemCoordinator()
        self._is_initialized = False

    async def initialize(self) -> bool:
        """初始化系统"""
        try:
            if self._is_initialized:
                return True

            await self.coordinator.initialize()
            self._is_initialized = True
            logger.info("LangGraphAgentSystem initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            return False

    async def start(self) -> bool:
        """启动系统"""
        try:
            if not self._is_initialized:
                await self.initialize()

            await self.coordinator.start()
            logger.info("LangGraphAgentSystem started")
            return True

        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            return False

    async def stop(self) -> bool:
        """停止系统"""
        try:
            await self.coordinator.stop()
            logger.info("LangGraphAgentSystem stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop system: {e}")
            return False

    async def submit_task(self, request: TaskRequest) -> TaskResponse:
        """提交任务"""
        try:
            if not self._is_initialized:
                return TaskResponse(
                    success=False,
                    message="System not initialized"
                )

            task_id = await self.coordinator.submit_task(
                title=request.title,
                description=request.description,
                priority=request.priority,
                requester_id=request.requester_id
            )

            if task_id:
                return TaskResponse(
                    success=True,
                    task_id=task_id,
                    message="Task submitted successfully"
                )
            else:
                return TaskResponse(
                    success=False,
                    message="Failed to submit task"
                )

        except Exception as e:
            logger.error(f"Error submitting task: {e}")
            return TaskResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    async def get_task_status(self, task_id: TaskId) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            task_info = await self.coordinator.task_manager.get_task_info(task_id)
            if not task_info:
                return {"error": "Task not found"}

            task_state = await self.coordinator.task_manager.get_task_state(task_id)
            execution_record = await self.coordinator.task_manager.get_execution_record(task_id)

            return {
                "task_id": task_id,
                "title": task_info.title,
                "description": task_info.description,
                "status": task_info.status.value,
                "priority": task_info.priority.value,
                "progress": task_state.progress if task_state else 0.0,
                "assigned_agent": task_info.assigned_agent,
                "created_at": task_info.created_at.isoformat(),
                "updated_at": task_info.updated_at.isoformat(),
                "result": task_state.result if task_state else None,
                "error": task_state.error if task_state else None,
                "execution_time": (
                    execution_record.completed_at - execution_record.started_at
                ).total_seconds() if execution_record and execution_record.completed_at else None
            }

        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return {"error": str(e)}

    async def cancel_task(self, task_id: TaskId, reason: str = "Cancelled by user") -> Dict[str, Any]:
        """取消任务"""
        try:
            success = await self.coordinator.task_lifecycle.cancel_task(task_id, reason)
            return {
                "success": success,
                "message": "Task cancelled successfully" if success else "Failed to cancel task"
            }

        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

    async def list_tasks(
        self,
        status: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """列出任务"""
        try:
            if status:
                task_status = TaskStatus(status)
                tasks = await self.coordinator.task_manager.get_tasks_by_status(task_status)
            elif agent_id:
                tasks = await self.coordinator.task_manager.get_tasks_by_agent(agent_id)
            else:
                # 获取所有任务
                all_tasks = []
                for task_status in TaskStatus:
                    tasks = await self.coordinator.task_manager.get_tasks_by_status(task_status)
                    all_tasks.extend(tasks)
                tasks = all_tasks

            # 转换为字典格式并限制数量
            task_list = []
            for task in tasks[:limit]:
                task_dict = {
                    "task_id": task.task_id,
                    "title": task.title,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "assigned_agent": task.assigned_agent,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat()
                }
                task_list.append(task_dict)

            return task_list

        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return []

    async def get_agents(self) -> List[AgentInfo]:
        """获取智能体列表"""
        try:
            agents = []
            registry_agents = self.coordinator.agent_registry.get_active_agents()

            for agent in registry_agents:
                agent_load = await self.coordinator.resource_manager.get_agent_load(agent.agent_id)

                agent_info = AgentInfo(
                    agent_id=agent.agent_id,
                    agent_type=agent.agent_type.value,
                    name=agent.name,
                    description=agent.description,
                    status=agent.status,
                    capabilities=[cap.name for cap in agent.capabilities],
                    current_tasks=agent_load.current_tasks if agent_load else 0,
                    load_percentage=agent_load.load_percentage if agent_load else 0.0
                )
                agents.append(agent_info)

            return agents

        except Exception as e:
            logger.error(f"Error getting agents: {e}")
            return []

    async def get_agent_details(self, agent_id: AgentId) -> Dict[str, Any]:
        """获取智能体详细信息"""
        try:
            agent_info = await self.coordinator.get_agent_info(agent_id)
            if not agent_info:
                return {"error": "Agent not found"}

            agent_load = await self.coordinator.resource_manager.get_agent_load(agent_id)

            return {
                **agent_info,
                "load": {
                    "current_tasks": agent_load.current_tasks if agent_load else 0,
                    "load_percentage": agent_load.load_percentage if agent_load else 0.0,
                    "max_concurrent_tasks": agent_load.max_concurrent_tasks if agent_load else 5
                }
            }

        except Exception as e:
            logger.error(f"Error getting agent details: {e}")
            return {"error": str(e)}

    async def get_system_status(self) -> SystemStatus:
        """获取系统状态"""
        try:
            status = await self.coordinator.get_system_status()
            health = await self.coordinator.perform_health_check()

            return SystemStatus(
                total_agents=status.total_agents,
                active_agents=status.active_agents,
                total_tasks=status.total_tasks,
                running_tasks=status.running_tasks,
                completed_tasks=status.completed_tasks,
                failed_tasks=status.failed_tasks,
                system_load=status.system_load,
                uptime_seconds=int(status.uptime.total_seconds()) if status.uptime else 0,
                is_healthy=health.get("overall") == "healthy"
            )

        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return SystemStatus(
                total_agents=0, active_agents=0, total_tasks=0,
                running_tasks=0, completed_tasks=0, failed_tasks=0,
                system_load=0.0, uptime_seconds=0, is_healthy=False
            )

    async def send_message_to_agent(
        self,
        sender_id: str,
        receiver_id: str,
        content: str,
        message_type: str = "task_request"
    ) -> Dict[str, Any]:
        """发送消息给智能体"""
        try:
            success = await self.coordinator.messaging_service.send_point_to_point(
                sender_id=sender_id,
                receiver_id=receiver_id,
                content=content,
                message_type=message_type,
                require_acknowledgment=True
            )

            return {
                "success": success,
                "message": "Message sent successfully" if success else "Failed to send message"
            }

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

    async def broadcast_message(
        self,
        sender_id: str,
        content: str,
        message_type: str = "broadcast"
    ) -> Dict[str, Any]:
        """广播消息"""
        try:
            results = await self.coordinator.broadcast_system_message(
                content=content,
                message_type=message_type,
                sender_id=sender_id
            )

            successful_count = sum(1 for success in results.values() if success)
            total_count = len(results)

            return {
                "success": True,
                "total_agents": total_count,
                "successful_deliveries": successful_count,
                "delivery_rate": successful_count / total_count * 100 if total_count > 0 else 0,
                "details": results
            }

        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

    async def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        try:
            # 获取各种指标
            system_status = await self.get_system_status()
            task_stats = await self.coordinator.task_manager.get_statistics()
            message_stats = self.coordinator.message_bus.get_statistics()
            resource_stats = await self.coordinator.resource_manager.get_resource_utilization()

            return {
                "timestamp": datetime.now().isoformat(),
                "system": system_status.dict(),
                "tasks": task_stats,
                "messages": message_stats,
                "resources": resource_stats,
                "health": await self.coordinator.perform_health_check()
            }

        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    async def export_system_data(self, format_type: str = "json") -> Dict[str, Any]:
        """导出系统数据"""
        try:
            if format_type.lower() != "json":
                return {"error": "Only JSON format is supported"}

            # 收集所有系统数据
            system_data = {
                "export_timestamp": datetime.now().isoformat(),
                "system_status": (await self.get_system_status()).dict(),
                "agents": [agent.dict() for agent in await self.get_agents()],
                "tasks": await self.list_tasks(limit=1000),  # 限制任务数量
                "metrics": await self.get_system_metrics()
            }

            return {
                "success": True,
                "data": system_data,
                "format": "json"
            }

        except Exception as e:
            logger.error(f"Error exporting system data: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # 便捷方法
    async def quick_submit_task(
        self,
        title: str,
        description: str,
        priority: str = "medium"
    ) -> str:
        """快速提交任务"""
        request = TaskRequest(
            title=title,
            description=description,
            priority=priority
        )
        response = await self.submit_task(request)
        return response.task_id if response.success else None

    async def wait_for_task_completion(
        self,
        task_id: TaskId,
        timeout: float = 3600.0
    ) -> Dict[str, Any]:
        """等待任务完成"""
        try:
            start_time = datetime.now()

            while True:
                # 检查超时
                if (datetime.now() - start_time).total_seconds() > timeout:
                    return {"error": "Timeout waiting for task completion"}

                # 获取任务状态
                task_status = await self.get_task_status(task_id)

                if "error" in task_status:
                    return task_status

                if task_status["status"] in ["completed", "failed", "cancelled"]:
                    return task_status

                # 等待一段时间再检查
                await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Error waiting for task completion: {e}")
            return {"error": str(e)}