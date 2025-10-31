"""
高级消息传递功能 - 点对点、广播、确认和重试
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass
from enum import Enum

from .message_bus import MessageBus, QueuedMessage
from .protocol import (
    MessageProtocol, MessageFactory, MessageSerializer,
    TaskRequestMessage, TaskResponseMessage, ErrorMessage
)
from ..core.types import MessageType, Priority, AgentId
from ..core.exceptions import CommunicationError, MessageDeliveryError
from ..utils.logging import get_logger

logger = get_logger(__name__)


class DeliveryStatus(Enum):
    """消息传递状态"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


@dataclass
class MessageTracker:
    """消息跟踪器"""
    message_id: str
    status: DeliveryStatus
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = None
    last_attempt: datetime = None
    delivered_at: Optional[datetime] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class MessagingService:
    """高级消息传递服务"""

    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self._message_trackers: Dict[str, MessageTracker] = {}
        self._awaiting_responses: Dict[str, asyncio.Future] = {}
        self._retry_intervals = [1, 2, 5, 10, 30]  # 秒
        self._default_timeout = 30.0  # 秒

    async def send_point_to_point(
        self,
        sender_id: AgentId,
        receiver_id: AgentId,
        content: Any,
        message_type: MessageType = MessageType.TASK_REQUEST,
        priority: Priority = Priority.MEDIUM,
        require_acknowledgment: bool = True,
        timeout: float = None
    ) -> bool:
        """发送点对点消息"""
        try:
            # 创建消息
            message = MessageFactory.create_task_request(
                sender_id=sender_id,
                receiver_id=receiver_id,
                task_id=str(uuid.uuid4()),
                title="Point-to-Point Message",
                description=str(content),
                priority=priority
            )

            # 创建跟踪器
            tracker = MessageTracker(
                message_id=message.message_id,
                status=DeliveryStatus.PENDING,
                max_attempts=3 if require_acknowledgment else 1
            )
            self._message_trackers[message.message_id] = tracker

            # 发送消息
            if require_acknowledgment:
                future = asyncio.Future()
                self._awaiting_responses[message.message_id] = future

                success = await self._send_with_retry(message, timeout or self._default_timeout)
                return success
            else:
                await self.message_bus.send_message(message)
                tracker.status = DeliveryStatus.SENT
                return True

        except Exception as e:
            logger.error(f"Failed to send point-to-point message: {e}")
            return False

    async def broadcast_to_all(
        self,
        sender_id: AgentId,
        content: Any,
        message_type: MessageType = MessageType.BROADCAST,
        priority: Priority = Priority.MEDIUM,
        exclude_agents: List[AgentId] = None,
        require_acknowledgment: bool = False
    ) -> Dict[AgentId, bool]:
        """向所有智能体广播消息"""
        results = {}

        # 创建广播消息
        broadcast_msg = MessageFactory.create_broadcast(
            sender_id=sender_id,
            content=str(content),
            priority=priority
        )

        # 发送广播
        await self.message_bus.send_message(broadcast_msg)

        # 获取所有活跃智能体
        active_agents = self.message_bus._active_agents
        exclude_agents = exclude_agents or []
        exclude_agents.append(sender_id)  # 排除发送者

        target_agents = active_agents - set(exclude_agents)

        if require_acknowledgment:
            # 等待确认
            ack_futures = {}
            for agent_id in target_agents:
                future = asyncio.Future()
                ack_futures[agent_id] = future
                self._awaiting_responses[f"ack_{agent_id}_{broadcast_msg.message_id}"] = future

            # 设置超时
            try:
                await asyncio.wait_for(
                    asyncio.gather(*ack_futures.values(), return_exceptions=True),
                    timeout=self._default_timeout
                )
            except asyncio.TimeoutError:
                pass

            # 收集结果
            for agent_id in target_agents:
                future = ack_futures[agent_id]
                results[agent_id] = not future.done() or future.exception() is None
        else:
            # 不需要确认，假设都成功
            for agent_id in target_agents:
                results[agent_id] = True

        logger.info(f"Broadcast completed, reached {len(results)} agents")
        return results

    async def send_with_acknowledgment(
        self,
        message: MessageProtocol,
        timeout: float = None
    ) -> bool:
        """发送消息并等待确认"""
        timeout = timeout or self._default_timeout

        # 创建跟踪器
        tracker = MessageTracker(
            message_id=message.message_id,
            status=DeliveryStatus.PENDING,
            max_attempts=3
        )
        self._message_trackers[message.message_id] = tracker

        return await self._send_with_retry(message, timeout)

    async def _send_with_retry(self, message: MessageProtocol, timeout: float) -> bool:
        """带重试的消息发送"""
        tracker = self._message_trackers[message.message_id]

        for attempt in range(tracker.max_attempts):
            try:
                tracker.attempts = attempt + 1
                tracker.last_attempt = datetime.now()

                if attempt > 0:
                    tracker.status = DeliveryStatus.RETRYING
                    retry_interval = self._retry_intervals[min(attempt - 1, len(self._retry_intervals) - 1)]
                    await asyncio.sleep(retry_interval)

                # 发送消息
                await self.message_bus.send_message(message)

                # 等待确认
                if message.message_id in self._awaiting_responses:
                    try:
                        await asyncio.wait_for(
                            self._awaiting_responses[message.message_id],
                            timeout=timeout
                        )
                        tracker.status = DeliveryStatus.DELIVERED
                        tracker.delivered_at = datetime.now()
                        logger.debug(f"Message delivered: {message.message_id}")
                        return True

                    except asyncio.TimeoutError:
                        tracker.status = DeliveryStatus.TIMEOUT
                        logger.warning(f"Message timeout: {message.message_id}")
                        continue

                else:
                    tracker.status = DeliveryStatus.SENT
                    return True

            except Exception as e:
                tracker.error = str(e)
                logger.error(f"Message send failed (attempt {attempt + 1}): {e}")

        # 所有尝试都失败
        tracker.status = DeliveryStatus.FAILED
        logger.error(f"Message failed after {tracker.max_attempts} attempts: {message.message_id}")
        return False

    async def handle_message_acknowledgment(self, message_id: str, success: bool = True) -> None:
        """处理消息确认"""
        if message_id in self._awaiting_responses:
            future = self._awaiting_responses.pop(message_id)
            if not future.done():
                future.set_result(success)

        # 更新跟踪器
        if message_id in self._message_trackers:
            tracker = self._message_trackers[message_id]
            if success:
                tracker.status = DeliveryStatus.DELIVERED
                tracker.delivered_at = datetime.now()
            else:
                tracker.status = DeliveryStatus.FAILED

    def get_message_status(self, message_id: str) -> Optional[MessageTracker]:
        """获取消息状态"""
        return self._message_trackers.get(message_id)

    def get_all_message_statuses(self) -> Dict[str, MessageTracker]:
        """获取所有消息状态"""
        return self._message_trackers.copy()

    async def cleanup_old_messages(self, max_age_hours: int = 24) -> int:
        """清理旧消息跟踪器"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0

        messages_to_remove = []
        for message_id, tracker in self._message_trackers.items():
            if tracker.created_at < cutoff_time:
                messages_to_remove.append(message_id)

        for message_id in messages_to_remove:
            self._message_trackers.pop(message_id, None)
            self._awaiting_responses.pop(message_id, None)
            cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old message trackers")

        return cleaned_count

    async def send_group_message(
        self,
        sender_id: AgentId,
        receiver_ids: List[AgentId],
        content: Any,
        message_type: MessageType = MessageType.TASK_REQUEST,
        priority: Priority = Priority.MEDIUM
    ) -> Dict[AgentId, bool]:
        """发送组消息"""
        results = {}

        # 并发发送
        tasks = []
        for receiver_id in receiver_ids:
            task = self.send_point_to_point(
                sender_id=sender_id,
                receiver_id=receiver_id,
                content=content,
                message_type=message_type,
                priority=priority,
                require_acknowledgment=False
            )
            tasks.append((receiver_id, task))

        # 等待所有发送完成
        for receiver_id, task in tasks:
            try:
                success = await task
                results[receiver_id] = success
            except Exception as e:
                logger.error(f"Failed to send to {receiver_id}: {e}")
                results[receiver_id] = False

        successful_count = sum(1 for success in results.values() if success)
        logger.info(f"Group message sent: {successful_count}/{len(receiver_ids)} successful")

        return results

    def get_messaging_stats(self) -> Dict[str, Any]:
        """获取消息传递统计"""
        total_messages = len(self._message_trackers)
        status_counts = {}
        for tracker in self._message_trackers.values():
            status = tracker.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_messages": total_messages,
            "status_distribution": status_counts,
            "awaiting_responses": len(self._awaiting_responses),
            "delivery_rate": (
                status_counts.get("delivered", 0) / total_messages * 100
                if total_messages > 0 else 0
            )
        }