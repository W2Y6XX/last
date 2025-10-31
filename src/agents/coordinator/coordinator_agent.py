"""
多智能体任务管理系统 - Coordinator-Agent（协调智能体）
创建时间: 2025-10-20
职责：智能体协调、任务分配、冲突解决

重构说明：从 agent-implementations/coordinator.py 迁移到新的结构化目录
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

from ..base.base_agent import BaseAgent, MessageType, Message, Config, AgentError, MessageBus

logger = logging.getLogger(__name__)

class CoordinatorAgent(BaseAgent):
    """协调智能体

    负责协调多个智能体的工作，解决冲突，优化任务分配。
    """

    def __init__(self, agent_id: str = "coordinator", config: Config = None, message_bus: MessageBus = None):
        super().__init__(agent_id, "coordinator", config, message_bus)

        # 协调器特有状态
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.agent_tasks: Dict[str, List[str]] = {}  # agent_id -> task_ids
        self.task_dependencies: Dict[str, List[str]] = {}  # task_id -> dependent task_ids
        self.coordination_history: List[Dict[str, Any]] = []

        # 协调指标
        self.coordination_metrics = {
            "coordinations_handled": 0,
            "conflicts_resolved": 0,
            "tasks_orchestrated": 0,
            "average_coordination_time": 0.0
        }

    async def initialize(self) -> bool:
        """初始化协调智能体"""
        try:
            # 注册消息处理器
            await self.register_message_handler(MessageType.TASK_REQUEST, self.handle_coordination_request)
            await self.register_message_handler(MessageType.TASK_RESPONSE, self.handle_task_response)

            # 注册协调能力
            await self.register_capability("task_coordination")
            await self.register_capability("conflict_resolution")
            await self.register_capability("resource_allocation")
            await self.register_capability("workflow_orchestration")

            self.is_initialized = True
            logger.info(f"协调智能体 {self.agent_id} 初始化完成")
            return True

        except Exception as e:
            logger.error(f"协调智能体初始化失败: {e}")
            return False

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理协调任务"""
        try:
            task_id = task_data.get("task_id", str(uuid.uuid4()))
            coordination_id = str(uuid.uuid4())
            start_time = datetime.now(timezone.utc)

            # 创建协调任务记录
            coordination_record = {
                "coordination_id": coordination_id,
                "task_id": task_id,
                "task_type": task_data.get("task_type", "general"),
                "subtasks": [],
                "assigned_agents": [],
                "status": "initializing",
                "start_time": start_time,
                "dependencies": task_data.get("dependencies", [])
            }

            # 分析任务并创建子任务
            subtasks = await self._analyze_and_decompose_task(task_data)
            coordination_record["subtasks"] = subtasks

            # 分配子任务给合适的智能体
            assignments = await self._assign_subtasks(subtasks)
            coordination_record["assigned_agents"] = assignments

            # 开始执行协调
            execution_result = await self._execute_coordination(coordination_record)

            # 记录协调历史
            coordination_record["end_time"] = datetime.now(timezone.utc)
            coordination_record["duration"] = (coordination_record["end_time"] - start_time).total_seconds()
            coordination_record["status"] = "completed" if execution_result.get("success") else "failed"
            self.coordination_history.append(coordination_record)

            # 更新指标
            self._update_coordination_metrics(coordination_record)

            return {
                "success": execution_result.get("success", False),
                "coordination_id": coordination_id,
                "subtasks_count": len(subtasks),
                "assigned_agents": assignments,
                "result": execution_result,
                "duration": coordination_record["duration"]
            }

        except Exception as e:
            logger.error(f"处理协调任务失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _analyze_and_decompose_task(self, task_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析并分解任务"""
        try:
            subtasks = []
            task_type = task_data.get("task_type", "general")
            input_data = task_data.get("input_data", {})

            # 根据任务类型创建子任务
            if task_type == "multi_step_process":
                # 多步骤处理任务
                steps = input_data.get("steps", [])
                for i, step in enumerate(steps):
                    subtask = {
                        "subtask_id": str(uuid.uuid4()),
                        "step_number": i,
                        "description": step.get("description", f"步骤 {i+1}"),
                        "agent_type": step.get("agent_type", "generic"),
                        "input_data": step.get("data", {}),
                        "dependencies": step.get("dependencies", [])
                    }
                    subtasks.append(subtask)

            elif task_type == "parallel_analysis":
                # 并行分析任务
                analysis_types = input_data.get("analysis_types", [])
                for analysis_type in analysis_types:
                    subtask = {
                        "subtask_id": str(uuid.uuid4()),
                        "analysis_type": analysis_type,
                        "description": f"分析: {analysis_type}",
                        "agent_type": "meta_agent",
                        "input_data": input_data,
                        "dependencies": []
                    }
                    subtasks.append(subtask)

            else:
                # 通用任务 - 单个子任务
                subtask = {
                    "subtask_id": str(uuid.uuid4()),
                    "description": task_data.get("description", "通用任务"),
                    "agent_type": task_data.get("preferred_agent", "generic"),
                    "input_data": input_data,
                    "dependencies": []
                }
                subtasks.append(subtask)

            return subtasks

        except Exception as e:
            logger.error(f"任务分解失败: {e}")
            return []

    async def _assign_subtasks(self, subtasks: List[Dict[str, Any]]) -> List[str]:
        """分配子任务给智能体"""
        try:
            assigned_agents = []

            for subtask in subtasks:
                agent_type = subtask.get("agent_type", "generic")

                # 这里应该有实际的智能体发现和选择逻辑
                # 目前简化处理，使用虚拟的智能体ID
                if agent_type == "meta_agent":
                    agent_id = "meta_agent_1"
                elif agent_type == "coordinator":
                    agent_id = "coordinator_1"
                elif agent_type == "task_decomposer":
                    agent_id = "task_decomposer_1"
                else:
                    agent_id = f"generic_agent_{len(assigned_agents) + 1}"

                assigned_agents.append(agent_id)

                # 记录任务分配
                if agent_id not in self.agent_tasks:
                    self.agent_tasks[agent_id] = []
                self.agent_tasks[agent_id].append(subtask["subtask_id"])

            return assigned_agents

        except Exception as e:
            logger.error(f"子任务分配失败: {e}")
            return []

    async def _execute_coordination(self, coordination_record: Dict[str, Any]) -> Dict[str, Any]:
        """执行协调"""
        try:
            coordination_record["status"] = "executing"
            subtasks = coordination_record["subtasks"]
            assigned_agents = coordination_record["assigned_agents"]

            # 简化的执行逻辑 - 实际应该有更复杂的协调逻辑
            results = []

            for i, (subtask, agent_id) in enumerate(zip(subtasks, assigned_agents)):
                # 检查依赖
                if not await self._check_dependencies(subtask):
                    logger.warning(f"子任务 {subtask['subtask_id']} 依赖未满足，跳过")
                    continue

                # 发送任务给智能体
                task_result = await self._send_subtask_to_agent(agent_id, subtask)
                results.append(task_result)

                # 检查是否需要等待其他子任务
                if i < len(subtasks) - 1:
                    await asyncio.sleep(0.1)  # 简单的延迟，实际应该根据依赖关系调整

            # 汇总结果
            success_count = sum(1 for result in results if result.get("success", False))
            total_count = len(results)

            return {
                "success": success_count > 0,
                "total_subtasks": total_count,
                "successful_subtasks": success_count,
                "success_rate": success_count / total_count if total_count > 0 else 0,
                "results": results
            }

        except Exception as e:
            logger.error(f"执行协调失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _check_dependencies(self, subtask: Dict[str, Any]) -> bool:
        """检查子任务依赖"""
        try:
            dependencies = subtask.get("dependencies", [])

            for dep in dependencies:
                if dep not in self.active_tasks or self.active_tasks[dep]["status"] != "completed":
                    return False

            return True

        except Exception as e:
            logger.error(f"检查依赖失败: {e}")
            return False

    async def _send_subtask_to_agent(self, agent_id: str, subtask: Dict[str, Any]) -> Dict[str, Any]:
        """发送子任务给智能体"""
        try:
            response = await self.send_message(
                recipient_id=agent_id,
                message_type=MessageType.TASK_REQUEST,
                content={
                    "task_id": subtask["subtask_id"],
                    "task_type": "subtask",
                    "input_data": subtask["input_data"],
                    "description": subtask["description"]
                }
            )

            return response or {"success": False, "error": "No response"}

        except Exception as e:
            logger.error(f"发送子任务给智能体失败: {e}")
            return {"success": False, "error": str(e)}

    def _update_coordination_metrics(self, coordination_record: Dict[str, Any]):
        """更新协调指标"""
        self.coordination_metrics["coordinations_handled"] += 1

        if coordination_record["status"] == "completed":
            self.coordination_metrics["tasks_orchestrated"] += len(coordination_record["subtasks"])

        # 更新平均协调时间
        total_time = self.coordination_metrics.get("total_coordination_time", 0)
        total_time += coordination_record.get("duration", 0)
        self.coordination_metrics["total_coordination_time"] = total_time
        self.coordination_metrics["average_coordination_time"] = (
            total_time / self.coordination_metrics["coordinations_handled"]
        )

    async def handle_coordination_request(self, message: Message) -> Optional[Message]:
        """处理协调请求"""
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
            logger.error(f"处理协调请求失败: {e}")
            return None

    async def handle_task_response(self, message: Message) -> Optional[Message]:
        """处理任务响应"""
        try:
            response_data = message.content
            task_id = response_data.get("task_id")

            if task_id:
                # 更新活动任务状态
                if task_id in self.active_tasks:
                    self.active_tasks[task_id].update({
                        "status": "completed" if response_data.get("success") else "failed",
                        "result": response_data,
                        "completion_time": datetime.now(timezone.utc)
                    })

            return None  # 响应消息不需要回复

        except Exception as e:
            logger.error(f"处理任务响应失败: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """获取协调智能体状态"""
        base_status = super().get_status()

        # 添加协调器特有状态
        coordination_status = {
            "active_tasks": len(self.active_tasks),
            "coordination_history_size": len(self.coordination_history),
            "coordination_metrics": self.coordination_metrics
        }

        base_status.update(coordination_status)
        return base_status

    def __str__(self) -> str:
        return f"CoordinatorAgent(id={self.agent_id}, active_tasks={len(self.active_tasks)})"