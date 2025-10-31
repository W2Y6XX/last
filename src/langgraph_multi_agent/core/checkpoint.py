"""检查点管理模块"""

import json
import sqlite3
import pickle
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import asdict
import uuid

from ..utils.logging import LoggerMixin
from ..utils.config import config
from .state import LangGraphTaskState, CheckpointData, WorkflowPhase


class CheckpointStorage(LoggerMixin):
    """检查点存储基类"""
    
    async def save_checkpoint(
        self,
        checkpoint_id: str,
        state: LangGraphTaskState,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """保存检查点"""
        raise NotImplementedError
    
    async def load_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[LangGraphTaskState]:
        """加载检查点"""
        raise NotImplementedError
    
    async def list_checkpoints(
        self,
        task_id: Optional[str] = None,
        limit: int = 100
    ) -> List[CheckpointData]:
        """列出检查点"""
        raise NotImplementedError
    
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        raise NotImplementedError


class MemoryCheckpointStorage(CheckpointStorage):
    """内存检查点存储"""
    
    def __init__(self):
        super().__init__()
        self.checkpoints: Dict[str, Dict[str, Any]] = {}
    
    async def save_checkpoint(
        self,
        checkpoint_id: str,
        state: LangGraphTaskState,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """保存检查点到内存"""
        try:
            checkpoint_data = {
                "checkpoint_id": checkpoint_id,
                "state": state,
                "metadata": metadata or {},
                "created_at": datetime.now(),
                "task_id": state["task_state"]["task_id"]
            }
            
            self.checkpoints[checkpoint_id] = checkpoint_data
            
            self.logger.info(
                "检查点已保存到内存",
                checkpoint_id=checkpoint_id,
                task_id=state["task_state"]["task_id"]
            )
            return True
            
        except Exception as e:
            self.logger.error("保存检查点失败", error=str(e))
            return False
    
    async def load_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[LangGraphTaskState]:
        """从内存加载检查点"""
        try:
            if checkpoint_id in self.checkpoints:
                checkpoint_data = self.checkpoints[checkpoint_id]
                self.logger.info("检查点已从内存加载", checkpoint_id=checkpoint_id)
                return checkpoint_data["state"]
            return None
            
        except Exception as e:
            self.logger.error("加载检查点失败", error=str(e))
            return None
    
    async def list_checkpoints(
        self,
        task_id: Optional[str] = None,
        limit: int = 100
    ) -> List[CheckpointData]:
        """列出内存中的检查点"""
        checkpoints = []
        
        for checkpoint_data in self.checkpoints.values():
            if task_id is None or checkpoint_data["task_id"] == task_id:
                state = checkpoint_data["state"]
                checkpoint_info = CheckpointData(
                    checkpoint_id=checkpoint_data["checkpoint_id"],
                    created_at=checkpoint_data["created_at"],
                    workflow_phase=state["workflow_context"]["current_phase"],
                    resumable=True,
                    metadata=checkpoint_data["metadata"],
                    state_snapshot={
                        "task_status": state["task_state"]["status"],
                        "current_node": state["current_node"],
                        "retry_count": state["retry_count"]
                    }
                )
                checkpoints.append(checkpoint_info)
        
        # 按创建时间排序并限制数量
        checkpoints.sort(key=lambda x: x["created_at"], reverse=True)
        return checkpoints[:limit]
    
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """从内存删除检查点"""
        if checkpoint_id in self.checkpoints:
            del self.checkpoints[checkpoint_id]
            self.logger.info("检查点已从内存删除", checkpoint_id=checkpoint_id)
            return True
        return False


class SQLiteCheckpointStorage(CheckpointStorage):
    """SQLite检查点存储"""
    
    def __init__(self, db_path: Optional[str] = None):
        super().__init__()
        self.db_path = db_path or config.database.sqlite_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        try:
            # 确保目录存在
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        checkpoint_id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        workflow_phase TEXT NOT NULL,
                        state_data BLOB NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        resumable BOOLEAN DEFAULT TRUE
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_task_id 
                    ON checkpoints(task_id)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_created_at 
                    ON checkpoints(created_at)
                """)
                
                conn.commit()
            finally:
                conn.close()
                
            self.logger.info("SQLite检查点数据库已初始化", db_path=self.db_path)
            
        except Exception as e:
            self.logger.error("初始化数据库失败", error=str(e))
            raise
    
    async def save_checkpoint(
        self,
        checkpoint_id: str,
        state: LangGraphTaskState,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """保存检查点到SQLite"""
        try:
            # 序列化状态数据
            state_data = pickle.dumps(state)
            metadata_json = json.dumps(metadata or {})
            
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO checkpoints 
                    (checkpoint_id, task_id, workflow_phase, state_data, metadata, resumable)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    checkpoint_id,
                    state["task_state"]["task_id"],
                    state["workflow_context"]["current_phase"].value,
                    state_data,
                    metadata_json,
                    True
                ))
                conn.commit()
            finally:
                conn.close()
            
            self.logger.info(
                "检查点已保存到SQLite",
                checkpoint_id=checkpoint_id,
                task_id=state["task_state"]["task_id"]
            )
            return True
            
        except Exception as e:
            self.logger.error("保存检查点失败", error=str(e))
            return False
    
    async def load_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[LangGraphTaskState]:
        """从SQLite加载检查点"""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute("""
                    SELECT state_data FROM checkpoints 
                    WHERE checkpoint_id = ? AND resumable = TRUE
                """, (checkpoint_id,))
                
                row = cursor.fetchone()
                if row:
                    state = pickle.loads(row[0])
                    self.logger.info("检查点已从SQLite加载", checkpoint_id=checkpoint_id)
                    return state
            finally:
                conn.close()
                
            return None
            
        except Exception as e:
            self.logger.error("加载检查点失败", error=str(e))
            return None
    
    async def list_checkpoints(
        self,
        task_id: Optional[str] = None,
        limit: int = 100
    ) -> List[CheckpointData]:
        """列出SQLite中的检查点"""
        try:
            checkpoints = []
            
            conn = sqlite3.connect(self.db_path)
            try:
                if task_id:
                    cursor = conn.execute("""
                        SELECT checkpoint_id, workflow_phase, metadata, created_at
                        FROM checkpoints 
                        WHERE task_id = ? 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    """, (task_id, limit))
                else:
                    cursor = conn.execute("""
                        SELECT checkpoint_id, workflow_phase, metadata, created_at
                        FROM checkpoints 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    """, (limit,))
                
                for row in cursor.fetchall():
                    checkpoint_id, workflow_phase, metadata_json, created_at = row
                    
                    checkpoint_info = CheckpointData(
                        checkpoint_id=checkpoint_id,
                        created_at=datetime.fromisoformat(created_at),
                        workflow_phase=WorkflowPhase(workflow_phase),
                        resumable=True,
                        metadata=json.loads(metadata_json) if metadata_json else {},
                        state_snapshot={}  # 不加载完整状态，只提供基本信息
                    )
                    checkpoints.append(checkpoint_info)
            finally:
                conn.close()
            
            return checkpoints
            
        except Exception as e:
            self.logger.error("列出检查点失败", error=str(e))
            return []
    
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """从SQLite删除检查点"""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute("""
                    DELETE FROM checkpoints WHERE checkpoint_id = ?
                """, (checkpoint_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info("检查点已从SQLite删除", checkpoint_id=checkpoint_id)
                    return True
            finally:
                conn.close()
                
            return False
            
        except Exception as e:
            self.logger.error("删除检查点失败", error=str(e))
            return False


class CheckpointManager(LoggerMixin):
    """检查点管理器"""
    
    def __init__(self, storage_type: str = "sqlite"):
        super().__init__()
        
        if storage_type == "memory":
            self.storage = MemoryCheckpointStorage()
        elif storage_type == "sqlite":
            self.storage = SQLiteCheckpointStorage()
        else:
            raise ValueError(f"不支持的存储类型: {storage_type}")
        
        self.auto_checkpoint_interval = timedelta(minutes=5)  # 自动检查点间隔
        self.max_checkpoints_per_task = 10  # 每个任务最大检查点数
    
    async def create_checkpoint(
        self,
        state: LangGraphTaskState,
        checkpoint_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """创建检查点"""
        if checkpoint_id is None:
            # 使用更精确的时间戳和随机数确保唯一性
            import time
            import random
            timestamp = int(time.time() * 1000000)  # 微秒级时间戳
            random_suffix = random.randint(1000, 9999)
            checkpoint_id = f"cp_{state['task_state']['task_id'][:8]}_{timestamp}_{random_suffix}"
        
        # 更新状态中的检查点数据
        checkpoint_data = CheckpointData(
            checkpoint_id=checkpoint_id,
            created_at=datetime.now(),
            workflow_phase=state["workflow_context"]["current_phase"],
            resumable=True,
            metadata=metadata or {},
            state_snapshot={
                "task_status": state["task_state"]["status"],
                "current_node": state["current_node"],
                "retry_count": state["retry_count"]
            }
        )
        
        state["checkpoint_data"] = checkpoint_data
        
        # 保存到存储
        success = await self.storage.save_checkpoint(checkpoint_id, state, metadata)
        
        if success:
            # 清理旧检查点
            await self._cleanup_old_checkpoints(state["task_state"]["task_id"])
            return checkpoint_id
        
        return None
    
    async def restore_checkpoint(
        self,
        checkpoint_id: str
    ) -> Optional[LangGraphTaskState]:
        """恢复检查点"""
        state = await self.storage.load_checkpoint(checkpoint_id)
        
        if state:
            self.logger.info("检查点已恢复", checkpoint_id=checkpoint_id)
        
        return state
    
    async def list_task_checkpoints(
        self,
        task_id: str,
        limit: int = 10
    ) -> List[CheckpointData]:
        """列出任务的检查点"""
        return await self.storage.list_checkpoints(task_id, limit)
    
    async def should_create_checkpoint(
        self,
        state: LangGraphTaskState
    ) -> bool:
        """判断是否应该创建检查点"""
        # 检查是否到了自动检查点时间
        if state["checkpoint_data"]:
            last_checkpoint_time = state["checkpoint_data"]["created_at"]
            if datetime.now() - last_checkpoint_time < self.auto_checkpoint_interval:
                return False
        
        # 在关键阶段转换时创建检查点
        critical_phases = [
            WorkflowPhase.ANALYSIS,
            WorkflowPhase.DECOMPOSITION,
            WorkflowPhase.COORDINATION,
            WorkflowPhase.EXECUTION,
            WorkflowPhase.REVIEW
        ]
        
        return state["workflow_context"]["current_phase"] in critical_phases
    
    async def _cleanup_old_checkpoints(self, task_id: str):
        """清理旧检查点"""
        try:
            checkpoints = await self.storage.list_checkpoints(task_id, limit=100)
            
            if len(checkpoints) > self.max_checkpoints_per_task:
                # 保留最新的检查点，删除旧的
                old_checkpoints = checkpoints[self.max_checkpoints_per_task:]
                
                for checkpoint in old_checkpoints:
                    await self.storage.delete_checkpoint(checkpoint["checkpoint_id"])
                
                self.logger.info(
                    "已清理旧检查点",
                    task_id=task_id,
                    deleted_count=len(old_checkpoints)
                )
                
        except Exception as e:
            self.logger.error("清理检查点失败", error=str(e))