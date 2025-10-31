"""错误恢复处理器 - 智能体错误重试和故障转移机制"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import traceback
import random

from ..core.state import LangGraphTaskState, WorkflowPhase, update_workflow_phase
from ..legacy.task_state import TaskStatus
from .checkpoint_manager import CheckpointManager

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """错误严重程度"""
    LOW = "low"           # 轻微错误，可以重试
    MEDIUM = "medium"     # 中等错误，需要降级处理
    HIGH = "high"         # 严重错误，需要故障转移
    CRITICAL = "critical" # 致命错误，需要人工干预


class RecoveryStrategy(str, Enum):
    """恢复策略"""
    RETRY = "retry"                    # 重试
    FALLBACK = "fallback"             # 降级处理
    FAILOVER = "failover"             # 故障转移
    SKIP = "skip"                     # 跳过
    MANUAL_INTERVENTION = "manual"     # 人工干预
    CIRCUIT_BREAKER = "circuit_break" # 熔断


class ErrorType(str, Enum):
    """错误类型"""
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    AUTHENTICATION_ERROR = "auth_error"
    RATE_LIMIT = "rate_limit"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    VALIDATION_ERROR = "validation_error"
    BUSINESS_LOGIC_ERROR = "business_error"
    SYSTEM_ERROR = "system_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorContext:
    """错误上下文"""
    
    def __init__(
        self,
        error: Exception,
        error_type: ErrorType,
        severity: ErrorSeverity,
        agent_id: str,
        task_id: str,
        retry_count: int = 0,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.error = error
        self.error_type = error_type
        self.severity = severity
        self.agent_id = agent_id
        self.task_id = task_id
        self.retry_count = retry_count
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}
        self.traceback = traceback.format_exc()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_message": str(self.error),
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "traceback": self.traceback
        }


class RecoveryAction:
    """恢复动作"""
    
    def __init__(
        self,
        strategy: RecoveryStrategy,
        delay_seconds: float = 0,
        max_attempts: int = 3,
        fallback_agent: Optional[str] = None,
        custom_handler: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.strategy = strategy
        self.delay_seconds = delay_seconds
        self.max_attempts = max_attempts
        self.fallback_agent = fallback_agent
        self.custom_handler = custom_handler
        self.metadata = metadata or {}


class ErrorClassifier:
    """错误分类器"""
    
    def __init__(self):
        self.classification_rules = self._initialize_classification_rules()
    
    def _initialize_classification_rules(self) -> Dict[str, Tuple[ErrorType, ErrorSeverity]]:
        """初始化分类规则"""
        return {
            # 超时错误
            "timeout": (ErrorType.TIMEOUT, ErrorSeverity.MEDIUM),
            "timed out": (ErrorType.TIMEOUT, ErrorSeverity.MEDIUM),
            "connection timeout": (ErrorType.TIMEOUT, ErrorSeverity.MEDIUM),
            
            # 连接错误
            "connection": (ErrorType.CONNECTION_ERROR, ErrorSeverity.MEDIUM),
            "network": (ErrorType.CONNECTION_ERROR, ErrorSeverity.MEDIUM),
            "unreachable": (ErrorType.CONNECTION_ERROR, ErrorSeverity.HIGH),
            
            # 认证错误
            "authentication": (ErrorType.AUTHENTICATION_ERROR, ErrorSeverity.HIGH),
            "unauthorized": (ErrorType.AUTHENTICATION_ERROR, ErrorSeverity.HIGH),
            "forbidden": (ErrorType.AUTHENTICATION_ERROR, ErrorSeverity.HIGH),
            
            # 限流错误
            "rate limit": (ErrorType.RATE_LIMIT, ErrorSeverity.MEDIUM),
            "too many requests": (ErrorType.RATE_LIMIT, ErrorSeverity.MEDIUM),
            "quota exceeded": (ErrorType.RATE_LIMIT, ErrorSeverity.MEDIUM),
            
            # 资源耗尽
            "out of memory": (ErrorType.RESOURCE_EXHAUSTED, ErrorSeverity.HIGH),
            "disk full": (ErrorType.RESOURCE_EXHAUSTED, ErrorSeverity.HIGH),
            "resource exhausted": (ErrorType.RESOURCE_EXHAUSTED, ErrorSeverity.HIGH),
            
            # 验证错误
            "validation": (ErrorType.VALIDATION_ERROR, ErrorSeverity.LOW),
            "invalid": (ErrorType.VALIDATION_ERROR, ErrorSeverity.LOW),
            "malformed": (ErrorType.VALIDATION_ERROR, ErrorSeverity.LOW),
            
            # 业务逻辑错误
            "business": (ErrorType.BUSINESS_LOGIC_ERROR, ErrorSeverity.MEDIUM),
            "logic": (ErrorType.BUSINESS_LOGIC_ERROR, ErrorSeverity.MEDIUM),
            
            # 系统错误
            "system": (ErrorType.SYSTEM_ERROR, ErrorSeverity.HIGH),
            "internal": (ErrorType.SYSTEM_ERROR, ErrorSeverity.HIGH),
            "fatal": (ErrorType.SYSTEM_ERROR, ErrorSeverity.CRITICAL)
        }
    
    def classify_error(self, error: Exception) -> Tuple[ErrorType, ErrorSeverity]:
        """分类错误"""
        error_message = str(error).lower()
        error_class = type(error).__name__.lower()
        
        # 检查错误消息
        for keyword, (error_type, severity) in self.classification_rules.items():
            if keyword in error_message or keyword in error_class:
                return error_type, severity
        
        # 根据异常类型分类
        if isinstance(error, TimeoutError):
            return ErrorType.TIMEOUT, ErrorSeverity.MEDIUM
        elif isinstance(error, ConnectionError):
            return ErrorType.CONNECTION_ERROR, ErrorSeverity.MEDIUM
        elif isinstance(error, ValueError):
            return ErrorType.VALIDATION_ERROR, ErrorSeverity.LOW
        elif isinstance(error, MemoryError):
            return ErrorType.RESOURCE_EXHAUSTED, ErrorSeverity.HIGH
        elif isinstance(error, PermissionError):
            return ErrorType.AUTHENTICATION_ERROR, ErrorSeverity.HIGH
        
        # 默认分类
        return ErrorType.UNKNOWN_ERROR, ErrorSeverity.MEDIUM


class CircuitBreaker:
    """熔断器"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func: Callable, *args, **kwargs):
        """调用函数并处理熔断"""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    async def acall(self, func: Callable, *args, **kwargs):
        """异步调用函数并处理熔断"""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
        )
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class RetryPolicy:
    """重试策略"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """获取延迟时间"""
        if attempt <= 0:
            return 0
        
        # 指数退避
        delay = self.base_delay * (self.backoff_multiplier ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        # 添加抖动
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """是否应该重试"""
        return attempt < self.max_attempts


class ErrorRecoveryHandler:
    """错误恢复处理器"""
    
    def __init__(
        self,
        checkpoint_manager: Optional[CheckpointManager] = None,
        default_retry_policy: Optional[RetryPolicy] = None
    ):
        self.checkpoint_manager = checkpoint_manager
        self.default_retry_policy = default_retry_policy or RetryPolicy()
        
        # 错误分类器
        self.error_classifier = ErrorClassifier()
        
        # 熔断器管理
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # 恢复策略映射
        self.recovery_strategies = self._initialize_recovery_strategies()
        
        # 错误历史
        self.error_history: List[ErrorContext] = []
        
        # 统计信息
        self.recovery_stats = {
            "total_errors": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "manual_interventions": 0,
            "circuit_breaks": 0
        }
        
        logger.info("错误恢复处理器初始化完成")
    
    def _initialize_recovery_strategies(self) -> Dict[Tuple[ErrorType, ErrorSeverity], RecoveryAction]:
        """初始化恢复策略"""
        return {
            # 超时错误 - 重试
            (ErrorType.TIMEOUT, ErrorSeverity.LOW): RecoveryAction(
                RecoveryStrategy.RETRY, delay_seconds=1.0, max_attempts=3
            ),
            (ErrorType.TIMEOUT, ErrorSeverity.MEDIUM): RecoveryAction(
                RecoveryStrategy.RETRY, delay_seconds=2.0, max_attempts=2
            ),
            
            # 连接错误 - 重试或故障转移
            (ErrorType.CONNECTION_ERROR, ErrorSeverity.MEDIUM): RecoveryAction(
                RecoveryStrategy.RETRY, delay_seconds=5.0, max_attempts=2
            ),
            (ErrorType.CONNECTION_ERROR, ErrorSeverity.HIGH): RecoveryAction(
                RecoveryStrategy.FAILOVER, delay_seconds=0
            ),
            
            # 认证错误 - 人工干预
            (ErrorType.AUTHENTICATION_ERROR, ErrorSeverity.HIGH): RecoveryAction(
                RecoveryStrategy.MANUAL_INTERVENTION
            ),
            
            # 限流错误 - 延迟重试
            (ErrorType.RATE_LIMIT, ErrorSeverity.MEDIUM): RecoveryAction(
                RecoveryStrategy.RETRY, delay_seconds=30.0, max_attempts=2
            ),
            
            # 资源耗尽 - 故障转移
            (ErrorType.RESOURCE_EXHAUSTED, ErrorSeverity.HIGH): RecoveryAction(
                RecoveryStrategy.FAILOVER
            ),
            
            # 验证错误 - 跳过或降级
            (ErrorType.VALIDATION_ERROR, ErrorSeverity.LOW): RecoveryAction(
                RecoveryStrategy.FALLBACK
            ),
            
            # 业务逻辑错误 - 降级处理
            (ErrorType.BUSINESS_LOGIC_ERROR, ErrorSeverity.MEDIUM): RecoveryAction(
                RecoveryStrategy.FALLBACK
            ),
            
            # 系统错误 - 根据严重程度处理
            (ErrorType.SYSTEM_ERROR, ErrorSeverity.HIGH): RecoveryAction(
                RecoveryStrategy.FAILOVER
            ),
            (ErrorType.SYSTEM_ERROR, ErrorSeverity.CRITICAL): RecoveryAction(
                RecoveryStrategy.MANUAL_INTERVENTION
            ),
            
            # 未知错误 - 重试
            (ErrorType.UNKNOWN_ERROR, ErrorSeverity.MEDIUM): RecoveryAction(
                RecoveryStrategy.RETRY, delay_seconds=2.0, max_attempts=1
            )
        }
    
    async def handle_error(
        self,
        error: Exception,
        agent_id: str,
        task_id: str,
        state: LangGraphTaskState,
        retry_count: int = 0
    ) -> Tuple[RecoveryStrategy, Optional[LangGraphTaskState]]:
        """处理错误并返回恢复策略"""
        try:
            self.recovery_stats["total_errors"] += 1
            
            # 分类错误
            error_type, severity = self.error_classifier.classify_error(error)
            
            # 创建错误上下文
            error_context = ErrorContext(
                error=error,
                error_type=error_type,
                severity=severity,
                agent_id=agent_id,
                task_id=task_id,
                retry_count=retry_count,
                metadata={
                    "workflow_phase": state["workflow_context"]["current_phase"].value,
                    "task_status": state["task_state"]["status"].value
                }
            )
            
            # 记录错误历史
            self.error_history.append(error_context)
            
            # 获取恢复策略
            recovery_action = self._get_recovery_action(error_type, severity, agent_id)
            
            # 执行恢复策略
            strategy, recovered_state = await self._execute_recovery_action(
                recovery_action, error_context, state
            )
            
            logger.info(f"错误恢复策略: {strategy.value}, 智能体: {agent_id}, 错误: {error_type.value}")
            
            return strategy, recovered_state
            
        except Exception as recovery_error:
            logger.error(f"错误恢复处理失败: {recovery_error}")
            self.recovery_stats["failed_recoveries"] += 1
            return RecoveryStrategy.MANUAL_INTERVENTION, None
    
    def _get_recovery_action(
        self, 
        error_type: ErrorType, 
        severity: ErrorSeverity, 
        agent_id: str
    ) -> RecoveryAction:
        """获取恢复动作"""
        # 检查熔断器状态
        if agent_id in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[agent_id]
            if circuit_breaker.state == "open":
                return RecoveryAction(RecoveryStrategy.CIRCUIT_BREAKER)
        
        # 获取预定义策略
        strategy_key = (error_type, severity)
        if strategy_key in self.recovery_strategies:
            return self.recovery_strategies[strategy_key]
        
        # 默认策略
        return RecoveryAction(RecoveryStrategy.RETRY, max_attempts=1)
    
    async def _execute_recovery_action(
        self,
        action: RecoveryAction,
        error_context: ErrorContext,
        state: LangGraphTaskState
    ) -> Tuple[RecoveryStrategy, Optional[LangGraphTaskState]]:
        """执行恢复动作"""
        try:
            if action.strategy == RecoveryStrategy.RETRY:
                return await self._handle_retry(action, error_context, state)
            
            elif action.strategy == RecoveryStrategy.FALLBACK:
                return await self._handle_fallback(action, error_context, state)
            
            elif action.strategy == RecoveryStrategy.FAILOVER:
                return await self._handle_failover(action, error_context, state)
            
            elif action.strategy == RecoveryStrategy.SKIP:
                return await self._handle_skip(action, error_context, state)
            
            elif action.strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                return await self._handle_circuit_breaker(action, error_context, state)
            
            elif action.strategy == RecoveryStrategy.MANUAL_INTERVENTION:
                return await self._handle_manual_intervention(action, error_context, state)
            
            else:
                logger.warning(f"未知恢复策略: {action.strategy}")
                return RecoveryStrategy.MANUAL_INTERVENTION, None
                
        except Exception as e:
            logger.error(f"执行恢复动作失败: {e}")
            return RecoveryStrategy.MANUAL_INTERVENTION, None
    
    async def _handle_retry(
        self,
        action: RecoveryAction,
        error_context: ErrorContext,
        state: LangGraphTaskState
    ) -> Tuple[RecoveryStrategy, Optional[LangGraphTaskState]]:
        """处理重试策略"""
        if error_context.retry_count >= action.max_attempts:
            logger.warning(f"重试次数已达上限: {error_context.agent_id}")
            return RecoveryStrategy.FAILOVER, state
        
        # 等待延迟
        if action.delay_seconds > 0:
            delay = self.default_retry_policy.get_delay(error_context.retry_count + 1)
            await asyncio.sleep(min(delay, action.delay_seconds))
        
        # 更新状态
        state["retry_count"] = error_context.retry_count + 1
        state["workflow_context"]["execution_metadata"]["last_retry_at"] = datetime.now().isoformat()
        
        self.recovery_stats["successful_recoveries"] += 1
        return RecoveryStrategy.RETRY, state
    
    async def _handle_fallback(
        self,
        action: RecoveryAction,
        error_context: ErrorContext,
        state: LangGraphTaskState
    ) -> Tuple[RecoveryStrategy, Optional[LangGraphTaskState]]:
        """处理降级策略"""
        # 标记为降级模式
        state["workflow_context"]["execution_metadata"]["fallback_mode"] = True
        state["workflow_context"]["execution_metadata"]["fallback_reason"] = error_context.to_dict()
        
        # 如果有指定的降级智能体
        if action.fallback_agent:
            state["workflow_context"]["execution_metadata"]["fallback_agent"] = action.fallback_agent
        
        self.recovery_stats["successful_recoveries"] += 1
        return RecoveryStrategy.FALLBACK, state
    
    async def _handle_failover(
        self,
        action: RecoveryAction,
        error_context: ErrorContext,
        state: LangGraphTaskState
    ) -> Tuple[RecoveryStrategy, Optional[LangGraphTaskState]]:
        """处理故障转移策略"""
        # 标记故障智能体
        failed_agents = state["workflow_context"]["execution_metadata"].get("failed_agents", [])
        if error_context.agent_id not in failed_agents:
            failed_agents.append(error_context.agent_id)
        state["workflow_context"]["execution_metadata"]["failed_agents"] = failed_agents
        
        # 如果有备用智能体
        if action.fallback_agent:
            state["workflow_context"]["execution_metadata"]["failover_agent"] = action.fallback_agent
        
        # 创建检查点（如果可用）
        if self.checkpoint_manager:
            await self.checkpoint_manager.create_checkpoint(
                thread_id=state["task_state"]["task_id"],
                state=state,
                metadata={"failover": True, "failed_agent": error_context.agent_id}
            )
        
        self.recovery_stats["successful_recoveries"] += 1
        return RecoveryStrategy.FAILOVER, state
    
    async def _handle_skip(
        self,
        action: RecoveryAction,
        error_context: ErrorContext,
        state: LangGraphTaskState
    ) -> Tuple[RecoveryStrategy, Optional[LangGraphTaskState]]:
        """处理跳过策略"""
        # 标记跳过的智能体
        skipped_agents = state["workflow_context"]["execution_metadata"].get("skipped_agents", [])
        if error_context.agent_id not in skipped_agents:
            skipped_agents.append(error_context.agent_id)
        state["workflow_context"]["execution_metadata"]["skipped_agents"] = skipped_agents
        
        # 记录跳过原因
        state["workflow_context"]["execution_metadata"]["skip_reason"] = error_context.to_dict()
        
        self.recovery_stats["successful_recoveries"] += 1
        return RecoveryStrategy.SKIP, state
    
    async def _handle_circuit_breaker(
        self,
        action: RecoveryAction,
        error_context: ErrorContext,
        state: LangGraphTaskState
    ) -> Tuple[RecoveryStrategy, Optional[LangGraphTaskState]]:
        """处理熔断策略"""
        # 标记熔断状态
        state["workflow_context"]["execution_metadata"]["circuit_breaker_active"] = True
        state["workflow_context"]["execution_metadata"]["circuit_break_agent"] = error_context.agent_id
        
        self.recovery_stats["circuit_breaks"] += 1
        return RecoveryStrategy.CIRCUIT_BREAKER, state
    
    async def _handle_manual_intervention(
        self,
        action: RecoveryAction,
        error_context: ErrorContext,
        state: LangGraphTaskState
    ) -> Tuple[RecoveryStrategy, Optional[LangGraphTaskState]]:
        """处理人工干预策略"""
        # 标记需要人工干预
        state["workflow_context"]["execution_metadata"]["requires_human_intervention"] = True
        state["workflow_context"]["execution_metadata"]["intervention_reason"] = error_context.to_dict()
        
        # 更新工作流阶段
        state = update_workflow_phase(state, WorkflowPhase.ERROR_HANDLING)
        
        # 创建检查点（如果可用）
        if self.checkpoint_manager:
            await self.checkpoint_manager.create_checkpoint(
                thread_id=state["task_state"]["task_id"],
                state=state,
                metadata={"manual_intervention": True, "error": error_context.to_dict()}
            )
        
        self.recovery_stats["manual_interventions"] += 1
        return RecoveryStrategy.MANUAL_INTERVENTION, state
    
    def add_circuit_breaker(
        self,
        agent_id: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ) -> None:
        """为智能体添加熔断器"""
        self.circuit_breakers[agent_id] = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
        logger.info(f"为智能体 {agent_id} 添加熔断器")
    
    def remove_circuit_breaker(self, agent_id: str) -> None:
        """移除智能体的熔断器"""
        if agent_id in self.circuit_breakers:
            del self.circuit_breakers[agent_id]
            logger.info(f"移除智能体 {agent_id} 的熔断器")
    
    def add_recovery_strategy(
        self,
        error_type: ErrorType,
        severity: ErrorSeverity,
        action: RecoveryAction
    ) -> None:
        """添加自定义恢复策略"""
        self.recovery_strategies[(error_type, severity)] = action
        logger.info(f"添加恢复策略: {error_type.value}/{severity.value} -> {action.strategy.value}")
    
    def get_error_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取错误历史"""
        return [error.to_dict() for error in self.error_history[-limit:]]
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """获取恢复统计信息"""
        total_handled = self.recovery_stats["successful_recoveries"] + self.recovery_stats["failed_recoveries"]
        
        return {
            **self.recovery_stats,
            "success_rate": (
                self.recovery_stats["successful_recoveries"] / max(1, total_handled)
            ),
            "circuit_breakers_count": len(self.circuit_breakers),
            "error_history_count": len(self.error_history),
            "recovery_strategies_count": len(self.recovery_strategies)
        }
    
    def clear_error_history(self) -> None:
        """清空错误历史"""
        self.error_history.clear()
        logger.info("错误历史已清空")
    
    def reset_circuit_breakers(self) -> None:
        """重置所有熔断器"""
        for circuit_breaker in self.circuit_breakers.values():
            circuit_breaker.failure_count = 0
            circuit_breaker.state = "closed"
            circuit_breaker.last_failure_time = None
        logger.info("所有熔断器已重置")


class HealthChecker:
    """系统健康检查器"""
    
    def __init__(self, error_recovery_handler: ErrorRecoveryHandler):
        self.error_recovery_handler = error_recovery_handler
        self.health_checks: Dict[str, Callable] = {}
        self.health_status: Dict[str, Dict[str, Any]] = {}
        self.check_interval = 60  # 60秒检查间隔
        self.running = False
    
    def add_health_check(self, name: str, check_func: Callable) -> None:
        """添加健康检查"""
        self.health_checks[name] = check_func
        logger.info(f"添加健康检查: {name}")
    
    async def run_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """运行所有健康检查"""
        results = {}
        
        for name, check_func in self.health_checks.items():
            try:
                start_time = datetime.now()
                
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                end_time = datetime.now()
                check_time = (end_time - start_time).total_seconds()
                
                results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "check_time": check_time,
                    "timestamp": end_time.isoformat(),
                    "details": result if isinstance(result, dict) else {}
                }
                
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        self.health_status = results
        return results
    
    async def start_monitoring(self) -> None:
        """开始健康监控"""
        self.running = True
        logger.info("开始系统健康监控")
        
        while self.running:
            try:
                await self.run_health_checks()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"健康检查失败: {e}")
                await asyncio.sleep(self.check_interval)
    
    def stop_monitoring(self) -> None:
        """停止健康监控"""
        self.running = False
        logger.info("停止系统健康监控")
    
    def get_health_status(self) -> Dict[str, Dict[str, Any]]:
        """获取健康状态"""
        return self.health_status
    
    def is_system_healthy(self) -> bool:
        """检查系统是否健康"""
        if not self.health_status:
            return False
        
        return all(
            status.get("status") == "healthy" 
            for status in self.health_status.values()
        )


# 便捷函数
def create_error_recovery_handler(
    checkpoint_manager: Optional[CheckpointManager] = None,
    max_retries: int = 3,
    base_delay: float = 1.0
) -> ErrorRecoveryHandler:
    """创建错误恢复处理器"""
    retry_policy = RetryPolicy(
        max_attempts=max_retries,
        base_delay=base_delay
    )
    
    return ErrorRecoveryHandler(
        checkpoint_manager=checkpoint_manager,
        default_retry_policy=retry_policy
    )


def create_health_checker(error_recovery_handler: ErrorRecoveryHandler) -> HealthChecker:
    """创建健康检查器"""
    return HealthChecker(error_recovery_handler)