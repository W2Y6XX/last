"""LLM模块 - 统一的大语言模型调用接口"""

from .siliconflow_client import (
    SiliconFlowClient,
    get_llm_client,
    set_llm_client,
    chat,
    batch_chat,
    get_llm_stats
)

__all__ = [
    "SiliconFlowClient",
    "get_llm_client", 
    "set_llm_client",
    "chat",
    "batch_chat",
    "get_llm_stats"
]