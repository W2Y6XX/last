"""工作流上下文管理模块"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
from ..utils.logging import LoggerMixin
from .state import WorkflowPhase, WorkflowContext


@dataclass
class PhaseMetrics:
    """阶段指标"""
    phase: WorkflowPhase
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    success: bool = True
    error_count: int = 0
    agent_count: int = 0
    message_count: int = 0


class WorkflowContextManager(LoggerMixin):
    """工作流上下文管理器"""
    
    def __init__(self):
        self.phase_metrics: Dict[str, PhaseMetrics] = {}
        self.global_context: Dict[str, Any] = {}
    
    def create_context(
        self,
        initial_phase: WorkflowPhase = WorkflowPhase.INITIALIZATION
    ) -> WorkflowContext:
        """创建新的工作流上下文"""
        current_time = datetime.now()
        
        context = WorkflowContext(
            current_phase=initial_phase,
            completed_phases=[],
            agent_results={},
            coordination_plan=None,
            execution_metadata={
                "created_at": current_time.isoformat(),
                "context_id": f"ctx_{int(current_time.timestamp())}"
            },
            phase_start_times={initial_phase.value: current_time},
            phase_durations={}
        )
        
        # 记录阶段指标
        self.phase_metrics[initial_phase.value] = PhaseMetrics(
            phase=initial_phase,
            start_time=current_time
        )
        
        self.logger.info("工作流上下文已创建", phase=initial_phase.value)
        return context
    
    def transition_phase(
        self,
        context: WorkflowContext,
        new_phase: WorkflowPhase,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WorkflowContext:
        """转换工作流阶段"""
        current_time = datetime.now()
        current_phase = context["current_phase"]
        
        # 完成当前阶段的指标记录
        if current_phase.value in self.phase_metrics:
            current_metrics = self.phase_metrics[current_phase.value]
            current_metrics.end_time = current_time
            current_metrics.duration = (current_time - current_metrics.start_time).total_seconds()
            
            # 记录阶段持续时间
            context["phase_durations"][current_phase.value] = current_metrics.duration
        
        # 更新上下文
        context["completed_phases"].append(current_phase)
        context["current_phase"] = new_phase
        context["phase_start_times"][new_phase.value] = current_time
        
        # 添加元数据
        if metadata:
            context["execution_metadata"].update(metadata)
        
        # 创建新阶段的指标记录
        self.phase_metrics[new_phase.value] = PhaseMetrics(
            phase=new_phase,
            start_time=current_time
        )
        
        self.logger.info(
            "工作流阶段转换",
            from_phase=current_phase.value,
            to_phase=new_phase.value,
            duration=context["phase_durations"].get(current_phase.value)
        )
        
        return context
    
    def add_agent_result(
        self,
        context: WorkflowContext,
        agent_type: str,
        result: Dict[str, Any],
        execution_time: Optional[float] = None
    ) -> WorkflowContext:
        """添加智能体执行结果"""
        timestamp = datetime.now().isoformat()
        
        agent_result = {
            "result": result,
            "timestamp": timestamp,
            "execution_time": execution_time,
            "phase": context["current_phase"].value
        }
        
        context["agent_results"][agent_type] = agent_result
        
        # 更新当前阶段的指标
        current_phase = context["current_phase"].value
        if current_phase in self.phase_metrics:
            self.phase_metrics[current_phase].agent_count += 1
        
        self.logger.info(
            "智能体结果已添加",
            agent_type=agent_type,
            phase=context["current_phase"].value,
            execution_time=execution_time
        )
        
        return context
    
    def set_coordination_plan(
        self,
        context: WorkflowContext,
        plan: Dict[str, Any]
    ) -> WorkflowContext:
        """设置协调计划"""
        context["coordination_plan"] = {
            **plan,
            "created_at": datetime.now().isoformat(),
            "phase": context["current_phase"].value
        }
        
        self.logger.info("协调计划已设置", phase=context["current_phase"].value)
        return context
    
    def get_phase_summary(self, context: WorkflowContext) -> Dict[str, Any]:
        """获取阶段摘要"""
        summary = {
            "current_phase": context["current_phase"].value,
            "completed_phases": [phase.value for phase in context["completed_phases"]],
            "total_phases": len(context["completed_phases"]) + 1,
            "total_duration": sum(context["phase_durations"].values()),
            "agent_results_count": len(context["agent_results"]),
            "has_coordination_plan": context["coordination_plan"] is not None
        }
        
        # 添加各阶段的详细信息
        phase_details = {}
        for phase_name, duration in context["phase_durations"].items():
            if phase_name in self.phase_metrics:
                metrics = self.phase_metrics[phase_name]
                phase_details[phase_name] = {
                    "duration": duration,
                    "success": metrics.success,
                    "error_count": metrics.error_count,
                    "agent_count": metrics.agent_count,
                    "message_count": metrics.message_count
                }
        
        summary["phase_details"] = phase_details
        return summary
    
    def record_error(
        self,
        context: WorkflowContext,
        error_type: str,
        error_message: str
    ) -> WorkflowContext:
        """记录错误"""
        current_phase = context["current_phase"].value
        if current_phase in self.phase_metrics:
            self.phase_metrics[current_phase].error_count += 1
            self.phase_metrics[current_phase].success = False
        
        # 在执行元数据中记录错误
        if "errors" not in context["execution_metadata"]:
            context["execution_metadata"]["errors"] = []
        
        context["execution_metadata"]["errors"].append({
            "error_type": error_type,
            "error_message": error_message,
            "phase": current_phase,
            "timestamp": datetime.now().isoformat()
        })
        
        self.logger.error(
            "工作流错误已记录",
            error_type=error_type,
            phase=current_phase
        )
        
        return context
    
    def calculate_efficiency_metrics(self, context: WorkflowContext) -> Dict[str, float]:
        """计算效率指标"""
        total_duration = sum(context["phase_durations"].values())
        if total_duration == 0:
            return {}
        
        metrics = {
            "total_duration": total_duration,
            "average_phase_duration": total_duration / max(len(context["phase_durations"]), 1),
            "agent_efficiency": len(context["agent_results"]) / total_duration if total_duration > 0 else 0,
        }
        
        # 计算各阶段的效率
        for phase_name, duration in context["phase_durations"].items():
            if phase_name in self.phase_metrics:
                phase_metrics = self.phase_metrics[phase_name]
                if phase_metrics.agent_count > 0:
                    metrics[f"{phase_name}_agent_efficiency"] = phase_metrics.agent_count / duration
        
        return metrics