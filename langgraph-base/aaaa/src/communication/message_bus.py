"""
消息总线实现 - 智能体间通信的核心组件
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import json

from ..core.types import (
    MessageType, MessageContent, Priority,
    AgentId, MessageId, AgentInfo
)
from ..core.exceptions import CommunicationError, MessageDeliveryError
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class QueuedMessage:
    """队列中的消息"""
    message: MessageContent
    timestamp: datetime
    retry_count: int = 0
    max_retries: int = 3
    priority: Priority = Priority.MEDIUM


class MessageBus:
    """消息总线 - 负责智能体间的消息传递"""

    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size

        # 消息队列 - 按优先级分组
        self._queues: Dict[Priority, deque] = {
            Priority.CRITICAL: deque(maxlen=max_queue_size // 4),
            Priority.HIGH: deque(maxlen=max_queue_size // 4),
            Priority.MEDIUM: deque(maxlen=max_queue_size // 2),
            Priority.LOW: deque(maxlen=max_queue_size // 2)
        }

        # 消息处理器
        self._message_handlers: Dict[MessageType, List[Callable]] = defaultdict(list)
        self._agent_handlers: Dict[AgentId, List[Callable]] = defaultdict(list)

        # 活跃智能体
        self._active_agents: Set[AgentId] = set()

        # 消息历史
        self._message_history: List[MessageContent] = []
        self._max_history_size = 10000

        # 等待响应的消息
        self._pending_responses: Dict[str, asyncio.Future] = {}

        # 统计信息
        self._stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
            "messages_delivered": 0
        }

        # 后台任务
        self._background_tasks: Set[asyncio.Task] = set()
        self._is_running = False

    async def start(self) -> None:
        """启动消息总线"""
        if self._is_running:
            return

        self._is_running = True
        # 启动消息处理任务
        task = asyncio.create_task(self._process_messages())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        logger.info("MessageBus started")

    async def stop(self) -> None:
        """停止消息总线"""
        self._is_running = False

        # 取消所有后台任务
        for task in self._background_tasks:
            task.cancel()

        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        logger.info("MessageBus stopped")

    async def register_agent(self, agent_id: AgentId, handler: Callable = None) -> None:
        """注册智能体"""
        self._active_agents.add(agent_id)
        if handler:
            self._agent_handlers[agent_id].append(handler)
        logger.info(f"Agent registered: {agent_id}")

    async def unregister_agent(self, agent_id: AgentId) -> None:
        """注销智能体"""
        self._active_agents.discard(agent_id)
        self._agent_handlers.pop(agent_id, None)
        logger.info(f"Agent unregistered: {agent_id}")

    async def send_message(
        self,
        message: MessageContent,
        expect_response: bool = False,
        timeout: float = 30.0
    ) -> Optional[Any]:
        """发送消息"""
        try:
            # 验证消息
            if not self._validate_message(message):
                raise CommunicationError("Invalid message format")

            # 生成消息ID
            if not hasattr(message, 'message_id'):
                message.message_id = str(uuid.uuid4())

            # 添加到队列
            queued_msg = QueuedMessage(
                message=message,
                timestamp=datetime.now(),
                priority=message.priority
            )

            queue = self._queues[message.priority]
            queue.append(queued_msg)

            # 如果期望响应，创建Future
            if expect_response:
                future = asyncio.Future()
                self._pending_responses[message.message_id] = future
                try:
                    return await asyncio.wait_for(future, timeout=timeout)
                except asyncio.TimeoutError:
                    self._pending_responses.pop(message.message_id, None)
                    raise CommunicationError(f"Message timeout: {message.message_id}")

            self._stats["messages_sent"] += 1
            logger.debug(f"Message queued: {message.message_id}")

            return None

        except Exception as e:
            self._stats["messages_failed"] += 1
            logger.error(f"Failed to send message: {e}")
            raise MessageDeliveryError(
                getattr(message, 'message_id', 'unknown'),
                str(e)
            )

    async def send_message_to_agent(
        self,
        sender_id: AgentId,
        receiver_id: AgentId,
        content: Any,
        message_type: MessageType = MessageType.TASK_REQUEST,
        priority: Priority = Priority.MEDIUM,
        correlation_id: str = None
    ) -> None:
        """向特定智能体发送消息"""
        message = MessageContent(
            message_type=message_type,
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            priority=priority,
            correlation_id=correlation_id
        )

        await self.send_message(message)

    async def broadcast_message(
        self,
        sender_id: AgentId,
        content: Any,
        message_type: MessageType = MessageType.BROADCAST,
        priority: Priority = Priority.MEDIUM,
        exclude_agents: List[AgentId] = None
    ) -> None:
        """广播消息给所有活跃智能体"""
        exclude_agents = exclude_agents or []
        exclude_agents.append(sender_id)  # 排除发送者

        message = MessageContent(
            message_type=message_type,
            sender_id=sender_id,
            receiver_id=None,  # 广播消息没有特定接收者
            content=content,
            priority=priority
        )

        await self.send_message(message)

    async def subscribe_to_message_type(
        self,
        message_type: MessageType,
        handler: Callable
    ) -> None:
        """订阅特定类型的消息"""
        self._message_handlers[message_type].append(handler)
        logger.debug(f"Handler subscribed to message type: {message_type}")

    async def unsubscribe_from_message_type(
        self,
        message_type: MessageType,
        handler: Callable
    ) -> None:
        """取消订阅特定类型的消息"""
        if handler in self._message_handlers[message_type]:
            self._message_handlers[message_type].remove(handler)
            logger.debug(f"Handler unsubscribed from message type: {message_type}")

    def get_message_history(
        self,
        agent_id: AgentId = None,
        message_type: MessageType = None,
        limit: int = 100
    ) -> List[MessageContent]:
        """获取消息历史"""
        history = self._message_history

        # 过滤
        if agent_id:
            history = [
                msg for msg in history
                if msg.sender_id == agent_id or msg.receiver_id == agent_id
            ]

        if message_type:
            history = [msg for msg in history if msg.message_type == message_type]

        # 限制数量
        return history[-limit:] if len(history) > limit else history

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "active_agents": len(self._active_agents),
            "queue_sizes": {
                priority.value: len(queue)
                for priority, queue in self._queues.items()
            },
            "pending_responses": len(self._pending_responses),
            "is_running": self._is_running
        }

    async def _process_messages(self) -> None:
        """处理消息队列"""
        while self._is_running:
            try:
                # 按优先级处理消息
                for priority in [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
                    queue = self._queues[priority]
                    if queue:
                        await self._process_single_message(queue.popleft())
                        break  # 处理一条消息后重新开始，确保高优先级消息优先处理

                await asyncio.sleep(0.01)  # 短暂休眠避免CPU占用过高

            except Exception as e:
                logger.error(f"Error in message processing loop: {e}")
                await asyncio.sleep(0.1)

    async def _process_single_message(self, queued_msg: QueuedMessage) -> None:
        """处理单条消息"""
        try:
            message = queued_msg.message

            # 验证接收者
            if message.receiver_id and message.receiver_id not in self._active_agents:
                raise CommunicationError(f"Receiver not active: {message.receiver_id}")

            # 添加到历史
            self._add_to_history(message)

            # 调用处理器
            await self._call_message_handlers(message)

            # 处理响应
            if message.correlation_id and message.correlation_id in self._pending_responses:
                future = self._pending_responses.pop(message.correlation_id)
                if not future.done():
                    future.set_result(message.content)

            self._stats["messages_delivered"] += 1
            logger.debug(f"Message delivered: {message.message_id}")

        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            self._stats["messages_failed"] += 1

            # 重试逻辑
            if queued_msg.retry_count < queued_msg.max_retries:
                queued_msg.retry_count += 1
                # 重新加入队列
                self._queues[queued_msg.priority].appendleft(queued_msg)
                logger.info(f"Message requeued for retry: {queued_msg.retry_count}/{queued_msg.max_retries}")

    async def _call_message_handlers(self, message: MessageContent) -> None:
        """调用消息处理器"""
        # 调用消息类型处理器
        for handler in self._message_handlers[message.message_type]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Message handler error: {e}")

        # 调用特定智能体处理器
        if message.receiver_id:
            for handler in self._agent_handlers[message.receiver_id]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    logger.error(f"Agent handler error: {e}")

        # 调用广播处理器
        if message.receiver_id is None:
            for agent_id in self._active_agents:
                if agent_id != message.sender_id:  # 不发送给发送者
                    for handler in self._agent_handlers[agent_id]:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(message)
                            else:
                                handler(message)
                        except Exception as e:
                            logger.error(f"Broadcast handler error: {e}")

    def _add_to_history(self, message: MessageContent) -> None:
        """添加消息到历史记录"""
        self._message_history.append(message)

        # 限制历史记录大小
        if len(self._message_history) > self._max_history_size:
            self._message_history = self._message_history[-self._max_history_size // 2:]

    def _validate_message(self, message: MessageContent) -> bool:
        """验证消息格式"""
        if not isinstance(message, MessageContent):
            return False

        if not message.sender_id:
            return False

        if message.message_type not in MessageType:
            return False

        if message.priority not in Priority:
            return False

        return True

    async def cleanup_expired_messages(self, max_age_hours: int = 24) -> None:
        """清理过期消息"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        # 清理消息历史
        self._message_history = [
            msg for msg in self._message_history
            if msg.timestamp > cutoff_time
        ]

        # 清理过期的响应等待
        expired_correlations = [
            corr_id for corr_id, future in self._pending_responses.items()
            if future.done()
        ]
        for corr_id in expired_correlations:
            self._pending_responses.pop(corr_id, None)

        logger.info(f"Cleaned up messages older than {max_age_hours} hours")