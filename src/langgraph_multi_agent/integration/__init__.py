"""集成模块 - 与现有智能体系统的集成适配器"""

from .state_adapter import StateAdapter
from .message_adapter import MessageBusAdapter
from .legacy_bridge import LegacySystemBridge

__all__ = [
    "StateAdapter",
    "MessageBusAdapter", 
    "LegacySystemBridge"
]