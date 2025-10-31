"""
状态定义和管理
"""

from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, MessagesState, add_messages

from .types import AgentInfo, TaskInfo, TaskStatus, AgentType


class AgentState(MessagesState):
    """智能体状态基类"""

    # 基本信息
    agent_id: str
    agent_type: AgentType
    agent_name: str

    # 状态信息
    is_active: bool = True
    last_heartbeat: datetime

    # 能力和配置
    capabilities: List[str]
    configuration: Dict[str, Any]

    # 工作流相关
    current_task: Optional[str] = None
    workflow_state: Dict[str, Any]

    # 性能指标
    messages_processed: int = 0
    tasks_completed: int = 0
    errors_encountered: int = 0


class MetaAgentState(AgentState):
    """元智能体状态"""

    # 任务分析相关
    analyzed_tasks: List[str]
    pending_tasks: List[str]

    # 需求澄清相关
    clarification_needed: List[str]
    clarification_responses: Dict[str, Any]

    # 智能体管理
    available_agents: List[AgentInfo]
    agent_assignments: Dict[str, str]  # task_id -> agent_id

    # 工作流状态
    workflow_stage: str  # "analysis", "clarification", "decomposition", "assignment"


class TaskState(MessagesState):
    """任务状态"""

    # 基本信息
    task_id: str
    title: str
    description: str

    # 状态管理
    status: TaskStatus
    priority: str
    progress: float = 0.0

    # 分配信息
    assigned_agent: Optional[str] = None
    dependencies: List[str]
    subtasks: List[str]

    # 时间戳
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 结果和错误
    result: Optional[Any] = None
    error: Optional[str] = None

    # 元数据
    metadata: Dict[str, Any]


class CommunicationState(MessagesState):
    """通信状态"""

    # 消息队列
    pending_messages: List[Dict[str, Any]]
    message_history: List[Dict[str, Any]]

    # 连接状态
    connected_agents: List[str]
    active_channels: Dict[str, Any]

    # 路由信息
    message_routes: Dict[str, List[str]]  # sender_id -> [receiver_ids]

    # 统计信息
    messages_sent: int = 0
    messages_received: int = 0
    failed_deliveries: int = 0


# 状态更新函数
def update_agent_state(state: AgentState, updates: Dict[str, Any]) -> AgentState:
    """更新智能体状态"""
    for key, value in updates.items():
        if hasattr(state, key):
            setattr(state, key, value)
        else:
            state[key] = value
    return state


def update_task_status(state: TaskState, new_status: TaskStatus, **kwargs) -> TaskState:
    """更新任务状态"""
    state.status = new_status
    state.updated_at = datetime.now()

    if new_status == TaskStatus.IN_PROGRESS and state.started_at is None:
        state.started_at = datetime.now()
    elif new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        state.completed_at = datetime.now()

    for key, value in kwargs.items():
        if hasattr(state, key):
            setattr(state, key, value)

    return state


def add_message_to_history(state: CommunicationState, message: Dict[str, Any]) -> CommunicationState:
    """添加消息到历史记录"""
    state.message_history.append(message)
    return state