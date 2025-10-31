"""
LangGraph多智能体系统 - 源代码包

这是一个基于LangGraph的多智能体协作系统，提供智能任务分解、
智能体协调和错误恢复能力。
"""

__version__ = "1.0.0"
__author__ = "LangGraph Multi-Agent Team"

# 导出主要模块
from . import agents
from . import shared

# 尝试导入LangGraph模块（可选）
try:
    from . import langgraph_multi_agent
    __all__ = [
        "langgraph_multi_agent",
        "agents",
        "shared"
    ]
except ImportError:
    # 如果LangGraph模块未就绪，仍然导出可用模块
    __all__ = [
        "agents",
        "shared"
    ]