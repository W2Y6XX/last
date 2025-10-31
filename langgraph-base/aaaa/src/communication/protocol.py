"""
通信协议定义和消息序列化
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator

from ..core.types import MessageType, Priority, AgentId, TaskId


class MessageProtocol(BaseModel):
    """消息协议基类"""
    version: str = "1.0"
    message_id: str
    message_type: MessageType
    sender_id: AgentId
    receiver_id: Optional[AgentId] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    priority: Priority = Priority.MEDIUM

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskRequestMessage(MessageProtocol):
    """任务请求消息"""
    task_id: TaskId
    task_title: str
    task_description: str
    requirements: Dict[str, Any] = Field(default_factory=dict)
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResponseMessage(MessageProtocol):
    """任务响应消息"""
    task_id: TaskId
    status: str  # "accepted", "rejected", "completed", "failed"
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StatusUpdateMessage(MessageProtocol):
    """状态更新消息"""
    entity_type: str  # "task", "agent", "workflow"
    entity_id: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorMessage(MessageProtocol):
    """错误消息"""
    error_code: str
    error_message: str
    error_details: Dict[str, Any] = Field(default_factory=dict)
    stack_trace: Optional[str] = None
    retry_after: Optional[int] = None  # 秒数


class HeartbeatMessage(MessageProtocol):
    """心跳消息"""
    agent_status: str = "active"
    load_percentage: float = 0.0
    available_capabilities: list = Field(default_factory=list)
    system_info: Dict[str, Any] = Field(default_factory=dict)


class BroadcastMessage(MessageProtocol):
    """广播消息"""
    broadcast_type: str  # "system_announcement", "alert", "info"
    target_audience: Optional[str] = None  # "all", "agents", "admins"
    content: str
    ttl: Optional[int] = None  # 生存时间（秒）


# 消息序列化器
class MessageSerializer:
    """消息序列化工具"""

    @staticmethod
    def serialize(message: MessageProtocol) -> str:
        """序列化消息为JSON字符串"""
        try:
            return message.json()
        except Exception as e:
            raise ValueError(f"Failed to serialize message: {e}")

    @staticmethod
    def deserialize(message_json: str, message_type: MessageType) -> MessageProtocol:
        """从JSON字符串反序列化消息"""
        try:
            data = json.loads(message_json)

            # 根据消息类型创建相应的消息对象
            message_classes = {
                MessageType.TASK_REQUEST: TaskRequestMessage,
                MessageType.TASK_RESPONSE: TaskResponseMessage,
                MessageType.STATUS_UPDATE: StatusUpdateMessage,
                MessageType.ERROR: ErrorMessage,
                MessageType.HEARTBEAT: HeartbeatMessage,
                MessageType.BROADCAST: BroadcastMessage
            }

            message_class = message_classes.get(message_type)
            if not message_class:
                raise ValueError(f"Unknown message type: {message_type}")

            return message_class.parse_obj(data)

        except Exception as e:
            raise ValueError(f"Failed to deserialize message: {e}")

    @staticmethod
    def serialize_batch(messages: list[MessageProtocol]) -> str:
        """批量序列化消息"""
        try:
            return json.dumps([
                json.loads(msg.json()) for msg in messages
            ])
        except Exception as e:
            raise ValueError(f"Failed to serialize message batch: {e}")

    @staticmethod
    def deserialize_batch(batch_json: str) -> list[MessageProtocol]:
        """批量反序列化消息"""
        try:
            data = json.loads(batch_json)
            messages = []

            for msg_data in data:
                message_type = MessageType(msg_data.get("message_type"))
                message = MessageSerializer.deserialize(
                    json.dumps(msg_data),
                    message_type
                )
                messages.append(message)

            return messages

        except Exception as e:
            raise ValueError(f"Failed to deserialize message batch: {e}")


# 消息验证器
class MessageValidator:
    """消息验证工具"""

    @staticmethod
    def validate_message(message: MessageProtocol) -> tuple[bool, Optional[str]]:
        """验证消息格式和内容"""
        try:
            # 基本字段验证
            if not message.message_id:
                return False, "Missing message_id"

            if not message.sender_id:
                return False, "Missing sender_id"

            if not isinstance(message.message_type, MessageType):
                return False, "Invalid message_type"

            if not isinstance(message.priority, Priority):
                return False, "Invalid priority"

            # 特定消息类型验证
            if isinstance(message, TaskRequestMessage):
                if not message.task_id:
                    return False, "TaskRequest missing task_id"
                if not message.task_title:
                    return False, "TaskRequest missing task_title"

            elif isinstance(message, TaskResponseMessage):
                if not message.task_id:
                    return False, "TaskResponse missing task_id"
                if message.status not in ["accepted", "rejected", "completed", "failed"]:
                    return False, "TaskResponse invalid status"

            elif isinstance(message, ErrorMessage):
                if not message.error_code:
                    return False, "ErrorMessage missing error_code"
                if not message.error_message:
                    return False, "ErrorMessage missing error_message"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    @staticmethod
    def sanitize_message(message: MessageProtocol) -> MessageProtocol:
        """清理和标准化消息"""
        # 确保时间戳是datetime对象
        if isinstance(message.timestamp, str):
            message.timestamp = datetime.fromisoformat(message.timestamp)

        # 确保优先级是大写
        if isinstance(message.priority, str):
            message.priority = Priority(message.priority.upper())

        # 确保消息类型是大写
        if isinstance(message.message_type, str):
            message.message_type = MessageType(message.message_type.upper())

        return message


# 消息工厂
class MessageFactory:
    """消息创建工厂"""

    @staticmethod
    def create_task_request(
        sender_id: AgentId,
        receiver_id: AgentId,
        task_id: TaskId,
        title: str,
        description: str,
        **kwargs
    ) -> TaskRequestMessage:
        """创建任务请求消息"""
        return TaskRequestMessage(
            message_id=f"task_{task_id}_{datetime.now().timestamp()}",
            message_type=MessageType.TASK_REQUEST,
            sender_id=sender_id,
            receiver_id=receiver_id,
            task_id=task_id,
            task_title=title,
            task_description=description,
            **kwargs
        )

    @staticmethod
    def create_task_response(
        sender_id: AgentId,
        receiver_id: AgentId,
        task_id: TaskId,
        status: str,
        **kwargs
    ) -> TaskResponseMessage:
        """创建任务响应消息"""
        return TaskResponseMessage(
            message_id=f"response_{task_id}_{datetime.now().timestamp()}",
            message_type=MessageType.TASK_RESPONSE,
            sender_id=sender_id,
            receiver_id=receiver_id,
            task_id=task_id,
            status=status,
            **kwargs
        )

    @staticmethod
    def create_error_message(
        sender_id: AgentId,
        receiver_id: Optional[AgentId],
        error_code: str,
        error_message: str,
        **kwargs
    ) -> ErrorMessage:
        """创建错误消息"""
        return ErrorMessage(
            message_id=f"error_{datetime.now().timestamp()}",
            message_type=MessageType.ERROR,
            sender_id=sender_id,
            receiver_id=receiver_id,
            error_code=error_code,
            error_message=error_message,
            **kwargs
        )

    @staticmethod
    def create_heartbeat(
        sender_id: AgentId,
        **kwargs
    ) -> HeartbeatMessage:
        """创建心跳消息"""
        return HeartbeatMessage(
            message_id=f"heartbeat_{sender_id}_{datetime.now().timestamp()}",
            message_type=MessageType.HEARTBEAT,
            sender_id=sender_id,
            **kwargs
        )

    @staticmethod
    def create_broadcast(
        sender_id: AgentId,
        content: str,
        broadcast_type: str = "info",
        **kwargs
    ) -> BroadcastMessage:
        """创建广播消息"""
        return BroadcastMessage(
            message_id=f"broadcast_{datetime.now().timestamp()}",
            message_type=MessageType.BROADCAST,
            sender_id=sender_id,
            content=content,
            broadcast_type=broadcast_type,
            **kwargs
        )