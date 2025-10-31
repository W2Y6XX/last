"""
多智能体任务管理系统 - BaseAgent（基础智能体抽象类）
创建时间: 2025-10-20
职责：为所有智能体提供基础功能和接口

重构说明：从 agent-implementations/base_agent.py 迁移到新的结构化目录
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid

# 更新导入路径以适应新结构
# TODO: 需要根据实际的通信模块结构更新导入
# from ...shared.communication.message_bus import MessageBus
# from ...shared.communication.protocol import Message, MessageType
# from ...shared.config import Config
# from ...shared.utils.exceptions import AgentError

logger = logging.getLogger(__name__)

# 临时的类定义，直到共享模块完全迁移
class MessageType:
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    SYSTEM_STATUS_REQUEST = "system_status_request"
    STATUS_RESPONSE = "status_response"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_RESPONSE = "heartbeat_response"
    SHUTDOWN_REQUEST = "shutdown_request"
    SHUTDOWN_ACKNOWLEDGMENT = "shutdown_acknowledgment"
    QUERY = "query"

class Message:
    def __init__(self, message_id: str, sender_id: str, recipient_id: str = None,
                 message_type: MessageType = None, content: Dict[str, Any] = None,
                 timestamp: datetime = None, reply_to: str = None):
        self.message_id = message_id
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.message_type = message_type
        self.content = content or {}
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.reply_to = reply_to

class MessageBus:
    def __init__(self):
        self.handlers = {}

    async def send_message(self, recipient_id: str, message: Message):
        pass

    async def broadcast(self, message: Message):
        pass

    async def register_handler(self, message_type: MessageType, handler: callable):
        self.handlers[message_type] = handler

class Config:
    def __init__(self):
        pass

class AgentError(Exception):
    pass

class BaseAgent(ABC):
    """基础智能体抽象类

    为所有智能体提供通用功能，包括消息处理、状态管理、配置管理等。
    所有具体智能体类都应该继承这个基类。
    """

    def __init__(self, agent_id: str, agent_type: str, config: Config = None, message_bus: MessageBus = None):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.config = config or Config()
        self.message_bus = message_bus or MessageBus()

        # 基础状态
        self.is_initialized = False
        self.is_running = False
        self.last_heartbeat = datetime.now(timezone.utc)

        # 能力注册
        self.capabilities: List[str] = []
        self.specializations: List[str] = []

        # 消息处理
        self.message_handlers: Dict[MessageType, callable] = {}
        self.pending_responses: Dict[str, asyncio.Future] = {}

        # 性能监控
        self.metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "tasks_processed": 0,
            "errors_count": 0,
            "uptime": 0.0
        }

        # 事件循环
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None

    @abstractmethod
    async def initialize(self) -> bool:
        """初始化智能体

        Returns:
            bool: 初始化是否成功
        """
        pass

    @abstractmethod
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务

        Args:
            task_data: 任务数据

        Returns:
            Dict[str, Any]: 处理结果
        """
        pass

    async def start(self) -> bool:
        """启动智能体"""
        try:
            if not self.is_initialized:
                if not await self.initialize():
                    raise AgentError("智能体初始化失败")

            self.is_running = True
            self.event_loop = asyncio.get_event_loop()

            # 启动心跳任务
            asyncio.create_task(self._heartbeat_loop())

            # 启动消息处理任务
            asyncio.create_task(self._message_processing_loop())

            logger.info(f"智能体 {self.agent_id} 已启动")
            return True

        except Exception as e:
            logger.error(f"智能体启动失败: {e}")
            return False

    async def stop(self):
        """停止智能体"""
        try:
            self.is_running = False

            # 执行清理操作
            await self.cleanup()

            logger.info(f"智能体 {self.agent_id} 已停止")

        except Exception as e:
            logger.error(f"智能体停止失败: {e}")

    async def cleanup(self):
        """清理资源"""
        # 子类可以重写此方法实现特定的清理逻辑
        pass

    async def register_capability(self, capability: str):
        """注册能力"""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
            logger.debug(f"智能体 {self.agent_id} 注册能力: {capability}")

    async def register_specialization(self, specialization: str):
        """注册专业化领域"""
        if specialization not in self.specializations:
            self.specializations.append(specialization)
            logger.debug(f"智能体 {self.agent_id} 注册专业化: {specialization}")

    async def send_message(self, recipient_id: str, message_type: MessageType, content: Dict[str, Any],
                          reply_to: str = None, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """发送消息

        Args:
            recipient_id: 接收者ID
            message_type: 消息类型
            content: 消息内容
            reply_to: 回复的消息ID
            timeout: 超时时间（秒）

        Returns:
            Optional[Dict[str, Any]]: 回复内容
        """
        try:
            message = Message(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=recipient_id,
                message_type=message_type,
                content=content,
                timestamp=datetime.now(timezone.utc),
                reply_to=reply_to
            )

            # 发送消息
            await self.message_bus.send_message(recipient_id, message)
            self.metrics["messages_sent"] += 1

            # 如果需要回复，等待回复
            if message_type in [MessageType.TASK_REQUEST, MessageType.SYSTEM_STATUS_REQUEST, MessageType.QUERY]:
                response_future = asyncio.Future()
                self.pending_responses[message.message_id] = response_future

                try:
                    response = await asyncio.wait_for(response_future, timeout=timeout)
                    return response
                except asyncio.TimeoutError:
                    logger.warning(f"消息超时: {message.message_id}")
                    if message.message_id in self.pending_responses:
                        del self.pending_responses[message.message_id]
                    return None

            return {"success": True, "message_id": message.message_id}

        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            self.metrics["errors_count"] += 1
            return None

    async def broadcast_message(self, message_type: MessageType, content: Dict[str, Any]) -> bool:
        """广播消息

        Args:
            message_type: 消息类型
            content: 消息内容

        Returns:
            bool: 广播是否成功
        """
        try:
            message = Message(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                message_type=message_type,
                content=content,
                timestamp=datetime.now(timezone.utc)
            )

            await self.message_bus.broadcast(message)
            self.metrics["messages_sent"] += 1
            return True

        except Exception as e:
            logger.error(f"广播消息失败: {e}")
            self.metrics["errors_count"] += 1
            return False

    async def register_message_handler(self, message_type: MessageType, handler: callable):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
        await self.message_bus.register_handler(message_type, handler)

    async def handle_message(self, message: Message) -> Optional[Message]:
        """处理接收到的消息"""
        try:
            self.metrics["messages_received"] += 1

            # 检查是否是回复消息
            if message.reply_to and message.reply_to in self.pending_responses:
                future = self.pending_responses[message.reply_to]
                if not future.done():
                    future.set_result(message.content)
                del self.pending_responses[message.reply_to]
                return None

            # 调用注册的处理器
            handler = self.message_handlers.get(message.message_type)
            if handler:
                response = await handler(message)
                return response
            else:
                logger.warning(f"未找到消息处理器: {message.message_type}")
                return None

        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            self.metrics["errors_count"] += 1
            return None

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # 每分钟发送一次心跳
                await self._send_heartbeat()
            except Exception as e:
                logger.error(f"心跳循环错误: {e}")

    async def _send_heartbeat(self):
        """发送心跳"""
        try:
            heartbeat_message = Message(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                message_type=MessageType.HEARTBEAT,
                content={
                    "agent_id": self.agent_id,
                    "agent_type": self.agent_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "running" if self.is_running else "stopped",
                    "capabilities": self.capabilities,
                    "current_load": self._get_current_load(),
                    "availability": self._get_availability()
                },
                timestamp=datetime.now(timezone.utc)
            )

            await self.message_bus.broadcast(heartbeat_message)
            self.last_heartbeat = datetime.now(timezone.utc)

        except Exception as e:
            logger.error(f"发送心跳失败: {e}")

    async def _message_processing_loop(self):
        """消息处理循环"""
        while self.is_running:
            try:
                await asyncio.sleep(0.1)  # 避免CPU占用过高
                # 消息处理由message_bus主动调用handle_message
            except Exception as e:
                logger.error(f"消息处理循环错误: {e}")

    def _get_current_load(self) -> int:
        """获取当前负载"""
        # 子类可以重写此方法
        return 0

    def _get_availability(self) -> float:
        """获取可用性"""
        # 子类可以重写此方法
        return 1.0 if self.is_running else 0.0

    async def handle_heartbeat_request(self, message: Message) -> Optional[Message]:
        """处理心跳请求"""
        return Message(
            message_id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type=MessageType.HEARTBEAT_RESPONSE,
            content={
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "status": "running" if self.is_running else "stopped",
                "last_heartbeat": self.last_heartbeat.isoformat(),
                "capabilities": self.capabilities,
                "metrics": self.metrics
            },
            timestamp=datetime.now(timezone.utc),
            reply_to=message.message_id
        )

    async def handle_status_request(self, message: Message) -> Optional[Message]:
        """处理状态请求"""
        return Message(
            message_id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type=MessageType.STATUS_RESPONSE,
            content=self.get_status(),
            timestamp=datetime.now(timezone.utc),
            reply_to=message.message_id
        )

    async def handle_shutdown_request(self, message: Message) -> Optional[Message]:
        """处理关闭请求"""
        logger.info(f"收到关闭请求: {message.sender_id}")
        await self.stop()

        return Message(
            message_id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type=MessageType.SHUTDOWN_ACKNOWLEDGMENT,
            content={"agent_id": self.agent_id, "shutdown": True},
            timestamp=datetime.now(timezone.utc),
            reply_to=message.message_id
        )

    def get_status(self) -> Dict[str, Any]:
        """获取智能体状态"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "capabilities": self.capabilities,
            "specializations": self.specializations,
            "metrics": self.metrics,
            "current_load": self._get_current_load(),
            "availability": self._get_availability()
        }

    def update_metrics(self, metric_name: str, value: Any):
        """更新指标"""
        if metric_name in self.metrics:
            if isinstance(self.metrics[metric_name], (int, float)):
                self.metrics[metric_name] += value
            else:
                self.metrics[metric_name] = value

    def reset_metrics(self):
        """重置指标"""
        self.metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "tasks_processed": 0,
            "errors_count": 0,
            "uptime": 0.0
        }

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        current_time = datetime.now(timezone.utc)
        time_since_last_heartbeat = (current_time - self.last_heartbeat).total_seconds()

        return {
            "healthy": self.is_running and time_since_last_heartbeat < 120,  # 2分钟内有心跳
            "status": "running" if self.is_running else "stopped",
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "time_since_last_heartbeat": time_since_last_heartbeat,
            "error_count": self.metrics["errors_count"],
            "message_queue_size": len(self.pending_responses)
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id={self.agent_id}, type={self.agent_type})"

    def __repr__(self) -> str:
        return self.__str__()