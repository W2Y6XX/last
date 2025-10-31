"""
MetaAgent 实现 - 基于LangGraph的元智能体
"""

from typing import Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END

from ..core.base_agent import BaseAgent
from ..core.state import MetaAgentState
from ..core.types import AgentType, TaskStatus
from ..utils.logging import get_logger
from .nodes import (
    task_analysis_node,
    requirement_clarification_node,
    task_decomposition_node,
    agent_assignment_node
)

logger = get_logger(__name__)


class MetaAgent(BaseAgent):
    """元智能体 - 负责任务分析、需求澄清和智能体协调"""

    def __init__(
        self,
        agent_id: str = "meta-agent",
        name: str = "MetaAgent",
        description: str = "负责任务分析、需求澄清和智能体协调的元智能体"
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.META,
            name=name,
            description=description,
            capabilities=[
                "task_analysis",
                "requirement_clarification",
                "task_decomposition",
                "agent_assignment",
                "workflow_coordination"
            ]
        )

    def create_workflow(self) -> StateGraph:
        """创建MetaAgent工作流"""
        workflow = StateGraph(MetaAgentState)

        # 添加节点
        workflow.add_node("task_analysis", task_analysis_node)
        workflow.add_node("requirement_clarification", requirement_clarification_node)
        workflow.add_node("task_decomposition", task_decomposition_node)
        workflow.add_node("agent_assignment", agent_assignment_node)

        # 定义条件路由
        workflow.add_conditional_edges(
            "task_analysis",
            self._should_clarify_requirements,
            {
                "clarify": "requirement_clarification",
                "decompose": "task_decomposition",
                "error": END
            }
        )

        workflow.add_conditional_edges(
            "requirement_clarification",
            self._check_clarification_complete,
            {
                "complete": "task_decomposition",
                "waiting": END,  # 等待用户回应
                "error": END
            }
        )

        # 线性流程边
        workflow.add_edge("task_decomposition", "agent_assignment")
        workflow.add_edge("agent_assignment", END)

        # 设置入口点
        workflow.add_edge(START, "task_analysis")

        return workflow

    def _should_clarify_requirements(self, state: MetaAgentState) -> str:
        """判断是否需要需求澄清"""
        try:
            analysis_result = state.get("current_analysis", {})
            clarification_needed = analysis_result.get("requires_clarification", False)

            if clarification_needed:
                logger.info("Requirements clarification needed")
                return "clarify"
            else:
                logger.info("No clarification needed, proceeding to decomposition")
                return "decompose"

        except Exception as e:
            logger.error(f"Error in clarification decision: {e}")
            return "error"

    def _check_clarification_complete(self, state: MetaAgentState) -> str:
        """检查澄清是否完成"""
        try:
            pending_clarifications = state.get("pending_clarifications", False)
            clarification_responses = state.get("clarification_responses", {})

            if not pending_clarifications:
                return "complete"

            # 检查是否有新的澄清回应
            if clarification_responses:
                logger.info("Clarification responses received, proceeding to decomposition")
                return "complete"
            else:
                logger.info("Waiting for clarification responses")
                return "waiting"

        except Exception as e:
            logger.error(f"Error checking clarification completion: {e}")
            return "error"

    async def process_task_request(self, task_description: str) -> Dict[str, Any]:
        """处理任务请求"""
        try:
            from langchain_core.messages import HumanMessage

            # 创建初始消息
            message = HumanMessage(content=task_description)

            # 执行工作流
            result = await self.workflow.ainvoke(self._create_initial_state([message]))

            # 提取结果
            return {
                "success": True,
                "workflow_stage": result.get("workflow_stage"),
                "analyzed_tasks": result.get("analyzed_tasks", []),
                "agent_assignments": result.get("agent_assignments", {}),
                "messages": result.get("messages", []),
                "current_analysis": result.get("current_analysis", {}),
                "task_decomposition": result.get("task_decomposition", {})
            }

        except Exception as e:
            logger.error(f"Error processing task request: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def add_clarification_response(self, response: str) -> None:
        """添加澄清回应"""
        # 这个方法将在后续版本中实现
        # 目前只是简单的日志记录
        logger.info(f"Clarification response received: {response}")

    def get_workflow_status(self) -> Dict[str, Any]:
        """获取工作流状态"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "capabilities": self.capabilities,
            "workflow_nodes": [
                "task_analysis",
                "requirement_clarification",
                "task_decomposition",
                "agent_assignment"
            ]
        }