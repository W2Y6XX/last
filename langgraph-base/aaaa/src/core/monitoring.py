"""
系统监控 - 性能监控、指标收集和健康检查
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json

from ..utils.logging import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """指标数据"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str] = None
    unit: str = ""

    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


@dataclass
class Alert:
    """告警信息"""
    alert_id: str
    level: AlertLevel
    message: str
    source: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self._metrics: List[Metric] = []
        self._alerts: List[Alert] = []
        self._metric_handlers: Dict[str, List[Callable]] = {}
        self._alert_handlers: List[Callable] = []

        # 监控配置
        self._monitoring_interval = 30  # 秒
        self._metrics_retention_period = timedelta(hours=24)
        self._alerts_retention_period = timedelta(days=7)

        # 监控任务
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_monitoring = False

        # 性能计数器
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._timers: Dict[str, List[float]] = {}

    async def start_monitoring(self, coordinator) -> None:
        """开始监控"""
        if self._is_monitoring:
            return

        self.coordinator = coordinator
        self._is_monitoring = True

        # 启动监控任务
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance monitoring started")

    async def stop_monitoring(self) -> None:
        """停止监控"""
        self._is_monitoring = False

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Performance monitoring stopped")

    def record_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None) -> None:
        """记录计数器指标"""
        self._counters[name] = self._counters.get(name, 0) + value

        metric = Metric(
            name=name,
            value=self._counters[name],
            metric_type=MetricType.COUNTER,
            timestamp=datetime.now(),
            labels=labels or {}
        )
        self._add_metric(metric)

    def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """记录仪表指标"""
        self._gauges[name] = value

        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            labels=labels or {}
        )
        self._add_metric(metric)

    def record_timer(self, name: str, duration: float, labels: Dict[str, str] = None) -> None:
        """记录计时器指标"""
        if name not in self._timers:
            self._timers[name] = []

        self._timers[name].append(duration)

        # 保留最近的100个记录
        if len(self._timers[name]) > 100:
            self._timers[name] = self._timers[name][-100:]

        metric = Metric(
            name=name,
            value=duration,
            metric_type=MetricType.TIMER,
            timestamp=datetime.now(),
            labels=labels or {},
            unit="seconds"
        )
        self._add_metric(metric)

    def create_alert(
        self,
        level: AlertLevel,
        message: str,
        source: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """创建告警"""
        alert = Alert(
            alert_id=f"alert_{int(time.time())}_{len(self._alerts)}",
            level=level,
            message=message,
            source=source,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )

        self._alerts.append(alert)
        logger.warning(f"Alert created: [{level.value}] {message} (source: {source})")

        # 触发告警处理器
        asyncio.create_task(self._trigger_alert_handlers(alert))

        return alert.alert_id

    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        for alert in self._alerts:
            if alert.alert_id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"Alert resolved: {alert_id}")
                return True

        return False

    def get_metrics(
        self,
        name_pattern: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 1000
    ) -> List[Metric]:
        """获取指标"""
        metrics = self._metrics

        # 时间过滤
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]

        # 名称过滤
        if name_pattern:
            metrics = [m for m in metrics if name_pattern in m.name]

        # 限制数量
        return metrics[-limit:] if len(metrics) > limit else metrics

    def get_alerts(
        self,
        level: AlertLevel = None,
        resolved: bool = None,
        limit: int = 100
    ) -> List[Alert]:
        """获取告警"""
        alerts = self._alerts

        # 级别过滤
        if level:
            alerts = [a for a in alerts if a.level == level]

        # 状态过滤
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]

        # 限制数量
        return alerts[-limit:] if len(alerts) > limit else alerts

    def get_aggregated_metrics(self, name: str, time_window: timedelta = None) -> Dict[str, float]:
        """获取聚合指标"""
        time_window = time_window or timedelta(hours=1)
        cutoff_time = datetime.now() - time_window

        recent_metrics = [m for m in self._metrics if m.name == name and m.timestamp >= cutoff_time]

        if not recent_metrics:
            return {}

        values = [m.value for m in recent_metrics]

        return {
            "count": len(values),
            "sum": sum(values),
            "average": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": values[-1] if values else 0
        }

    def add_metric_handler(self, name: str, handler: Callable) -> None:
        """添加指标处理器"""
        if name not in self._metric_handlers:
            self._metric_handlers[name] = []
        self._metric_handlers[name].append(handler)

    def add_alert_handler(self, handler: Callable) -> None:
        """添加告警处理器"""
        self._alert_handlers.append(handler)

    def export_metrics(self, file_path: str, format_type: str = "json") -> bool:
        """导出指标"""
        try:
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "metrics": [
                    {
                        **asdict(metric),
                        "timestamp": metric.timestamp.isoformat(),
                        "metric_type": metric.metric_type.value
                    }
                    for metric in self._metrics
                ],
                "alerts": [
                    {
                        **asdict(alert),
                        "timestamp": alert.timestamp.isoformat(),
                        "level": alert.level.value,
                        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
                    }
                    for alert in self._alerts
                ]
            }

            if format_type.lower() == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"Unsupported format: {format_type}")

            logger.info(f"Metrics exported to: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return False

    # 私有方法
    def _add_metric(self, metric: Metric) -> None:
        """添加指标"""
        self._metrics.append(metric)

        # 触发处理器
        if metric.name in self._metric_handlers:
            for handler in self._metric_handlers[metric.name]:
                try:
                    handler(metric)
                except Exception as e:
                    logger.error(f"Metric handler error: {e}")

    async def _trigger_alert_handlers(self, alert: Alert) -> None:
        """触发告警处理器"""
        for handler in self._alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    async def _monitoring_loop(self) -> None:
        """监控主循环"""
        while self._is_monitoring:
            try:
                await self._collect_system_metrics()
                await self._check_health_conditions()
                await self._cleanup_old_data()

                await asyncio.sleep(self._monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(10)  # 错误时等待更短时间

    async def _collect_system_metrics(self) -> None:
        """收集系统指标"""
        try:
            # 获取系统状态
            system_status = await self.coordinator.get_system_status()

            # 记录系统指标
            self.record_gauge("system.total_agents", system_status.total_agents)
            self.record_gauge("system.active_agents", system_status.active_agents)
            self.record_gauge("system.total_tasks", system_status.total_tasks)
            self.record_gauge("system.running_tasks", system_status.running_tasks)
            self.record_gauge("system.completed_tasks", system_status.completed_tasks)
            self.record_gauge("system.failed_tasks", system_status.failed_tasks)
            self.record_gauge("system.load_percentage", system_status.system_load)

            # 获取消息统计
            message_stats = self.coordinator.message_bus.get_statistics()
            for key, value in message_stats.items():
                if isinstance(value, (int, float)):
                    self.record_gauge(f"messages.{key}", value)

            # 获取资源统计
            resource_stats = await self.coordinator.resource_manager.get_system_load()
            for key, value in resource_stats.items():
                if isinstance(value, (int, float)):
                    self.record_gauge(f"resources.{key}", value)

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")

    async def _check_health_conditions(self) -> None:
        """检查健康条件"""
        try:
            system_status = await self.coordinator.get_system_status()

            # 检查系统负载
            if system_status.system_load > 90:
                self.create_alert(
                    level=AlertLevel.WARNING,
                    message=f"High system load: {system_status.system_load}%",
                    source="monitoring",
                    metadata={"load_percentage": system_status.system_load}
                )

            # 检查失败任务率
            if system_status.total_tasks > 0:
                failure_rate = system_status.failed_tasks / system_status.total_tasks * 100
                if failure_rate > 20:
                    self.create_alert(
                        level=AlertLevel.ERROR,
                        message=f"High task failure rate: {failure_rate:.1f}%",
                        source="monitoring",
                        metadata={
                            "failure_rate": failure_rate,
                            "failed_tasks": system_status.failed_tasks,
                            "total_tasks": system_status.total_tasks
                        }
                    )

            # 检查活跃智能体数量
            if system_status.active_agents == 0 and system_status.total_agents > 0:
                self.create_alert(
                    level=AlertLevel.CRITICAL,
                    message="No active agents in the system",
                    source="monitoring",
                    metadata={
                        "total_agents": system_status.total_agents,
                        "active_agents": system_status.active_agents
                    }
                )

        except Exception as e:
            logger.error(f"Failed to check health conditions: {e}")

    async def _cleanup_old_data(self) -> None:
        """清理旧数据"""
        try:
            current_time = datetime.now()

            # 清理旧指标
            cutoff_time = current_time - self._metrics_retention_period
            original_count = len(self._metrics)
            self._metrics = [m for m in self._metrics if m.timestamp >= cutoff_time]
            cleaned_metrics = original_count - len(self._metrics)

            # 清理旧告警
            alert_cutoff_time = current_time - self._alerts_retention_period
            original_alert_count = len(self._alerts)
            self._alerts = [a for a in self._alerts if a.timestamp >= alert_cutoff_time or not a.resolved]
            cleaned_alerts = original_alert_count - len(self._alerts)

            if cleaned_metrics > 0 or cleaned_alerts > 0:
                logger.debug(f"Cleanup completed: {cleaned_metrics} metrics, {cleaned_alerts} alerts removed")

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")


# 默认告警处理器
async def default_alert_handler(alert: Alert) -> None:
    """默认告警处理器"""
    logger.warning(f"ALERT [{alert.level.value.upper()}] {alert.message} (source: {alert.source})")


# 性能监控装饰器
def monitor_performance(metric_name: str, monitor: PerformanceMonitor = None):
    """性能监控装饰器"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                if monitor:
                    monitor.record_timer(f"{metric_name}.duration", duration)
                    monitor.record_counter(f"{metric_name}.success")
                return result
            except Exception as e:
                duration = time.time() - start_time
                if monitor:
                    monitor.record_timer(f"{metric_name}.duration", duration)
                    monitor.record_counter(f"{metric_name}.error")
                raise

        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                if monitor:
                    monitor.record_timer(f"{metric_name}.duration", duration)
                    monitor.record_counter(f"{metric_name}.success")
                return result
            except Exception as e:
                duration = time.time() - start_time
                if monitor:
                    monitor.record_timer(f"{metric_name}.duration", duration)
                    monitor.record_counter(f"{metric_name}.error")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator