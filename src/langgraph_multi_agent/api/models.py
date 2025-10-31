"""API数据模型定义"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator

from ..legacy.task_state import TaskStatus
from ..core.state import WorkflowPhase


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class TaskType(str, Enum):
    """任务类型"""
    GENERAL = "general"
    ANALYSIS = "analysis"
    RESEARCH = "research"
    DEVELOPMENT = "development"
    COORDINATION = "coordination"
    REPORTING = "reporting"


class WorkflowExecutionMode(str, Enum):
    """工作流执行模式"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"


# 请求模型
class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    title: str = Field(..., min_length=1, max_length=200, description="任务标题")
    description: str = Field(..., min_length=1, max_length=2000, description="任务描述")
    task_type: TaskType = Field(default=TaskType.GENERAL, description="任务类型")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="任务优先级")
    requirements: List[str] = Field(default_factory=list, description="任务需求")
    constraints: List[str] = Field(default_factory=list, description="任务约束")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="输入数据")
    execution_mode: WorkflowExecutionMode = Field(default=WorkflowExecutionMode.ADAPTIVE, description="执行模式")
    timeout_seconds: Optional[int] = Field(default=3600, ge=60, le=86400, description="超时时间（秒）")
    requester_id: Optional[str] = Field(default=None, description="请求者ID")
    
    @validator('requirements')
    def validate_requirements(cls, v):
        if len(v) > 20:
            raise ValueError('需求数量不能超过20个')
        return v
    
    @validator('constraints')
    def validate_constraints(cls, v):
        if len(v) > 10:
            raise ValueError('约束数量不能超过10个')
        return v


class TaskUpdateRequest(BaseModel):
    """更新任务请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="任务标题")
    description: Optional[str] = Field(None, min_length=1, max_length=2000, description="任务描述")
    priority: Optional[TaskPriority] = Field(None, description="任务优先级")
    requirements: Optional[List[str]] = Field(None, description="任务需求")
    constraints: Optional[List[str]] = Field(None, description="任务约束")
    input_data: Optional[Dict[str, Any]] = Field(None, description="输入数据")


class TaskActionRequest(BaseModel):
    """任务操作请求"""
    action: str = Field(..., description="操作类型：pause, resume, cancel, retry")
    reason: Optional[str] = Field(None, description="操作原因")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="操作元数据")


class WorkflowConfigRequest(BaseModel):
    """工作流配置请求"""
    execution_mode: Optional[WorkflowExecutionMode] = Field(None, description="执行模式")
    checkpoint_interval: Optional[int] = Field(None, ge=10, le=3600, description="检查点间隔（秒）")
    max_retries: Optional[int] = Field(None, ge=0, le=10, description="最大重试次数")
    timeout_seconds: Optional[int] = Field(None, ge=60, le=86400, description="超时时间（秒）")
    agents_config: Optional[Dict[str, Any]] = Field(None, description="智能体配置")


# 响应模型
class TaskInfo(BaseModel):
    """任务信息"""
    task_id: str = Field(..., description="任务ID")
    title: str = Field(..., description="任务标题")
    description: str = Field(..., description="任务描述")
    task_type: str = Field(..., description="任务类型")
    priority: int = Field(..., description="任务优先级")
    status: str = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    requester_id: Optional[str] = Field(None, description="请求者ID")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskDetail(TaskInfo):
    """任务详情"""
    requirements: List[str] = Field(..., description="任务需求")
    constraints: List[str] = Field(..., description="任务约束")
    input_data: Dict[str, Any] = Field(..., description="输入数据")
    output_data: Optional[Dict[str, Any]] = Field(None, description="输出数据")
    subtasks: List[Dict[str, Any]] = Field(default_factory=list, description="子任务")
    execution_metadata: Dict[str, Any] = Field(default_factory=dict, description="执行元数据")
    error_info: Optional[Dict[str, Any]] = Field(None, description="错误信息")


class WorkflowStatus(BaseModel):
    """工作流状态"""
    workflow_id: str = Field(..., description="工作流ID")
    task_id: str = Field(..., description="任务ID")
    current_phase: str = Field(..., description="当前阶段")
    status: str = Field(..., description="工作流状态")
    progress: float = Field(..., ge=0, le=1, description="进度百分比")
    active_agents: List[str] = Field(..., description="活跃智能体")
    completed_agents: List[str] = Field(..., description="已完成智能体")
    failed_agents: List[str] = Field(..., description="失败智能体")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")
    estimated_remaining_time: Optional[float] = Field(None, description="预计剩余时间（秒）")


class AgentInfo(BaseModel):
    """智能体信息"""
    agent_id: str = Field(..., description="智能体ID")
    agent_type: str = Field(..., description="智能体类型")
    name: str = Field(..., description="智能体名称")
    description: str = Field(..., description="智能体描述")
    capabilities: List[str] = Field(..., description="智能体能力")
    status: str = Field(..., description="智能体状态")
    current_task: Optional[str] = Field(None, description="当前任务")
    execution_stats: Dict[str, Any] = Field(..., description="执行统计")


class SystemHealth(BaseModel):
    """系统健康状态"""
    overall_healthy: bool = Field(..., description="整体健康状态")
    timestamp: datetime = Field(..., description="检查时间")
    health_checks: Dict[str, Dict[str, Any]] = Field(..., description="健康检查结果")
    active_alerts: Dict[str, Dict[str, Any]] = Field(..., description="活跃告警")
    error_metrics: Dict[str, Any] = Field(..., description="错误指标")
    performance_metrics: Dict[str, Any] = Field(..., description="性能指标")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskInfo] = Field(..., description="任务列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="页大小")
    has_next: bool = Field(..., description="是否有下一页")


class ApiResponse(BaseModel):
    """通用API响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    error_code: Optional[str] = Field(None, description="错误代码")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(default=False, description="是否成功")
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# WebSocket消息模型
class WebSocketMessage(BaseModel):
    """WebSocket消息"""
    type: str = Field(..., description="消息类型")
    data: Dict[str, Any] = Field(..., description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskStatusUpdate(BaseModel):
    """任务状态更新"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    phase: str = Field(..., description="工作流阶段")
    progress: float = Field(..., ge=0, le=1, description="进度")
    message: Optional[str] = Field(None, description="状态消息")
    agent_updates: List[Dict[str, Any]] = Field(default_factory=list, description="智能体更新")
    timestamp: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentStatusUpdate(BaseModel):
    """智能体状态更新"""
    agent_id: str = Field(..., description="智能体ID")
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="智能体状态")
    progress: Optional[float] = Field(None, ge=0, le=1, description="进度")
    message: Optional[str] = Field(None, description="状态消息")
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    timestamp: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# 查询参数模型
class TaskQueryParams(BaseModel):
    """任务查询参数"""
    status: Optional[str] = Field(None, description="任务状态过滤")
    task_type: Optional[str] = Field(None, description="任务类型过滤")
    priority: Optional[int] = Field(None, ge=1, le=4, description="优先级过滤")
    requester_id: Optional[str] = Field(None, description="请求者ID过滤")
    created_after: Optional[datetime] = Field(None, description="创建时间起始")
    created_before: Optional[datetime] = Field(None, description="创建时间结束")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="页大小")
    sort_by: str = Field(default="created_at", description="排序字段")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="排序顺序")


class AgentQueryParams(BaseModel):
    """智能体查询参数"""
    agent_type: Optional[str] = Field(None, description="智能体类型过滤")
    status: Optional[str] = Field(None, description="状态过滤")
    capability: Optional[str] = Field(None, description="能力过滤")
    task_id: Optional[str] = Field(None, description="任务ID过滤")


# 批量操作模型
class BatchTaskAction(BaseModel):
    """批量任务操作"""
    task_ids: List[str] = Field(..., min_items=1, max_items=100, description="任务ID列表")
    action: str = Field(..., description="操作类型")
    reason: Optional[str] = Field(None, description="操作原因")
    
    @validator('task_ids')
    def validate_task_ids(cls, v):
        if len(set(v)) != len(v):
            raise ValueError('任务ID列表不能包含重复项')
        return v


class BatchOperationResult(BaseModel):
    """批量操作结果"""
    total: int = Field(..., description="总数量")
    successful: int = Field(..., description="成功数量")
    failed: int = Field(..., description="失败数量")
    results: List[Dict[str, Any]] = Field(..., description="详细结果")
    errors: List[Dict[str, Any]] = Field(..., description="错误信息")


# 统计和分析模型
class TaskStatistics(BaseModel):
    """任务统计"""
    total_tasks: int = Field(..., description="总任务数")
    completed_tasks: int = Field(..., description="已完成任务数")
    failed_tasks: int = Field(..., description="失败任务数")
    running_tasks: int = Field(..., description="运行中任务数")
    pending_tasks: int = Field(..., description="待处理任务数")
    average_execution_time: float = Field(..., description="平均执行时间")
    success_rate: float = Field(..., ge=0, le=1, description="成功率")
    tasks_by_type: Dict[str, int] = Field(..., description="按类型统计")
    tasks_by_priority: Dict[str, int] = Field(..., description="按优先级统计")


class SystemMetrics(BaseModel):
    """系统指标"""
    cpu_usage: float = Field(..., ge=0, le=100, description="CPU使用率")
    memory_usage: float = Field(..., ge=0, le=100, description="内存使用率")
    active_workflows: int = Field(..., description="活跃工作流数")
    active_agents: int = Field(..., description="活跃智能体数")
    requests_per_minute: float = Field(..., description="每分钟请求数")
    average_response_time: float = Field(..., description="平均响应时间")
    error_rate: float = Field(..., ge=0, le=1, description="错误率")
    uptime_seconds: int = Field(..., description="运行时间（秒）")
    timestamp: datetime = Field(default_factory=datetime.now, description="指标时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }