"""
任务执行规划 - 依赖关系分析和执行计划生成
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import networkx as nx

from ..core.types import TaskId, Priority, ExecutionMode
from ..core.exceptions import DependencyResolutionError
from .task_manager import TaskManager, DependencyGraph
from ..utils.logging import get_logger

logger = get_logger(__name__)


class PlanningStrategy(Enum):
    """规划策略"""
    ASAP = "asap"                    # 尽快开始
    ALAP = "alap"                    # 尽晚开始
    CRITICAL_PATH = "critical_path"  # 关键路径优先
    LOAD_BALANCED = "load_balanced"  # 负载均衡
    DEADLINE_DRIVEN = "deadline_driven"  # 截止时间驱动


@dataclass
class ExecutionPlan:
    """执行计划"""
    plan_id: str
    task_ids: List[TaskId]
    execution_groups: List[List[TaskId]]  # 按顺序的执行组
    estimated_duration: timedelta
    created_at: datetime
    strategy: PlanningStrategy
    metadata: Dict[str, Any]


@dataclass
class CriticalPathAnalysis:
    """关键路径分析"""
    critical_path: List[TaskId]
    total_duration: timedelta
    task_floats: Dict[TaskId, timedelta]  # 任务的浮动时间
    path_activities: Set[TaskId]


class TaskPlanner:
    """任务规划器"""

    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self._plans: Dict[str, ExecutionPlan] = {}
        self._critical_path_cache: Dict[str, CriticalPathAnalysis] = {}

    async def create_execution_plan(
        self,
        task_ids: List[TaskId],
        strategy: PlanningStrategy = PlanningStrategy.ASAP,
        constraints: Dict[str, Any] = None
    ) -> ExecutionPlan:
        """创建执行计划"""
        try:
            # 获取依赖图
            dependency_graph = await self._build_dependency_graph(task_ids)

            # 验证依赖关系
            await self._validate_dependencies(dependency_graph)

            # 根据策略创建执行组
            execution_groups = await self._create_execution_groups(
                dependency_graph,
                strategy,
                constraints or {}
            )

            # 估算执行时间
            estimated_duration = await self._estimate_duration(execution_groups)

            # 创建计划
            plan = ExecutionPlan(
                plan_id=f"plan_{datetime.now().timestamp()}",
                task_ids=task_ids,
                execution_groups=execution_groups,
                estimated_duration=estimated_duration,
                created_at=datetime.now(),
                strategy=strategy,
                metadata={
                    "dependency_count": len([
                        dep for deps in dependency_graph.edges.values()
                        for dep in deps
                    ]),
                    "group_count": len(execution_groups)
                }
            )

            self._plans[plan.plan_id] = plan
            logger.info(f"Execution plan created: {plan.plan_id} with {len(execution_groups)} groups")

            return plan

        except Exception as e:
            logger.error(f"Failed to create execution plan: {e}")
            raise DependencyResolutionError("planning", [str(e)])

    async def analyze_critical_path(self, task_ids: List[TaskId]) -> CriticalPathAnalysis:
        """分析关键路径"""
        try:
            cache_key = "_".join(sorted(task_ids))
            if cache_key in self._critical_path_cache:
                return self._critical_path_cache[cache_key]

            # 构建NetworkX图
            G = nx.DiGraph()

            # 获取任务估算时间
            task_durations = {}
            for task_id in task_ids:
                task_info = await self.task_manager.get_task_info(task_id)
                if task_info:
                    duration = await self._estimate_task_duration(task_id)
                    task_durations[task_id] = duration
                    G.add_node(task_id, duration=duration)

            # 添加依赖边
            for task_id in task_ids:
                task_info = await self.task_manager.get_task_info(task_id)
                if task_info:
                    for dep_id in task_info.dependencies:
                        if dep_id in task_durations:
                            G.add_edge(dep_id, task_id)

            # 计算关键路径
            critical_path = nx.dag_longest_path(G, weight='duration')

            # 计算总时长
            total_duration = timedelta(seconds=0)
            for task_id in critical_path:
                total_duration += task_durations[task_id]

            # 计算浮动时间
            task_floats = {}
            for task_id in G.nodes():
                # 最早开始时间
                earliest_start = 0
                for predecessor in G.predecessors(task_id):
                    pred_duration = task_durations[predecessor]
                    pred_earliest = task_floats.get(predecessor, {}).get('earliest_finish', 0)
                    earliest_start = max(earliest_start, pred_earliest + pred_duration.total_seconds())

                # 最晚开始时间
                latest_start = total_duration.total_seconds()
                for successor in G.successors(task_id):
                    succ_latest = task_floats.get(successor, {}).get('latest_start', total_duration.total_seconds())
                    latest_start = min(latest_start, succ_latest)

                float_time = timedelta(seconds=latest_start - earliest_start)
                task_floats[task_id] = {
                    'earliest_start': earliest_start,
                    'latest_start': latest_start,
                    'float': float_time
                }

            analysis = CriticalPathAnalysis(
                critical_path=critical_path,
                total_duration=total_duration,
                task_floats=task_floats,
                path_activities=set(critical_path)
            )

            self._critical_path_cache[cache_key] = analysis
            logger.info(f"Critical path analysis completed: {len(critical_path)} tasks, {total_duration}")

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze critical path: {e}")
            raise DependencyResolutionError("critical_path", [str(e)])

    async def optimize_execution_order(
        self,
        task_ids: List[TaskId],
        criteria: str = "duration"  # "duration", "priority", "resources"
    ) -> List[TaskId]:
        """优化执行顺序"""
        try:
            if criteria == "duration":
                return await self._optimize_by_duration(task_ids)
            elif criteria == "priority":
                return await self._optimize_by_priority(task_ids)
            elif criteria == "resources":
                return await self._optimize_by_resources(task_ids)
            else:
                raise ValueError(f"Unknown optimization criteria: {criteria}")

        except Exception as e:
            logger.error(f"Failed to optimize execution order: {e}")
            return task_ids

    async def detect_resource_conflicts(
        self,
        task_ids: List[TaskId]
    ) -> Dict[str, List[TaskId]]:
        """检测资源冲突"""
        try:
            resource_usage = {}

            for task_id in task_ids:
                task_info = await self.task_manager.get_task_info(task_id)
                if not task_info:
                    continue

                # 分析任务资源需求
                required_resources = await self._analyze_task_resources(task_id)

                for resource, amount in required_resources.items():
                    if resource not in resource_usage:
                        resource_usage[resource] = []
                    resource_usage[resource].append((task_id, amount))

            # 检测冲突
            conflicts = {}
            for resource, tasks in resource_usage.items():
                if len(tasks) > 1:
                    conflicts[resource] = [task_id for task_id, _ in tasks]

            return conflicts

        except Exception as e:
            logger.error(f"Failed to detect resource conflicts: {e}")
            return {}

    async def generate_gantt_chart_data(
        self,
        plan: ExecutionPlan
    ) -> Dict[str, Any]:
        """生成甘特图数据"""
        try:
            gantt_data = {
                "tasks": [],
                "links": [],
                "timeline": {
                    "start": datetime.now(),
                    "end": datetime.now() + plan.estimated_duration
                }
            }

            current_time = datetime.now()
            for group_idx, group in enumerate(plan.execution_groups):
                group_start = current_time

                # 计算组内任务的持续时间
                group_duration = timedelta(seconds=0)
                for task_id in group:
                    duration = await self._estimate_task_duration(task_id)
                    group_duration = max(group_duration, duration)

                # 添加任务数据
                for task_id in group:
                    task_info = await self.task_manager.get_task_info(task_id)
                    if task_info:
                        task_duration = await self._estimate_task_duration(task_id)

                        gantt_data["tasks"].append({
                            "id": task_id,
                            "name": task_info.title,
                            "start": group_start.isoformat(),
                            "end": (group_start + task_duration).isoformat(),
                            "progress": 0,
                            "dependencies": task_info.dependencies,
                            "group": group_idx
                        })

                current_time += group_duration

            # 添加依赖链接
            for task in gantt_data["tasks"]:
                for dep_id in task["dependencies"]:
                    dep_task = next((t for t in gantt_data["tasks"] if t["id"] == dep_id), None)
                    if dep_task:
                        gantt_data["links"].append({
                            "source": dep_id,
                            "target": task["id"],
                            "type": "0"  # 完成到开始
                        })

            return gantt_data

        except Exception as e:
            logger.error(f"Failed to generate Gantt chart data: {e}")
            return {}

    # 私有方法
    async def _build_dependency_graph(self, task_ids: List[TaskId]) -> DependencyGraph:
        """构建依赖图"""
        graph = DependencyGraph()

        for task_id in task_ids:
            graph.add_node(task_id)

            task_info = await self.task_manager.get_task_info(task_id)
            if task_info:
                for dep_id in task_info.dependencies:
                    if dep_id in task_ids:
                        graph.add_edge(dep_id, task_id)

        return graph

    async def _validate_dependencies(self, graph: DependencyGraph) -> None:
        """验证依赖关系"""
        # 检查循环依赖
        cycles = graph.detect_cycles()
        if cycles:
            cycle_strs = [" -> ".join(cycle) for cycle in cycles]
            raise DependencyResolutionError("validation", [f"Circular dependencies: {'; '.join(cycle_strs)}"])

    async def _create_execution_groups(
        self,
        graph: DependencyGraph,
        strategy: PlanningStrategy,
        constraints: Dict[str, Any]
    ) -> List[List[TaskId]]:
        """创建执行组"""
        if strategy == PlanningStrategy.ASAP:
            return await self._create_asap_groups(graph)
        elif strategy == PlanningStrategy.ALAP:
            return await self._create_alap_groups(graph)
        elif strategy == PlanningStrategy.CRITICAL_PATH:
            return await self._create_critical_path_groups(graph)
        elif strategy == PlanningStrategy.LOAD_BALANCED:
            return await self._create_load_balanced_groups(graph)
        else:
            return await self._create_asap_groups(graph)

    async def _create_asap_groups(self, graph: DependencyGraph) -> List[List[TaskId]]:
        """创建ASAP执行组"""
        groups = []
        completed = set()
        remaining = set(graph.nodes)

        while remaining:
            ready = graph.get_ready_tasks(completed) & remaining
            if not ready:
                raise DependencyResolutionError("asap_planning", ["No ready tasks found"])

            groups.append(list(ready))
            completed.update(ready)
            remaining -= ready

        return groups

    async def _create_alap_groups(self, graph: DependencyGraph) -> List[List[TaskId]]:
        """创建ALAP执行组"""
        # 反向构建执行组
        groups = []
        completed = set()
        remaining = set(graph.nodes)

        # 找出没有后继的任务（终点任务）
        end_tasks = set()
        for task_id in graph.nodes:
            if not graph.get_dependents(task_id):
                end_tasks.add(task_id)

        while remaining:
            ready = set()
            for task_id in remaining:
                deps = graph.get_dependencies(task_id)
                if deps.issubset(completed):
                    ready.add(task_id)

            if not ready:
                # 如果没有就绪任务，选择终点的依赖
                ready = end_tasks & remaining

            groups.append(list(ready))
            completed.update(ready)
            remaining -= ready

        # 反转组顺序（ALAP是从后往前）
        return list(reversed(groups))

    async def _create_critical_path_groups(self, graph: DependencyGraph) -> List[List[TaskId]]:
        """创建关键路径优先的执行组"""
        # 首先分析关键路径
        all_tasks = list(graph.nodes)
        critical_analysis = await self.analyze_critical_path(all_tasks)

        # 将任务分为关键路径上的任务和非关键任务
        critical_tasks = critical_analysis.path_activities
        non_critical_tasks = set(all_tasks) - critical_tasks

        # 关键路径任务优先执行
        groups = []
        completed = set()

        # 先执行关键路径任务
        critical_remaining = critical_tasks.copy()
        while critical_remaining:
            ready = set()
            for task_id in critical_remaining:
                deps = graph.get_dependencies(task_id)
                if deps.issubset(completed):
                    ready.add(task_id)

            if ready:
                groups.append(list(ready))
                completed.update(ready)
                critical_remaining -= ready
            else:
                break

        # 再执行非关键任务
        non_critical_remaining = non_critical_tasks.copy()
        while non_critical_remaining:
            ready = set()
            for task_id in non_critical_remaining:
                deps = graph.get_dependencies(task_id)
                if deps.issubset(completed):
                    ready.add(task_id)

            if ready:
                groups.append(list(ready))
                completed.update(ready)
                non_critical_remaining -= ready
            else:
                break

        return groups

    async def _create_load_balanced_groups(self, graph: DependencyGraph) -> List[List[TaskId]]:
        """创建负载均衡的执行组"""
        # 简单实现：基于任务估算时间平衡每组的工作量
        groups = []
        completed = set()
        remaining = set(graph.nodes)
        target_group_duration = timedelta(hours=1)  # 每组目标时长

        while remaining:
            ready = graph.get_ready_tasks(completed) & remaining
            if not ready:
                raise DependencyResolutionError("load_balanced_planning", ["No ready tasks found"])

            current_group = []
            group_duration = timedelta(seconds=0)

            # 贪心算法：选择能加入当前组的任务
            while ready:
                best_task = None
                best_duration = None

                for task_id in ready:
                    duration = await self._estimate_task_duration(task_id)
                    if group_duration + duration <= target_group_duration:
                        if best_task is None or duration > best_duration:
                            best_task = task_id
                            best_duration = duration

                if best_task is None:
                    # 没有任务能加入当前组，选择最短的任务
                    best_task = min(ready, key=lambda tid: self._estimate_task_duration(tid))
                    best_duration = await self._estimate_task_duration(best_task)

                current_group.append(best_task)
                group_duration += best_duration
                ready.remove(best_task)
                remaining.remove(best_task)

            groups.append(current_group)
            completed.update(current_group)

        return groups

    async def _estimate_duration(self, execution_groups: List[List[TaskId]]) -> timedelta:
        """估算执行时间"""
        total_duration = timedelta(seconds=0)

        for group in execution_groups:
            group_duration = timedelta(seconds=0)
            for task_id in group:
                duration = await self._estimate_task_duration(task_id)
                group_duration = max(group_duration, duration)
            total_duration += group_duration

        return total_duration

    async def _estimate_task_duration(self, task_id: TaskId) -> timedelta:
        """估算单个任务的执行时间"""
        task_info = await self.task_manager.get_task_info(task_id)
        if not task_info:
            return timedelta(minutes=30)  # 默认30分钟

        # 基于任务类型和优先级估算
        base_duration = timedelta(minutes=30)

        # 根据优先级调整
        if task_info.priority == Priority.CRITICAL:
            base_duration = timedelta(minutes=15)
        elif task_info.priority == Priority.HIGH:
            base_duration = timedelta(minutes=25)
        elif task_info.priority == Priority.LOW:
            base_duration = timedelta(minutes=45)

        # 根据任务复杂度调整（基于描述长度）
        complexity_factor = min(len(task_info.description) / 500, 2.0)
        base_duration = timedelta(seconds=int(base_duration.total_seconds() * (1 + complexity_factor)))

        return base_duration

    async def _analyze_task_resources(self, task_id: TaskId) -> Dict[str, int]:
        """分析任务资源需求"""
        # 简化实现：基于任务类型分析资源需求
        task_info = await self.task_manager.get_task_info(task_id)
        if not task_info:
            return {}

        resources = {"cpu": 1, "memory": 1}  # 默认资源

        # 根据任务标题和描述分析资源需求
        title_lower = task_info.title.lower()
        desc_lower = task_info.description.lower()

        if any(word in title_lower + desc_lower for word in ["复杂", "困难", "大型"]):
            resources["cpu"] = 4
            resources["memory"] = 8
        elif any(word in title_lower + desc_lower for word in ["中等", "一般"]):
            resources["cpu"] = 2
            resources["memory"] = 4

        return resources

    async def _optimize_by_duration(self, task_ids: List[TaskId]) -> List[TaskId]:
        """按时长优化执行顺序"""
        task_durations = []
        for task_id in task_ids:
            duration = await self._estimate_task_duration(task_id)
            task_durations.append((task_id, duration))

        # 按时长排序（短任务优先）
        task_durations.sort(key=lambda x: x[1].total_seconds())
        return [task_id for task_id, _ in task_durations]

    async def _optimize_by_priority(self, task_ids: List[TaskId]) -> List[TaskId]:
        """按优先级优化执行顺序"""
        task_priorities = []
        for task_id in task_ids:
            task_info = await self.task_manager.get_task_info(task_id)
            if task_info:
                priority_value = {
                    Priority.CRITICAL: 4,
                    Priority.HIGH: 3,
                    Priority.MEDIUM: 2,
                    Priority.LOW: 1
                }.get(task_info.priority, 2)
                task_priorities.append((task_id, priority_value))

        # 按优先级排序（高优先级优先）
        task_priorities.sort(key=lambda x: x[1], reverse=True)
        return [task_id for task_id, _ in task_priorities]

    async def _optimize_by_resources(self, task_ids: List[TaskId]) -> List[TaskId]:
        """按资源需求优化执行顺序"""
        task_resources = []
        for task_id in task_ids:
            resources = await self._analyze_task_resources(task_id)
            total_resources = sum(resources.values())
            task_resources.append((task_id, total_resources))

        # 按资源需求排序（资源需求少的优先）
        task_resources.sort(key=lambda x: x[1])
        return [task_id for task_id, _ in task_resources]