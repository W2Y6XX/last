"""错误处理集成 - 统一错误处理和监控系统"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from datetime import datetime
from abc import ABC, abstractmethod
import json

from ..workflow.error_recovery import (
    ErrorRecoveryHandler, 
    ErrorContext, 
    ErrorType, 
    ErrorSeverity,
    RecoveryStrategy,
    HealthChecker
)
from ..workflow.monitoring import WorkflowMonitor
from ..core.state import LangGraphTaskState
from ..legacy.task_state import TaskStatus

logger = logging.getLogger(__name__)


class ErrorReporter(ABC):
    """错误报告器抽象基类"""
    
    @abstractmethod
    async def report_error(self, error_context: ErrorContext) -> bool:
        """报告错误"""
        pass
    
    @abstractmethod
    async def report_recovery(self, error_context: ErrorContext, strategy: RecoveryStrategy) -> bool:
        """报告恢复"""
        pass


class LogErrorReporter(ErrorReporter):
    """日志错误报告器"""
    
    def __init__(self, logger_name: str = "error_reporter"):
        self.logger = logging.getLogger(logger_name)
    
    async def report_error(self, error_context: ErrorContext) -> bool:
        """报告错误到日志"""
        try:
            self.logger.error(
                f"智能体错误 - Agent: {error_context.agent_id}, "
                f"Task: {error_context.task_id}, "
                f"Type: {error_context.error_type.value}, "
                f"Severity: {error_context.severity.value}, "
                f"Error: {error_context.error}"
            )
            return True
        except Exception as e:
            self.logger.error(f"错误报告失败: {e}")
            return False
    
    async def report_recovery(self, error_context: ErrorContext, strategy: RecoveryStrategy) -> bool:
        """报告恢复到日志"""
        try:
            self.logger.info(
                f"错误恢复 - Agent: {error_context.agent_id}, "
                f"Task: {error_context.task_id}, "
                f"Strategy: {strategy.value}, "
                f"Attempt: {error_context.retry_count + 1}"
            )
            return True
        except Exception as e:
            self.logger.error(f"恢复报告失败: {e}")
            return False


class MetricsErrorReporter(ErrorReporter):
    """指标错误报告器"""
    
    def __init__(self):
        self.error_metrics = {
            "total_errors": 0,
            "errors_by_type": {},
            "errors_by_severity": {},
            "errors_by_agent": {},
            "recovery_attempts": 0,
            "successful_recoveries": 0
        }
    
    async def report_error(self, error_context: ErrorContext) -> bool:
        """报告错误到指标"""
        try:
            self.error_metrics["total_errors"] += 1
            
            # 按类型统计
            error_type = error_context.error_type.value
            self.error_metrics["errors_by_type"][error_type] = (
                self.error_metrics["errors_by_type"].get(error_type, 0) + 1
            )
            
            # 按严重程度统计
            severity = error_context.severity.value
            self.error_metrics["errors_by_severity"][severity] = (
                self.error_metrics["errors_by_severity"].get(severity, 0) + 1
            )
            
            # 按智能体统计
            agent_id = error_context.agent_id
            self.error_metrics["errors_by_agent"][agent_id] = (
                self.error_metrics["errors_by_agent"].get(agent_id, 0) + 1
            )
            
            return True
        except Exception as e:
            logger.error(f"指标报告失败: {e}")
            return False
    
    async def report_recovery(self, error_context: ErrorContext, strategy: RecoveryStrategy) -> bool:
        """报告恢复到指标"""
        try:
            self.error_metrics["recovery_attempts"] += 1
            
            if strategy in [RecoveryStrategy.RETRY, RecoveryStrategy.FALLBACK, RecoveryStrategy.FAILOVER]:
                self.error_metrics["successful_recoveries"] += 1
            
            return True
        except Exception as e:
            logger.error(f"恢复指标报告失败: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取错误指标"""
        return self.error_metrics.copy()


class WebhookErrorReporter(ErrorReporter):
    """Webhook错误报告器"""
    
    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}
    
    async def report_error(self, error_context: ErrorContext) -> bool:
        """报告错误到Webhook"""
        try:
            import aiohttp
            
            payload = {
                "type": "error",
                "timestamp": error_context.timestamp.isoformat(),
                "agent_id": error_context.agent_id,
                "task_id": error_context.task_id,
                "error_type": error_context.error_type.value,
                "severity": error_context.severity.value,
                "error_message": str(error_context.error),
                "retry_count": error_context.retry_count,
                "metadata": error_context.metadata
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status < 400
                    
        except Exception as e:
            logger.error(f"Webhook错误报告失败: {e}")
            return False
    
    async def report_recovery(self, error_context: ErrorContext, strategy: RecoveryStrategy) -> bool:
        """报告恢复到Webhook"""
        try:
            import aiohttp
            
            payload = {
                "type": "recovery",
                "timestamp": datetime.now().isoformat(),
                "agent_id": error_context.agent_id,
                "task_id": error_context.task_id,
                "recovery_strategy": strategy.value,
                "original_error": {
                    "type": error_context.error_type.value,
                    "severity": error_context.severity.value,
                    "message": str(error_context.error)
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status < 400
                    
        except Exception as e:
            logger.error(f"Webhook恢复报告失败: {e}")
            return False


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.alert_rules: List[Dict[str, Any]] = []
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self.alert_handlers: List[Callable] = []
    
    def add_alert_rule(
        self,
        name: str,
        condition: Callable[[ErrorContext], bool],
        severity: str = "warning",
        cooldown_minutes: int = 5,
        description: str = ""
    ) -> None:
        """添加告警规则"""
        rule = {
            "name": name,
            "condition": condition,
            "severity": severity,
            "cooldown_minutes": cooldown_minutes,
            "description": description,
            "last_triggered": None
        }
        self.alert_rules.append(rule)
        logger.info(f"添加告警规则: {name}")
    
    def add_alert_handler(self, handler: Callable) -> None:
        """添加告警处理器"""
        self.alert_handlers.append(handler)
    
    async def check_alerts(self, error_context: ErrorContext) -> None:
        """检查告警条件"""
        current_time = datetime.now()
        
        for rule in self.alert_rules:
            try:
                # 检查冷却时间
                if rule["last_triggered"]:
                    cooldown = timedelta(minutes=rule["cooldown_minutes"])
                    if current_time - rule["last_triggered"] < cooldown:
                        continue
                
                # 检查告警条件
                if rule["condition"](error_context):
                    alert = {
                        "rule_name": rule["name"],
                        "severity": rule["severity"],
                        "description": rule["description"],
                        "error_context": error_context.to_dict(),
                        "triggered_at": current_time.isoformat()
                    }
                    
                    # 触发告警
                    await self._trigger_alert(alert)
                    rule["last_triggered"] = current_time
                    
            except Exception as e:
                logger.error(f"告警规则检查失败 {rule['name']}: {e}")
    
    async def _trigger_alert(self, alert: Dict[str, Any]) -> None:
        """触发告警"""
        alert_id = f"{alert['rule_name']}_{alert['triggered_at']}"
        self.active_alerts[alert_id] = alert
        
        logger.warning(f"触发告警: {alert['rule_name']} - {alert['description']}")
        
        # 调用告警处理器
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")
    
    def get_active_alerts(self) -> Dict[str, Dict[str, Any]]:
        """获取活跃告警"""
        return self.active_alerts.copy()
    
    def clear_alert(self, alert_id: str) -> bool:
        """清除告警"""
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
            logger.info(f"清除告警: {alert_id}")
            return True
        return False


class IntegratedErrorHandler:
    """集成错误处理器"""
    
    def __init__(
        self,
        error_recovery_handler: ErrorRecoveryHandler,
        workflow_monitor: Optional[WorkflowMonitor] = None
    ):
        self.error_recovery_handler = error_recovery_handler
        self.workflow_monitor = workflow_monitor
        
        # 错误报告器
        self.error_reporters: List[ErrorReporter] = []
        
        # 告警管理器
        self.alert_manager = AlertManager()
        
        # 健康检查器
        self.health_checker = HealthChecker(error_recovery_handler)
        
        # 自愈机制
        self.self_healing_enabled = True
        self.healing_strategies: Dict[str, Callable] = {}
        
        # 初始化默认组件
        self._initialize_default_components()
        
        logger.info("集成错误处理器初始化完成")
    
    def _initialize_default_components(self) -> None:
        """初始化默认组件"""
        # 添加默认错误报告器
        self.add_error_reporter(LogErrorReporter())
        self.add_error_reporter(MetricsErrorReporter())
        
        # 添加默认告警规则
        self._add_default_alert_rules()
        
        # 添加默认健康检查
        self._add_default_health_checks()
        
        # 添加默认自愈策略
        self._add_default_healing_strategies()
    
    def _add_default_alert_rules(self) -> None:
        """添加默认告警规则"""
        # 高频错误告警
        self.alert_manager.add_alert_rule(
            name="high_error_rate",
            condition=lambda ctx: ctx.retry_count >= 3,
            severity="critical",
            description="智能体错误重试次数过多"
        )
        
        # 严重错误告警
        self.alert_manager.add_alert_rule(
            name="critical_error",
            condition=lambda ctx: ctx.severity == ErrorSeverity.CRITICAL,
            severity="critical",
            description="发生严重错误"
        )
        
        # 系统错误告警
        self.alert_manager.add_alert_rule(
            name="system_error",
            condition=lambda ctx: ctx.error_type == ErrorType.SYSTEM_ERROR,
            severity="warning",
            description="系统错误"
        )
    
    def _add_default_health_checks(self) -> None:
        """添加默认健康检查"""
        # 错误率健康检查
        async def error_rate_check():
            stats = self.error_recovery_handler.get_recovery_statistics()
            error_rate = 1 - stats.get("success_rate", 0)
            return error_rate < 0.1  # 错误率小于10%
        
        self.health_checker.add_health_check("error_rate", error_rate_check)
        
        # 熔断器健康检查
        async def circuit_breaker_check():
            stats = self.error_recovery_handler.get_recovery_statistics()
            return stats.get("circuit_breaks", 0) == 0
        
        self.health_checker.add_health_check("circuit_breakers", circuit_breaker_check)
    
    def _add_default_healing_strategies(self) -> None:
        """添加默认自愈策略"""
        # 重置熔断器
        async def reset_circuit_breakers():
            self.error_recovery_handler.reset_circuit_breakers()
            logger.info("自愈: 重置熔断器")
        
        self.healing_strategies["reset_circuit_breakers"] = reset_circuit_breakers
        
        # 清理错误历史
        async def cleanup_error_history():
            self.error_recovery_handler.clear_error_history()
            logger.info("自愈: 清理错误历史")
        
        self.healing_strategies["cleanup_error_history"] = cleanup_error_history
    
    def add_error_reporter(self, reporter: ErrorReporter) -> None:
        """添加错误报告器"""
        self.error_reporters.append(reporter)
        logger.info(f"添加错误报告器: {type(reporter).__name__}")
    
    def add_webhook_reporter(self, webhook_url: str, headers: Optional[Dict[str, str]] = None) -> None:
        """添加Webhook报告器"""
        reporter = WebhookErrorReporter(webhook_url, headers)
        self.add_error_reporter(reporter)
    
    async def handle_integrated_error(
        self,
        error: Exception,
        agent_id: str,
        task_id: str,
        state: LangGraphTaskState,
        retry_count: int = 0
    ) -> Tuple[RecoveryStrategy, Optional[LangGraphTaskState]]:
        """集成错误处理"""
        try:
            # 使用错误恢复处理器处理错误
            strategy, recovered_state = await self.error_recovery_handler.handle_error(
                error, agent_id, task_id, state, retry_count
            )
            
            # 创建错误上下文
            error_type, severity = self.error_recovery_handler.error_classifier.classify_error(error)
            error_context = ErrorContext(
                error=error,
                error_type=error_type,
                severity=severity,
                agent_id=agent_id,
                task_id=task_id,
                retry_count=retry_count
            )
            
            # 报告错误
            await self._report_error(error_context)
            
            # 检查告警
            await self.alert_manager.check_alerts(error_context)
            
            # 报告恢复
            await self._report_recovery(error_context, strategy)
            
            # 更新监控指标
            if self.workflow_monitor:
                await self.workflow_monitor.record_error(
                    agent_id=agent_id,
                    error_type=error_type.value,
                    severity=severity.value,
                    recovery_strategy=strategy.value
                )
            
            # 触发自愈机制
            if self.self_healing_enabled:
                await self._trigger_self_healing(error_context, strategy)
            
            return strategy, recovered_state
            
        except Exception as integration_error:
            logger.error(f"集成错误处理失败: {integration_error}")
            return RecoveryStrategy.MANUAL_INTERVENTION, None
    
    async def _report_error(self, error_context: ErrorContext) -> None:
        """报告错误到所有报告器"""
        for reporter in self.error_reporters:
            try:
                await reporter.report_error(error_context)
            except Exception as e:
                logger.error(f"错误报告失败 {type(reporter).__name__}: {e}")
    
    async def _report_recovery(self, error_context: ErrorContext, strategy: RecoveryStrategy) -> None:
        """报告恢复到所有报告器"""
        for reporter in self.error_reporters:
            try:
                await reporter.report_recovery(error_context, strategy)
            except Exception as e:
                logger.error(f"恢复报告失败 {type(reporter).__name__}: {e}")
    
    async def _trigger_self_healing(self, error_context: ErrorContext, strategy: RecoveryStrategy) -> None:
        """触发自愈机制"""
        try:
            # 根据错误类型和恢复策略选择自愈策略
            if strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                # 延迟重置熔断器
                asyncio.create_task(self._delayed_healing("reset_circuit_breakers", 300))  # 5分钟后
            
            elif error_context.severity == ErrorSeverity.HIGH:
                # 清理错误历史
                asyncio.create_task(self._delayed_healing("cleanup_error_history", 600))  # 10分钟后
            
        except Exception as e:
            logger.error(f"自愈机制触发失败: {e}")
    
    async def _delayed_healing(self, strategy_name: str, delay_seconds: int) -> None:
        """延迟自愈"""
        await asyncio.sleep(delay_seconds)
        
        if strategy_name in self.healing_strategies:
            try:
                healing_func = self.healing_strategies[strategy_name]
                if asyncio.iscoroutinefunction(healing_func):
                    await healing_func()
                else:
                    healing_func()
            except Exception as e:
                logger.error(f"自愈策略执行失败 {strategy_name}: {e}")
    
    def add_healing_strategy(self, name: str, strategy_func: Callable) -> None:
        """添加自愈策略"""
        self.healing_strategies[name] = strategy_func
        logger.info(f"添加自愈策略: {name}")
    
    def enable_self_healing(self) -> None:
        """启用自愈机制"""
        self.self_healing_enabled = True
        logger.info("自愈机制已启用")
    
    def disable_self_healing(self) -> None:
        """禁用自愈机制"""
        self.self_healing_enabled = False
        logger.info("自愈机制已禁用")
    
    async def start_health_monitoring(self) -> None:
        """开始健康监控"""
        await self.health_checker.start_monitoring()
    
    def stop_health_monitoring(self) -> None:
        """停止健康监控"""
        self.health_checker.stop_monitoring()
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        return {
            "overall_healthy": self.health_checker.is_system_healthy(),
            "health_checks": self.health_checker.get_health_status(),
            "active_alerts": self.alert_manager.get_active_alerts(),
            "recovery_stats": self.error_recovery_handler.get_recovery_statistics(),
            "self_healing_enabled": self.self_healing_enabled
        }
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """获取错误指标"""
        metrics = {}
        
        for reporter in self.error_reporters:
            if isinstance(reporter, MetricsErrorReporter):
                metrics.update(reporter.get_metrics())
                break
        
        return metrics
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """获取综合状态"""
        return {
            "system_health": self.get_system_health(),
            "error_metrics": self.get_error_metrics(),
            "error_history": self.error_recovery_handler.get_error_history(50),
            "timestamp": datetime.now().isoformat()
        }


# 便捷函数
def create_integrated_error_handler(
    error_recovery_handler: ErrorRecoveryHandler,
    workflow_monitor: Optional[WorkflowMonitor] = None,
    webhook_url: Optional[str] = None
) -> IntegratedErrorHandler:
    """创建集成错误处理器"""
    handler = IntegratedErrorHandler(error_recovery_handler, workflow_monitor)
    
    if webhook_url:
        handler.add_webhook_reporter(webhook_url)
    
    return handler


def setup_default_error_handling(
    error_recovery_handler: ErrorRecoveryHandler
) -> IntegratedErrorHandler:
    """设置默认错误处理"""
    return create_integrated_error_handler(error_recovery_handler)