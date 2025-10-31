"""
LangGraph多智能体系统

基于LangGraph框架的多智能体任务管理系统，集成现有智能体架构。
"""

from .workflow.multi_agent_workflow import MultiAgentWorkflow
from .core.state import LangGraphTaskState
from .agents.wrappers import AgentNodeWrapper
from .api.app import create_app

__version__ = "1.0.0"
__all__ = [
    "MultiAgentWorkflow",
    "LangGraphTaskState", 
    "AgentNodeWrapper",
    "create_app"
]