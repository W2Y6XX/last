"""
MVP2前端错误处理和用户反馈系统
提供用户友好的错误处理和反馈收集机制
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import asyncio
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误分类"""
    NETWORK = "network"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class MVP2Error:
    """MVP2错误数据模型"""
    error_id: str
    error_code: str
    error_type: str
    message: str
    user_message: str
    severity: str
    category: str
    context: Dict[str, Any]
    timestamp: str
    stack_trace: Optional[str] = None
    resolution_steps: List[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class UserFeedback:
    """用户反馈数据模型"""
    feedback_id: str
    error_id: Optional[str]
    feedback_type: str  # bug_report, feature_request, general
    rating: Optional[int]  # 1-5
    message: str
    user_context: Dict[str, Any]
    timestamp: str
    status: str = "pending"  # pending, reviewed, resolved
    tags: List[str] = None


class MVP2ErrorClassifier:
    """MVP2错误分类器"""
    
    def __init__(self):
        self.classification_rules = {
            # 网络错误
            ErrorCategory.NETWORK: [
                "connection", "timeout", "network", "unreachable",
                "dns", "socket", "http", "ssl", "certificate"
            ],
            # 验证错误
            ErrorCategory.VALIDATION: [
                "validation", "invalid", "format", "required",
                "missing", "empty", "length", "range"
            ],
            # 认证错误
            ErrorCategory.AUTHENTICATION: [
                "authentication", "login", "password", "token",
                "expired", "unauthorized", "credentials"
            ],
            # 授权错误
            ErrorCategory.AUTHORIZATION: [
                "authorization", "permission", "access", "forbidden",
                "privilege", "role", "scope"
            ],
            # 业务逻辑错误
            ErrorCategory.BUSINESS_LOGIC: [
                "business", "logic", "rule", "constraint",
                "conflict", "duplicate", "state"
            ],
            # 系统错误
            ErrorCategory.SYSTEM: [
                "system", "internal", "server", "database",
                "memory", "disk", "cpu", "resource"
            ]
        }
    
    def classify_error(self, error_message: str, error_type: str = "") -> ErrorCategory:
        """分类错误"""
        message_lower = error_message.lower()
        type_lower = error_type.lower()
        
        for category, keywords in self.classification_rules.items():
            for keyword in keywords:
                if keyword in message_lower or keyword in type_lower:
                    return category
        
        return ErrorCategory.UNKNOWN
    
    def determine_severity(self, error_type: str, category: ErrorCategory) -> ErrorSeverity:
        """确定错误严重程度"""
        # 关键系统错误
        if category == ErrorCategory.SYSTEM and any(
            keyword in error_type.lower() 
            for keyword in ["internal", "server", "database", "memory"]
        ):
            return ErrorSeverity.CRITICAL
        
        # 认证授权错误
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.AUTHORIZATION]:
            return ErrorSeverity.HIGH
        
        # 网络错误
        if category == ErrorCategory.NETWORK:
            return ErrorSeverity.MEDIUM
        
        # 验证错误
        if category == ErrorCategory.VALIDATION:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM


class MVP2ErrorRecovery:
    """MVP2错误恢复处理器"""
    
    def __init__(self):
        self.recovery_strategies = {
            ErrorCategory.NETWORK: self._network_recovery,
            ErrorCategory.VALIDATION: self._validation_recovery,
            ErrorCategory.AUTHENTICATION: self._auth_recovery,
            ErrorCategory.AUTHORIZATION: self._authz_recovery,
            ErrorCategory.BUSINESS_LOGIC: self._business_recovery,
            ErrorCategory.SYSTEM: self._system_recovery
        }
    
    def get_recovery_steps(self, error: MVP2Error) -> List[str]:
        """获取错误恢复步骤"""
        category = ErrorCategory(error.category)
        
        if category in self.recovery_strategies:
            return self.recovery_strategies[category](error)
        
        return self._default_recovery(error)
    
    def _network_recovery(self, error: MVP2Error) -> List[str]:
        """网络错误恢复"""
        return [
            "检查网络连接是否正常",
            "尝试刷新页面",
            "检查防火墙设置",
            "联系网络管理员",
            "稍后重试"
        ]
    
    def _validation_recovery(self, error: MVP2Error) -> List[str]:
        """验证错误恢复"""
        return [
            "检查输入数据格式",
            "确保必填字段已填写",
            "验证数据范围和长度",
            "参考输入示例",
            "重新提交表单"
        ]
    
    def _auth_recovery(self, error: MVP2Error) -> List[str]:
        """认证错误恢复"""
        return [
            "检查用户名和密码",
            "尝试重新登录",
            "检查账户是否被锁定",
            "重置密码",
            "联系系统管理员"
        ]
    
    def _authz_recovery(self, error: MVP2Error) -> List[str]:
        """授权错误恢复"""
        return [
            "检查用户权限",
            "联系管理员申请权限",
            "确认操作范围",
            "切换到有权限的账户",
            "查看帮助文档"
        ]
    
    def _business_recovery(self, error: MVP2Error) -> List[str]:
        """业务逻辑错误恢复"""
        return [
            "检查业务规则",
            "验证数据完整性",
            "确认操作顺序",
            "查看相关文档",
            "联系业务支持"
        ]
    
    def _system_recovery(self, error: MVP2Error) -> List[str]:
        """系统错误恢复"""
        return [
            "稍后重试",
            "刷新页面",
            "清除浏览器缓存",
            "联系技术支持",
            "查看系统状态页面"
        ]
    
    def _default_recovery(self, error: MVP2Error) -> List[str]:
        """默认恢复步骤"""
        return [
            "刷新页面重试",
            "检查输入数据",
            "查看帮助文档",
            "联系技术支持",
            "稍后再试"
        ]


class MVP2UserFeedbackManager:
    """MVP2用户反馈管理器"""
    
    def __init__(self, max_feedback_size: int = 10000):
        self.feedback_storage: deque = deque(maxlen=max_feedback_size)
        self.feedback_stats = defaultdict(int)
        self.feedback_handlers: List[Callable] = []
    
    def add_feedback_handler(self, handler: Callable):
        """添加反馈处理器"""
        self.feedback_handlers.append(handler)
    
    async def collect_feedback(self, feedback_data: Dict[str, Any]) -> UserFeedback:
        """收集用户反馈"""
        try:
            feedback = UserFeedback(
                feedback_id=f"fb_{datetime.now().timestamp()}",
                error_id=feedback_data.get("error_id"),
                feedback_type=feedback_data.get("type", "general"),
                rating=feedback_data.get("rating"),
                message=feedback_data.get("message", ""),
                user_context=feedback_data.get("context", {}),
                timestamp=datetime.now().isoformat(),
                tags=feedback_data.get("tags", [])
            )
            
            # 存储反馈
            self.feedback_storage.append(feedback)
            
            # 更新统计
            self.feedback_stats[feedback.feedback_type] += 1
            if feedback.rating:
                self.feedback_stats[f"rating_{feedback.rating}"] += 1
            
            # 触发处理器
            for handler in self.feedback_handlers:
                try:
                    await handler(feedback)
                except Exception as e:
                    logger.error(f"反馈处理器执行失败: {e}")
            
            logger.info(f"收集用户反馈: {feedback.feedback_id}")
            return feedback
            
        except Exception as e:
            logger.error(f"收集用户反馈失败: {e}")
            raise
    
    def get_feedback_summary(self, days: int = 7) -> Dict[str, Any]:
        """获取反馈摘要"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_feedback = [
            fb for fb in self.feedback_storage
            if datetime.fromisoformat(fb.timestamp) >= cutoff_date
        ]
        
        # 统计分析
        total_feedback = len(recent_feedback)
        type_counts = defaultdict(int)
        rating_counts = defaultdict(int)
        
        for fb in recent_feedback:
            type_counts[fb.feedback_type] += 1
            if fb.rating:
                rating_counts[fb.rating] += 1
        
        # 计算平均评分
        total_ratings = sum(rating_counts.values())
        avg_rating = (
            sum(rating * count for rating, count in rating_counts.items()) / total_ratings
            if total_ratings > 0 else 0
        )
        
        return {
            "period_days": days,
            "total_feedback": total_feedback,
            "feedback_by_type": dict(type_counts),
            "ratings_distribution": dict(rating_counts),
            "average_rating": round(avg_rating, 2),
            "recent_feedback": [asdict(fb) for fb in recent_feedback[-10:]]
        }


class MVP2ErrorHandler:
    """MVP2前端错误处理器主类"""
    
    def __init__(self):
        self.classifier = MVP2ErrorClassifier()
        self.recovery = MVP2ErrorRecovery()
        self.feedback_manager = MVP2UserFeedbackManager()
        self.error_storage: deque = deque(maxlen=1000)
        self.error_stats = defaultdict(int)
        
        # 注册默认反馈处理器
        self.feedback_manager.add_feedback_handler(self._log_feedback)
    
    async def handle_error(
        self, 
        exception: Exception, 
        context: Dict[str, Any] = None
    ) -> MVP2Error:
        """处理错误并生成MVP2错误对象"""
        try:
            error_type = type(exception).__name__
            error_message = str(exception)
            
            # 分类错误
            category = self.classifier.classify_error(error_message, error_type)
            severity = self.classifier.determine_severity(error_type, category)
            
            # 创建错误对象
            error = MVP2Error(
                error_id=f"err_{datetime.now().timestamp()}",
                error_code=f"{category.value.upper()}_{error_type.upper()}",
                error_type=error_type,
                message=error_message,
                user_message=self._generate_user_message(error_message, category),
                severity=severity.value,
                category=category.value,
                context=context or {},
                timestamp=datetime.now().isoformat(),
                stack_trace=None  # 生产环境不返回堆栈跟踪
            )
            
            # 获取恢复步骤
            error.resolution_steps = self.recovery.get_recovery_steps(error)
            
            # 存储错误
            self.error_storage.append(error)
            
            # 更新统计
            self.error_stats[category.value] += 1
            self.error_stats[severity.value] += 1
            
            logger.error(f"处理MVP2错误: {error.error_id} - {error_message}")
            
            return error
            
        except Exception as e:
            logger.error(f"错误处理失败: {e}")
            # 返回默认错误
            return MVP2Error(
                error_id=f"err_fallback_{datetime.now().timestamp()}",
                error_code="UNKNOWN_ERROR",
                error_type="Exception",
                message="发生未知错误",
                user_message="系统遇到问题，请稍后重试",
                severity=ErrorSeverity.MEDIUM.value,
                category=ErrorCategory.UNKNOWN.value,
                context={},
                timestamp=datetime.now().isoformat(),
                resolution_steps=["刷新页面", "稍后重试", "联系技术支持"]
            )
    
    def _generate_user_message(self, error_message: str, category: ErrorCategory) -> str:
        """生成用户友好的错误消息"""
        user_messages = {
            ErrorCategory.NETWORK: "网络连接异常，请检查网络设置后重试",
            ErrorCategory.VALIDATION: "输入数据格式不正确，请检查后重新提交",
            ErrorCategory.AUTHENTICATION: "身份验证失败，请重新登录",
            ErrorCategory.AUTHORIZATION: "您没有执行此操作的权限",
            ErrorCategory.BUSINESS_LOGIC: "操作不符合业务规则，请检查后重试",
            ErrorCategory.SYSTEM: "系统暂时无法处理您的请求，请稍后重试",
            ErrorCategory.UNKNOWN: "系统遇到问题，请稍后重试"
        }
        
        return user_messages.get(category, "系统遇到问题，请稍后重试")
    
    async def _log_feedback(self, feedback: UserFeedback):
        """记录反馈日志"""
        logger.info(f"用户反馈: {feedback.feedback_type} - {feedback.message[:100]}")
    
    def get_error_summary(self, days: int = 7) -> Dict[str, Any]:
        """获取错误摘要"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_errors = [
            err for err in self.error_storage
            if datetime.fromisoformat(err.timestamp) >= cutoff_date
        ]
        
        # 统计分析
        total_errors = len(recent_errors)
        category_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for err in recent_errors:
            category_counts[err.category] += 1
            severity_counts[err.severity] += 1
        
        return {
            "period_days": days,
            "total_errors": total_errors,
            "errors_by_category": dict(category_counts),
            "errors_by_severity": dict(severity_counts),
            "recent_errors": [asdict(err) for err in recent_errors[-10:]]
        }
    
    async def collect_user_feedback(self, feedback_data: Dict[str, Any]) -> UserFeedback:
        """收集用户反馈"""
        return await self.feedback_manager.collect_feedback(feedback_data)
    
    def get_feedback_summary(self, days: int = 7) -> Dict[str, Any]:
        """获取反馈摘要"""
        return self.feedback_manager.get_feedback_summary(days)


# 全局错误处理器实例
mvp2_error_handler = MVP2ErrorHandler()