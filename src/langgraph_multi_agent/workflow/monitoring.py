"""工作流监控和日志系统"""

import logging
import time
import json
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import threading
from contextlib import contextmanager
import uuid

from ..core.state import LangGraphTaskState, WorkflowPhase
from ..legacy.task_state import TaskStatus

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str]
    unit: Optional[str] = None


@dataclass
class WorkflowEvent:
    """工作流事件"""
    event_id: str
    event_type: str
    timestamp: datetime
    workflow_id: str
    thread_id: str
    phase: WorkflowPhase
    agent_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None


@dataclass
class ExecutionTrace:
    """执行追踪"""
    trace_id: str
    workflow_id: str
    thread_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    events: List[WorkflowEvent] = None
    metrics: List[PerformanceMetric] = None
    status: str = "running"
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.events is None:
            self.events = []
        if self.metrics is None:
            self.metrics = []


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.lock = threading.RLock()
        self.counters: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = {}
    
    def increment_counter(
        self, 
        name: str, 
        value: float = 1.0, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """增加计数器"""
        with self.lock:
            key = self._get_metric_key(name, labels)
            self.counters[key] = self.counters.get(key, 0) + value
            
            metric = PerformanceMetric(
                name=name,
                value=self.counters[key],
                metric_type=MetricType.COUNTER,
                timestamp=datetime.now(),
                labels=labels or {}
            )
            self.metrics.append(metric)
    
    def set_gauge(
        self, 
        name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """设置仪表值"""
        with self.lock:
            key = self._get_metric_key(name, labels)
            self.gauges[key] = value
            
            metric = PerformanceMetric(
                name=name,
                value=value,
                metric_type=MetricType.GAUGE,
                timestamp=datetime.now(),
                labels=labels or {}
            )
            self.metrics.append(metric)
    
    def record_histogram(
        self, 
        name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """记录直方图值"""
        with self.lock:
            key = self._get_metric_key(name, labels)
            if key not in self.histograms:
                self.histograms[key] = []
            self.histograms[key].append(value)
            
            metric = PerformanceMetric(
                name=name,
                value=value,
                metric_type=MetricType.HISTOGRAM,
                timestamp=datetime.now(),
                labels=labels or {}
            )
            self.metrics.append(metric)
    
    @contextmanager
    def timer(self, name: str, labels: Optional[Dict[str, str]] = None):
        """计时器上下文管理器"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = (time.time() - start_time) * 1000  # 转换为毫秒
            self.record_histogram(name, duration, labels)
    
    def get_metrics(
        self, 
        name_filter: Optional[str] = None,
        limit: int = 1000
    ) -> List[PerformanceMetric]:
        """获取指标"""
        with self.lock:
            metrics = self.metrics
            if name_filter:
                metrics = [m for m in metrics if name_filter in m.name]
            return metrics[-limit:]
    
    def clear_metrics(self) -> None:
        """清空指标"""
        with self.lock:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
    
    def _get_metric_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """获取指标键"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str = "workflow"):
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}
        self.lock = threading.RLock()
    
    def set_context(self, **kwargs) -> None:
        """设置日志上下文"""
        with self.lock:
            self.context.update(kwargs)
    
    def clear_context(self) -> None:
        """清空日志上下文"""
        with self.lock:
            self.context.clear()
    
    def log(
        self, 
        level: LogLevel, 
        message: str, 
        **kwargs
    ) -> None:
        """记录结构化日志"""
        with self.lock:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "message": message,
                **self.context,
                **kwargs
            }
            
            log_message = json.dumps(log_data, ensure_ascii=False)
            
            if level == LogLevel.DEBUG:
                self.logger.debug(log_message)
            elif level == LogLevel.INFO:
                self.logger.info(log_message)
            elif level == LogLevel.WARNING:
                self.logger.warning(log_message)
            elif level == LogLevel.ERROR:
                self.logger.error(log_message)
            elif level == LogLevel.CRITICAL:
                self.logger.critical(log_message)
    
    def debug(self, message: str, **kwargs) -> None:
        """记录调试日志"""
        self.log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """记录信息日志"""
        self.log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """记录警告日志"""
        self.log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """记录错误日志"""
        self.log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """记录严重错误日志"""
        self.log(LogLevel.CRITICAL, message, **kwargs)


class WorkflowTracer:
    """工作流追踪器"""
    
    def __init__(self):
        self.traces: Dict[str, ExecutionTrace] = {}
        self.lock = threading.RLock()
        self.event_handlers: List[Callable[[WorkflowEvent], None]] = []
    
    def start_trace(
        self, 
        workflow_id: str, 
        thread_id: str,
        trace_id: Optional[str] = None
    ) -> str:
        """开始追踪"""
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        
        with self.lock:
            trace = ExecutionTrace(
                trace_id=trace_id,
                workflow_id=workflow_id,
                thread_id=thread_id,
                start_time=datetime.now()
            )
            self.traces[trace_id] = trace
        
        return trace_id
    
    def end_trace(self, trace_id: str, status: str = "completed", error: Optional[str] = None) -> None:
        """结束追踪"""
        with self.lock:
            if trace_id in self.traces:
                trace = self.traces[trace_id]
                trace.end_time = datetime.now()
                trace.status = status
                trace.error = error
    
    def add_event(
        self, 
        trace_id: str, 
        event_type: str, 
        phase: WorkflowPhase,
        agent_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """添加事件"""
        with self.lock:
            if trace_id not in self.traces:
                return
            
            trace = self.traces[trace_id]
            event = WorkflowEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.now(),
                workflow_id=trace.workflow_id,
                thread_id=trace.thread_id,
                phase=phase,
                agent_id=agent_id,
                data=data,
                duration_ms=duration_ms
            )
            
            trace.events.append(event)
            
            # 调用事件处理器
            for handler in self.event_handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"事件处理器失败: {e}")
    
    def add_metric(self, trace_id: str, metric: PerformanceMetric) -> None:
        """添加指标"""
        with self.lock:
            if trace_id in self.traces:
                self.traces[trace_id].metrics.append(metric)
    
    def get_trace(self, trace_id: str) -> Optional[ExecutionTrace]:
        """获取追踪"""
        with self.lock:
            return self.traces.get(trace_id)
    
    def list_traces(
        self, 
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[ExecutionTrace]:
        """列出追踪"""
        with self.lock:
            traces = list(self.traces.values())
            
            if workflow_id:
                traces = [t for t in traces if t.workflow_id == workflow_id]
            
            if status:
                traces = [t for t in traces if t.status == status]
            
            # 按开始时间排序
            traces.sort(key=lambda t: t.start_time, reverse=True)
            
            return traces[:limit]
    
    def register_event_handler(self, handler: Callable[[WorkflowEvent], None]) -> None:
        """注册事件处理器"""
        self.event_handlers.append(handler)
    
    def clear_traces(self, older_than: Optional[datetime] = None) -> int:
        """清理追踪"""
        with self.lock:
            if older_than is None:
                older_than = datetime.now() - timedelta(days=7)
            
            to_remove = []
            for trace_id, trace in self.traces.items():
                if trace.start_time < older_than:
                    to_remove.append(trace_id)
            
            for trace_id in to_remove:
                del self.traces[trace_id]
            
            return len(to_remove)


class WorkflowMonitor:
    """工作流监控器"""
    
    def __init__(self, enable_metrics: bool = True, enable_tracing: bool = True, 
                 metrics_config: Optional[Dict[str, Any]] = None):
        self.enable_metrics = enable_metrics
        self.enable_tracing = enable_tracing
        self.metrics_config = metrics_config or {}
        
        self.metrics_collector = MetricsCollector() if enable_metrics else None
        self.tracer = WorkflowTracer() if enable_tracing else None
        self.logger = StructuredLogger("workflow_monitor")
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()
        
        # 注册默认事件处理器
        if self.tracer:
            self._add_trace_event('register_event_handler', self._handle_workflow_event)
    
    def _record_metric(self, method_name: str, *args, **kwargs):
        """安全记录指标"""
        if self.metrics_collector:
            try:
                method = getattr(self.metrics_collector, method_name, None)
                if method:
                    method(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Failed to record metric {method_name}: {e}")
    
    def _safe_metrics_call(self, func_name: str, *args, **kwargs):
        """安全调用metrics方法"""
        if self.metrics_collector:
            try:
                func = getattr(self.metrics_collector, func_name)
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Metrics call {func_name} failed: {e}")
                return {} if func_name == 'get_metrics' else None
        return {} if func_name == 'get_metrics' else None
    
    def _add_trace_event(self, method_name: str, *args, **kwargs):
        """安全添加追踪事件"""
        if self.tracer:
            try:
                method = getattr(self.tracer, method_name, None)
                if method:
                    return method(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Tracer call {method_name} failed: {e}")
        return None
    
    def start_workflow_monitoring(
        self, 
        workflow_id: str, 
        thread_id: str,
        initial_state: LangGraphTaskState
    ) -> str:
        """开始工作流监控"""
        trace_id = self._add_trace_event('start_trace', workflow_id, thread_id)
        
        with self.lock:
            self.active_workflows[thread_id] = {
                "workflow_id": workflow_id,
                "trace_id": trace_id,
                "start_time": datetime.now(),
                "current_phase": initial_state["workflow_context"]["current_phase"],
                "task_status": initial_state["task_state"]["status"],
                "agent_count": len(initial_state["workflow_context"]["agent_results"])
            }
        
        # 记录开始事件
        self._add_trace_event('add_event',
            trace_id=trace_id,
            event_type="workflow_started",
            phase=initial_state["workflow_context"]["current_phase"],
            data={
                "task_title": initial_state["task_state"]["title"],
                "task_type": initial_state["task_state"]["task_type"],
                "priority": initial_state["task_state"]["priority"]
            }
        )
        
        # 增加计数器
        self._record_metric(
            "increment_counter",
            "workflows_started_total",
            labels={"workflow_id": workflow_id}
        )
        
        # 记录日志
        self.logger.info(
            "工作流监控开始",
            workflow_id=workflow_id,
            thread_id=thread_id,
            trace_id=trace_id
        )
        
        return trace_id
    
    def update_workflow_state(
        self, 
        thread_id: str, 
        state: LangGraphTaskState
    ) -> None:
        """更新工作流状态"""
        with self.lock:
            if thread_id not in self.active_workflows:
                return
            
            workflow_info = self.active_workflows[thread_id]
            trace_id = workflow_info["trace_id"]
            
            # 检查阶段变化
            current_phase = state["workflow_context"]["current_phase"]
            if workflow_info["current_phase"] != current_phase:
                self._add_trace_event('add_event',
                    trace_id=trace_id,
                    event_type="phase_changed",
                    phase=current_phase,
                    data={
                        "from_phase": workflow_info["current_phase"].value,
                        "to_phase": current_phase.value
                    }
                )
                workflow_info["current_phase"] = current_phase
            
            # 检查任务状态变化
            task_status = state["task_state"]["status"]
            if workflow_info["task_status"] != task_status:
                self._add_trace_event('add_event',
                    trace_id=trace_id,
                    event_type="status_changed",
                    phase=current_phase,
                    data={
                        "from_status": workflow_info["task_status"].value,
                        "to_status": task_status.value
                    }
                )
                workflow_info["task_status"] = task_status
            
            # 检查智能体数量变化
            agent_count = len(state["workflow_context"]["agent_results"])
            if workflow_info["agent_count"] != agent_count:
                self._add_trace_event('add_event',
                    trace_id=trace_id,
                    event_type="agents_updated",
                    phase=current_phase,
                    data={
                        "agent_count": agent_count,
                        "agents": list(state["workflow_context"]["agent_results"].keys())
                    }
                )
                workflow_info["agent_count"] = agent_count
            
            # 更新仪表指标
            self._safe_metrics_call('set_gauge',
                "active_workflows",
                len(self.active_workflows)
            )
            
            self._safe_metrics_call('set_gauge',
                "workflow_agents_count",
                agent_count,
                labels={"thread_id": thread_id}
            )
    
    def record_agent_execution(
        self, 
        thread_id: str, 
        agent_id: str, 
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """记录智能体执行"""
        with self.lock:
            if thread_id not in self.active_workflows:
                return
            
            workflow_info = self.active_workflows[thread_id]
            trace_id = workflow_info["trace_id"]
            
            # 添加执行事件
            self._add_trace_event('add_event',
                trace_id=trace_id,
                event_type="agent_executed",
                phase=workflow_info["current_phase"],
                agent_id=agent_id,
                data={
                    "success": success,
                    "error": error
                },
                duration_ms=duration_ms
            )
            
            # 记录执行时间
            self._safe_metrics_call('record_histogram',
                "agent_execution_duration_ms",
                duration_ms,
                labels={"agent_id": agent_id, "success": str(success)}
            )
            
            # 增加执行计数
            self._safe_metrics_call('increment_counter',
                "agent_executions_total",
                labels={"agent_id": agent_id, "success": str(success)}
            )
    
    def end_workflow_monitoring(
        self, 
        thread_id: str, 
        final_state: LangGraphTaskState,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """结束工作流监控"""
        with self.lock:
            if thread_id not in self.active_workflows:
                return
            
            workflow_info = self.active_workflows.pop(thread_id)
            trace_id = workflow_info["trace_id"]
            
            # 计算总执行时间
            total_duration = (datetime.now() - workflow_info["start_time"]).total_seconds() * 1000
            
            # 结束追踪
            status = "completed" if success else "failed"
            self._add_trace_event('end_trace', trace_id, status, error)
            
            # 添加结束事件
            self._add_trace_event('add_event',
                trace_id=trace_id,
                event_type="workflow_completed",
                phase=final_state["workflow_context"]["current_phase"],
                data={
                    "success": success,
                    "error": error,
                    "final_status": final_state["task_state"]["status"].value
                },
                duration_ms=total_duration
            )
            
            # 记录总执行时间
            self._safe_metrics_call('record_histogram',
                "workflow_duration_ms",
                total_duration,
                labels={"workflow_id": workflow_info["workflow_id"], "success": str(success)}
            )
            
            # 增加完成计数
            self._safe_metrics_call('increment_counter',
                "workflows_completed_total",
                labels={"workflow_id": workflow_info["workflow_id"], "success": str(success)}
            )
            
            # 记录日志
            self.logger.info(
                "工作流监控结束",
                workflow_id=workflow_info["workflow_id"],
                thread_id=thread_id,
                trace_id=trace_id,
                success=success,
                duration_ms=total_duration
            )
    
    def get_workflow_metrics(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """获取工作流指标"""
        metrics = self._safe_metrics_call('get_metrics') if self.metrics_collector else {}
        
        if workflow_id:
            metrics = [m for m in metrics if m.labels.get("workflow_id") == workflow_id]
        
        # 按类型分组
        grouped_metrics = {
            "counters": [],
            "gauges": [],
            "histograms": []
        }
        
        for metric in metrics:
            if metric.metric_type == MetricType.COUNTER:
                grouped_metrics["counters"].append(asdict(metric))
            elif metric.metric_type == MetricType.GAUGE:
                grouped_metrics["gauges"].append(asdict(metric))
            elif metric.metric_type == MetricType.HISTOGRAM:
                grouped_metrics["histograms"].append(asdict(metric))
        
        return grouped_metrics
    
    def get_execution_traces(
        self, 
        workflow_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取执行追踪"""
        traces = self._add_trace_event('list_traces', workflow_id=workflow_id, limit=limit)
        return [asdict(trace) for trace in traces]
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        with self.lock:
            active_count = len(self.active_workflows)
            total_traces = len(self.tracer.traces)
            
            # 计算成功率
            completed_traces = [t for t in self.tracer.traces.values() if t.status in ["completed", "failed"]]
            success_count = len([t for t in completed_traces if t.status == "completed"])
            success_rate = success_count / len(completed_traces) if completed_traces else 0
            
            return {
                "active_workflows": active_count,
                "total_traces": total_traces,
                "completed_traces": len(completed_traces),
                "success_rate": success_rate,
                "total_metrics": len(self.metrics_collector.metrics),
                "uptime": datetime.now().isoformat()
            }
    
    def _handle_workflow_event(self, event: WorkflowEvent) -> None:
        """处理工作流事件"""
        # 记录事件日志
        self.logger.debug(
            f"工作流事件: {event.event_type}",
            event_id=event.event_id,
            workflow_id=event.workflow_id,
            thread_id=event.thread_id,
            phase=event.phase.value,
            agent_id=event.agent_id,
            duration_ms=event.duration_ms
        )
        
        # 增加事件计数
        self._safe_metrics_call('increment_counter',
            "workflow_events_total",
            labels={
                "event_type": event.event_type,
                "phase": event.phase.value
            }
        )


# 全局监控实例
workflow_monitor = WorkflowMonitor()


def get_workflow_monitor() -> WorkflowMonitor:
    """获取全局工作流监控器"""
    return workflow_monitor