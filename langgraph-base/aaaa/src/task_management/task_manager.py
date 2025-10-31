"""
任务管理器 - 负责任务的创建、分配、跟踪和协调
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

from ..core.types import (
    TaskId, AgentId, TaskInfo, TaskStatus, Priority,
    TaskDependency, AgentInfo, ExecutionMode
)
from ..core.exceptions import TaskError, DependencyResolutionError
from ..core.state import TaskState
from ..utils.logging import get_logger

logger = get_logger(__name__)




@dataclass
class TaskExecution:
    """任务执行记录"""
    task_id: TaskId
    assigned_agent: AgentId
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.IN_PROGRESS
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_log: List[str] = field(default_factory=list)
    resource_usage: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyGraph:
    """依赖关系图"""
    nodes: Set[TaskId] = field(default_factory=set)
    edges: Dict[TaskId, Set[TaskId]] = field(default_factory=dict)  # task_id -> dependencies
    reverse_edges: Dict[TaskId, Set[TaskId]] = field(default_factory=dict)  # task_id -> dependents

    def add_node(self, task_id: TaskId) -> None:
        """添加节点"""
        self.nodes.add(task_id)
        if task_id not in self.edges:
            self.edges[task_id] = set()
        if task_id not in self.reverse_edges:
            self.reverse_edges[task_id] = set()

    def add_edge(self, from_task: TaskId, to_task: TaskId) -> None:
        """添加依赖边 (to_task depends on from_task)"""
        self.add_node(from_task)
        self.add_node(to_task)

        self.edges[to_task].add(from_task)
        self.reverse_edges[from_task].add(to_task)

    def get_dependencies(self, task_id: TaskId) -> Set[TaskId]:
        """获取任务的依赖"""
        return self.edges.get(task_id, set())

    def get_dependents(self, task_id: TaskId) -> Set[TaskId]:
        """获取依赖此任务的任务"""
        return self.reverse_edges.get(task_id, set())

    def get_ready_tasks(self, completed_tasks: Set[TaskId]) -> List[TaskId]:
        """获取可以执行的任务（依赖已完成）"""
        ready_tasks = []
        for task_id in self.nodes:
            if task_id in completed_tasks:
                continue

            dependencies = self.get_dependencies(task_id)
            if dependencies.issubset(completed_tasks):
                ready_tasks.append(task_id)

        return ready_tasks

    def detect_cycles(self) -> List[List[TaskId]]:
        """检测循环依赖"""
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node: TaskId, path: List[TaskId]) -> bool:
            if node in rec_stack:
                # 找到循环
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return True

            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.edges.get(node, set()):
                if dfs(neighbor, path.copy()):
                    return True

            rec_stack.remove(node)
            return False

        for node in self.nodes:
            if node not in visited:
                dfs(node, [])

        return cycles


class TaskManager:
    """任务管理器 - 核心任务协调和管理"""

    def __init__(self):
        # 任务存储
        self._tasks: Dict[TaskId, TaskInfo] = {}
        self._task_states: Dict[TaskId, TaskState] = {}
        self._task_executions: Dict[TaskId, TaskExecution] = {}

        # 依赖关系管理
        self._dependency_graph = DependencyGraph()
        self._execution_groups: Dict[str, Set[TaskId]] = {}  # 执行组

        # 状态跟踪
        self._completed_tasks: Set[TaskId] = set()
        self._failed_tasks: Set[TaskId] = set()
        self._running_tasks: Set[TaskId] = set()

        # 调度器
        self._scheduler_running = False
        self._scheduler_task: Optional[asyncio.Task] = None

        # 事件处理器
        self._event_handlers: Dict[str, List[Callable]] = {}

        # 统计信息
        self._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "running_tasks": 0,
            "average_execution_time": 0.0
        }

    async def start(self) -> None:
        """启动任务管理器"""
        if self._scheduler_running:
            return

        self._scheduler_running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("TaskManager started")

    async def stop(self) -> None:
        """停止任务管理器"""
        self._scheduler_running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        logger.info("TaskManager stopped")

    async def create_task(
        self,
        title: str,
        description: str,
        priority: Priority = Priority.MEDIUM,
        dependencies: List[TaskId] = None,
        execution_group: str = None,
        metadata: Dict[str, Any] = None
    ) -> TaskId:
        """创建新任务"""
        try:
            task_id = str(uuid.uuid4())

            # 创建任务信息
            task_info = TaskInfo(
                task_id=task_id,
                title=title,
                description=description,
                status=TaskStatus.PENDING,
                priority=priority,
                dependencies=dependencies or [],
                created_at=datetime.now(),
                metadata=metadata or {}
            )

            # 创建任务状态
            task_state = TaskState(
                task_id=task_id,
                title=title,
                description=description,
                status=TaskStatus.PENDING,
                priority=priority.value,
                dependencies=dependencies or [],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            # 存储任务
            self._tasks[task_id] = task_info
            self._task_states[task_id] = task_state

            # 更新依赖图
            self._dependency_graph.add_node(task_id)
            for dep_id in dependencies or []:
                self._dependency_graph.add_edge(dep_id, task_id)

            # 添加到执行组
            if execution_group:
                if execution_group not in self._execution_groups:
                    self._execution_groups[execution_group] = set()
                self._execution_groups[execution_group].add(task_id)

            # 更新统计
            self._stats["total_tasks"] += 1

            # 触发事件
            await self._trigger_event("task_created", {
                "task_id": task_id,
                "task_info": task_info
            })

            logger.info(f"Task created: {task_id} - {title}")
            return task_id

        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise TaskError(f"Task creation failed: {str(e)}")

    async def update_task_status(
        self,
        task_id: TaskId,
        status: TaskStatus,
        progress: float = None,
        result: Any = None,
        error: str = None
    ) -> bool:
        """更新任务状态"""
        try:
            if task_id not in self._tasks:
                raise TaskError(f"Task not found: {task_id}")

            task_info = self._tasks[task_id]
            task_state = self._task_states[task_id]

            # 更新状态
            old_status = task_info.status
            task_info.status = status
            task_state.status = status
            task_info.updated_at = datetime.now()
            task_state.updated_at = datetime.now()

            # 更新进度和结果
            if progress is not None:
                task_state.progress = progress

            if result is not None:
                task_state.result = result
                task_info.metadata["result"] = result

            if error is not None:
                task_state.error = error
                task_info.metadata["error"] = error

            # 更新执行记录
            if task_id in self._task_executions:
                execution = self._task_executions[task_id]
                execution.status = status
                if result is not None:
                    execution.result = result
                if error is not None:
                    execution.error = error
                if progress is not None:
                    execution.progress = progress

                if status == TaskStatus.COMPLETED:
                    execution.completed_at = datetime.now()
                elif status == TaskStatus.FAILED:
                    execution.completed_at = datetime.now()

            # 更新状态跟踪
            if status == TaskStatus.IN_PROGRESS:
                self._running_tasks.add(task_id)
                self._completed_tasks.discard(task_id)
                self._failed_tasks.discard(task_id)

            elif status == TaskStatus.COMPLETED:
                self._running_tasks.discard(task_id)
                self._completed_tasks.add(task_id)
                self._failed_tasks.discard(task_id)

            elif status == TaskStatus.FAILED:
                self._running_tasks.discard(task_id)
                self._failed_tasks.add(task_id)
                self._completed_tasks.discard(task_id)

            # 触发事件
            await self._trigger_event("task_status_updated", {
                "task_id": task_id,
                "old_status": old_status,
                "new_status": status,
                "progress": progress
            })

            logger.info(f"Task status updated: {task_id} -> {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            return False

    async def assign_task(
        self,
        task_id: TaskId,
        agent_id: AgentId,
        force: bool = False
    ) -> bool:
        """分配任务给智能体"""
        try:
            if task_id not in self._tasks:
                raise TaskError(f"Task not found: {task_id}")

            task_info = self._tasks[task_id]

            # 检查任务是否可分配
            if not force and task_info.status != TaskStatus.PENDING:
                logger.warning(f"Task not assignable: {task_id} (status: {task_info.status})")
                return False

            # 检查依赖是否完成
            if not force:
                incomplete_deps = [
                    dep_id for dep_id in task_info.dependencies
                    if dep_id not in self._completed_tasks
                ]
                if incomplete_deps:
                    logger.warning(f"Task dependencies not completed: {task_id} -> {incomplete_deps}")
                    return False

            # 分配任务
            task_info.assigned_agent = agent_id
            task_info.status = TaskStatus.IN_PROGRESS
            task_info.updated_at = datetime.now()

            # 创建执行记录
            execution = TaskExecution(
                task_id=task_id,
                assigned_agent=agent_id,
                started_at=datetime.now()
            )
            self._task_executions[task_id] = execution

            # 更新状态跟踪
            self._running_tasks.add(task_id)

            # 触发事件
            await self._trigger_event("task_assigned", {
                "task_id": task_id,
                "agent_id": agent_id
            })

            logger.info(f"Task assigned: {task_id} -> {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to assign task: {e}")
            return False

    async def get_ready_tasks(self, agent_id: AgentId = None) -> List[TaskInfo]:
        """获取准备执行的任务"""
        ready_tasks = []

        for task_id in self._dependency_graph.get_ready_tasks(self._completed_tasks):
            if task_id in self._tasks:
                task_info = self._tasks[task_id]

                # 检查任务状态
                if task_info.status == TaskStatus.PENDING:
                    # 检查是否指定了智能体
                    if agent_id is None or task_info.assigned_agent == agent_id:
                        ready_tasks.append(task_info)

        # 按优先级排序
        ready_tasks.sort(key=lambda t: self._priority_value(t.priority), reverse=True)
        return ready_tasks

    async def get_task_info(self, task_id: TaskId) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self._tasks.get(task_id)

    async def get_task_state(self, task_id: TaskId) -> Optional[TaskState]:
        """获取任务状态"""
        return self._task_states.get(task_id)

    async def get_execution_record(self, task_id: TaskId) -> Optional[TaskExecution]:
        """获取任务执行记录"""
        return self._task_executions.get(task_id)

    async def get_tasks_by_status(self, status: TaskStatus) -> List[TaskInfo]:
        """根据状态获取任务"""
        return [
            task for task in self._tasks.values()
            if task.status == status
        ]

    async def get_tasks_by_agent(self, agent_id: AgentId) -> List[TaskInfo]:
        """获取智能体的任务"""
        return [
            task for task in self._tasks.values()
            if task.assigned_agent == agent_id
        ]

    async def validate_dependencies(self, task_id: TaskId) -> bool:
        """验证任务依赖"""
        try:
            if task_id not in self._tasks:
                return False

            # 检查循环依赖
            cycles = self._dependency_graph.detect_cycles()
            if cycles:
                cycle_str = " -> ".join(cycles[0])
                logger.error(f"Circular dependency detected: {cycle_str}")
                return False

            # 检查依赖存在性
            task_info = self._tasks[task_id]
            for dep_id in task_info.dependencies:
                if dep_id not in self._tasks:
                    logger.error(f"Dependency not found: {dep_id} for task {task_id}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Dependency validation failed: {e}")
            return False

    async def get_dependency_graph(self) -> Dict[str, Any]:
        """获取依赖关系图"""
        return {
            "nodes": list(self._dependency_graph.nodes),
            "edges": {
                node: list(deps)
                for node, deps in self._dependency_graph.edges.items()
            },
            "execution_groups": {
                group: list(tasks)
                for group, tasks in self._execution_groups.items()
            }
        }

    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_execution_time = 0
        completed_count = 0

        for execution in self._task_executions.values():
            if execution.completed_at and execution.status == TaskStatus.COMPLETED:
                execution_time = (execution.completed_at - execution.started_at).total_seconds()
                total_execution_time += execution_time
                completed_count += 1

        avg_execution_time = total_execution_time / completed_count if completed_count > 0 else 0

        return {
            **self._stats,
            "running_tasks": len(self._running_tasks),
            "completed_tasks": len(self._completed_tasks),
            "failed_tasks": len(self._failed_tasks),
            "average_execution_time": avg_execution_time,
            "pending_tasks": len(await self.get_tasks_by_status(TaskStatus.PENDING)),
            "execution_groups": len(self._execution_groups)
        }

    async def export_tasks(self, file_path: str) -> bool:
        """导出任务数据"""
        try:
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "tasks": {
                    task_id: task_info.dict()
                    for task_id, task_info in self._tasks.items()
                },
                "dependency_graph": await self.get_dependency_graph(),
                "statistics": await self.get_statistics()
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"Tasks exported to: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export tasks: {e}")
            return False

    async def _scheduler_loop(self) -> None:
        """调度器主循环"""
        while self._scheduler_running:
            try:
                # 检查准备执行的任务
                ready_tasks = await self.get_ready_tasks()

                # 触发任务就绪事件
                if ready_tasks:
                    await self._trigger_event("tasks_ready", {
                        "tasks": ready_tasks
                    })

                await asyncio.sleep(1)  # 每秒检查一次

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(5)  # 错误时等待更长时间

    async def _trigger_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """触发事件"""
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")

    def _priority_value(self, priority: Priority) -> int:
        """获取优先级数值"""
        priority_values = {
            Priority.LOW: 1,
            Priority.MEDIUM: 2,
            Priority.HIGH: 3,
            Priority.CRITICAL: 4
        }
        return priority_values.get(priority, 2)

    # 事件处理器管理
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """添加事件处理器"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """移除事件处理器"""
        if event_type in self._event_handlers:
            if handler in self._event_handlers[event_type]:
                self._event_handlers[event_type].remove(handler)