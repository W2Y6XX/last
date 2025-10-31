"""
MVP2前端适配层
提供MVP2前端特定的数据转换和接口适配功能
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import json
import logging
from dataclasses import dataclass, asdict
from enum import Enum

from ..core.state import LangGraphTaskState
from ..api.models import TaskCreateRequest, TaskDetail, ApiResponse, TaskStatistics
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class MVP2TaskStatus(Enum):
    """MVP2任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class MVP2Priority(Enum):
    """MVP2优先级枚举"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    URGENT = "紧急"


@dataclass
class MVP2Task:
    """MVP2任务数据模型"""
    id: str
    name: str
    description: str
    priority: str
    deadline: str
    assignee: str
    progress: int
    status: str
    created_at: str
    updated_at: Optional[str] = None


# 临时模型定义，用于兼容性
class TaskRequest(BaseModel):
    """任务请求模型（兼容性）"""
    title: str
    description: str
    task_type: str = "general"
    priority: int = 2
    requirements: List[str] = []
    constraints: List[str] = []
    input_data: Dict[str, Any] = {}

class TaskResponse(BaseModel):
    """任务响应模型（兼容性）"""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None

class ChatMessage(BaseModel):
    """聊天消息模型（兼容性）"""
    type: str
    content: str
    sender: str
    timestamp: str

class AnalyticsData(BaseModel):
    """分析数据模型（兼容性）"""
    total_tasks: int = 0
    completed_tasks: int = 0
    active_tasks: int = 0
    success_rate: float = 0.0

@dataclass
class MVP2ChatMessage:
    """MVP2聊天消息数据模型"""
    type: str  # 'user' or 'ai'
    content: str
    sender: str
    timestamp: str


@dataclass
class MVP2Analytics:
    """MVP2分析数据模型"""
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    urgent_tasks: int
    completion_rate: float
    trend_data: List[Dict[str, Any]]
    category_data: List[Dict[str, Any]]


class MVP2DataTransformer:
    """MVP2数据转换器"""
    
    @staticmethod
    def task_to_mvp2(task_state: LangGraphTaskState) -> MVP2Task:
        """将LangGraph任务状态转换为MVP2任务格式"""
        try:
            task_data = task_state.get("task_state", {})
            
            # 状态映射
            status_mapping = {
                "pending": MVP2TaskStatus.PENDING.value,
                "running": MVP2TaskStatus.IN_PROGRESS.value,
                "completed": MVP2TaskStatus.COMPLETED.value,
                "failed": MVP2TaskStatus.FAILED.value
            }
            
            # 优先级映射
            priority_mapping = {
                1: MVP2Priority.LOW.value,
                2: MVP2Priority.MEDIUM.value,
                3: MVP2Priority.HIGH.value,
                4: MVP2Priority.URGENT.value
            }
            
            return MVP2Task(
                id=task_data.get("task_id", ""),
                name=task_data.get("title", "未命名任务"),
                description=task_data.get("description", ""),
                priority=priority_mapping.get(task_data.get("priority", 1), MVP2Priority.LOW.value),
                deadline=task_data.get("deadline", datetime.now().isoformat()),
                assignee=task_data.get("assignee", "未分配"),
                progress=task_data.get("progress", 0),
                status=status_mapping.get(task_data.get("status", "pending"), MVP2TaskStatus.PENDING.value),
                created_at=task_data.get("created_at", datetime.now().isoformat()),
                updated_at=task_data.get("updated_at")
            )
        except Exception as e:
            logger.error(f"任务转换失败: {e}")
            raise ValueError(f"任务数据转换错误: {e}")
    
    @staticmethod
    def mvp2_to_task_request(mvp2_task: Dict[str, Any]) -> TaskRequest:
        """将MVP2任务数据转换为TaskRequest"""
        try:
            # 优先级反向映射
            priority_mapping = {
                MVP2Priority.LOW.value: 1,
                MVP2Priority.MEDIUM.value: 2,
                MVP2Priority.HIGH.value: 3,
                MVP2Priority.URGENT.value: 4
            }
            
            return TaskRequest(
                title=mvp2_task.get("name", ""),
                description=mvp2_task.get("description", ""),
                task_type="mvp2_task",
                priority=priority_mapping.get(mvp2_task.get("priority", MVP2Priority.LOW.value), 1),
                input_data={
                    "deadline": mvp2_task.get("deadline"),
                    "assignee": mvp2_task.get("assignee", "未分配"),
                    "progress": mvp2_task.get("progress", 0),
                    "mvp2_format": True
                }
            )
        except Exception as e:
            logger.error(f"MVP2任务请求转换失败: {e}")
            raise ValueError(f"MVP2任务数据转换错误: {e}")
    
    @staticmethod
    def chat_message_to_mvp2(message: ChatMessage) -> MVP2ChatMessage:
        """将聊天消息转换为MVP2格式"""
        try:
            return MVP2ChatMessage(
                type="user" if message.sender == "user" else "ai",
                content=message.content,
                sender="用户" if message.sender == "user" else "时光守护者",
                timestamp=message.timestamp.isoformat() if hasattr(message.timestamp, 'isoformat') else str(message.timestamp)
            )
        except Exception as e:
            logger.error(f"聊天消息转换失败: {e}")
            raise ValueError(f"聊天消息转换错误: {e}")
    
    @staticmethod
    def analytics_to_mvp2(analytics: AnalyticsData, tasks: List[LangGraphTaskState]) -> MVP2Analytics:
        """将分析数据转换为MVP2格式"""
        try:
            # 计算任务统计
            total_tasks = len(tasks)
            completed_tasks = len([t for t in tasks if t.get("task_state", {}).get("status") == "completed"])
            pending_tasks = total_tasks - completed_tasks
            urgent_tasks = len([t for t in tasks if t.get("task_state", {}).get("priority", 1) >= 4])
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # 生成趋势数据
            trend_data = [
                {"month": "1月", "completed": 12},
                {"month": "2月", "completed": 19},
                {"month": "3月", "completed": 23},
                {"month": "4月", "completed": 25},
                {"month": "5月", "completed": 32},
                {"month": "6月", "completed": completed_tasks}
            ]
            
            # 生成分类数据
            category_data = [
                {"category": "工作", "count": int(total_tasks * 0.45)},
                {"category": "学习", "count": int(total_tasks * 0.25)},
                {"category": "生活", "count": int(total_tasks * 0.20)},
                {"category": "其他", "count": int(total_tasks * 0.10)}
            ]
            
            return MVP2Analytics(
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                pending_tasks=pending_tasks,
                urgent_tasks=urgent_tasks,
                completion_rate=round(completion_rate, 1),
                trend_data=trend_data,
                category_data=category_data
            )
        except Exception as e:
            logger.error(f"分析数据转换失败: {e}")
            raise ValueError(f"分析数据转换错误: {e}")


class MVP2StateSync:
    """MVP2前端状态同步管理器"""
    
    def __init__(self):
        self.sync_enabled = True
        self.sync_interval = 5  # 秒
        self.last_sync = None
        self.sync_callbacks = []
    
    def register_sync_callback(self, callback):
        """注册状态同步回调"""
        self.sync_callbacks.append(callback)
    
    def trigger_sync(self, data: Dict[str, Any]):
        """触发状态同步"""
        if not self.sync_enabled:
            return
        
        try:
            for callback in self.sync_callbacks:
                callback(data)
            self.last_sync = datetime.now(timezone.utc)
            logger.info("MVP2状态同步完成")
        except Exception as e:
            logger.error(f"状态同步失败: {e}")
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            "enabled": self.sync_enabled,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "interval": self.sync_interval,
            "callbacks_count": len(self.sync_callbacks)
        }


class MVP2ErrorHandler:
    """MVP2前端错误处理器"""
    
    @staticmethod
    def format_error_for_mvp2(error: Exception, context: str = "") -> Dict[str, Any]:
        """格式化错误信息为MVP2前端格式"""
        error_type = type(error).__name__
        error_message = str(error)
        
        # 错误类型映射
        error_mapping = {
            "ValidationError": "数据验证错误",
            "ConnectionError": "网络连接错误",
            "TimeoutError": "请求超时",
            "ValueError": "数据格式错误",
            "KeyError": "数据字段缺失",
            "Exception": "系统错误"
        }
        
        return {
            "error": True,
            "error_type": error_mapping.get(error_type, "未知错误"),
            "message": error_message,
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "user_message": MVP2ErrorHandler._get_user_friendly_message(error_type, error_message)
        }
    
    @staticmethod
    def _get_user_friendly_message(error_type: str, error_message: str) -> str:
        """获取用户友好的错误消息"""
        if "网络" in error_message or "connection" in error_message.lower():
            return "网络连接异常，请检查网络设置后重试"
        elif "超时" in error_message or "timeout" in error_message.lower():
            return "请求处理时间过长，请稍后重试"
        elif "验证" in error_message or "validation" in error_message.lower():
            return "输入数据格式不正确，请检查后重新提交"
        elif "权限" in error_message or "permission" in error_message.lower():
            return "您没有执行此操作的权限"
        else:
            return "系统暂时无法处理您的请求，请稍后重试"


class MVP2FeedbackCollector:
    """MVP2用户反馈收集器"""
    
    def __init__(self):
        self.feedback_queue = []
        self.max_queue_size = 1000
    
    def collect_user_feedback(self, feedback_data: Dict[str, Any]) -> bool:
        """收集用户反馈"""
        try:
            feedback_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": feedback_data.get("type", "general"),
                "rating": feedback_data.get("rating"),
                "message": feedback_data.get("message", ""),
                "context": feedback_data.get("context", {}),
                "user_agent": feedback_data.get("user_agent", ""),
                "session_id": feedback_data.get("session_id", "")
            }
            
            # 队列管理
            if len(self.feedback_queue) >= self.max_queue_size:
                self.feedback_queue.pop(0)  # 移除最旧的反馈
            
            self.feedback_queue.append(feedback_entry)
            logger.info(f"收集到用户反馈: {feedback_entry['type']}")
            return True
            
        except Exception as e:
            logger.error(f"收集用户反馈失败: {e}")
            return False
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """获取反馈摘要"""
        if not self.feedback_queue:
            return {"total": 0, "summary": "暂无反馈数据"}
        
        total_feedback = len(self.feedback_queue)
        feedback_types = {}
        ratings = []
        
        for feedback in self.feedback_queue:
            feedback_type = feedback.get("type", "general")
            feedback_types[feedback_type] = feedback_types.get(feedback_type, 0) + 1
            
            if feedback.get("rating"):
                ratings.append(feedback["rating"])
        
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        return {
            "total": total_feedback,
            "types": feedback_types,
            "average_rating": round(avg_rating, 2),
            "recent_feedback": self.feedback_queue[-5:] if self.feedback_queue else []
        }


class MVP2Adapter:
    """MVP2前端适配器主类"""
    
    def __init__(self):
        self.transformer = MVP2DataTransformer()
        self.state_sync = MVP2StateSync()
        self.error_handler = MVP2ErrorHandler()
        self.feedback_collector = MVP2FeedbackCollector()
        self.logger = logging.getLogger(__name__)
    
    def transform_task_for_frontend(self, task_state: LangGraphTaskState) -> Dict[str, Any]:
        """为前端转换任务数据"""
        try:
            mvp2_task = self.transformer.task_to_mvp2(task_state)
            return asdict(mvp2_task)
        except Exception as e:
            self.logger.error(f"任务转换失败: {e}")
            return self.error_handler.format_error_for_mvp2(e, "task_transformation")
    
    def transform_task_from_frontend(self, mvp2_data: Dict[str, Any]) -> TaskRequest:
        """从前端转换任务数据"""
        try:
            return self.transformer.mvp2_to_task_request(mvp2_data)
        except Exception as e:
            self.logger.error(f"前端任务数据转换失败: {e}")
            raise
    
    def transform_chat_for_frontend(self, message: ChatMessage) -> Dict[str, Any]:
        """为前端转换聊天消息"""
        try:
            mvp2_message = self.transformer.chat_message_to_mvp2(message)
            return asdict(mvp2_message)
        except Exception as e:
            self.logger.error(f"聊天消息转换失败: {e}")
            return self.error_handler.format_error_for_mvp2(e, "chat_transformation")
    
    def transform_analytics_for_frontend(self, analytics: AnalyticsData, tasks: List[LangGraphTaskState]) -> Dict[str, Any]:
        """为前端转换分析数据"""
        try:
            mvp2_analytics = self.transformer.analytics_to_mvp2(analytics, tasks)
            return asdict(mvp2_analytics)
        except Exception as e:
            self.logger.error(f"分析数据转换失败: {e}")
            return self.error_handler.format_error_for_mvp2(e, "analytics_transformation")
    
    def handle_frontend_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """处理前端错误"""
        return self.error_handler.format_error_for_mvp2(error, context)
    
    def sync_state_to_frontend(self, data: Dict[str, Any]):
        """同步状态到前端"""
        self.state_sync.trigger_sync(data)
    
    def collect_feedback(self, feedback_data: Dict[str, Any]) -> bool:
        """收集用户反馈"""
        return self.feedback_collector.collect_user_feedback(feedback_data)
    
    def get_adapter_status(self) -> Dict[str, Any]:
        """获取适配器状态"""
        return {
            "sync_status": self.state_sync.get_sync_status(),
            "feedback_summary": self.feedback_collector.get_feedback_summary(),
            "adapter_version": "1.0.0",
            "last_activity": datetime.now().isoformat()
        }


# 全局适配器实例
mvp2_adapter = MVP2Adapter()