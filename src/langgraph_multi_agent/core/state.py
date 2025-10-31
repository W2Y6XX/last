"""LangGraph状态定义模块"""

from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
from enum import Enum
import uuid

# 导入现有的状态定义
try:
    from langgraph_multi_agent.state import TaskState as BaseTaskState, TaskStatus, AgentStatus
except ImportError:
    # 如果无法导入，使用本地定义
    from ..legacy.task_state import TaskState as BaseTaskState, TaskStatus, AgentStatus


class WorkflowPhase(str, Enum):
    """工作流阶段枚举"""
    INITIALIZATION = "initialization"
    ANALYSIS = "analysis"
    DECOMPOSITION = "decomposition"
    COORDINATION = "coordination"
    EXECUTION = "execution"
    REVIEW = "review"
    COMPLETION = "completion"
    ERROR_HANDLING = "error_handling"


class WorkflowContext(TypedDict):
    """工作流上下文"""
    current_phase: WorkflowPhase
    completed_phases: List[WorkflowPhase]
    agent_results: Dict[str, Any]
    coordination_plan: Optional[Dict[str, Any]]
    execution_metadata: Dict[str, Any]
    phase_start_times: Dict[str, datetime]
    phase_durations: Dict[str, float]


class CheckpointData(TypedDict):
    """检查点数据"""
    checkpoint_id: str
    created_at: datetime
    workflow_phase: WorkflowPhase
    resumable: bool
    metadata: Dict[str, Any]
    state_snapshot: Dict[str, Any]


class AgentMessage(TypedDict):
    """智能体消息"""
    message_id: str
    sender_agent: str
    receiver_agent: Optional[str]
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime
    priority: int
    requires_response: bool


class CoordinationState(TypedDict):
    """协调状态"""
    active_agents: List[str]
    agent_assignments: Dict[str, List[str]]  # agent_id -> task_ids
    resource_allocation: Dict[str, Any]
    coordination_mode: str
    sync_points: List[str]
    conflicts: List[Dict[str, Any]]


class ErrorState(TypedDict):
    """错误状态"""
    error_id: str
    error_type: str
    error_message: str
    failed_node: str
    failed_agent: Optional[str]
    retry_count: int
    max_retries: int
    recovery_strategy: Optional[str]
    timestamp: datetime


def add_to_list(existing: List[Any], new_item: Any) -> List[Any]:
    """列表添加操作的reducer函数"""
    if existing is None:
        existing = []
    return existing + [new_item]


def update_dict(existing: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """字典更新操作的reducer函数"""
    if existing is None:
        existing = {}
    result = existing.copy()
    result.update(updates)
    return result


class LangGraphTaskState(TypedDict):
    """LangGraph任务状态
    
    这是LangGraph工作流的主要状态结构，集成了现有的TaskState
    并添加了LangGraph特有的字段。
    """
    # 继承现有TaskState的所有字段
    task_state: BaseTaskState
    
    # LangGraph工作流控制字段
    current_node: str
    next_nodes: List[str]
    should_continue: bool
    
    # 工作流上下文
    workflow_context: Annotated[WorkflowContext, update_dict]
    
    # 检查点和恢复
    checkpoint_data: Optional[CheckpointData]
    
    # 智能体通信
    agent_messages: Annotated[List[AgentMessage], add_to_list]
    coordination_state: Annotated[CoordinationState, update_dict]
    
    # 错误处理
    error_state: Optional[ErrorState]
    retry_count: int
    
    # 执行元数据
    execution_start_time: Optional[datetime]
    execution_end_time: Optional[datetime]
    total_execution_time: Optional[float]
    
    # 性能指标
    performance_metrics: Annotated[Dict[str, Any], update_dict]


def create_initial_state(
    title: str,
    description: str,
    task_type: str = "general",
    priority: int = 1,
    input_data: Optional[Dict[str, Any]] = None,
    requester_id: Optional[str] = None
) -> LangGraphTaskState:
    """创建初始的LangGraph任务状态"""
    
    # 创建基础任务状态
    base_task_state = BaseTaskState.create_new(
        title=title,
        description=description,
        task_type=task_type,
        priority=priority,
        input_data=input_data,
        requester_id=requester_id
    )
    
    # 创建工作流上下文
    workflow_context = WorkflowContext(
        current_phase=WorkflowPhase.INITIALIZATION,
        completed_phases=[],
        agent_results={},
        coordination_plan=None,
        execution_metadata={},
        phase_start_times={WorkflowPhase.INITIALIZATION.value: datetime.now()},
        phase_durations={}
    )
    
    # 创建协调状态
    coordination_state = CoordinationState(
        active_agents=[],
        agent_assignments={},
        resource_allocation={},
        coordination_mode="centralized",
        sync_points=[],
        conflicts=[]
    )
    
    return LangGraphTaskState(
        task_state=base_task_state,
        current_node="start",
        next_nodes=["meta_agent"],
        should_continue=True,
        workflow_context=workflow_context,
        checkpoint_data=None,
        agent_messages=[],
        coordination_state=coordination_state,
        error_state=None,
        retry_count=0,
        execution_start_time=datetime.now(),
        execution_end_time=None,
        total_execution_time=None,
        performance_metrics={}
    )


def update_workflow_phase(
    state: LangGraphTaskState, 
    new_phase: WorkflowPhase
) -> LangGraphTaskState:
    """更新工作流阶段"""
    current_time = datetime.now()
    current_phase = state["workflow_context"]["current_phase"]
    
    # 记录当前阶段的持续时间
    if current_phase in state["workflow_context"]["phase_start_times"]:
        start_time = state["workflow_context"]["phase_start_times"][current_phase.value]
        duration = (current_time - start_time).total_seconds()
        state["workflow_context"]["phase_durations"][current_phase.value] = duration
    
    # 更新到新阶段
    state["workflow_context"]["current_phase"] = new_phase
    state["workflow_context"]["completed_phases"].append(current_phase)
    state["workflow_context"]["phase_start_times"][new_phase.value] = current_time
    
    return state


def add_agent_message(
    state: LangGraphTaskState,
    sender_agent: str,
    content: Dict[str, Any],
    message_type: str = "result",
    receiver_agent: Optional[str] = None,
    priority: int = 1,
    requires_response: bool = False
) -> LangGraphTaskState:
    """添加智能体消息"""
    message = AgentMessage(
        message_id=str(uuid.uuid4()),
        sender_agent=sender_agent,
        receiver_agent=receiver_agent,
        message_type=message_type,
        content=content,
        timestamp=datetime.now(),
        priority=priority,
        requires_response=requires_response
    )
    
    state["agent_messages"].append(message)
    return state


def create_checkpoint(
    state: LangGraphTaskState,
    checkpoint_id: Optional[str] = None
) -> LangGraphTaskState:
    """创建检查点"""
    if checkpoint_id is None:
        checkpoint_id = str(uuid.uuid4())
    
    checkpoint_data = CheckpointData(
        checkpoint_id=checkpoint_id,
        created_at=datetime.now(),
        workflow_phase=state["workflow_context"]["current_phase"],
        resumable=True,
        metadata={
            "current_node": state["current_node"],
            "retry_count": state["retry_count"],
            "agent_count": len(state["coordination_state"]["active_agents"])
        },
        state_snapshot={
            "task_status": state["task_state"]["status"],
            "workflow_phase": state["workflow_context"]["current_phase"].value,
            "active_agents": state["coordination_state"]["active_agents"]
        }
    )
    
    state["checkpoint_data"] = checkpoint_data
    return state


def validate_state_transition(
    current_state: LangGraphTaskState,
    new_phase: WorkflowPhase
) -> bool:
    """验证状态转换是否有效"""
    current_phase = current_state["workflow_context"]["current_phase"]
    
    # 定义有效的状态转换
    valid_transitions = {
        WorkflowPhase.INITIALIZATION: [WorkflowPhase.ANALYSIS, WorkflowPhase.ERROR_HANDLING],
        WorkflowPhase.ANALYSIS: [WorkflowPhase.DECOMPOSITION, WorkflowPhase.COORDINATION, WorkflowPhase.COMPLETION, WorkflowPhase.ERROR_HANDLING],
        WorkflowPhase.DECOMPOSITION: [WorkflowPhase.COORDINATION, WorkflowPhase.ERROR_HANDLING],
        WorkflowPhase.COORDINATION: [WorkflowPhase.EXECUTION, WorkflowPhase.ERROR_HANDLING],
        WorkflowPhase.EXECUTION: [WorkflowPhase.REVIEW, WorkflowPhase.ERROR_HANDLING],
        WorkflowPhase.REVIEW: [WorkflowPhase.COMPLETION, WorkflowPhase.DECOMPOSITION, WorkflowPhase.ERROR_HANDLING],
        WorkflowPhase.ERROR_HANDLING: [WorkflowPhase.ANALYSIS, WorkflowPhase.DECOMPOSITION, WorkflowPhase.COORDINATION, WorkflowPhase.EXECUTION],
        WorkflowPhase.COMPLETION: []  # 完成状态不能转换到其他状态
    }
    
    return new_phase in valid_transitions.get(current_phase, [])


def update_task_status(
    state: LangGraphTaskState,
    new_status: "TaskStatus"
) -> LangGraphTaskState:
    """更新任务状态并同步工作流阶段"""
    from ..legacy.task_state import TaskStatus
    
    # 更新基础任务状态
    state["task_state"]["status"] = new_status
    state["task_state"]["updated_at"] = datetime.now()
    
    # 根据任务状态同步工作流阶段
    status_to_phase = {
        TaskStatus.PENDING: WorkflowPhase.INITIALIZATION,
        TaskStatus.ANALYZING: WorkflowPhase.ANALYSIS,
        TaskStatus.DECOMPOSED: WorkflowPhase.DECOMPOSITION,
        TaskStatus.IN_PROGRESS: WorkflowPhase.EXECUTION,
        TaskStatus.REVIEWING: WorkflowPhase.REVIEW,
        TaskStatus.COMPLETED: WorkflowPhase.COMPLETION,
        TaskStatus.FAILED: WorkflowPhase.ERROR_HANDLING,
        TaskStatus.CANCELLED: WorkflowPhase.COMPLETION
    }
    
    if new_status in status_to_phase:
        target_phase = status_to_phase[new_status]
        if validate_state_transition(state, target_phase):
            state = update_workflow_phase(state, target_phase)
    
    return state


def add_performance_metric(
    state: LangGraphTaskState,
    metric_name: str,
    metric_value: Any,
    timestamp: Optional[datetime] = None
) -> LangGraphTaskState:
    """添加性能指标"""
    if timestamp is None:
        timestamp = datetime.now()
    
    if metric_name not in state["performance_metrics"]:
        state["performance_metrics"][metric_name] = []
    
    state["performance_metrics"][metric_name].append({
        "value": metric_value,
        "timestamp": timestamp.isoformat()
    })
    
    return state


def calculate_execution_time(state: LangGraphTaskState) -> Optional[float]:
    """计算执行时间"""
    if state["execution_start_time"] and state["execution_end_time"]:
        return (state["execution_end_time"] - state["execution_start_time"]).total_seconds()
    elif state["execution_start_time"]:
        return (datetime.now() - state["execution_start_time"]).total_seconds()
    return None


def get_active_agents(state: LangGraphTaskState) -> List[str]:
    """获取当前活跃的智能体列表"""
    return state["coordination_state"]["active_agents"]


def assign_agent_to_task(
    state: LangGraphTaskState,
    agent_id: str,
    task_ids: List[str]
) -> LangGraphTaskState:
    """分配智能体到任务"""
    if agent_id not in state["coordination_state"]["active_agents"]:
        state["coordination_state"]["active_agents"].append(agent_id)
    
    state["coordination_state"]["agent_assignments"][agent_id] = task_ids
    
    return state


def remove_agent_from_coordination(
    state: LangGraphTaskState,
    agent_id: str
) -> LangGraphTaskState:
    """从协调中移除智能体"""
    if agent_id in state["coordination_state"]["active_agents"]:
        state["coordination_state"]["active_agents"].remove(agent_id)
    
    if agent_id in state["coordination_state"]["agent_assignments"]:
        del state["coordination_state"]["agent_assignments"][agent_id]
    
    return state


def add_conflict(
    state: LangGraphTaskState,
    conflict_type: str,
    description: str,
    involved_agents: List[str]
) -> LangGraphTaskState:
    """添加冲突记录"""
    conflict = {
        "conflict_id": str(uuid.uuid4()),
        "conflict_type": conflict_type,
        "description": description,
        "involved_agents": involved_agents,
        "detected_at": datetime.now().isoformat(),
        "resolved": False
    }
    
    state["coordination_state"]["conflicts"].append(conflict)
    return state


def resolve_conflict(
    state: LangGraphTaskState,
    conflict_id: str,
    resolution: str
) -> LangGraphTaskState:
    """解决冲突"""
    for conflict in state["coordination_state"]["conflicts"]:
        if conflict["conflict_id"] == conflict_id:
            conflict["resolved"] = True
            conflict["resolution"] = resolution
            conflict["resolved_at"] = datetime.now().isoformat()
            break
    
    return state


def create_error_state(
    error_type: str,
    error_message: str,
    failed_node: str,
    failed_agent: Optional[str] = None,
    max_retries: int = 3
) -> ErrorState:
    """创建错误状态"""
    return ErrorState(
        error_id=str(uuid.uuid4()),
        error_type=error_type,
        error_message=error_message,
        failed_node=failed_node,
        failed_agent=failed_agent,
        retry_count=0,
        max_retries=max_retries,
        recovery_strategy=None,
        timestamp=datetime.now()
    )


def handle_error(
    state: LangGraphTaskState,
    error: Exception,
    failed_node: str,
    failed_agent: Optional[str] = None
) -> LangGraphTaskState:
    """处理错误"""
    error_state = create_error_state(
        error_type=type(error).__name__,
        error_message=str(error),
        failed_node=failed_node,
        failed_agent=failed_agent
    )
    
    state["error_state"] = error_state
    state["retry_count"] += 1
    
    # 更新到错误处理阶段
    if validate_state_transition(state, WorkflowPhase.ERROR_HANDLING):
        state = update_workflow_phase(state, WorkflowPhase.ERROR_HANDLING)
    
    return state


def clear_error_state(state: LangGraphTaskState) -> LangGraphTaskState:
    """清除错误状态"""
    state["error_state"] = None
    return state


def is_state_valid(state: LangGraphTaskState) -> bool:
    """验证状态是否有效"""
    try:
        # 检查必需字段
        required_fields = [
            "task_state", "current_node", "workflow_context",
            "coordination_state", "agent_messages", "performance_metrics"
        ]
        
        for field in required_fields:
            if field not in state:
                return False
        
        # 检查工作流阶段是否有效
        current_phase = state["workflow_context"]["current_phase"]
        if not isinstance(current_phase, WorkflowPhase):
            return False
        
        # 检查智能体消息格式
        for message in state["agent_messages"]:
            if not all(key in message for key in ["message_id", "sender_agent", "timestamp"]):
                return False
        
        return True
        
    except Exception:
        return False