"""
检查点和状态持久化支持
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from abc import ABC, abstractmethod

from langgraph.checkpoint import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .exceptions import WorkflowError
from ..utils.logging import get_logger

logger = get_logger(__name__)


class FileCheckpointSaver(BaseCheckpointSaver):
    """基于文件系统的检查点保存器"""

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    async def save(self, config: Dict[str, Any], checkpoint: Dict[str, Any]) -> None:
        """保存检查点"""
        try:
            checkpoint_id = config.get("thread_id", "default")
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

            checkpoint_data = {
                "config": config,
                "checkpoint": checkpoint,
                "timestamp": datetime.now().isoformat(),
                "checkpoint_id": checkpoint_id
            }

            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2, default=str)

            self.logger.info(f"Checkpoint saved: {checkpoint_file}")

        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            raise WorkflowError("checkpoint_save", e)

    async def load(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """加载检查点"""
        try:
            checkpoint_id = config.get("thread_id", "default")
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

            if not checkpoint_file.exists():
                return None

            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)

            self.logger.info(f"Checkpoint loaded: {checkpoint_file}")
            return checkpoint_data.get("checkpoint")

        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            raise WorkflowError("checkpoint_load", e)

    async def list_checkpoints(self, thread_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出检查点"""
        try:
            checkpoints = []

            for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                if thread_id and checkpoint_file.stem != thread_id:
                    continue

                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        checkpoint_data = json.load(f)
                    checkpoints.append(checkpoint_data)
                except Exception as e:
                    self.logger.warning(f"Failed to read checkpoint {checkpoint_file}: {e}")

            return checkpoints

        except Exception as e:
            self.logger.error(f"Failed to list checkpoints: {e}")
            return []

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        try:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
            if checkpoint_file.exists():
                checkpoint_file.unlink()
                self.logger.info(f"Checkpoint deleted: {checkpoint_file}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Failed to delete checkpoint: {e}")
            return False


class CheckpointManager:
    """检查点管理器"""

    def __init__(self, saver: BaseCheckpointSaver = None):
        self.saver = saver or MemorySaver()
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    async def create_checkpoint(
        self,
        state: AgentState,
        config: Dict[str, Any] = None
    ) -> str:
        """创建检查点"""
        if config is None:
            config = {"thread_id": f"workflow_{datetime.now().timestamp()}"}

        try:
            checkpoint = {
                "state": state,
                "timestamp": datetime.now().isoformat(),
                "config": config
            }

            await self.saver.save(config, checkpoint)
            self.logger.info(f"Checkpoint created for thread: {config.get('thread_id')}")
            return config.get("thread_id")

        except Exception as e:
            self.logger.error(f"Failed to create checkpoint: {e}")
            raise WorkflowError("checkpoint_creation", e)

    async def restore_checkpoint(self, thread_id: str) -> Optional[AgentState]:
        """恢复检查点"""
        try:
            config = {"thread_id": thread_id}
            checkpoint = await self.saver.load(config)

            if checkpoint:
                state = checkpoint.get("state")
                self.logger.info(f"Checkpoint restored for thread: {thread_id}")
                return state
            else:
                self.logger.warning(f"No checkpoint found for thread: {thread_id}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to restore checkpoint: {e}")
            raise WorkflowError("checkpoint_restore", e)

    async def auto_checkpoint(
        self,
        state: AgentState,
        interval: int = 300  # 5分钟
    ) -> None:
        """自动检查点（后台任务）"""
        while True:
            try:
                await asyncio.sleep(interval)
                await self.create_checkpoint(state)
                self.logger.debug("Auto checkpoint created")
            except Exception as e:
                self.logger.error(f"Auto checkpoint failed: {e}")


# 工作流状态持久化工具
class WorkflowStatePersistence:
    """工作流状态持久化工具"""

    def __init__(self, persistence_dir: str = "workflow_states"):
        self.persistence_dir = Path(persistence_dir)
        self.persistence_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    async def save_workflow_state(
        self,
        workflow_id: str,
        state: Dict[str, Any]
    ) -> None:
        """保存工作流状态"""
        try:
            state_file = self.persistence_dir / f"{workflow_id}.json"

            state_data = {
                "workflow_id": workflow_id,
                "state": state,
                "timestamp": datetime.now().isoformat(),
                "version": "1.0"
            }

            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2, default=str)

            self.logger.info(f"Workflow state saved: {workflow_id}")

        except Exception as e:
            self.logger.error(f"Failed to save workflow state: {e}")
            raise WorkflowError("state_persistence", e)

    async def load_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """加载工作流状态"""
        try:
            state_file = self.persistence_dir / f"{workflow_id}.json"

            if not state_file.exists():
                return None

            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            self.logger.info(f"Workflow state loaded: {workflow_id}")
            return state_data.get("state")

        except Exception as e:
            self.logger.error(f"Failed to load workflow state: {e}")
            return None

    async def list_workflow_states(self) -> List[str]:
        """列出所有工作流状态"""
        try:
            state_files = list(self.persistence_dir.glob("*.json"))
            return [f.stem for f in state_files]

        except Exception as e:
            self.logger.error(f"Failed to list workflow states: {e}")
            return []