"""
资源管理器 - 智能体资源分配和负载均衡
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from ..core.types import AgentId, TaskId, Priority
from ..communication.registry import AgentRegistry
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ResourceType(Enum):
    """资源类型"""
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    STORAGE = "storage"
    CUSTOM = "custom"


@dataclass
class ResourceRequirement:
    """资源需求"""
    resource_type: ResourceType
    amount: float
    unit: str
    optional: bool = False


@dataclass
class ResourceAllocation:
    """资源分配"""
    task_id: TaskId
    agent_id: AgentId
    resources: Dict[ResourceType, float]
    allocated_at: datetime
    expected_duration: timedelta
    actual_duration: Optional[timedelta] = None


@dataclass
class AgentLoad:
    """智能体负载"""
    agent_id: AgentId
    current_tasks: int
    max_concurrent_tasks: int
    cpu_usage: float
    memory_usage: float
    load_percentage: float
    last_updated: datetime


class ResourceManager:
    """资源管理器"""

    def __init__(self, agent_registry: AgentRegistry):
        self.agent_registry = agent_registry
        self._allocations: Dict[TaskId, ResourceAllocation] = {}
        self._agent_loads: Dict[AgentId, AgentLoad] = {}
        self._resource_pools: Dict[ResourceType, float] = {}
        self._allocation_history: List[ResourceAllocation] = []

        # 默认资源限制
        self._default_agent_limits = {
            "max_concurrent_tasks": 5,
            "max_cpu_usage": 80.0,
            "max_memory_usage": 80.0
        }

        # 监控任务
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_monitoring = False

    async def start(self) -> None:
        """启动资源管理器"""
        if self._is_monitoring:
            return

        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("ResourceManager started")

    async def stop(self) -> None:
        """停止资源管理器"""
        self._is_monitoring = False

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("ResourceManager stopped")

    async def allocate_resources(
        self,
        task_id: TaskId,
        resource_requirements: List[ResourceRequirement],
        preferred_agents: List[AgentId] = None
    ) -> Optional[AgentId]:
        """分配资源给任务"""
        try:
            # 获取候选智能体
            candidates = await self._find_candidate_agents(
                resource_requirements,
                preferred_agents
            )

            if not candidates:
                logger.warning(f"No suitable agents found for task {task_id}")
                return None

            # 选择最佳智能体
            best_agent = await self._select_best_agent(candidates, resource_requirements)

            # 创建资源分配
            allocation = ResourceAllocation(
                task_id=task_id,
                agent_id=best_agent,
                resources={
                    req.resource_type: req.amount
                    for req in resource_requirements
                },
                allocated_at=datetime.now(),
                expected_duration=timedelta(hours=1)  # 默认预期时长
            )

            # 记录分配
            self._allocations[task_id] = allocation
            self._allocation_history.append(allocation)

            # 更新智能体负载
            await self._update_agent_load(best_agent, allocation.resources)

            logger.info(f"Resources allocated for task {task_id} to agent {best_agent}")
            return best_agent

        except Exception as e:
            logger.error(f"Failed to allocate resources for task {task_id}: {e}")
            return None

    async def release_resources(self, task_id: TaskId) -> bool:
        """释放任务资源"""
        try:
            if task_id not in self._allocations:
                logger.warning(f"No allocation found for task {task_id}")
                return False

            allocation = self._allocations.pop(task_id)

            # 更新智能体负载
            await self._update_agent_load(allocation.agent_id, allocation.resources, release=True)

            # 计算实际使用时长
            allocation.actual_duration = datetime.now() - allocation.allocated_at

            logger.info(f"Resources released for task {task_id} from agent {allocation.agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to release resources for task {task_id}: {e}")
            return False

    async def get_agent_load(self, agent_id: AgentId) -> Optional[AgentLoad]:
        """获取智能体负载"""
        return self._agent_loads.get(agent_id)

    async def get_system_load(self) -> Dict[str, Any]:
        """获取系统负载统计"""
        if not self._agent_loads:
            return {
                "total_agents": 0,
                "average_load": 0.0,
                "load_distribution": {}
            }

        total_load = sum(load.load_percentage for load in self._agent_loads.values())
        average_load = total_load / len(self._agent_loads)

        load_distribution = {}
        for load in self._agent_loads.values():
            load_range = self._get_load_range(load.load_percentage)
            load_distribution[load_range] = load_distribution.get(load_range, 0) + 1

        return {
            "total_agents": len(self._agent_loads),
            "average_load": average_load,
            "load_distribution": load_distribution,
            "total_active_tasks": sum(load.current_tasks for load in self._agent_loads.values()),
            "max_capacity": sum(load.max_concurrent_tasks for load in self._agent_loads.values())
        }

    async def find_least_loaded_agents(
        self,
        count: int = 1,
        capability_filter: List[str] = None
    ) -> List[AgentId]:
        """找到负载最小的智能体"""
        try:
            # 获取所有活跃智能体
            active_agents = self.agent_registry.get_active_agents()
            if capability_filter:
                filtered_agents = []
                for agent in active_agents:
                    agent_capabilities = [cap.name for cap in agent.capabilities]
                    if any(cap in agent_capabilities for cap in capability_filter):
                        filtered_agents.append(agent)
                active_agents = filtered_agents

            if not active_agents:
                return []

            # 按负载排序
            agent_loads = []
            for agent in active_agents:
                load = await self.get_agent_load(agent.agent_id)
                if load:
                    agent_loads.append((agent.agent_id, load.load_percentage))
                else:
                    agent_loads.append((agent.agent_id, 0.0))

            agent_loads.sort(key=lambda x: x[1])
            return [agent_id for agent_id, _ in agent_loads[:count]]

        except Exception as e:
            logger.error(f"Failed to find least loaded agents: {e}")
            return []

    async def rebalance_load(self) -> Dict[str, Any]:
        """重新平衡负载"""
        try:
            rebalance_actions = []
            overloaded_agents = []
            underloaded_agents = []

            # 识别过载和低负载智能体
            for agent_id, load in self._agent_loads.items():
                if load.load_percentage > 80.0:
                    overloaded_agents.append((agent_id, load))
                elif load.load_percentage < 30.0:
                    underloaded_agents.append((agent_id, load))

            # 尝试重新分配任务
            for overloaded_id, overloaded_load in overloaded_agents:
                if not underloaded_agents:
                    break

                # 找到可移动的任务
                movable_tasks = await self._find_movable_tasks(overloaded_id)
                if not movable_tasks:
                    continue

                # 选择最佳的目标智能体
                best_target = min(underloaded_agents, key=lambda x: x[1].load_percentage)
                target_id, target_load = best_target

                # 移动任务
                if movable_tasks:
                    task_id = movable_tasks[0]  # 简化：只移动一个任务
                    await self._move_task(task_id, overloaded_id, target_id)
                    rebalance_actions.append({
                        "action": "move_task",
                        "task_id": task_id,
                        "from_agent": overloaded_id,
                        "to_agent": target_id
                    })

                    # 更新负载记录
                    overloaded_load.current_tasks -= 1
                    overloaded_load.load_percentage = max(0, overloaded_load.load_percentage - 20)
                    target_load.current_tasks += 1
                    target_load.load_percentage = min(100, target_load.load_percentage + 20)

                    # 如果目标负载不再低负载，从列表中移除
                    if target_load.load_percentage >= 50.0:
                        underloaded_agents.remove(best_target)

            return {
                "actions_taken": len(rebalance_actions),
                "rebalance_actions": rebalance_actions,
                "overloaded_agents": len(overloaded_agents),
                "underloaded_agents": len(underloaded_agents)
            }

        except Exception as e:
            logger.error(f"Failed to rebalance load: {e}")
            return {"error": str(e)}

    async def get_resource_utilization(self, time_window: timedelta = None) -> Dict[str, Any]:
        """获取资源利用率统计"""
        time_window = time_window or timedelta(hours=1)
        cutoff_time = datetime.now() - time_window

        recent_allocations = [
            alloc for alloc in self._allocation_history
            if alloc.allocated_at >= cutoff_time
        ]

        if not recent_allocations:
            return {
                "total_allocations": 0,
                "resource_types": {},
                "average_duration": 0.0
            }

        # 统计资源使用
        resource_usage = {}
        total_duration = timedelta(seconds=0)
        completed_count = 0

        for allocation in recent_allocations:
            for resource_type, amount in allocation.resources.items():
                if resource_type not in resource_usage:
                    resource_usage[resource_type] = 0
                resource_usage[resource_type] += amount

            if allocation.actual_duration:
                total_duration += allocation.actual_duration
                completed_count += 1

        average_duration = total_duration / completed_count if completed_count > 0 else timedelta(0)

        return {
            "total_allocations": len(recent_allocations),
            "resource_types": {
                rt.value: usage for rt, usage in resource_usage.items()
            },
            "average_duration": average_duration.total_seconds(),
            "completion_rate": completed_count / len(recent_allocations) * 100
        }

    # 私有方法
    async def _find_candidate_agents(
        self,
        resource_requirements: List[ResourceRequirement],
        preferred_agents: List[AgentId] = None
    ) -> List[AgentId]:
        """查找候选智能体"""
        candidates = []

        # 获取所有活跃智能体
        active_agents = self.agent_registry.get_active_agents()

        for agent in active_agents:
            agent_id = agent.agent_id

            # 检查是否在偏好列表中
            if preferred_agents and agent_id not in preferred_agents:
                continue

            # 检查负载情况
            load = await self.get_agent_load(agent_id)
            if load and load.load_percentage > 90.0:
                continue  # 跳过高负载智能体

            # 检查资源能力
            if await self._can_handle_resources(agent_id, resource_requirements):
                candidates.append(agent_id)

        return candidates

    async def _can_handle_resources(
        self,
        agent_id: AgentId,
        resource_requirements: List[ResourceRequirement]
    ) -> bool:
        """检查智能体是否能处理资源需求"""
        # 简化实现：假设所有智能体都能处理标准资源需求
        return True

    async def _select_best_agent(
        self,
        candidates: List[AgentId],
        resource_requirements: List[ResourceRequirement]
    ) -> AgentId:
        """选择最佳智能体"""
        if not candidates:
            raise ValueError("No candidates available")

        # 简单策略：选择负载最低的智能体
        best_agent = candidates[0]
        min_load = float('inf')

        for agent_id in candidates:
            load = await self.get_agent_load(agent_id)
            if load and load.load_percentage < min_load:
                min_load = load.load_percentage
                best_agent = agent_id

        return best_agent

    async def _update_agent_load(
        self,
        agent_id: AgentId,
        resources: Dict[ResourceType, float],
        release: bool = False
    ) -> None:
        """更新智能体负载"""
        if agent_id not in self._agent_loads:
            # 初始化负载记录
            self._agent_loads[agent_id] = AgentLoad(
                agent_id=agent_id,
                current_tasks=0,
                max_concurrent_tasks=self._default_agent_limits["max_concurrent_tasks"],
                cpu_usage=0.0,
                memory_usage=0.0,
                load_percentage=0.0,
                last_updated=datetime.now()
            )

        load = self._agent_loads[agent_id]

        if release:
            # 释放资源
            load.current_tasks = max(0, load.current_tasks - 1)
            load.cpu_usage = max(0, load.cpu_usage - 10.0)  # 简化：每个任务使用10% CPU
            load.memory_usage = max(0, load.memory_usage - 15.0)  # 简化：每个任务使用15% 内存
        else:
            # 分配资源
            load.current_tasks += 1
            load.cpu_usage = min(100, load.cpu_usage + 10.0)
            load.memory_usage = min(100, load.memory_usage + 15.0)

        # 计算负载百分比
        load.load_percentage = max(
            load.cpu_usage,
            load.memory_usage,
            (load.current_tasks / load.max_concurrent_tasks) * 100
        )

        load.last_updated = datetime.now()

    async def _monitoring_loop(self) -> None:
        """监控循环"""
        while self._is_monitoring:
            try:
                # 更新智能体负载信息
                await self._update_all_agent_loads()

                # 检查是否需要负载平衡
                system_load = await self.get_system_load()
                if system_load.get("average_load", 0) > 70.0:
                    logger.info("High system load detected, triggering rebalance")
                    await self.rebalance_load()

                await asyncio.sleep(60)  # 每分钟检查一次

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)  # 错误时等待更短时间

    async def _update_all_agent_loads(self) -> None:
        """更新所有智能体负载"""
        active_agents = self.agent_registry.get_active_agents()

        for agent in active_agents:
            agent_id = agent.agent_id
            registry_load = self.agent_registry.get_agent_load(agent_id)

            if agent_id not in self._agent_loads:
                self._agent_loads[agent_id] = AgentLoad(
                    agent_id=agent_id,
                    current_tasks=0,
                    max_concurrent_tasks=self._default_agent_limits["max_concurrent_tasks"],
                    cpu_usage=registry_load,
                    memory_usage=registry_load,
                    load_percentage=registry_load,
                    last_updated=datetime.now()
                )
            else:
                load = self._agent_loads[agent_id]
                load.cpu_usage = registry_load
                load.memory_usage = registry_load
                load.load_percentage = registry_load
                load.last_updated = datetime.now()

    def _get_load_range(self, load_percentage: float) -> str:
        """获取负载范围"""
        if load_percentage < 20:
            return "very_low"
        elif load_percentage < 40:
            return "low"
        elif load_percentage < 60:
            return "medium"
        elif load_percentage < 80:
            return "high"
        else:
            return "very_high"

    async def _find_movable_tasks(self, agent_id: AgentId) -> List[TaskId]:
        """找到可移动的任务"""
        movable_tasks = []
        current_time = datetime.now()

        for task_id, allocation in self._allocations.items():
            if allocation.agent_id == agent_id:
                # 检查任务是否刚开始（可以移动）
                time_since_allocation = current_time - allocation.allocated_at
                if time_since_allocation < timedelta(minutes=5):  # 5分钟内的任务可以移动
                    movable_tasks.append(task_id)

        return movable_tasks

    async def _move_task(self, task_id: TaskId, from_agent: AgentId, to_agent: AgentId) -> bool:
        """移动任务到另一个智能体"""
        try:
            if task_id not in self._allocations:
                return False

            allocation = self._allocations[task_id]
            old_resources = allocation.resources.copy()

            # 释放旧资源
            await self.release_resources(task_id)

            # 分配新资源
            new_requirements = [
                ResourceRequirement(
                    resource_type=resource_type,
                    amount=amount,
                    unit="units"
                )
                for resource_type, amount in old_resources.items()
            ]

            new_agent = await self.allocate_resources(task_id, new_requirements, [to_agent])

            return new_agent == to_agent

        except Exception as e:
            logger.error(f"Failed to move task {task_id}: {e}")
            return False