"""MetaAgent包装器 - 任务分析和需求澄清"""

from typing import Dict, Any, Optional
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
from ..utils.helpers import calculate_complexity_score
from ..llm import chat


class MetaAgentWrapper(AgentNodeWrapper):
    """MetaAgent包装器
    
    负责任务分析、复杂度评估、需求澄清和智能体推荐。
    MetaAgent是工作流的入口点，决定任务的处理策略。
    """
    
    def __init__(self, meta_agent_instance: Any = None, agent_id: str = None, llm: Any = None, name: str = None, description: str = None, **kwargs):
        # Handle backward compatibility with old test interface
        if meta_agent_instance is None and agent_id is not None:
            # Create a mock agent instance for testing
            class MockMetaAgent:
                def __init__(self, agent_id, llm=None, name=None, description=None):
                    self.agent_id = agent_id
                    self.llm = llm
                    self.name = name or "MetaAgent"
                    self.description = description or "任务分析智能体"
                
                async def process_task(self, task_data):
                    return {
                        "analysis_result": "success",
                        "complexity_score": 0.5,
                        "requires_decomposition": False,
                        "clarification_needed": False,
                        "recommended_agents": ["coordinator"],
                        "analysis_summary": "Task analyzed successfully"
                    }
            
            meta_agent_instance = MockMetaAgent(agent_id, llm, name, description)
        
        if meta_agent_instance is None:
            raise TypeError("MetaAgentWrapper.__init__() missing 1 required positional argument: 'meta_agent_instance'")
        
        super().__init__(meta_agent_instance, "meta_agent", **kwargs)
        
        # MetaAgent特有的配置
        self.complexity_threshold = 0.6  # 复杂度阈值
        self.requires_decomposition_threshold = 0.7  # 需要拆解的阈值
        self.max_clarification_rounds = 3  # 最大澄清轮数
    
    def _extract_task_data(self, state: LangGraphTaskState) -> Dict[str, Any]:
        """从LangGraph状态提取MetaAgent需要的任务数据"""
        task_state = state["task_state"]
        workflow_context = state["workflow_context"]
        
        # 构造MetaAgent专用的任务数据
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
            
            # 分析上下文
            "analysis_context": {
                "current_phase": workflow_context["current_phase"].value,
                "previous_results": workflow_context["agent_results"],
                "retry_count": state["retry_count"],
                "execution_metadata": workflow_context["execution_metadata"]
            },
            
            # 计算初始复杂度分数
            "initial_complexity": calculate_complexity_score({
                "description": task_state["description"],
                "requirements": task_state["requirements"],
                "input_data": task_state["input_data"],
                "priority": task_state["priority"]
            }),
            
            # 历史信息
            "agent_messages": state["agent_messages"],
            "coordination_state": state["coordination_state"],
            
            # MetaAgent特有参数
            "analysis_mode": "comprehensive",  # 分析模式
            "include_recommendations": True,   # 包含智能体推荐
            "clarification_enabled": True      # 启用需求澄清
        }
        
        return task_data
    
    async def _update_state(
        self, 
        state: LangGraphTaskState, 
        execution_result: AgentExecutionResult
    ) -> LangGraphTaskState:
        """更新LangGraph状态"""
        if execution_result.success:
            result = execution_result.result
            
            # 添加MetaAgent分析消息
            state = add_agent_message(
                state,
                sender_agent="meta_agent",
                content={
                    "analysis_result": result,
                    "analysis_type": "task_analysis",
                    "execution_time": execution_result.execution_time
                },
                message_type="analysis_result",
                priority=2  # 高优先级
            )
            
            # 更新工作流上下文
            state["workflow_context"]["agent_results"]["meta_agent"] = {
                "result": result,
                "timestamp": execution_result.timestamp.isoformat(),
                "execution_time": execution_result.execution_time,
                "phase": state["workflow_context"]["current_phase"].value
            }
            
            # 根据分析结果更新任务状态和工作流阶段
            await self._process_analysis_result(state, result)
            
            # 添加性能指标
            if execution_result.execution_time:
                state = add_performance_metric(
                    state,
                    "meta_agent_analysis",
                    {
                        "execution_time": execution_result.execution_time,
                        "complexity_score": result.get("complexity_score", 0),
                        "requires_decomposition": result.get("requires_decomposition", False),
                        "recommended_agents": len(result.get("recommended_agents", [])),
                        "clarification_needed": result.get("clarification_needed", False)
                    },
                    execution_result.timestamp
                )
            
            # 更新任务的输出数据
            if state["task_state"]["output_data"] is None:
                state["task_state"]["output_data"] = {}
            
            state["task_state"]["output_data"]["meta_agent"] = {
                "analysis_completed": True,
                "complexity_score": result.get("complexity_score", 0),
                "analysis_summary": result.get("analysis_summary", ""),
                "next_steps": result.get("next_steps", []),
                "timestamp": execution_result.timestamp.isoformat()
            }
            
        else:
            # 处理分析失败
            error_message = str(execution_result.error) if execution_result.error else "MetaAgent分析失败"
            
            state = add_agent_message(
                state,
                sender_agent="meta_agent",
                content={
                    "error": error_message,
                    "analysis_failed": True,
                    "retry_count": execution_result.retry_count
                },
                message_type="analysis_error",
                priority=3  # 最高优先级
            )
            
            # 如果分析失败，可能需要人工干预
            if execution_result.retry_count >= self.max_retries:
                state["workflow_context"]["execution_metadata"]["requires_human_intervention"] = True
        
        # 更新任务的更新时间
        state["task_state"]["updated_at"] = datetime.now()
        
        return state
    
    async def _process_analysis_result(self, state: LangGraphTaskState, result: Dict[str, Any]):
        """处理分析结果并更新工作流状态"""
        try:
            # 根据分析结果决定下一步工作流阶段
            complexity_score = result.get("complexity_score", 0)
            requires_decomposition = result.get("requires_decomposition", False)
            clarification_needed = result.get("clarification_needed", False)
            recommended_agents = result.get("recommended_agents", [])
            
            # 更新任务状态
            if clarification_needed:
                # 需要澄清需求
                state = update_task_status(state, TaskStatus.PENDING)
                state = update_workflow_phase(state, WorkflowPhase.ANALYSIS)
                
                # 设置澄清相关的元数据
                state["workflow_context"]["execution_metadata"]["clarification_required"] = True
                state["workflow_context"]["execution_metadata"]["clarification_questions"] = result.get("clarification_questions", [])
                
            elif requires_decomposition:
                # 需要任务拆解
                state = update_task_status(state, TaskStatus.IN_PROGRESS)
                state = update_workflow_phase(state, WorkflowPhase.DECOMPOSITION)
                
                # 设置拆解相关的元数据
                state["workflow_context"]["execution_metadata"]["decomposition_strategy"] = result.get("decomposition_strategy", "sequential")
                state["workflow_context"]["execution_metadata"]["subtask_count"] = result.get("estimated_subtasks", 0)
                
            elif recommended_agents:
                # 可以直接分配给智能体
                state = update_task_status(state, TaskStatus.IN_PROGRESS)
                state = update_workflow_phase(state, WorkflowPhase.COORDINATION)
                
                # 设置智能体分配相关的元数据
                state["workflow_context"]["execution_metadata"]["recommended_agents"] = recommended_agents
                state["workflow_context"]["execution_metadata"]["coordination_strategy"] = result.get("coordination_strategy", "sequential")
                
            else:
                # 任务过于简单或复杂，需要特殊处理
                if complexity_score < 0.2:
                    # 简单任务，直接执行
                    state = update_task_status(state, TaskStatus.IN_PROGRESS)
                    state = update_workflow_phase(state, WorkflowPhase.EXECUTION)
                else:
                    # 复杂任务但无明确处理策略，需要人工干预
                    state = update_task_status(state, TaskStatus.PENDING)
                    state = update_workflow_phase(state, WorkflowPhase.ERROR_HANDLING)
                    state["workflow_context"]["execution_metadata"]["requires_human_intervention"] = True
            
            # 记录分析结果到工作流上下文
            state["workflow_context"]["execution_metadata"]["meta_analysis"] = {
                "complexity_score": complexity_score,
                "requires_decomposition": requires_decomposition,
                "clarification_needed": clarification_needed,
                "analysis_timestamp": datetime.now().isoformat(),
                "analysis_summary": result.get("analysis_summary", "")
            }
            
        except Exception as e:
            # 分析结果处理失败，转入错误处理阶段
            state = update_workflow_phase(state, WorkflowPhase.ERROR_HANDLING)
            state["workflow_context"]["execution_metadata"]["analysis_processing_error"] = str(e)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取MetaAgent包装器信息"""
        base_info = {
            "agent_type": self.agent_type,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "execution_statistics": self.get_execution_statistics()
        }
        
        # 添加MetaAgent特有信息
        meta_info = {
            "complexity_threshold": self.complexity_threshold,
            "decomposition_threshold": self.requires_decomposition_threshold,
            "max_clarification_rounds": self.max_clarification_rounds,
            "analysis_capabilities": [
                "task_complexity_assessment",
                "requirement_clarification",
                "agent_recommendation",
                "decomposition_strategy",
                "coordination_planning"
            ],
            "supported_task_types": [
                "general",
                "analysis",
                "research",
                "planning",
                "coordination",
                "complex_workflow"
            ]
        }
        
        base_info.update(meta_info)
        return base_info