"""工作流检查点和恢复机制"""

import logging
import json
import sqlite3
import pickle
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from abc import ABC, abstractmethod
import threading
from contextlib import contextmanager

from ..core.state import LangGraphTaskState, WorkflowPhase
from dataclasses import dataclass
from ..legacy.task_state import TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class CheckpointData:
    """检查点数据"""
    checkpoint_id: str
    timestamp: datetime
    state: LangGraphTaskState
    metadata: Dict[str, Any]


def create_checkpoint(
    state: LangGraphTaskState,
    metadata: Optional[Dict[str, Any]] = None
) -> CheckpointData:
    """创建检查点数据"""
    import uuid
    
    checkpoint_id = f"cp_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
    
    return CheckpointData(
        checkpoint_id=checkpoint_id,
        timestamp=datetime.now(),
        state=state,
        metadata=metadata or {}
    )


class CheckpointStorage(ABC):
    """检查点存储抽象基类"""
    
    @abstractmethod
    async def save_checkpoint(
        self, 
        thread_id: str, 
        checkpoint_data: CheckpointData
    ) -> bool:
        """保存检查点"""
        pass
    
    @abstractmethod
    async def load_checkpoint(
        self, 
        thread_id: str, 
        checkpoint_id: Optional[str] = None
    ) -> Optional[CheckpointData]:
        """加载检查点"""
        pass
    
    @abstractmethod
    async def list_checkpoints(
        self, 
        thread_id: str, 
        limit: int = 10
    ) -> List[CheckpointData]:
        """列出检查点"""
        pass
    
    @abstractmethod
    async def delete_checkpoint(
        self, 
        thread_id: str, 
        checkpoint_id: str
    ) -> bool:
        """删除检查点"""
        pass
    
    @abstractmethod
    async def cleanup_old_checkpoints(
        self, 
        older_than: datetime
    ) -> int:
        """清理旧检查点"""
        pass


class MemoryCheckpointStorage(CheckpointStorage):
    """内存检查点存储"""
    
    def __init__(self):
        self.checkpoints: Dict[str, List[CheckpointData]] = {}
        self.lock = threading.RLock()
    
    async def save_checkpoint(
        self, 
        thread_id: str, 
        checkpoint_data: CheckpointData
    ) -> bool:
        """保存检查点到内存"""
        try:
            with self.lock:
                if thread_id not in self.checkpoints:
                    self.checkpoints[thread_id] = []
                
                # 添加新检查点
                self.checkpoints[thread_id].append(checkpoint_data)
                
                # 保持最新的10个检查点
                if len(self.checkpoints[thread_id]) > 10:
                    self.checkpoints[thread_id] = self.checkpoints[thread_id][-10:]
                
                logger.debug(f"保存检查点到内存: {thread_id}/{checkpoint_data.checkpoint_id}")
                return True
                
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
            return False
    
    async def load_checkpoint(
        self, 
        thread_id: str, 
        checkpoint_id: Optional[str] = None
    ) -> Optional[CheckpointData]:
        """从内存加载检查点"""
        try:
            with self.lock:
                if thread_id not in self.checkpoints:
                    return None
                
                checkpoints = self.checkpoints[thread_id]
                if not checkpoints:
                    return None
                
                if checkpoint_id is None:
                    # 返回最新的检查点
                    return checkpoints[-1]
                
                # 查找指定的检查点
                for checkpoint in reversed(checkpoints):
                    if checkpoint.checkpoint_id == checkpoint_id:
                        return checkpoint
                
                return None
                
        except Exception as e:
            logger.error(f"加载检查点失败: {e}")
            return None
    
    async def list_checkpoints(
        self, 
        thread_id: str, 
        limit: int = 10
    ) -> List[CheckpointData]:
        """列出检查点"""
        try:
            with self.lock:
                if thread_id not in self.checkpoints:
                    return []
                
                checkpoints = self.checkpoints[thread_id]
                return list(reversed(checkpoints[-limit:]))
                
        except Exception as e:
            logger.error(f"列出检查点失败: {e}")
            return []
    
    async def delete_checkpoint(
        self, 
        thread_id: str, 
        checkpoint_id: str
    ) -> bool:
        """删除检查点"""
        try:
            with self.lock:
                if thread_id not in self.checkpoints:
                    return False
                
                checkpoints = self.checkpoints[thread_id]
                for i, checkpoint in enumerate(checkpoints):
                    if checkpoint.checkpoint_id == checkpoint_id:
                        checkpoints.pop(i)
                        logger.debug(f"删除检查点: {thread_id}/{checkpoint_id}")
                        return True
                
                return False
                
        except Exception as e:
            logger.error(f"删除检查点失败: {e}")
            return False
    
    async def cleanup_old_checkpoints(
        self, 
        older_than: datetime
    ) -> int:
        """清理旧检查点"""
        try:
            cleaned_count = 0
            with self.lock:
                for thread_id, checkpoints in self.checkpoints.items():
                    original_count = len(checkpoints)
                    self.checkpoints[thread_id] = [
                        cp for cp in checkpoints 
                        if cp.timestamp > older_than
                    ]
                    cleaned_count += original_count - len(self.checkpoints[thread_id])
                
                logger.info(f"清理了 {cleaned_count} 个旧检查点")
                return cleaned_count
                
        except Exception as e:
            logger.error(f"清理检查点失败: {e}")
            return 0


class SQLiteCheckpointStorage(CheckpointStorage):
    """SQLite检查点存储"""
    
    def __init__(self, db_path: str = "checkpoints.db"):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        thread_id TEXT NOT NULL,
                        checkpoint_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        state_data BLOB NOT NULL,
                        metadata TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(thread_id, checkpoint_id)
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_thread_timestamp 
                    ON checkpoints(thread_id, timestamp DESC)
                """)
                
                conn.commit()
                logger.info(f"SQLite检查点存储初始化完成: {self.db_path}")
                
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
            raise
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()
    
    async def save_checkpoint(
        self, 
        thread_id: str, 
        checkpoint_data: CheckpointData
    ) -> bool:
        """保存检查点到SQLite"""
        try:
            with self.lock:
                with self._get_connection() as conn:
                    # 序列化状态数据
                    state_blob = pickle.dumps(checkpoint_data.state)
                    metadata_json = json.dumps(checkpoint_data.metadata)
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO checkpoints 
                        (thread_id, checkpoint_id, timestamp, state_data, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        thread_id,
                        checkpoint_data.checkpoint_id,
                        checkpoint_data.timestamp.isoformat(),
                        state_blob,
                        metadata_json
                    ))
                    
                    conn.commit()
                    
                    # 保持每个线程最多50个检查点
                    conn.execute("""
                        DELETE FROM checkpoints 
                        WHERE thread_id = ? AND id NOT IN (
                            SELECT id FROM checkpoints 
                            WHERE thread_id = ? 
                            ORDER BY timestamp DESC 
                            LIMIT 50
                        )
                    """, (thread_id, thread_id))
                    
                    conn.commit()
                    
                    logger.debug(f"保存检查点到SQLite: {thread_id}/{checkpoint_data.checkpoint_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
            return False
    
    async def load_checkpoint(
        self, 
        thread_id: str, 
        checkpoint_id: Optional[str] = None
    ) -> Optional[CheckpointData]:
        """从SQLite加载检查点"""
        try:
            with self.lock:
                with self._get_connection() as conn:
                    if checkpoint_id is None:
                        # 加载最新检查点
                        cursor = conn.execute("""
                            SELECT checkpoint_id, timestamp, state_data, metadata
                            FROM checkpoints 
                            WHERE thread_id = ? 
                            ORDER BY timestamp DESC 
                            LIMIT 1
                        """, (thread_id,))
                    else:
                        # 加载指定检查点
                        cursor = conn.execute("""
                            SELECT checkpoint_id, timestamp, state_data, metadata
                            FROM checkpoints 
                            WHERE thread_id = ? AND checkpoint_id = ?
                        """, (thread_id, checkpoint_id))
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    # 反序列化数据
                    state = pickle.loads(row['state_data'])
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    timestamp = datetime.fromisoformat(row['timestamp'])
                    
                    return CheckpointData(
                        checkpoint_id=row['checkpoint_id'],
                        timestamp=timestamp,
                        state=state,
                        metadata=metadata
                    )
                    
        except Exception as e:
            logger.error(f"加载检查点失败: {e}")
            return None
    
    async def list_checkpoints(
        self, 
        thread_id: str, 
        limit: int = 10
    ) -> List[CheckpointData]:
        """列出检查点"""
        try:
            with self.lock:
                with self._get_connection() as conn:
                    cursor = conn.execute("""
                        SELECT checkpoint_id, timestamp, metadata
                        FROM checkpoints 
                        WHERE thread_id = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (thread_id, limit))
                    
                    checkpoints = []
                    for row in cursor.fetchall():
                        metadata = json.loads(row['metadata']) if row['metadata'] else {}
                        timestamp = datetime.fromisoformat(row['timestamp'])
                        
                        # 创建轻量级检查点数据（不包含完整状态）
                        checkpoint = CheckpointData(
                            checkpoint_id=row['checkpoint_id'],
                            timestamp=timestamp,
                            state={},  # 空状态，节省内存
                            metadata=metadata
                        )
                        checkpoints.append(checkpoint)
                    
                    return checkpoints
                    
        except Exception as e:
            logger.error(f"列出检查点失败: {e}")
            return []
    
    async def delete_checkpoint(
        self, 
        thread_id: str, 
        checkpoint_id: str
    ) -> bool:
        """删除检查点"""
        try:
            with self.lock:
                with self._get_connection() as conn:
                    cursor = conn.execute("""
                        DELETE FROM checkpoints 
                        WHERE thread_id = ? AND checkpoint_id = ?
                    """, (thread_id, checkpoint_id))
                    
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        logger.debug(f"删除检查点: {thread_id}/{checkpoint_id}")
                        return True
                    
                    return False
                    
        except Exception as e:
            logger.error(f"删除检查点失败: {e}")
            return False
    
    async def cleanup_old_checkpoints(
        self, 
        older_than: datetime
    ) -> int:
        """清理旧检查点"""
        try:
            with self.lock:
                with self._get_connection() as conn:
                    cursor = conn.execute("""
                        DELETE FROM checkpoints 
                        WHERE timestamp < ?
                    """, (older_than.isoformat(),))
                    
                    conn.commit()
                    
                    cleaned_count = cursor.rowcount
                    logger.info(f"清理了 {cleaned_count} 个旧检查点")
                    return cleaned_count
                    
        except Exception as e:
            logger.error(f"清理检查点失败: {e}")
            return 0


class CheckpointManager:
    """检查点管理器"""
    
    def __init__(
        self,
        storage: Optional[CheckpointStorage] = None,
        auto_checkpoint_interval: int = 300,  # 5分钟
        max_checkpoints_per_thread: int = 50,
        cleanup_interval: int = 86400  # 24小时
    ):
        self.storage = storage or MemoryCheckpointStorage()
        self.auto_checkpoint_interval = auto_checkpoint_interval
        self.max_checkpoints_per_thread = max_checkpoints_per_thread
        self.cleanup_interval = cleanup_interval
        
        # 运行时状态
        self.active_threads: Dict[str, Dict[str, Any]] = {}
        self.last_checkpoint_times: Dict[str, datetime] = {}
        self.paused_threads: Dict[str, CheckpointData] = {}
        
        # 统计信息
        self.checkpoint_stats = {
            "total_checkpoints": 0,
            "successful_saves": 0,
            "failed_saves": 0,
            "successful_loads": 0,
            "failed_loads": 0,
            "recovery_operations": 0
        }
        
        logger.info("检查点管理器初始化完成")
    
    async def create_checkpoint(
        self,
        thread_id: str,
        state: LangGraphTaskState,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """创建检查点"""
        try:
            # 创建检查点数据
            checkpoint_data = create_checkpoint(
                state=state,
                metadata=metadata or {}
            )
            
            # 保存检查点
            success = await self.storage.save_checkpoint(thread_id, checkpoint_data)
            
            if success:
                self.last_checkpoint_times[thread_id] = datetime.now()
                self.checkpoint_stats["total_checkpoints"] += 1
                self.checkpoint_stats["successful_saves"] += 1
                
                logger.info(f"创建检查点成功: {thread_id}/{checkpoint_data.checkpoint_id}")
                return checkpoint_data.checkpoint_id
            else:
                self.checkpoint_stats["failed_saves"] += 1
                logger.error(f"创建检查点失败: {thread_id}")
                return None
                
        except Exception as e:
            self.checkpoint_stats["failed_saves"] += 1
            logger.error(f"创建检查点异常: {thread_id}, {e}")
            return None
    
    async def load_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[LangGraphTaskState]:
        """加载检查点"""
        try:
            checkpoint_data = await self.storage.load_checkpoint(thread_id, checkpoint_id)
            
            if checkpoint_data:
                self.checkpoint_stats["successful_loads"] += 1
                logger.info(f"加载检查点成功: {thread_id}/{checkpoint_data.checkpoint_id}")
                return checkpoint_data.state
            else:
                self.checkpoint_stats["failed_loads"] += 1
                logger.warning(f"检查点不存在: {thread_id}/{checkpoint_id}")
                return None
                
        except Exception as e:
            self.checkpoint_stats["failed_loads"] += 1
            logger.error(f"加载检查点异常: {thread_id}, {e}")
            return None
    
    async def pause_execution(
        self,
        thread_id: str,
        state: LangGraphTaskState
    ) -> bool:
        """暂停执行并保存检查点"""
        try:
            # 创建暂停检查点
            checkpoint_id = await self.create_checkpoint(
                thread_id=thread_id,
                state=state,
                metadata={
                    "operation": "pause",
                    "paused_at": datetime.now().isoformat(),
                    "phase": state["workflow_context"]["current_phase"].value
                }
            )
            
            if checkpoint_id:
                # 记录暂停状态
                checkpoint_data = await self.storage.load_checkpoint(thread_id, checkpoint_id)
                if checkpoint_data:
                    self.paused_threads[thread_id] = checkpoint_data
                    logger.info(f"执行已暂停: {thread_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"暂停执行失败: {thread_id}, {e}")
            return False
    
    async def resume_execution(
        self,
        thread_id: str
    ) -> Optional[LangGraphTaskState]:
        """恢复执行"""
        try:
            # 检查是否有暂停的线程
            if thread_id in self.paused_threads:
                checkpoint_data = self.paused_threads.pop(thread_id)
                state = checkpoint_data.state
                
                # 更新恢复信息
                state["workflow_context"]["execution_metadata"]["resumed_at"] = datetime.now().isoformat()
                state["workflow_context"]["execution_metadata"]["resume_from_checkpoint"] = checkpoint_data.checkpoint_id
                
                self.checkpoint_stats["recovery_operations"] += 1
                logger.info(f"从暂停状态恢复执行: {thread_id}")
                return state
            
            # 从最新检查点恢复
            state = await self.load_checkpoint(thread_id)
            if state:
                state["workflow_context"]["execution_metadata"]["resumed_at"] = datetime.now().isoformat()
                self.checkpoint_stats["recovery_operations"] += 1
                logger.info(f"从检查点恢复执行: {thread_id}")
                return state
            
            logger.warning(f"没有找到可恢复的检查点: {thread_id}")
            return None
            
        except Exception as e:
            logger.error(f"恢复执行失败: {thread_id}, {e}")
            return None
    
    async def rollback_to_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str
    ) -> Optional[LangGraphTaskState]:
        """回滚到指定检查点"""
        try:
            state = await self.load_checkpoint(thread_id, checkpoint_id)
            
            if state:
                # 添加回滚信息
                state["workflow_context"]["execution_metadata"]["rolled_back_at"] = datetime.now().isoformat()
                state["workflow_context"]["execution_metadata"]["rollback_to_checkpoint"] = checkpoint_id
                
                self.checkpoint_stats["recovery_operations"] += 1
                logger.info(f"回滚到检查点: {thread_id}/{checkpoint_id}")
                return state
            
            return None
            
        except Exception as e:
            logger.error(f"回滚失败: {thread_id}, {e}")
            return None
    
    async def should_create_checkpoint(
        self,
        thread_id: str,
        state: LangGraphTaskState
    ) -> bool:
        """判断是否应该创建检查点"""
        try:
            # 检查工作流阶段变化
            current_phase = state["workflow_context"]["current_phase"]
            if thread_id in self.active_threads:
                last_phase = self.active_threads[thread_id].get("last_phase")
                if last_phase != current_phase:
                    return True
            
            # 检查任务状态变化
            task_status = state["task_state"]["status"]
            if thread_id in self.active_threads:
                last_status = self.active_threads[thread_id].get("last_status")
                if last_status != task_status:
                    return True
            
            # 检查智能体结果更新
            agent_results = state["workflow_context"]["agent_results"]
            if thread_id in self.active_threads:
                last_agent_count = self.active_threads[thread_id].get("agent_count", 0)
                current_agent_count = len(agent_results)
                if current_agent_count > last_agent_count:
                    return True
            
            # 检查时间间隔
            last_checkpoint = self.last_checkpoint_times.get(thread_id)
            if last_checkpoint:
                elapsed = (datetime.now() - last_checkpoint).total_seconds()
                return elapsed >= self.auto_checkpoint_interval
            
            # 没有历史记录，应该创建检查点
            return True
            
        except Exception as e:
            logger.error(f"检查点判断失败: {thread_id}, {e}")
            return False
    
    async def update_thread_state(
        self,
        thread_id: str,
        state: LangGraphTaskState
    ) -> None:
        """更新线程状态"""
        try:
            self.active_threads[thread_id] = {
                "last_phase": state["workflow_context"]["current_phase"],
                "last_status": state["task_state"]["status"],
                "agent_count": len(state["workflow_context"]["agent_results"]),
                "last_update": datetime.now()
            }
        except Exception as e:
            logger.error(f"更新线程状态失败: {thread_id}, {e}")
    
    async def list_thread_checkpoints(
        self,
        thread_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """列出线程的检查点"""
        try:
            checkpoints = await self.storage.list_checkpoints(thread_id, limit)
            
            return [
                {
                    "checkpoint_id": cp.checkpoint_id,
                    "timestamp": cp.timestamp.isoformat(),
                    "metadata": cp.metadata
                }
                for cp in checkpoints
            ]
            
        except Exception as e:
            logger.error(f"列出检查点失败: {thread_id}, {e}")
            return []
    
    async def delete_thread_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str
    ) -> bool:
        """删除线程检查点"""
        try:
            success = await self.storage.delete_checkpoint(thread_id, checkpoint_id)
            if success:
                logger.info(f"删除检查点: {thread_id}/{checkpoint_id}")
            return success
            
        except Exception as e:
            logger.error(f"删除检查点失败: {thread_id}/{checkpoint_id}, {e}")
            return False
    
    async def cleanup_old_checkpoints(
        self,
        days_old: int = 7
    ) -> int:
        """清理旧检查点"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_old)
            cleaned_count = await self.storage.cleanup_old_checkpoints(cutoff_time)
            
            logger.info(f"清理了 {cleaned_count} 个超过 {days_old} 天的检查点")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理检查点失败: {e}")
            return 0
    
    def get_checkpoint_statistics(self) -> Dict[str, Any]:
        """获取检查点统计信息"""
        return {
            **self.checkpoint_stats,
            "active_threads": len(self.active_threads),
            "paused_threads": len(self.paused_threads),
            "success_rate": (
                self.checkpoint_stats["successful_saves"] / 
                max(1, self.checkpoint_stats["total_checkpoints"])
            ),
            "load_success_rate": (
                self.checkpoint_stats["successful_loads"] / 
                max(1, self.checkpoint_stats["successful_loads"] + self.checkpoint_stats["failed_loads"])
            )
        }
    
    def is_thread_paused(self, thread_id: str) -> bool:
        """检查线程是否暂停"""
        return thread_id in self.paused_threads
    
    def get_paused_threads(self) -> List[str]:
        """获取所有暂停的线程"""
        return list(self.paused_threads.keys())