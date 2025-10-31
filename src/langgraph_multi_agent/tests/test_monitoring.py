"""工作流监控系统测试"""

import pytest
import time
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from langgraph_multi_agent.workflow.monitoring import (
    MetricsCollector,
    StructuredLogger,
    WorkflowTracer,
    WorkflowMonitor,
    PerformanceMetric,
    WorkflowEvent,
    ExecutionTrace,
    MetricType,
    LogLevel,
    get_workflow_monitor
)
from langgraph_multi_agent.core.state import (
    create_initial_state,
    WorkflowPhase
)
from langgraph_multi_agent.legacy.task_state import TaskStatus


class TestMetricsCollector:
    """指标收集器测试"""
    
    def test_collector_initialization(self):
        """测试收集器初始化"""
        collector = MetricsCollector()
        
        assert len(collector.metrics) == 0
        assert len(collector.counters) == 0
        assert len(collector.gauges) == 0
        assert len(collector.histograms) == 0
    
    def test_counter_operations(self):
        """测试计数器操作"""
        collector = MetricsCollector()
        
        # 增加计数器
        collector.increment_counter("test_counter", 1.0, {"label": "value"})
        collector.increment_counter("test_counter", 2.0, {"label": "value"})
        
        # 验证计数器值
        key = "test_counter[label=value]"
        assert collector.counters[key] == 3.0
        
        # 验证指标记录
        metrics = collector.get_metrics("test_counter")
        assert len(metrics) == 2
        assert metrics[-1].value == 3.0
        assert metrics[-1].metric_type == MetricType.COUNTER
    
    def test_gauge_operations(self):
        """测试仪表操作"""
        collector = MetricsCollector()
        
        # 设置仪表值
        collector.set_gauge("test_gauge", 42.5, {"env": "test"})
        collector.set_gauge("test_gauge", 55.0, {"env": "test"})
        
        # 验证仪表值
        key = "test_gauge[env=test]"
        assert collector.gauges[key] == 55.0
        
        # 验证指标记录
        metrics = collector.get_metrics("test_gauge")
        assert len(metrics) == 2
        assert metrics[-1].value == 55.0
        assert metrics[-1].metric_type == MetricType.GAUGE
    
    def test_histogram_operations(self):
        """测试直方图操作"""
        collector = MetricsCollector()
        
        # 记录直方图值
        values = [10.0, 20.0, 30.0, 15.0, 25.0]
        for value in values:
            collector.record_histogram("test_histogram", value, {"type": "duration"})
        
        # 验证直方图值
        key = "test_histogram[type=duration]"
        assert collector.histograms[key] == values
        
        # 验证指标记录
        metrics = collector.get_metrics("test_histogram")
        assert len(metrics) == 5
        assert all(m.metric_type == MetricType.HISTOGRAM for m in metrics)
    
    def test_timer_context_manager(self):
        """测试计时器上下文管理器"""
        collector = MetricsCollector()
        
        # 使用计时器
        with collector.timer("test_timer", {"operation": "test"}):
            time.sleep(0.01)  # 睡眠10毫秒
        
        # 验证计时记录
        metrics = collector.get_metrics("test_timer")
        assert len(metrics) == 1
        assert metrics[0].metric_type == MetricType.HISTOGRAM
        assert metrics[0].value >= 10  # 至少10毫秒
        assert metrics[0].labels["operation"] == "test"
    
    def test_metrics_filtering_and_limiting(self):
        """测试指标过滤和限制"""
        collector = MetricsCollector()
        
        # 添加多种指标
        for i in range(10):
            collector.increment_counter(f"counter_{i % 3}", 1.0)
            collector.set_gauge(f"gauge_{i % 2}", float(i))
        
        # 测试过滤
        counter_metrics = collector.get_metrics("counter_0")
        assert len(counter_metrics) > 0
        assert all("counter_0" in m.name for m in counter_metrics)
        
        # 测试限制
        limited_metrics = collector.get_metrics(limit=5)
        assert len(limited_metrics) == 5
    
    def test_clear_metrics(self):
        """测试清空指标"""
        collector = MetricsCollector()
        
        # 添加一些指标
        collector.increment_counter("test", 1.0)
        collector.set_gauge("test", 1.0)
        collector.record_histogram("test", 1.0)
        
        assert len(collector.metrics) > 0
        assert len(collector.counters) > 0
        assert len(collector.gauges) > 0
        assert len(collector.histograms) > 0
        
        # 清空指标
        collector.clear_metrics()
        
        assert len(collector.metrics) == 0
        assert len(collector.counters) == 0
        assert len(collector.gauges) == 0
        assert len(collector.histograms) == 0


class TestStructuredLogger:
    """结构化日志记录器测试"""
    
    def test_logger_initialization(self):
        """测试日志记录器初始化"""
        logger = StructuredLogger("test_logger")
        
        assert logger.logger.name == "test_logger"
        assert len(logger.context) == 0
    
    def test_context_management(self):
        """测试上下文管理"""
        logger = StructuredLogger("test")
        
        # 设置上下文
        logger.set_context(user_id="123", session_id="abc")
        assert logger.context["user_id"] == "123"
        assert logger.context["session_id"] == "abc"
        
        # 更新上下文
        logger.set_context(user_id="456", request_id="def")
        assert logger.context["user_id"] == "456"
        assert logger.context["session_id"] == "abc"
        assert logger.context["request_id"] == "def"
        
        # 清空上下文
        logger.clear_context()
        assert len(logger.context) == 0
    
    @patch('langgraph_multi_agent.workflow.monitoring.logging.getLogger')
    def test_structured_logging(self, mock_get_logger):
        """测试结构化日志记录"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        logger = StructuredLogger("test")
        logger.set_context(workflow_id="wf_123")
        
        # 测试不同级别的日志
        logger.debug("Debug message", extra_field="debug_value")
        logger.info("Info message", extra_field="info_value")
        logger.warning("Warning message", extra_field="warning_value")
        logger.error("Error message", extra_field="error_value")
        logger.critical("Critical message", extra_field="critical_value")
        
        # 验证日志调用
        assert mock_logger.debug.called
        assert mock_logger.info.called
        assert mock_logger.warning.called
        assert mock_logger.error.called
        assert mock_logger.critical.called


class TestWorkflowTracer:
    """工作流追踪器测试"""
    
    def test_tracer_initialization(self):
        """测试追踪器初始化"""
        tracer = WorkflowTracer()
        
        assert len(tracer.traces) == 0
        assert len(tracer.event_handlers) == 0
    
    def test_trace_lifecycle(self):
        """测试追踪生命周期"""
        tracer = WorkflowTracer()
        
        # 开始追踪
        trace_id = tracer.start_trace("workflow_123", "thread_456")
        assert trace_id is not None
        assert trace_id in tracer.traces
        
        trace = tracer.get_trace(trace_id)
        assert trace is not None
        assert trace.workflow_id == "workflow_123"
        assert trace.thread_id == "thread_456"
        assert trace.status == "running"
        assert trace.end_time is None
        
        # 结束追踪
        tracer.end_trace(trace_id, "completed")
        
        trace = tracer.get_trace(trace_id)
        assert trace.status == "completed"
        assert trace.end_time is not None
    
    def test_event_management(self):
        """测试事件管理"""
        tracer = WorkflowTracer()
        
        # 开始追踪
        trace_id = tracer.start_trace("workflow_123", "thread_456")
        
        # 添加事件
        tracer.add_event(
            trace_id=trace_id,
            event_type="phase_changed",
            phase=WorkflowPhase.ANALYSIS,
            agent_id="agent_1",
            data={"from": "init", "to": "analysis"},
            duration_ms=150.0
        )
        
        trace = tracer.get_trace(trace_id)
        assert len(trace.events) == 1
        
        event = trace.events[0]
        assert event.event_type == "phase_changed"
        assert event.phase == WorkflowPhase.ANALYSIS
        assert event.agent_id == "agent_1"
        assert event.duration_ms == 150.0
        assert event.data["from"] == "init"
    
    def test_event_handlers(self):
        """测试事件处理器"""
        tracer = WorkflowTracer()
        
        # 注册事件处理器
        handler_calls = []
        def test_handler(event):
            handler_calls.append(event)
        
        tracer.register_event_handler(test_handler)
        
        # 开始追踪并添加事件
        trace_id = tracer.start_trace("workflow_123", "thread_456")
        tracer.add_event(trace_id, "test_event", WorkflowPhase.ANALYSIS)
        
        # 验证处理器被调用
        assert len(handler_calls) == 1
        assert handler_calls[0].event_type == "test_event"
    
    def test_trace_listing_and_filtering(self):
        """测试追踪列表和过滤"""
        tracer = WorkflowTracer()
        
        # 创建多个追踪
        trace_ids = []
        for i in range(5):
            trace_id = tracer.start_trace(f"workflow_{i % 2}", f"thread_{i}")
            trace_ids.append(trace_id)
            if i % 2 == 0:
                tracer.end_trace(trace_id, "completed")
            else:
                tracer.end_trace(trace_id, "failed")
        
        # 测试列出所有追踪
        all_traces = tracer.list_traces()
        assert len(all_traces) == 5
        
        # 测试按工作流ID过滤
        workflow_0_traces = tracer.list_traces(workflow_id="workflow_0")
        assert len(workflow_0_traces) == 3
        assert all(t.workflow_id == "workflow_0" for t in workflow_0_traces)
        
        # 测试按状态过滤
        completed_traces = tracer.list_traces(status="completed")
        assert len(completed_traces) == 3
        assert all(t.status == "completed" for t in completed_traces)
        
        # 测试限制数量
        limited_traces = tracer.list_traces(limit=2)
        assert len(limited_traces) == 2
    
    def test_trace_cleanup(self):
        """测试追踪清理"""
        tracer = WorkflowTracer()
        
        # 创建新旧追踪
        old_trace_id = tracer.start_trace("old_workflow", "old_thread")
        new_trace_id = tracer.start_trace("new_workflow", "new_thread")
        
        # 手动设置旧追踪的时间
        old_trace = tracer.get_trace(old_trace_id)
        old_trace.start_time = datetime.now() - timedelta(days=10)
        
        # 清理旧追踪
        cutoff_time = datetime.now() - timedelta(days=5)
        cleaned_count = tracer.clear_traces(cutoff_time)
        
        assert cleaned_count == 1
        assert old_trace_id not in tracer.traces
        assert new_trace_id in tracer.traces


class TestWorkflowMonitor:
    """工作流监控器测试"""
    
    def test_monitor_initialization(self):
        """测试监控器初始化"""
        monitor = WorkflowMonitor()
        
        assert isinstance(monitor.metrics_collector, MetricsCollector)
        assert isinstance(monitor.tracer, WorkflowTracer)
        assert isinstance(monitor.logger, StructuredLogger)
        assert len(monitor.active_workflows) == 0
    
    def test_workflow_monitoring_lifecycle(self):
        """测试工作流监控生命周期"""
        monitor = WorkflowMonitor()
        
        # 创建初始状态
        state = create_initial_state("测试工作流", "测试描述")
        state["workflow_context"]["current_phase"] = WorkflowPhase.ANALYSIS
        state["task_state"]["status"] = TaskStatus.IN_PROGRESS
        
        # 开始监控
        trace_id = monitor.start_workflow_monitoring("wf_123", "thread_456", state)
        
        assert trace_id is not None
        assert "thread_456" in monitor.active_workflows
        
        workflow_info = monitor.active_workflows["thread_456"]
        assert workflow_info["workflow_id"] == "wf_123"
        assert workflow_info["trace_id"] == trace_id
        assert workflow_info["current_phase"] == WorkflowPhase.ANALYSIS
        
        # 更新状态
        state["workflow_context"]["current_phase"] = WorkflowPhase.DECOMPOSITION
        state["task_state"]["status"] = TaskStatus.IN_PROGRESS
        state["workflow_context"]["agent_results"]["agent_1"] = {"result": "test"}
        
        monitor.update_workflow_state("thread_456", state)
        
        # 验证状态更新
        workflow_info = monitor.active_workflows["thread_456"]
        assert workflow_info["current_phase"] == WorkflowPhase.DECOMPOSITION
        assert workflow_info["agent_count"] == 1
        
        # 记录智能体执行
        monitor.record_agent_execution("thread_456", "agent_1", 250.0, True)
        
        # 结束监控
        monitor.end_workflow_monitoring("thread_456", state, True)
        
        assert "thread_456" not in monitor.active_workflows
        
        # 验证追踪完成
        trace = monitor.tracer.get_trace(trace_id)
        assert trace.status == "completed"
        assert trace.end_time is not None
    
    def test_agent_execution_recording(self):
        """测试智能体执行记录"""
        monitor = WorkflowMonitor()
        
        # 开始监控
        state = create_initial_state("测试", "测试")
        trace_id = monitor.start_workflow_monitoring("wf_123", "thread_456", state)
        
        # 记录成功执行
        monitor.record_agent_execution("thread_456", "agent_1", 100.0, True)
        
        # 记录失败执行
        monitor.record_agent_execution("thread_456", "agent_2", 200.0, False, "执行错误")
        
        # 验证事件记录
        trace = monitor.tracer.get_trace(trace_id)
        execution_events = [e for e in trace.events if e.event_type == "agent_executed"]
        assert len(execution_events) == 2
        
        # 验证成功执行事件
        success_event = execution_events[0]
        assert success_event.agent_id == "agent_1"
        assert success_event.duration_ms == 100.0
        assert success_event.data["success"] is True
        
        # 验证失败执行事件
        failure_event = execution_events[1]
        assert failure_event.agent_id == "agent_2"
        assert failure_event.duration_ms == 200.0
        assert failure_event.data["success"] is False
        assert failure_event.data["error"] == "执行错误"
    
    def test_metrics_collection(self):
        """测试指标收集"""
        monitor = WorkflowMonitor()
        
        # 开始监控
        state = create_initial_state("测试", "测试")
        monitor.start_workflow_monitoring("wf_123", "thread_456", state)
        
        # 记录一些执行
        monitor.record_agent_execution("thread_456", "agent_1", 100.0, True)
        monitor.record_agent_execution("thread_456", "agent_1", 150.0, True)
        monitor.record_agent_execution("thread_456", "agent_2", 200.0, False)
        
        # 结束监控
        monitor.end_workflow_monitoring("thread_456", state, True)
        
        # 获取所有指标（不按workflow_id过滤）
        metrics = monitor.get_workflow_metrics()
        
        # 验证指标类型
        assert "counters" in metrics
        assert "gauges" in metrics
        assert "histograms" in metrics
        
        # 验证有相关指标
        counter_names = [m["name"] for m in metrics["counters"]]
        assert "workflows_started_total" in counter_names
        assert "workflows_completed_total" in counter_names
        assert "agent_executions_total" in counter_names
        
        histogram_names = [m["name"] for m in metrics["histograms"]]
        assert "workflow_duration_ms" in histogram_names
        assert "agent_execution_duration_ms" in histogram_names
    
    def test_monitoring_summary(self):
        """测试监控摘要"""
        monitor = WorkflowMonitor()
        
        # 开始一些监控
        state = create_initial_state("测试", "测试")
        trace_id_1 = monitor.start_workflow_monitoring("wf_1", "thread_1", state)
        trace_id_2 = monitor.start_workflow_monitoring("wf_2", "thread_2", state)
        
        # 完成一个工作流
        monitor.end_workflow_monitoring("thread_1", state, True)
        
        # 获取摘要
        summary = monitor.get_monitoring_summary()
        
        assert summary["active_workflows"] == 1
        assert summary["total_traces"] == 2
        assert summary["completed_traces"] == 1
        assert summary["success_rate"] == 1.0
        assert "uptime" in summary
        assert "total_metrics" in summary
    
    def test_execution_traces_retrieval(self):
        """测试执行追踪获取"""
        monitor = WorkflowMonitor()
        
        # 创建一些追踪
        state = create_initial_state("测试", "测试")
        trace_id_1 = monitor.start_workflow_monitoring("wf_1", "thread_1", state)
        trace_id_2 = monitor.start_workflow_monitoring("wf_2", "thread_2", state)
        
        monitor.end_workflow_monitoring("thread_1", state, True)
        monitor.end_workflow_monitoring("thread_2", state, False, "测试错误")
        
        # 获取所有追踪
        all_traces = monitor.get_execution_traces()
        assert len(all_traces) == 2
        
        # 获取特定工作流的追踪
        wf1_traces = monitor.get_execution_traces("wf_1")
        assert len(wf1_traces) == 1
        assert wf1_traces[0]["workflow_id"] == "wf_1"
        assert wf1_traces[0]["status"] == "completed"
        
        wf2_traces = monitor.get_execution_traces("wf_2")
        assert len(wf2_traces) == 1
        assert wf2_traces[0]["workflow_id"] == "wf_2"
        assert wf2_traces[0]["status"] == "failed"
        assert wf2_traces[0]["error"] == "测试错误"


class TestGlobalMonitor:
    """全局监控器测试"""
    
    def test_global_monitor_singleton(self):
        """测试全局监控器单例"""
        monitor1 = get_workflow_monitor()
        monitor2 = get_workflow_monitor()
        
        assert monitor1 is monitor2
        assert isinstance(monitor1, WorkflowMonitor)


class TestIntegrationScenarios:
    """集成场景测试"""
    
    def test_complete_workflow_monitoring(self):
        """测试完整的工作流监控"""
        monitor = WorkflowMonitor()
        
        # 创建复杂的工作流状态
        state = create_initial_state("复杂工作流", "多阶段处理任务")
        state["workflow_context"]["current_phase"] = WorkflowPhase.INITIALIZATION
        state["task_state"]["status"] = TaskStatus.PENDING
        
        # 开始监控
        trace_id = monitor.start_workflow_monitoring("complex_wf", "main_thread", state)
        
        # 模拟工作流执行过程
        phases = [
            WorkflowPhase.ANALYSIS,
            WorkflowPhase.DECOMPOSITION,
            WorkflowPhase.COORDINATION,
            WorkflowPhase.EXECUTION,
            WorkflowPhase.REVIEW
        ]
        
        agents = ["meta_agent", "task_decomposer", "coordinator", "executor", "reviewer"]
        
        for i, (phase, agent) in enumerate(zip(phases, agents)):
            # 更新阶段
            state["workflow_context"]["current_phase"] = phase
            state["workflow_context"]["agent_results"][agent] = {"result": f"phase_{i}_result"}
            
            monitor.update_workflow_state("main_thread", state)
            
            # 模拟智能体执行
            execution_time = 100.0 + i * 50.0
            success = i < 4  # 最后一个失败
            error = "Review failed" if not success else None
            
            monitor.record_agent_execution("main_thread", agent, execution_time, success, error)
        
        # 结束监控
        state["task_state"]["status"] = TaskStatus.COMPLETED
        monitor.end_workflow_monitoring("main_thread", state, True)
        
        # 验证完整的追踪
        trace = monitor.tracer.get_trace(trace_id)
        assert trace.status == "completed"
        assert len(trace.events) >= 10  # 开始 + 5个阶段变化 + 5个智能体执行 + 结束
        
        # 验证事件类型
        event_types = [e.event_type for e in trace.events]
        assert "workflow_started" in event_types
        assert "phase_changed" in event_types
        assert "agents_updated" in event_types
        assert "agent_executed" in event_types
        assert "workflow_completed" in event_types
        
        # 验证指标收集
        metrics = monitor.get_workflow_metrics("complex_wf")
        assert len(metrics["counters"]) > 0
        assert len(metrics["histograms"]) > 0
        
        # 验证监控摘要
        summary = monitor.get_monitoring_summary()
        assert summary["active_workflows"] == 0
        assert summary["completed_traces"] == 1
        assert summary["success_rate"] == 1.0
    
    def test_concurrent_workflow_monitoring(self):
        """测试并发工作流监控"""
        monitor = WorkflowMonitor()
        
        # 启动多个并发工作流
        workflows = []
        for i in range(3):
            state = create_initial_state(f"工作流_{i}", f"并发任务_{i}")
            trace_id = monitor.start_workflow_monitoring(f"wf_{i}", f"thread_{i}", state)
            workflows.append((f"thread_{i}", trace_id, state))
        
        # 验证并发监控
        assert len(monitor.active_workflows) == 3
        
        # 模拟并发执行
        for thread_id, trace_id, state in workflows:
            monitor.record_agent_execution(thread_id, "test_agent", 100.0, True)
            state["workflow_context"]["current_phase"] = WorkflowPhase.EXECUTION
            monitor.update_workflow_state(thread_id, state)
        
        # 完成所有工作流
        for thread_id, trace_id, state in workflows:
            monitor.end_workflow_monitoring(thread_id, state, True)
        
        # 验证结果
        assert len(monitor.active_workflows) == 0
        
        summary = monitor.get_monitoring_summary()
        assert summary["completed_traces"] == 3
        assert summary["success_rate"] == 1.0
        
        # 验证每个追踪都完整
        for thread_id, trace_id, state in workflows:
            trace = monitor.tracer.get_trace(trace_id)
            assert trace.status == "completed"
            assert len(trace.events) >= 3  # 开始 + 执行 + 结束
    
    def test_error_handling_and_recovery_monitoring(self):
        """测试错误处理和恢复监控"""
        monitor = WorkflowMonitor()
        
        # 开始监控
        state = create_initial_state("错误测试工作流", "测试错误处理")
        trace_id = monitor.start_workflow_monitoring("error_wf", "error_thread", state)
        
        # 模拟正常执行
        monitor.record_agent_execution("error_thread", "agent_1", 100.0, True)
        
        # 模拟错误
        monitor.record_agent_execution("error_thread", "agent_2", 200.0, False, "网络超时")
        monitor.record_agent_execution("error_thread", "agent_2", 150.0, False, "重试失败")
        
        # 模拟恢复
        monitor.record_agent_execution("error_thread", "agent_3", 120.0, True)
        
        # 结束监控（失败）
        monitor.end_workflow_monitoring("error_thread", state, False, "最终执行失败")
        
        # 验证错误追踪
        trace = monitor.tracer.get_trace(trace_id)
        assert trace.status == "failed"
        assert trace.error == "最终执行失败"
        
        # 验证错误事件
        execution_events = [e for e in trace.events if e.event_type == "agent_executed"]
        failed_events = [e for e in execution_events if not e.data.get("success", True)]
        assert len(failed_events) == 2
        
        # 验证错误指标
        metrics = monitor.get_workflow_metrics()
        failure_counters = [
            m for m in metrics["counters"] 
            if m["name"] == "agent_executions_total" and m["labels"].get("success") == "False"
        ]
        assert len(failure_counters) > 0