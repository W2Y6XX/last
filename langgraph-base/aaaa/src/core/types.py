"""
核心类型定义和类型注解
"""

from typing import Dict, List, Any, Optional, Union, Callable, Set, Tuple
from enum import Enum
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


class AgentType(str, Enum):
    """智能体类型枚举"""
    META = "meta"
    COORDINATOR = "coordinator"
    TASK_DECOMPOSER = "task_decomposer"
    HUMAN = "human"
    CUSTOM = "custom"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(str, Enum):
    """消息类型枚举"""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    BROADCAST = "broadcast"


class Priority(str, Enum):
    """优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __lt__(self, other):
        priority_order = {
            Priority.LOW: 1,
            Priority.MEDIUM: 2,
            Priority.HIGH: 3,
            Priority.CRITICAL: 4
        }
        return priority_order[self] < priority_order[other]


class ExecutionMode(str, Enum):
    """任务执行模式"""
    SEQUENTIAL = "sequential"      # 顺序执行
    PARALLEL = "parallel"         # 并行执行
    CONDITIONAL = "conditional"   # 条件执行
    HYBRID = "hybrid"             # 混合模式


@dataclass
class AgentCapability:
    """智能体能力定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    dependencies: Set[str] = Field(default_factory=set)


@dataclass
class TaskDependency:
    """任务依赖关系"""
    task_id: str
    dependency_type: str  # "sequential", "parallel", "conditional"
    condition: Optional[Callable[[Any], bool]] = None


class AgentInfo(BaseModel):
    """智能体信息"""
    agent_id: str
    agent_type: AgentType
    name: str
    description: str
    capabilities: List[AgentCapability]
    status: str = "active"
    last_heartbeat: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskInfo(BaseModel):
    """任务信息"""
    task_id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    assigned_agent: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageContent(BaseModel):
    """消息内容"""
    message_id: Optional[str] = None
    message_type: MessageType
    sender_id: str
    receiver_id: Optional[str] = None
    content: Any
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    priority: Priority = Priority.MEDIUM


# 类型别名
AgentId = str
TaskId = str
MessageId = str
StateKey = str
WorkflowNode = Callable[..., Any]
WorkflowCondition = Callable[..., bool]