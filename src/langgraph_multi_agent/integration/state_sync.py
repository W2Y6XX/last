"""状态同步管理器"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime
from enum import Enum
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from ..core.state import LangGraphTaskState, WorkflowPhase
from ..legacy.task_state import TaskState, TaskStatus
from .state_adapter import StateAdapter
from .message_adapter import MessageAdapter

logger = logging.getLogger(__name__)


class SyncDirection(str, Enum):
    """同步方向"""
    LANGGRAPH_TO_LEGACY = "langgraph_to_legacy"
    LEGACY_TO_LANGGRAPH = "legacy_to_langgraph"
    BIDIRECTIONAL = "bidirectional"


class SyncStatus(str, Enum):
    """同步状态"""
    IDLE = "idle"
    SYNCING = "syncing"
    ERROR = "error"
    PAUSED = "paused"


class SyncConflictResolution(str, Enum):
    """同步冲突解决策略"""
    LANGGRAPH_WINS = "langgraph_wins"
    LEGACY_WINS = "legacy_wins"
    MERGE = "merge"
    MANUAL = "manual"


class StateSyncManager:
    """状态同步管理器"""
    
    def __init__(
        self,
        sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        conflict_resolution: SyncConflictResolution = SyncConflictResolution.LANGGRAPH_WINS,
        sync_interval: float = 1.0,
        max_workers: int = 4
    ):
        self.sync_direction = sync_direction
        self.conflict_resolution = conflict_resolution
        self.sync_interval = sync_interval
        self.max_workers = max_workers
        
        # 状态管理
        self.sync_status = SyncStatus.IDLE
        self.last_sync_time = None
        self.sync_errors = []
        
        # 适配器
        self.state_adapter = StateAdapter()
        self.message_adapter = MessageAdapter()
        
        # 同步任务管理
        self.active_syncs: Dict[str, asyncio.Task] = {}
        self.sync_callbacks: Dict[str, List[Callable]] = {}
        self.sync_locks: Dict[str, threading.Lock] = {}
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 冲突记录
        self.conflicts: List[Dict[str, Any]] = []
        
        # 监听器
        self.change_listeners: Set[Callable] = set()
        
        logger.info(f"状态同步管理器初始化完成: {sync_direction.value}, 冲突解决: {conflict_resolution.value}")
    
    def register_change_listener(self, listener: Callable[[str, Any, Any], None]):
        """注册状态变更监听器"""
        self.change_listeners.add(listener)
    
    def unregister_change_listener(self, listener: Callable):
        """取消注册状态变更监听器"""
        self.change_listeners.discard(listener)
    
    def _notify_change_listeners(self, task_id: str, old_state: Any, new_state: Any):
        """通知状态变更监听器"""
        for listener in self.change_listeners:
            try:
                listener(task_id, old_state, new_state)
            except Exception as e:
                logger.warning(f"状态变更监听器执行失败: {e}")
    
    async def sync_state(
        self,
        task_id: str,
        langgraph_state: Optional[LangGraphTaskState] = None,
        legacy_state: Optional[TaskState] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """同步状态"""
        if task_id in self.active_syncs and not force:
            logger.warning(f"任务 {task_id} 正在同步中，跳过")
            return {"status": "skipped", "reason": "already_syncing"}
        
        # 获取同步锁
        if task_id not in self.sync_locks:
            self.sync_l