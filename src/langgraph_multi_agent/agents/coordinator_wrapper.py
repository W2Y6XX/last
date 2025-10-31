"""Coordinator包装器 - 智能体协调和冲突解决"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .wrappers import AgentNodeWrapper, AgentExecutionResult
from ..core.state import (
    LangGraphTaskState,
    WorkflowPhase,
    update_workflow_phase,
    update_task_status,
    add_agent_message,
    add_performance_metric
)
from ..legacy.task_state import TaskStatus


class CoordinatorWrapper(AgentNodeWrapper):
    """Coordinator包装器
    
    负责智能体间的协调、冲突解决和资源分配。
    在多智能体协作场景中管理智能体间的通信和协调。
    """
    
    def __init__(self, coordinator_instance: Any, **kwargs):
        super().__init__(coordinator_instance, "coordinator", **kwargs)
        
        # Coordinator特有的配置
        self.max_coordination_attempts = 3  # 最大协调尝试次数
        self.conflict_resolution_timeout = 60  # 冲突解决超时时间（秒）
        self.session_timeout = 3600  # 协作会话超时时间（秒）
    
    def _extract_task_data(self, state: LangGraphTaskState) -> Dict[str, Any]:
        """从LangGraph状态提取Coordinator需要的任务数据"""
        task_state = state["task_state"]
        workflow_context = state["workflow_context"]
        coordination_state = state["coordination_state"]
        
        # 构造Coordinator专用的任务数据
        task_data = {
            # 基本任务信息
            "task_id": task_state["task_id"],
            "title": task_state["title"],
            "description": task_state["description"],
            "task_type": task_state["task_type"],
            "priority": task_state["priority"],
            
            # 协调上下文
            "coordination_context": {
                "current_phase": workflow_context["current_phase"].value,
                "agent_results": workflow_context["agent_results"],
                "coordination_plan": workflow_context.get("coordination_plan"),
                "execution_metadata": workflow_context["execution_metadata"]
            },
            
            # 协调状态
            "coordination_state": coordination_state,
            "active_agents": list(workflow_context["agent_results"].keys()),
            "agent_messages": state["agent_messages"],
            
            # 确定协调类型
            "coordination_type": self._determine_coordination_type(state),
            
            # 协调参数
            "coordination_params": {
                "max_attempts": self.max_coordination_attempts,
                "timeout": self.conflict_resolution_timeout,
                "session_timeout": self.session_timeout
            }
        }
        
        return task_data
    
    def _determine_coordination_type(self, state: LangGraphTaskState) -> str:
        """确定协调类型"""
        workflow_context = state["workflow_context"]
        current_phase = workflow_context["current_phase"]
        coordination_state = state["coordination_state"]
        
        # 检查是否有活跃冲突
        if coordination_state.get("conflicts"):
            return "resolve_conflict"
        
        # 检查是否需要建立协作
        if current_phase == WorkflowPhase.COORDINATION and not coordination_state.get("active_sessions"):
            return "establish_collaboration"
        
        # 检查是否需要同步智能体
        if coordination_state.get("sync_required"):
            return "synchronize_agents"
        
        # 检查是否需要协调执行
        if current_phase == WorkflowPhase.EXECUTION:
            return "coordinate_execution"
        
        # 默认为通用协调
        return "general_coordination"
    
    async def _update_state(
        self, 
        state: LangGraphTaskState, 
        execution_result: AgentExecutionResult
    ) -> LangGraphTaskState:
        """更新LangGraph状态"""
        if execution_result.success:
            result = execution_result.result
            coordination_type = result.get("coordination_type", "general_coordination")
            
            # 添加Coordinator协调消息
            state = add_agent_message(
                state,
                sender_agent="coordinator",
                content={
                    "coordination_result": result,
                    "coordination_type": coordination_type,
                    "execution_time": execution_result.execution_time
                },
                message_type="coordination_result",
                priority=2  # 高优先级
            )
            
            # 更新工作流上下文
            state["workflow_context"]["agent_results"]["coordinator"] = {
                "result": result,
                "timestamp": execution_result.timestamp.isoformat(),
                "execution_time": execution_result.execution_time,
                "phase": state["workflow_context"]["current_phase"].value
            }
            
            # 根据协调结果更新状态
            await self._process_coordination_result(state, result, coordination_type)
            
            # 添加性能指标
            if execution_result.execution_time:
                state = add_performance_metric(
                    state,
                    "coordinator_coordination",
                    {
                        "execution_time": execution_result.execution_time,
                        "coordination_type": coordination_type,
                        "success": result.get("success", True),
                        "agents_coordinated": len(result.get("involved_agents", [])),
                        "conflicts_resolved": len(result.get("resolved_conflicts", []))
                    },
                    execution_result.timestamp
                )
            
            # 更新任务的输出数据
            if state["task_state"]["output_data"] is None:
                state["task_state"]["output_data"] = {}
            
            state["task_state"]["output_data"]["coordinator"] = {
                "coordination_completed": True,
                "coordination_type": coordination_type,
                "coordination_summary": result.get("message", ""),
                "timestamp": execution_result.timestamp.isoformat()
            }
            
        else:
            # 处理协调失败
            error_message = str(execution_result.error) if execution_result.error else "Coordinator协调失败"
            
            state = add_agent_message(
                state,
                sender_agent="coordinator",
                content={
                    "error": error_message,
                    "coordination_failed": True,
                    "retry_count": execution_result.retry_count
                },
                message_type="coordination_error",
                priority=3  # 最高优先级
            )
            
            # 如果协调失败，可能需要人工干预
            if execution_result.retry_count >= self.max_retries:
                state["workflow_context"]["execution_metadata"]["requires_human_intervention"] = True
                state["workflow_context"]["execution_metadata"]["coordination_failure"] = True
        
        # 更新任务的更新时间
        state["task_state"]["updated_at"] = datetime.now()
        
        return state
    
    async def _process_coordination_result(
        self, 
        state: LangGraphTaskState, 
        result: Dict[str, Any], 
        coordination_type: str
    ):
        """处理协调结果并更新工作流状态"""
        try:
            if coordination_type == "establish_collaboration":
                # 协作建立成功
                if result.get("success"):
                    session_id = result.get("session_id")
                    participants = result.get("participants", [])
                    
                    # 更新协调状态
                    state["coordination_state"]["active_sessions"] = state["coordination_state"].get("active_sessions", {})
                    state["coordination_state"]["active_sessions"][session_id] = {
                        "participants": participants,
                        "status": "active",
                        "created_at": datetime.now().isoformat()
                    }
                    
                    # 更新工作流阶段
                    state = update_workflow_phase(state, WorkflowPhase.EXECUTION)
                    state = update_task_status(state, TaskStatus.IN_PROGRESS)
                    
            elif coordination_type == "resolve_conflict":
                # 冲突解决成功
                if result.get("success"):
                    conflict_id = result.get("conflict_id")
                    
                    # 从活跃冲突中移除
                    if "conflicts" in state["coordination_state"]:
                        state["coordination_state"]["conflicts"].pop(conflict_id, None)
                    
                    # 记录解决的冲突
                    if "resolved_conflicts" not in state["coordination_state"]:
                        state["coordination_state"]["resolved_conflicts"] = []
                    
                    state["coordination_state"]["resolved_conflicts"].append({
                        "conflict_id": conflict_id,
                        "resolution_strategy": result.get("resolution_strategy"),
                        "resolved_at": datetime.now().isoformat()
                    })
                    
            elif coordination_type == "coordinate_execution":
                # 执行协调成功
                if result.get("success"):
                    session_id = result.get("session_id")
                    
                    # 更新会话状态
                    if session_id in state["coordination_state"].get("active_sessions", {}):
                        state["coordination_state"]["active_sessions"][session_id]["execution_coordinated"] = True
                        state["coordination_state"]["active_sessions"][session_id]["coordination_result"] = result.get("coordination_result")
                    
            elif coordination_type == "synchronize_agents":
                # 智能体同步成功
                if result.get("success"):
                    sync_results = result.get("sync_results", {})
                    successful_syncs = result.get("successful_syncs", 0)
                    
                    # 更新同步状态
                    state["coordination_state"]["last_sync"] = {
                        "timestamp": datetime.now().isoformat(),
                        "successful_syncs": successful_syncs,
                        "sync_results": sync_results
                    }
                    
                    # 清除同步要求标志
                    state["coordination_state"]["sync_required"] = False
            
            # 记录协调结果到工作流上下文
            state["workflow_context"]["execution_metadata"]["coordination_history"] = state["workflow_context"]["execution_metadata"].get("coordination_history", [])
            state["workflow_context"]["execution_metadata"]["coordination_history"].append({
                "coordination_type": coordination_type,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            # 协调结果处理失败，转入错误处理阶段
            state = update_workflow_phase(state, WorkflowPhase.ERROR_HANDLING)
            state["workflow_context"]["execution_metadata"]["coordination_processing_error"] = str(e)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取Coordinator包装器信息"""
        base_info = {
            "agent_type": self.agent_type,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "execution_statistics": self.get_execution_statistics()
        }
        
        # 添加Coordinator特有信息
        coordinator_info = {
            "max_coordination_attempts": self.max_coordination_attempts,
            "conflict_resolution_timeout": self.conflict_resolution_timeout,
            "session_timeout": self.session_timeout,
            "coordination_capabilities": [
                "agent_coordination",
                "conflict_resolution",
                "resource_allocation",
                "collaboration_management",
                "message_routing",
                "state_synchronization"
            ],
            "supported_coordination_types": [
                "establish_collaboration",
                "resolve_conflict",
                "coordinate_execution",
                "synchronize_agents",
                "general_coordination"
            ],
            "conflict_resolution_strategies": [
                "resource_reallocation",
                "priority_negotiation",
                "mediated_priority",
                "parallel_execution",
                "escalation"
            ]
        }
        
        base_info.update(coordinator_info)
        return base_info
    
    def get_coordination_statistics(self) -> Dict[str, Any]:
        """获取协调统计信息"""
        stats = self.get_execution_statistics()
        
        # 添加协调特有统计
        coordination_stats = {
            "coordination_success_rate": stats.get("success_rate", 0.0),
            "average_coordination_time": stats.get("average_execution_time", 0.0),
            "total_coordinations": stats.get("total_executions", 0),
            "failed_coordinations": stats.get("failed_executions", 0)
        }
        
        return coordination_stats