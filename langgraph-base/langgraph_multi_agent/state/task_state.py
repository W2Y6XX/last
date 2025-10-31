"""任务状态管理

定义多智能体系统中的任务状态结构和流转逻辑。
"""

from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
from enum import Enum
import uuid


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"           # 待处理
    ANALYZING = "analyzing"       # 分析中
    DECOMPOSED = "decomposed"     # 已拆解
    IN_PROGRESS = "in_progress"   # 执行中
    REVIEWING = "reviewing"       # 审核中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"       # 已取消


class AgentStatus(str, Enum):
    """智能体状态枚举"""
    IDLE = "idle"                 # 空闲
    BUSY = "busy"                 # 忙碌
    COORDINATING = "coordinating" # 协调中
    ERROR = "error"               # 错误


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
    progress: Dict[str, Any]  # 各个阶段的进度信息
    logs: List[Dict[str, Any]]  # 执行日志

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

    def add_subtask(
        self,
        title: str,
        description: str,
        task_type: str,
        dependencies: Optional[List[str]] = None,
        input_data: Optional[Dict[str, Any]] = None,
        priority: int = 1
    ) -> str:
        """添加子任务"""
        subtask_id = str(uuid.uuid4())
        now = datetime.now()

        subtask = SubTask(
            task_id=subtask_id,
            title=title,
            description=description,
            task_type=task_type,
            assigned_agent=None,
            status=TaskStatus.PENDING,
            dependencies=dependencies or [],
            input_data=input_data or {},
            output_data=None,
            priority=priority,
            created_at=now,
            started_at=None,
            completed_at=None
        )

        self["subtasks"].append(subtask)
        self["updated_at"] = now

        return subtask_id

    def update_status(self, new_status: TaskStatus):
        """更新任务状态"""
        self["status"] = new_status
        self["updated_at"] = datetime.now()

        if new_status == TaskStatus.IN_PROGRESS and self["started_at"] is None:
            self["started_at"] = datetime.now()
        elif new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self["completed_at"] = datetime.now()

    def get_subtask_by_id(self, subtask_id: str) -> Optional[SubTask]:
        """根据ID获取子任务"""
        for subtask in self["subtasks"]:
            if subtask["task_id"] == subtask_id:
                return subtask
        return None

    def get_pending_subtasks(self) -> List[SubTask]:
        """获取待处理的子任务"""
        return [st for st in self["subtasks"] if st["status"] == TaskStatus.PENDING]

    def get_in_progress_subtasks(self) -> List[SubTask]:
        """获取进行中的子任务"""
        return [st for st in self["subtasks"] if st["status"] == TaskStatus.IN_PROGRESS]

    def calculate_progress(self) -> float:
        """计算任务整体进度"""
        if not self["subtasks"]:
            return 0.0

        completed_count = sum(1 for st in self["subtasks"] if st["status"] == TaskStatus.COMPLETED)
        return completed_count / len(self["subtasks"])

    def add_log(self, level: str, message: str, agent_id: Optional[str] = None):
        """添加执行日志"""
        log_entry = {
            "timestamp": datetime.now(),
            "level": level,
            "message": message,
            "agent_id": agent_id
        }
        self["logs"].append(log_entry)
        self["updated_at"] = datetime.now()