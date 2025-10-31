"""通用智能体包装器"""

from typing import Dict, Any
from datetime import datetime

from .wrappers import AgentNodeWrapper, AgentExecutionResult
from ..core.state import (
    LangGraphTaskState,
    add_agent_message,
    add_performance_metric,
    handle_error
)


class GenericAgentWrapper(AgentNodeWrapper):
    """通用智能体包装器
    
    为不需要特殊处理的智能体提供标准的包装实现。
    """
    
    def _extract_task_data(self, state: LangGraphTaskState) -> Dict[str, Any]:
        """从LangGraph状态提取任务数据"""
        task_state = state["task_state"]
        workflow_context = state["workflow_context"]
        
        # 构造标准的任务数据格式
        task_data = {
            "task_id": task_state["task_id"],
            "title": task_state["title"],
            "description": task_state["description"],
            "task_type": task_state["task_type"],
            "priority": task_state["priority"],
            "requirements": task_state["requirements"],
            "constraints": task_state["constraints"],
            "input_data": task_state["input_data"],
            
            # 添加工作流上下文
            "workflow_context": {
                "current_phase": workflow_context["current_phase"].value,
                "completed_phases": [phase.value for phase in workflow_context["completed_phases"]],
                "agent_results": workflow_context["agent_results"],
                "coordination_plan": workflow_context["coordination_plan"]
            },
            
            # 添加协调状态
            "coordination_state": state["coordination_state"],
            
            # 添加执行元数据
            "execution_metadata": {
                "current_node": state["current_node"],
                "retry_count": state["retry_count"],
                "execution_start_time": state["execution_start_time"].isoformat() if state["execution_start_time"] else None
            }
        }
        
        return task_data
    
    async def _update_state(
        self, 
        state: LangGraphTaskState, 
        execution_result: AgentExecutionResult
    ) -> LangGraphTaskState:
        """更新LangGraph状态"""
        if execution_result.success:
            # 成功执行的状态更新
            result = execution_result.result
            
            # 添加智能体消息
            state = add_agent_message(
                state,
                sender_agent=self.agent_type,
                content={
                    "execution_result": result,
                    "success": True,
                    "execution_time": execution_result.execution_time
                },
                message_type="execution_result"
            )
            
            # 更新工作流上下文中的智能体结果
            state["workflow_context"]["agent_results"][self.agent_type] = {
                "result": result,
                "timestamp": execution_result.timestamp.isoformat(),
                "execution_time": execution_result.execution_time,
                "phase": state["workflow_context"]["current_phase"].value
            }
            
            # 如果智能体返回了输出数据，更新任务状态
            if "output_data" in result:
                if state["task_state"]["output_data"] is None:
                    state["task_state"]["output_data"] = {}
                state["task_state"]["output_data"][self.agent_type] = result["output_data"]
            
            # 添加性能指标
            if execution_result.execution_time:
                state = add_performance_metric(
                    state,
                    f"{self.agent_type}_performance",
                    {
                        "execution_time": execution_result.execution_time,
                        "success": True,
                        "retry_count": execution_result.retry_count
                    }
                )
            
            # 更新任务的更新时间
            state["task_state"]["updated_at"] = datetime.now()
            
        else:
            # 执行失败的状态更新
            error_message = str(execution_result.error) if execution_result.error else "未知错误"
            
            # 添加错误消息
            state = add_agent_message(
                state,
                sender_agent=self.agent_type,
                content={
                    "error": error_message,
                    "success": False,
                    "retry_count": execution_result.retry_count
                },
                message_type="execution_error"
            )
            
            # 处理错误状态
            if execution_result.error:
                state = handle_error(
                    state, 
                    execution_result.error, 
                    self.agent_type, 
                    self.agent_type
                )
        
        return state
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取智能体信息"""
        info = {
            "agent_type": self.agent_type,
            "agent_class": self.agent.__class__.__name__ if self.agent else "Unknown",
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "enable_monitoring": self.enable_monitoring,
            "has_process_task": hasattr(self.agent, 'process_task') if self.agent else False
        }
        
        # 如果智能体有额外的信息方法，调用它们
        if hasattr(self.agent, 'get_status'):
            try:
                if asyncio.iscoroutinefunction(self.agent.get_status):
                    # 对于异步方法，这里不能直接调用，返回占位符
                    info["agent_status"] = "async_method_available"
                else:
                    info["agent_status"] = self.agent.get_status()
            except Exception as e:
                info["agent_status_error"] = str(e)
        
        if hasattr(self.agent, 'capabilities'):
            info["capabilities"] = getattr(self.agent, 'capabilities', [])
        
        if hasattr(self.agent, 'specializations'):
            info["specializations"] = getattr(self.agent, 'specializations', [])
        
        return info