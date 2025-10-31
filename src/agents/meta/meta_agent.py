"""
多智能体任务管理系统 - Meta-Agent（元智能体）
创建时间: 2025-10-20
职责：系统总体协调、任务分发、结果汇总、系统监控

重构说明：从 agent-implementations/meta_agent.py 迁移到新的结构化目录
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from ..base.base_agent import BaseAgent, MessageType, Message, Config, AgentError, MessageBus

logger = logging.getLogger(__name__)

class AgentState(Enum):
    """智能体状态枚举"""
    IDLE = "idle"
    BUSY = "busy"
    COORDINATING = "coordinating"
    MONITORING = "monitoring"
    ERROR = "error"

@dataclass
class TaskRequest:
    """任务请求数据结构"""
    task_id: str
    task_type: str
    priority: int
    input_data: Dict[str, Any]
    requirements: List[str]
    deadline: Optional[datetime] = None
    requester_id: Optional[str] = None

@dataclass
class AgentCapability:
    """智能体能力数据结构"""
    agent_id: str
    agent_type: str
    capabilities: List[str]
    availability: float
    current_load: int

class MetaAgent(BaseAgent):
    """元智能体

    负责任务分析、智能体协调、系统监控等高层功能。
    """

    def __init__(self, agent_id: str = "meta_agent", config: Config = None, message_bus: MessageBus = None):
        super().__init__(agent_id, "meta_agent", config, message_bus)

        # 元智能体特有状态
        self.active_tasks: Dict[str, TaskRequest] = {}
        self.registered_agents: Dict[str, AgentCapability] = {}
        self.task_queue: List[TaskRequest] = []
        self.system_state = AgentState.IDLE

        # 性能指标
        self.task_metrics = {
            "tasks_received": 0,
            "tasks_assigned": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_task_duration": 0.0
        }

    async def initialize(self) -> bool:
        """初始化元智能体"""
        try:
            # 注册消息处理器
            await self.register_message_handler(MessageType.TASK_REQUEST, self.handle_task_request)
            await self.register_message_handler(MessageType.HEARTBEAT, self.handle_agent_heartbeat)
            await self.register_message_handler(MessageType.STATUS_RESPONSE, self.handle_status_response)

            # 注册基础能力
            await self.register_capability("task_analysis")
            await self.register_capability("agent_coordination")
            await self.register_capability("system_monitoring")
            await self.register_capability("task_assignment")

            self.is_initialized = True
            logger.info(f"元智能体 {self.agent_id} 初始化完成")
            return True

        except Exception as e:
            logger.error(f"元智能体初始化失败: {e}")
            return False

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务"""
        try:
            task_request = TaskRequest(
                task_id=task_data.get("task_id", str(uuid.uuid4())),
                task_type=task_data.get("task_type", "general"),
                priority=task_data.get("priority", 2),
                input_data=task_data.get("input_data", {}),
                requirements=task_data.get("requirements", []),
                deadline=task_data.get("deadline"),
                requester_id=task_data.get("requester_id")
            )

            # 分析任务复杂度
            complexity = await self._analyze_task_complexity(task_request)

            # 确定执行策略
            strategy = await self._determine_execution_strategy(task_request, complexity)

            # 分配任务
            assignment_result = await self._assign_task(task_request, strategy)

            # 更新指标
            self.task_metrics["tasks_received"] += 1
            if assignment_result["success"]:
                self.task_metrics["tasks_assigned"] += 1
            else:
                self.task_metrics["tasks_failed"] += 1

            return {
                "success": True,
                "task_id": task_request.task_id,
                "complexity": complexity,
                "strategy": strategy,
                "assignment": assignment_result
            }

        except Exception as e:
            logger.error(f"处理任务失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _analyze_task_complexity(self, task: TaskRequest) -> Dict[str, Any]:
        """分析任务复杂度"""
        try:
            # 基于输入数据大小、任务类型、要求等评估复杂度
            input_size = len(json.dumps(task.input_data, default=str))
            requirements_count = len(task.requirements)

            # 简单的复杂度计算逻辑
            if input_size < 1000 and requirements_count <= 2:
                complexity_level = "low"
            elif input_size < 10000 and requirements_count <= 5:
                complexity_level = "medium"
            else:
                complexity_level = "high"

            # 检查是否需要任务分解
            needs_decomposition = (
                complexity_level in ["medium", "high"] or
                task.task_type in ["complex_analysis", "multi_step_process"]
            )

            return {
                "level": complexity_level,
                "input_size": input_size,
                "requirements_count": requirements_count,
                "needs_decomposition": needs_decomposition,
                "estimated_duration": self._estimate_task_duration(complexity_level)
            }

        except Exception as e:
            logger.error(f"任务复杂度分析失败: {e}")
            return {
                "level": "unknown",
                "error": str(e)
            }

    async def _determine_execution_strategy(self, task: TaskRequest, complexity: Dict[str, Any]) -> Dict[str, Any]:
        """确定执行策略"""
        try:
            strategy = {
                "execution_mode": "sequential",
                "agents_needed": [],
                "estimated_duration": complexity.get("estimated_duration", 60),
                "parallel_execution": False
            }

            # 根据任务复杂度确定策略
            if complexity.get("needs_decomposition", False):
                strategy["execution_mode"] = "coordinated"
                strategy["agents_needed"] = ["task_decomposer"]

            # 根据任务类型确定所需智能体
            if task.task_type == "analysis":
                strategy["agents_needed"].append("meta_agent")
            elif task.task_type == "coordination":
                strategy["agents_needed"].append("coordinator")
            elif task.task_type == "decomposition":
                strategy["agents_needed"].append("task_decomposer")

            # 如果需要多个智能体，考虑并行执行
            if len(strategy["agents_needed"]) > 1:
                strategy["parallel_execution"] = True
                strategy["execution_mode"] = "parallel"

            return strategy

        except Exception as e:
            logger.error(f"执行策略确定失败: {e}")
            return {
                "execution_mode": "sequential",
                "agents_needed": [],
                "error": str(e)
            }

    async def _assign_task(self, task: TaskRequest, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """分配任务"""
        try:
            assignment_id = str(uuid.uuid4())

            # 根据策略分配任务
            if strategy["execution_mode"] == "sequential":
                # 顺序执行 - 选择单个最合适的智能体
                assigned_agent = await self._select_best_agent(task)
                if assigned_agent:
                    result = await self._send_task_to_agent(assigned_agent, task)
                    return {
                        "success": result.get("success", False),
                        "assignment_id": assignment_id,
                        "assigned_agents": [assigned_agent],
                        "execution_mode": "sequential"
                    }

            elif strategy["execution_mode"] == "coordinated":
                # 协调执行 - 分配给协调智能体
                coordinator = self._find_agent_by_type("coordinator")
                if coordinator:
                    result = await self._send_task_to_agent(coordinator, task)
                    return {
                        "success": result.get("success", False),
                        "assignment_id": assignment_id,
                        "assigned_agents": [coordinator],
                        "execution_mode": "coordinated"
                    }

            elif strategy["execution_mode"] == "parallel":
                # 并行执行 - 分配给多个智能体
                assigned_agents = []
                success_count = 0

                for agent_type in strategy["agents_needed"]:
                    agent = self._find_agent_by_type(agent_type)
                    if agent:
                        result = await self._send_task_to_agent(agent, task)
                        if result.get("success", False):
                            success_count += 1
                            assigned_agents.append(agent)

                return {
                    "success": success_count > 0,
                    "assignment_id": assignment_id,
                    "assigned_agents": assigned_agents,
                    "execution_mode": "parallel",
                    "success_rate": success_count / len(strategy["agents_needed"])
                }

            return {
                "success": False,
                "assignment_id": assignment_id,
                "error": "No suitable agents found"
            }

        except Exception as e:
            logger.error(f"任务分配失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _select_best_agent(self, task: TaskRequest) -> Optional[str]:
        """选择最适合的智能体"""
        try:
            best_agent = None
            best_score = -1

            for agent_id, capability in self.registered_agents.items():
                # 计算匹配分数
                score = 0

                # 基于可用性
                score += capability.availability * 10

                # 基于负载（负载越低分数越高）
                score += (10 - capability.current_load) * 2

                # 基于能力匹配
                if task.task_type in capability.capabilities:
                    score += 20

                if score > best_score:
                    best_score = score
                    best_agent = agent_id

            return best_agent

        except Exception as e:
            logger.error(f"选择最佳智能体失败: {e}")
            return None

    def _find_agent_by_type(self, agent_type: str) -> Optional[str]:
        """根据类型查找智能体"""
        for agent_id, capability in self.registered_agents.items():
            if capability.agent_type == agent_type and capability.availability > 0.5:
                return agent_id
        return None

    async def _send_task_to_agent(self, agent_id: str, task: TaskRequest) -> Dict[str, Any]:
        """发送任务给智能体"""
        try:
            response = await self.send_message(
                recipient_id=agent_id,
                message_type=MessageType.TASK_REQUEST,
                content={
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "priority": task.priority,
                    "input_data": task.input_data,
                    "requirements": task.requirements,
                    "deadline": task.deadline.isoformat() if task.deadline else None,
                    "requester_id": task.requester_id
                }
            )

            return response or {"success": False, "error": "No response"}

        except Exception as e:
            logger.error(f"发送任务给智能体失败: {e}")
            return {"success": False, "error": str(e)}

    def _estimate_task_duration(self, complexity_level: str) -> int:
        """估算任务执行时间（秒）"""
        duration_map = {
            "low": 30,
            "medium": 120,
            "high": 300
        }
        return duration_map.get(complexity_level, 60)

    async def handle_task_request(self, message: Message) -> Optional[Message]:
        """处理任务请求"""
        try:
            task_data = message.content
            result = await self.process_task(task_data)

            return Message(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type=MessageType.TASK_RESPONSE,
                content=result,
                timestamp=datetime.now(timezone.utc),
                reply_to=message.message_id
            )

        except Exception as e:
            logger.error(f"处理任务请求失败: {e}")
            return None

    async def handle_agent_heartbeat(self, message: Message) -> Optional[Message]:
        """处理智能体心跳"""
        try:
            agent_data = message.content
            agent_id = agent_data.get("agent_id")

            if agent_id:
                # 更新智能体注册信息
                self.registered_agents[agent_id] = AgentCapability(
                    agent_id=agent_id,
                    agent_type=agent_data.get("agent_type"),
                    capabilities=agent_data.get("capabilities", []),
                    availability=agent_data.get("availability", 0.0),
                    current_load=agent_data.get("current_load", 0)
                )

            return None  # 心跳消息不需要回复

        except Exception as e:
            logger.error(f"处理智能体心跳失败: {e}")
            return None

    async def handle_status_response(self, message: Message) -> Optional[Message]:
        """处理状态响应"""
        try:
            # 更新系统状态
            status_data = message.content
            agent_id = status_data.get("agent_id")

            if agent_id and agent_id in self.registered_agents:
                # 更新智能体状态信息
                capability = self.registered_agents[agent_id]
                capability.current_load = status_data.get("current_load", 0)
                capability.availability = status_data.get("availability", 1.0)

            return None

        except Exception as e:
            logger.error(f"处理状态响应失败: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """获取元智能体状态"""
        base_status = super().get_status()

        # 添加元智能体特有状态
        meta_status = {
            "active_tasks": len(self.active_tasks),
            "registered_agents": len(self.registered_agents),
            "system_state": self.system_state.value,
            "task_queue_size": len(self.task_queue),
            "task_metrics": self.task_metrics
        }

        base_status.update(meta_status)
        return base_status

    def __str__(self) -> str:
        return f"MetaAgent(id={self.agent_id}, state={self.system_state.value})"