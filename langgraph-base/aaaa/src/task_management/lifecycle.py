"""
任务生命周期管理 - 管理任务从创建到完成的全过程
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from enum import Enum
from dataclasses import dataclass

from ..core.types import TaskId, TaskStatus, Priority, AgentId
from ..core.exceptions import TaskError
from .task_manager import TaskManager, TaskExecution
from ..utils.logging import get_logger

logger = get_logger(__name__)


class LifecycleEvent(Enum):
    """生命周期事件"""
    CREATED = "created"
    ASSIGNED = "assigned"
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    RESUMED = "resumed"
    PAUSED = "paused"


@dataclass
class LifecycleTransition:
    """生命周期转换"""
    from_status: TaskStatus
    to_status: TaskStatus
    event: LifecycleEvent
    timestamp: datetime
    reason: Optional[str] = None
    metadata: Dict[str, Any] = None


class TaskLifecycle:
    """任务生命周期管理器"""

    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self._lifecycle_history: Dict[TaskId, List[LifecycleTransition]] = {}
        self._transition_handlers: Dict[LifecycleEvent, List[Callable]] = {}
        self._timeout_watchers: Dict[TaskId, asyncio.Task] = {}
        self._default_timeout = 3600  # 1小时

        # 定义允许的状态转换
        self._allowed_transitions = {
            TaskStatus.PENDING: {
                TaskStatus.IN_PROGRESS,
                TaskStatus.CANCELLED
            },
            TaskStatus.IN_PROGRESS: {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
                TaskStatus.PENDING  # 重新调度
            },
            TaskStatus.COMPLETED: set(),  # 终态
            TaskStatus.FAILED: {
                TaskStatus.PENDING,  # 重试
                TaskStatus.CANCELLED
            },
            TaskStatus.CANCELLED: set()  # 终态
        }

        # 注册事件处理器
        self.task_manager.add_event_handler("task_created", self._on_task_created)
        self.task_manager.add_event_handler("task_assigned", self._on_task_assigned)
        self.task_manager.add_event_handler("task_status_updated", self._on_task_status_updated)

    async def create_task(self, **kwargs) -> TaskId:
        """创建任务并记录生命周期开始"""
        task_id = await self.task_manager.create_task(**kwargs)
        await self._record_transition(
            task_id,
            TaskStatus.PENDING,
            TaskStatus.PENDING,
            LifecycleEvent.CREATED,
            reason="Task created"
        )
        return task_id

    async def start_task(self, task_id: TaskId, agent_id: AgentId = None) -> bool:
        """开始任务执行"""
        try:
            task_info = await self.task_manager.get_task_info(task_id)
            if not task_info:
                logger.error(f"Task not found: {task_id}")
                return False

            if task_info.status != TaskStatus.PENDING:
                logger.warning(f"Task not in PENDING status: {task_id} ({task_info.status})")
                return False

            # 分配任务（如果指定了智能体）
            if agent_id:
                success = await self.task_manager.assign_task(task_id, agent_id)
                if not success:
                    return False

            # 更新状态为进行中
            success = await self.task_manager.update_task_status(
                task_id,
                TaskStatus.IN_PROGRESS,
                progress=0.0
            )

            if success:
                await self._record_transition(
                    task_id,
                    TaskStatus.PENDING,
                    TaskStatus.IN_PROGRESS,
                    LifecycleEvent.STARTED,
                    reason=f"Task started by agent {agent_id or 'auto'}"
                )

                # 启动超时监控
                await self._start_timeout_watcher(task_id)

            return success

        except Exception as e:
            logger.error(f"Failed to start task {task_id}: {e}")
            return False

    async def complete_task(self, task_id: TaskId, result: Any = None) -> bool:
        """完成任务"""
        try:
            success = await self.task_manager.update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                progress=100.0,
                result=result
            )

            if success:
                await self._record_transition(
                    task_id,
                    TaskStatus.IN_PROGRESS,
                    TaskStatus.COMPLETED,
                    LifecycleEvent.COMPLETED,
                    reason="Task completed successfully"
                )

                # 停止超时监控
                await self._stop_timeout_watcher(task_id)

            return success

        except Exception as e:
            logger.error(f"Failed to complete task {task_id}: {e}")
            return False

    async def fail_task(self, task_id: TaskId, error: str, retryable: bool = True) -> bool:
        """标记任务失败"""
        try:
            success = await self.task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=error
            )

            if success:
                await self._record_transition(
                    task_id,
                    TaskStatus.IN_PROGRESS,
                    TaskStatus.FAILED,
                    LifecycleEvent.FAILED,
                    reason=error,
                    metadata={"retryable": retryable}
                )

                # 停止超时监控
                await self._stop_timeout_watcher(task_id)

                # 如果可重试，自动重新调度
                if retryable:
                    await self._schedule_retry(task_id)

            return success

        except Exception as e:
            logger.error(f"Failed to fail task {task_id}: {e}")
            return False

    async def cancel_task(self, task_id: TaskId, reason: str = "Cancelled by user") -> bool:
        """取消任务"""
        try:
            task_info = await self.task_manager.get_task_info(task_id)
            if not task_info:
                return False

            old_status = task_info.status
            new_status = TaskStatus.CANCELLED

            # 检查是否可以取消
            if not self._can_transition(old_status, new_status):
                logger.warning(f"Cannot cancel task {task_id} from status {old_status}")
                return False

            success = await self.task_manager.update_task_status(task_id, new_status)

            if success:
                await self._record_transition(
                    task_id,
                    old_status,
                    new_status,
                    LifecycleEvent.CANCELLED,
                    reason=reason
                )

                # 停止超时监控
                await self._stop_timeout_watcher(task_id)

            return success

        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False

    async def pause_task(self, task_id: TaskId, reason: str = "Paused by user") -> bool:
        """暂停任务"""
        try:
            # 暂停是 IN_PROGRESS 状态的特殊标记
            success = await self.task_manager.update_task_status(
                task_id,
                TaskStatus.IN_PROGRESS,
                metadata={"paused": True, "pause_reason": reason}
            )

            if success:
                await self._record_transition(
                    task_id,
                    TaskStatus.IN_PROGRESS,
                    TaskStatus.IN_PROGRESS,
                    LifecycleEvent.PAUSED,
                    reason=reason
                )

            return success

        except Exception as e:
            logger.error(f"Failed to pause task {task_id}: {e}")
            return False

    async def resume_task(self, task_id: TaskId) -> bool:
        """恢复任务"""
        try:
            task_info = await self.task_manager.get_task_info(task_id)
            if not task_info:
                return False

            # 检查是否处于暂停状态
            if not task_info.metadata.get("paused", False):
                logger.warning(f"Task {task_id} is not paused")
                return False

            # 清除暂停标记
            success = await self.task_manager.update_task_status(
                task_id,
                TaskStatus.IN_PROGRESS,
                metadata={"paused": False, "pause_reason": None}
            )

            if success:
                await self._record_transition(
                    task_id,
                    TaskStatus.IN_PROGRESS,
                    TaskStatus.IN_PROGRESS,
                    LifecycleEvent.RESUMED,
                    reason="Task resumed"
                )

            return success

        except Exception as e:
            logger.error(f"Failed to resume task {task_id}: {e}")
            return False

    async def update_progress(self, task_id: TaskId, progress: float) -> bool:
        """更新任务进度"""
        try:
            if not (0 <= progress <= 100):
                raise ValueError("Progress must be between 0 and 100")

            task_info = await self.task_manager.get_task_info(task_id)
            if not task_info or task_info.status != TaskStatus.IN_PROGRESS:
                logger.warning(f"Cannot update progress for task {task_id} (status: {task_info.status if task_info else 'unknown'})")
                return False

            success = await self.task_manager.update_task_status(
                task_id,
                TaskStatus.IN_PROGRESS,
                progress=progress
            )

            if success:
                logger.debug(f"Task progress updated: {task_id} -> {progress}%")

            return success

        except Exception as e:
            logger.error(f"Failed to update progress for task {task_id}: {e}")
            return False

    async def set_timeout(self, task_id: TaskId, timeout_seconds: int) -> bool:
        """设置任务超时"""
        try:
            task_info = await self.task_manager.get_task_info(task_id)
            if not task_info:
                return False

            if task_info.status != TaskStatus.IN_PROGRESS:
                logger.warning(f"Cannot set timeout for task {task_id} (status: {task_info.status})")
                return False

            # 重新启动超时监控
            await self._stop_timeout_watcher(task_id)
            await self._start_timeout_watcher(task_id, timeout_seconds)

            logger.info(f"Timeout set for task {task_id}: {timeout_seconds} seconds")
            return True

        except Exception as e:
            logger.error(f"Failed to set timeout for task {task_id}: {e}")
            return False

    def get_lifecycle_history(self, task_id: TaskId) -> List[LifecycleTransition]:
        """获取任务生命周期历史"""
        return self._lifecycle_history.get(task_id, [])

    async def get_task_duration(self, task_id: TaskId) -> Optional[float]:
        """获取任务执行时长（秒）"""
        history = self.get_lifecycle_history(task_id)
        if not history:
            return None

        start_time = None
        end_time = None

        for transition in history:
            if transition.event == LifecycleEvent.STARTED:
                start_time = transition.timestamp
            elif transition.event in [LifecycleEvent.COMPLETED, LifecycleEvent.FAILED, LifecycleEvent.CANCELLED]:
                end_time = transition.timestamp

        if start_time and end_time:
            return (end_time - start_time).total_seconds()
        elif start_time:
            return (datetime.now() - start_time).total_seconds()

        return None

    def add_transition_handler(self, event: LifecycleEvent, handler: Callable) -> None:
        """添加转换处理器"""
        if event not in self._transition_handlers:
            self._transition_handlers[event] = []
        self._transition_handlers[event].append(handler)

    def remove_transition_handler(self, event: LifecycleEvent, handler: Callable) -> None:
        """移除转换处理器"""
        if event in self._transition_handlers:
            if handler in self._transition_handlers[event]:
                self._transition_handlers[event].remove(handler)

    # 私有方法
    async def _record_transition(
        self,
        task_id: TaskId,
        from_status: TaskStatus,
        to_status: TaskStatus,
        event: LifecycleEvent,
        reason: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """记录生命周期转换"""
        transition = LifecycleTransition(
            from_status=from_status,
            to_status=to_status,
            event=event,
            timestamp=datetime.now(),
            reason=reason,
            metadata=metadata or {}
        )

        if task_id not in self._lifecycle_history:
            self._lifecycle_history[task_id] = []

        self._lifecycle_history[task_id].append(transition)

        # 触发处理器
        await self._trigger_transition_handlers(event, transition)

        logger.debug(f"Lifecycle transition recorded: {task_id} {from_status} -> {to_status} ({event.value})")

    async def _trigger_transition_handlers(self, event: LifecycleEvent, transition: LifecycleTransition) -> None:
        """触发转换处理器"""
        if event in self._transition_handlers:
            for handler in self._transition_handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(transition)
                    else:
                        handler(transition)
                except Exception as e:
                    logger.error(f"Transition handler error: {e}")

    async def _start_timeout_watcher(self, task_id: TaskId, timeout: Optional[int] = None) -> None:
        """启动超时监控"""
        timeout = timeout or self._default_timeout

        async def timeout_watcher():
            try:
                await asyncio.sleep(timeout)

                # 检查任务是否仍在进行中
                task_info = await self.task_manager.get_task_info(task_id)
                if task_info and task_info.status == TaskStatus.IN_PROGRESS:
                    logger.warning(f"Task {task_id} timed out after {timeout} seconds")
                    await self.fail_task(task_id, f"Task timed out after {timeout} seconds", retryable=False)

                    # 记录超时事件
                    await self._record_transition(
                        task_id,
                        TaskStatus.IN_PROGRESS,
                        TaskStatus.FAILED,
                        LifecycleEvent.TIMEOUT,
                        reason=f"Task timed out after {timeout} seconds"
                    )

            except asyncio.CancelledError:
                logger.debug(f"Timeout watcher cancelled for task {task_id}")

        watcher_task = asyncio.create_task(timeout_watcher())
        self._timeout_watchers[task_id] = watcher_task

    async def _stop_timeout_watcher(self, task_id: TaskId) -> None:
        """停止超时监控"""
        if task_id in self._timeout_watchers:
            watcher_task = self._timeout_watchers.pop(task_id)
            watcher_task.cancel()
            try:
                await watcher_task
            except asyncio.CancelledError:
                pass

    async def _schedule_retry(self, task_id: TaskId) -> None:
        """调度重试"""
        try:
            # 重置任务状态为 PENDING
            await self.task_manager.update_task_status(task_id, TaskStatus.PENDING)

            await self._record_transition(
                task_id,
                TaskStatus.FAILED,
                TaskStatus.PENDING,
                LifecycleEvent.RESUMED,
                reason="Task scheduled for retry"
            )

            logger.info(f"Task {task_id} scheduled for retry")

        except Exception as e:
            logger.error(f"Failed to schedule retry for task {task_id}: {e}")

    def _can_transition(self, from_status: TaskStatus, to_status: TaskStatus) -> bool:
        """检查状态转换是否允许"""
        allowed = self._allowed_transitions.get(from_status, set())
        return to_status in allowed

    # 事件处理器
    async def _on_task_created(self, data: Dict[str, Any]) -> None:
        """任务创建事件处理器"""
        task_id = data["task_id"]
        logger.debug(f"Task created event: {task_id}")

    async def _on_task_assigned(self, data: Dict[str, Any]) -> None:
        """任务分配事件处理器"""
        task_id = data["task_id"]
        agent_id = data["agent_id"]
        logger.debug(f"Task assigned event: {task_id} -> {agent_id}")

    async def _on_task_status_updated(self, data: Dict[str, Any]) -> None:
        """任务状态更新事件处理器"""
        task_id = data["task_id"]
        new_status = data["new_status"]
        logger.debug(f"Task status updated event: {task_id} -> {new_status}")