"""
共享组件模块

包含多个模块之间共享的组件，如通信、配置和工具函数。
"""

from . import communication
from . import config
from . import utils

__all__ = [
    "communication",
    "config",
    "utils"
]