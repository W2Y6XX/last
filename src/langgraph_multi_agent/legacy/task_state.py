"""任务状态定义 - 基于现有系统的简化版本"""

from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
from enum import Enum
import uuid


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    DECOMPOSED = "decomposed"
    IN_PROGRESS = "in_progress"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    """智能体状态枚举"""
    IDLE = "idle"
    BUSY = "busy"
    COORDINATING = "coordinating"
    ERROR = "error"


class SubTask(TypedDict):
    """子任务结构"""
    task_id: str
    title: str
    description: str
    task_type: str
    assigned_agent: Optional[str]
    status: TaskStatus
    dependencies: List[str]
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    priority: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class AgentCapability(TypedDict):
    """智能体能力结构"""
    agent_id: str
    agent_type: str
    capabilities: List[str]
    specializations: List[str]
    current_status: AgentStatus
    current_task: Optional[str]
    last_active: datetime


class TaskState(TypedDict):
    """主任务状态结构"""
    # 基本信息
    task_id: str
    title: str
    description: str
    task_type: str
    priority: int

    # 状态管理
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    # 任务内容
    requirements: List[str]
    constraints: List[str]
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]

    # 任务拆解
    subtasks: List[SubTask]
    task_dependencies: List[str]

    # 智能体分配
    assigned_agents: List[str]
    agent_capabilities: Dict[str, AgentCapability]

    # 执行信息
    execution_plan: Dict[str, Any]
    progress: Dict[str, Any]
    logs: List[Dict[str, Any]]

    # 元数据
    requester_id: Optional[str]
    metadata: Dict[str, Any]

    @classmethod
    def create_new(
        cls,
        title: str,
        description: str,
        task_type: str = "general",
        priority: int = 1,
        requirements: Optional[List[str]] = None,
        input_data: Optional[Dict[str, Any]] = None,
        requester_id: Optional[str] = None
    ) -> "TaskState":
        """创建新的任务状态"""
        task_id = str(uuid.uuid4())
        now = datetime.now()

        return cls(
            task_id=task_id,
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            started_at=None,
            completed_at=None,
            requirements=requirements or [],
            constraints=[],
            input_data=input_data or {},
            output_data=None,
            subtasks=[],
            task_dependencies=[],
            assigned_agents=[],
            agent_capabilities={},
            execution_plan={},
            progress={},
            logs=[],
            requester_id=requester_id,
            metadata={}
        )