"""
基础智能体抽象类
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END

from .state import AgentState, update_agent_state
from .types import AgentType, AgentInfo, TaskInfo, Priority
from .exceptions import AgentError, WorkflowExecutionError
from ..utils.logging import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """基础智能体抽象类"""

    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        name: str,
        description: str,
        capabilities: List[str] = None,
        configuration: Dict[str, Any] = None
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.capabilities = capabilities or []
        self.configuration = configuration or {}

        # 工作流相关
        self.workflow: Optional[StateGraph] = None
        self.is_initialized = False
        self.is_running = False

        # 日志器
        self.logger = get_logger(f"{__name__}.{agent_id}")

    @abstractmethod
    def create_workflow(self) -> StateGraph:
        """创建智能体工作流 - 子类必须实现"""
        pass

    def initialize(self) -> None:
        """初始化智能体"""
        if self.is_initialized:
            return

        try:
            self.workflow = self.create_workflow()
            self.is_initialized = True
            self.logger.info(f"Agent {self.agent_id} initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize agent {self.agent_id}: {e}")
            raise WorkflowExecutionError("initialization", e)

    async def start(self) -> None:
        """启动智能体"""
        if not self.is_initialized:
            self.initialize()

        self.is_running = True
        self.logger.info(f"Agent {self.agent_id} started")

    async def stop(self) -> None:
        """停止智能体"""
        self.is_running = False
        self.logger.info(f"Agent {self.agent_id} stopped")

    def get_agent_info(self) -> AgentInfo:
        """获取智能体信息"""
        return AgentInfo(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            name=self.name,
            description=self.description,
            capabilities=[],  # 将在具体实现中填充
            status="active" if self.is_running else "inactive",
            metadata=self.configuration
        )

    def _create_initial_state(self, messages: List[BaseMessage] = None) -> AgentState:
        """创建初始状态"""
        return AgentState(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            agent_name=self.name,
            is_active=True,
            last_heartbeat=datetime.now(),
            capabilities=self.capabilities,
            configuration=self.configuration,
            messages=messages or [],
            workflow_state={},
            current_task=None,
            messages_processed=0,
            tasks_completed=0,
            errors_encountered=0
        )

    async def process_message(self, message: BaseMessage) -> BaseMessage:
        """处理单个消息"""
        if not self.is_initialized:
            raise AgentError("Agent not initialized")

        try:
            initial_state = self._create_initial_state([message])
            result = await self.workflow.ainvoke(initial_state)

            # 从结果中提取最后的消息作为响应
            if result.get("messages"):
                return result["messages"][-1]
            else:
                return AIMessage(content="No response generated")

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            raise WorkflowExecutionError("message_processing", e)

    def _log_node_execution(self, node_name: str, state: Dict[str, Any]) -> None:
        """记录节点执行日志"""
        self.logger.debug(f"Executing node: {node_name}")
        self.logger.debug(f"Current workflow stage: {state.get('workflow_stage', 'unknown')}")