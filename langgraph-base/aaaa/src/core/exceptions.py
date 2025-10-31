"""
自定义异常类定义
"""

from typing import List


class AgentSystemError(Exception):
    """系统基础异常"""
    pass


class AgentError(AgentSystemError):
    """智能体相关异常"""
    pass


class TaskError(AgentSystemError):
    """任务相关异常"""
    pass


class CommunicationError(AgentSystemError):
    """通信相关异常"""
    pass


class WorkflowError(AgentSystemError):
    """工作流相关异常"""
    pass


class ValidationError(AgentSystemError):
    """验证相关异常"""
    pass


class ConfigurationError(AgentSystemError):
    """配置相关异常"""
    pass


class ResourceError(AgentSystemError):
    """资源相关异常"""
    pass


# 具体异常类
class AgentNotFoundError(AgentError):
    """智能体未找到异常"""
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        super().__init__(f"Agent not found: {agent_id}")


class TaskNotFoundError(TaskError):
    """任务未找到异常"""
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"Task not found: {task_id}")


class MessageDeliveryError(CommunicationError):
    """消息传递失败异常"""
    def __init__(self, message_id: str, reason: str):
        self.message_id = message_id
        self.reason = reason
        super().__init__(f"Message delivery failed for {message_id}: {reason}")


class WorkflowExecutionError(WorkflowError):
    """工作流执行异常"""
    def __init__(self, node_name: str, error: Exception):
        self.node_name = node_name
        self.original_error = error
        super().__init__(f"Workflow node {node_name} failed: {str(error)}")


class StateValidationError(ValidationError):
    """状态验证异常"""
    def __init__(self, state_key: str, reason: str):
        self.state_key = state_key
        self.reason = reason
        super().__init__(f"State validation failed for {state_key}: {reason}")


class DependencyResolutionError(TaskError):
    """依赖解析异常"""
    def __init__(self, task_id: str, dependency_errors: List[str]):
        self.task_id = task_id
        self.dependency_errors = dependency_errors
        super().__init__(f"Dependency resolution failed for {task_id}: {'; '.join(dependency_errors)}")