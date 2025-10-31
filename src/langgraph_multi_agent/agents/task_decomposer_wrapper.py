"""TaskDecomposer包装器 - 任务拆解和依赖分析"""

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


class TaskDecomposerWrapper(AgentNodeWrapper):
    """TaskDecomposer包装器
    
    负责将复杂任务分解为可执行的子任务，分析任务依赖关系，
    生成执行计划和资源分配策略。
    """
    
    def __init__(self, task_decomposer_instance: Any, **kwargs):
        super().__init__(task_decomposer_instance, "task_decomposer", **kwargs)
        
        # TaskDecomposer特有的配置
        self.max_decomposition_depth = 5  # 最大分解深度
        self.decomposition_timeout = 300  # 分解超时时间（秒）
        self.min_subtask_complexity = 0.1  # 最小子任务复杂度阈值
    
    def _extract_task_data(self, state: LangGraphTaskState) -> Dict[str, Any]:
        """从LangGraph状态提取TaskDecomposer需要的任务数据"""
        task_state = state["task_state"]
        workflow_context = state["workflow_context"]
        
        # 构造TaskDecomposer专用的任务数据
        task_data = {
            # 基本任务信息
            "task_id": task_state["task_id"],
            "title": task_state["title"],
            "description": task_state["description"],
            "task_type": task_state["task_type"],
            "priority": task_state["priority"],
            "requirements": task_state["requirements"],
            "constraints": task_state["constraints"],
            "input_data": task_state["input_data"],
            
            # 分解上下文
            "decomposition_context": {
                "current_phase": workflow_context["current_phase"].value,
                "agent_results": workflow_context["agent_results"],
                "execution_metadata": workflow_context["execution_metadata"]
            },
            
            # 确定分解类型
            "decomposition_type": self._determine_decomposition_type(state),
            
            # 分解参数
            "decomposition_params": {
                "max_depth": self.max_decomposition_depth,
                "timeout": self.decomposition_timeout,
                "min_complexity": self.min_subtask_complexity,
                "strategy": self._select_decomposition_strategy(state)
            },
            
            # 历史信息
            "agent_messages": state["agent_messages"],
            "previous_decompositions": workflow_context["execution_metadata"].get("decomposition_history", [])
        }
        
        return task_data
    
    def _determine_decomposition_type(self, state: LangGraphTaskState) -> str:
        """确定分解类型"""
        task_state = state["task_state"]
        workflow_context = state["workflow_context"]
        
        # 检查是否有MetaAgent的分析结果
        meta_result = workflow_context["agent_results"].get("meta_agent", {}).get("result", {})
        
        if meta_result.get("requires_decomposition"):
            return "complex_task"
        
        # 根据任务类型确定分解类型
        task_type = task_state["task_type"]
        if task_type in ["analysis", "research", "investigation"]:
            return "workflow_analysis"
        elif task_type in ["development", "implementation", "creation"]:
            return "task_decomposition"
        else:
            return "complex_task"
    
    def _select_decomposition_strategy(self, state: LangGraphTaskState) -> str:
        """选择分解策略"""
        task_state = state["task_state"]
        
        # 根据任务复杂度和类型选择策略
        complexity_score = state["workflow_context"]["execution_metadata"].get("meta_analysis", {}).get("complexity_score", 0.5)
        
        if complexity_score > 0.8:
            return "hierarchical"  # 高复杂度使用层次分解
        elif "parallel" in task_state["description"].lower():
            return "parallel"  # 明确提到并行的使用并行分解
        elif "step" in task_state["description"].lower() or "sequence" in task_state["description"].lower():
            return "sequential"  # 明确提到步骤的使用顺序分解
        else:
            return "hierarchical"  # 默认使用层次分解
    
    async def _update_state(
        self, 
        state: LangGraphTaskState, 
        execution_result: AgentExecutionResult
    ) -> LangGraphTaskState:
        """更新LangGraph状态"""
        if execution_result.success:
            result = execution_result.result
            decomposition_type = result.get("decomposition_type", "complex_task")
            
            # 添加TaskDecomposer分解消息
            state = add_agent_message(
                state,
                sender_agent="task_decomposer",
                content={
                    "decomposition_result": result,
                    "decomposition_type": decomposition_type,
                    "execution_time": execution_result.execution_time
                },
                message_type="decomposition_result",
                priority=2  # 高优先级
            )
            
            # 更新工作流上下文
            state["workflow_context"]["agent_results"]["task_decomposer"] = {
                "result": result,
                "timestamp": execution_result.timestamp.isoformat(),
                "execution_time": execution_result.execution_time,
                "phase": state["workflow_context"]["current_phase"].value
            }
            
            # 根据分解结果更新状态
            await self._process_decomposition_result(state, result, decomposition_type)
            
            # 添加性能指标
            if execution_result.execution_time:
                state = add_performance_metric(
                    state,
                    "task_decomposer_decomposition",
                    {
                        "execution_time": execution_result.execution_time,
                        "decomposition_type": decomposition_type,
                        "subtasks_count": result.get("subtasks_count", 0),
                        "estimated_duration": result.get("estimated_duration", 0),
                        "decomposition_depth": result.get("decomposition", {}).get("metadata", {}).get("depth", 0)
                    },
                    execution_result.timestamp
                )
            
            # 更新任务的输出数据
            if state["task_state"]["output_data"] is None:
                state["task_state"]["output_data"] = {}
            
            state["task_state"]["output_data"]["task_decomposer"] = {
                "decomposition_completed": True,
                "decomposition_type": decomposition_type,
                "subtasks_count": result.get("subtasks_count", 0),
                "execution_plan_created": "execution_plan" in result,
                "timestamp": execution_result.timestamp.isoformat()
            }
            
        else:
            # 处理分解失败
            error_message = str(execution_result.error) if execution_result.error else "TaskDecomposer分解失败"
            
            state = add_agent_message(
                state,
                sender_agent="task_decomposer",
                content={
                    "error": error_message,
                    "decomposition_failed": True,
                    "retry_count": execution_result.retry_count
                },
                message_type="decomposition_error",
                priority=3  # 最高优先级
            )
            
            # 如果分解失败，可能需要人工干预
            if execution_result.retry_count >= self.max_retries:
                state["workflow_context"]["execution_metadata"]["requires_human_intervention"] = True
                state["workflow_context"]["execution_metadata"]["decomposition_failure"] = True
        
        # 更新任务的更新时间
        state["task_state"]["updated_at"] = datetime.now()
        
        return state
    
    async def _process_decomposition_result(
        self, 
        state: LangGraphTaskState, 
        result: Dict[str, Any], 
        decomposition_type: str
    ):
        """处理分解结果并更新工作流状态"""
        try:
            if result.get("success"):
                decomposition = result.get("decomposition", {})
                execution_plan = result.get("execution_plan", {})
                subtasks_count = result.get("subtasks_count", 0)
                
                # 更新任务状态为进行中
                state = update_task_status(state, TaskStatus.IN_PROGRESS)
                
                # 如果有子任务，转入协调阶段
                if subtasks_count > 0:
                    state = update_workflow_phase(state, WorkflowPhase.COORDINATION)
                    
                    # 设置协调相关的元数据
                    state["workflow_context"]["execution_metadata"]["subtasks_generated"] = True
                    state["workflow_context"]["execution_metadata"]["subtasks_count"] = subtasks_count
                    state["workflow_context"]["execution_metadata"]["decomposition_strategy"] = decomposition.get("decomposition_strategy")
                    
                    # 存储子任务信息
                    if "subtasks" not in state["task_state"]:
                        state["task_state"]["subtasks"] = []
                    
                    subtasks = decomposition.get("subtasks", [])
                    for subtask in subtasks:
                        state["task_state"]["subtasks"].append({
                            "id": subtask.get("id"),
                            "name": subtask.get("name"),
                            "description": subtask.get("description"),
                            "type": subtask.get("type"),
                            "status": "pending",
                            "created_at": datetime.now().isoformat()
                        })
                    
                    # 存储任务依赖关系
                    dependencies = decomposition.get("dependencies", [])
                    if dependencies:
                        state["workflow_context"]["execution_metadata"]["task_dependencies"] = dependencies
                    
                    # 存储执行计划
                    if execution_plan:
                        state["workflow_context"]["execution_metadata"]["execution_plan"] = execution_plan
                        state["workflow_context"]["execution_metadata"]["estimated_duration"] = execution_plan.get("estimated_duration", 0)
                        state["workflow_context"]["execution_metadata"]["execution_order"] = execution_plan.get("execution_order", [])
                
                else:
                    # 没有子任务，直接转入执行阶段
                    state = update_workflow_phase(state, WorkflowPhase.EXECUTION)
                
                # 记录分解历史
                decomposition_history = state["workflow_context"]["execution_metadata"].get("decomposition_history", [])
                decomposition_history.append({
                    "decomposition_type": decomposition_type,
                    "result": result,
                    "timestamp": datetime.now().isoformat(),
                    "subtasks_count": subtasks_count
                })
                state["workflow_context"]["execution_metadata"]["decomposition_history"] = decomposition_history
                
            else:
                # 分解失败，转入错误处理阶段
                state = update_workflow_phase(state, WorkflowPhase.ERROR_HANDLING)
                state["workflow_context"]["execution_metadata"]["decomposition_failed"] = True
                
        except Exception as e:
            # 分解结果处理失败，转入错误处理阶段
            state = update_workflow_phase(state, WorkflowPhase.ERROR_HANDLING)
            state["workflow_context"]["execution_metadata"]["decomposition_processing_error"] = str(e)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取TaskDecomposer包装器信息"""
        base_info = {
            "agent_type": self.agent_type,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "execution_statistics": self.get_execution_statistics()
        }
        
        # 添加TaskDecomposer特有信息
        decomposer_info = {
            "max_decomposition_depth": self.max_decomposition_depth,
            "decomposition_timeout": self.decomposition_timeout,
            "min_subtask_complexity": self.min_subtask_complexity,
            "decomposition_capabilities": [
                "task_decomposition",
                "dependency_analysis",
                "execution_planning",
                "resource_allocation",
                "workflow_analysis",
                "complexity_assessment"
            ],
            "supported_decomposition_types": [
                "complex_task",
                "task_decomposition",
                "workflow_analysis"
            ],
            "decomposition_strategies": [
                "hierarchical",
                "parallel",
                "sequential"
            ],
            "analysis_features": [
                "bottleneck_identification",
                "critical_path_calculation",
                "resource_estimation",
                "risk_assessment",
                "optimization_suggestions"
            ]
        }
        
        base_info.update(decomposer_info)
        return base_info
    
    def get_decomposition_statistics(self) -> Dict[str, Any]:
        """获取分解统计信息"""
        stats = self.get_execution_statistics()
        
        # 添加分解特有统计
        decomposition_stats = {
            "decomposition_success_rate": stats.get("success_rate", 0.0),
            "average_decomposition_time": stats.get("average_execution_time", 0.0),
            "total_decompositions": stats.get("total_executions", 0),
            "failed_decompositions": stats.get("failed_executions", 0)
        }
        
        return decomposition_stats