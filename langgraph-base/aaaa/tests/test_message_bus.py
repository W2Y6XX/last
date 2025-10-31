"""
消息总线单元测试
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from src.communication.message_bus import MessageBus, QueuedMessage
from src.core.types import MessageType, Priority, AgentId
from src.communication.messaging import MessageFactory


class TestMessageBus:
    """测试消息总线"""

    @pytest.fixture
    async def message_bus(self):
        """创建消息总线实例"""
        bus = MessageBus(max_queue_size=100)
        await bus.start()
        yield bus
        await bus.stop()

    @pytest.mark.asyncio
    async def test_start_stop(self, message_bus):
        """测试启动和停止"""
        assert message_bus._is_running

        await message_bus.stop()
        assert not message_bus._is_running

        await message_bus.start()
        assert message_bus._is_running

    @pytest.mark.asyncio
    async def test_register_agent(self, message_bus):
        """测试注册智能体"""
        agent_id = "test-agent"
        handler = Mock()

        await message_bus.register_agent(agent_id, handler)

        assert agent_id in message_bus._active_agents
        assert agent_id in message_bus._agent_handlers
        assert handler in message_bus._agent_handlers[agent_id]

    @pytest.mark.asyncio
    async def test_unregister_agent(self, message_bus):
        """测试注销智能体"""
        agent_id = "test-agent"
        handler = Mock()

        await message_bus.register_agent(agent_id, handler)
        await message_bus.unregister_agent(agent_id)

        assert agent_id not in message_bus._active_agents
        assert agent_id not in message_bus._agent_handlers

    @pytest.mark.asyncio
    async def test_send_point_to_point_message(self, message_bus):
        """测试发送点对点消息"""
        # 注册发送者和接收者
        sender_handler = Mock()
        receiver_handler = AsyncMock()

        await message_bus.register_agent("sender", sender_handler)
        await message_bus.register_agent("receiver", receiver_handler)

        # 发送消息
        message = MessageFactory.create_task_request(
            sender_id="sender",
            receiver_id="receiver",
            task_id="task-1",
            title="Test Task",
            description="Test description"
        )

        await message_bus.send_message(message)

        # 等待消息处理
        await asyncio.sleep(0.1)

        # 验证接收者收到了消息
        receiver_handler.assert_called_once()
        call_args = receiver_handler.call_args[0][0]
        assert call_args.content == message.content
        assert call_args.sender_id == "sender"

    @pytest.mark.asyncio
    async def test_broadcast_message(self, message_bus):
        """测试广播消息"""
        # 注册多个智能体
        handlers = []
        for i in range(3):
            handler = AsyncMock()
            await message_bus.register_agent(f"agent-{i}", handler)
            handlers.append(handler)

        # 发送广播消息
        message = MessageFactory.create_broadcast(
            sender_id="sender",
            content="Broadcast message"
        )

        await message_bus.send_message(message)

        # 等待消息处理
        await asyncio.sleep(0.1)

        # 验证所有智能体都收到了消息
        for handler in handlers:
            handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_priority(self, message_bus):
        """测试消息优先级"""
        processed_messages = []

        # 创建消息处理器
        async def message_handler(message):
            processed_messages.append(message.content)

        # 注册智能体
        await message_bus.register_agent("receiver", message_handler)

        # 发送不同优先级的消息
        messages = [
            MessageFactory.create_task_request(
                sender_id="sender",
                receiver_id="receiver",
                task_id="task-low",
                title="Low Priority",
                description="Low",
                priority=Priority.LOW
            ),
            MessageFactory.create_task_request(
                sender_id="sender",
                receiver_id="receiver",
                task_id="task-critical",
                title="Critical Priority",
                description="Critical",
                priority=Priority.CRITICAL
            ),
            MessageFactory.create_task_request(
                sender_id="sender",
                receiver_id="receiver",
                task_id="task-medium",
                title="Medium Priority",
                description="Medium",
                priority=Priority.MEDIUM
            )
        ]

        # 逆序发送（低优先级先发送）
        for message in reversed(messages):
            await message_bus.send_message(message)

        # 等待消息处理
        await asyncio.sleep(0.1)

        # 验证高优先级消息先处理
        assert len(processed_messages) == 3
        assert "Critical" in processed_messages[0]  # 关键优先级最先

    @pytest.mark.asyncio
    async def test_message_statistics(self, message_bus):
        """测试消息统计"""
        # 注册智能体
        handler = AsyncMock()
        await message_bus.register_agent("agent", handler)

        initial_stats = message_bus.get_statistics()
        assert initial_stats["messages_sent"] == 0

        # 发送消息
        message = MessageFactory.create_task_request(
            sender_id="sender",
            receiver_id="agent",
            task_id="task-1",
            title="Test",
            description="Test"
        )

        await message_bus.send_message(message)

        # 等待消息处理
        await asyncio.sleep(0.1)

        updated_stats = message_bus.get_statistics()
        assert updated_stats["messages_sent"] == 1
        assert updated_stats["messages_delivered"] >= 0

    @pytest.mark.asyncio
    async def test_message_history(self, message_bus):
        """测试消息历史"""
        # 注册智能体
        handler = AsyncMock()
        await message_bus.register_agent("agent", handler)

        # 发送多条消息
        for i in range(3):
            message = MessageFactory.create_task_request(
                sender_id="sender",
                receiver_id="agent",
                task_id=f"task-{i}",
                title=f"Task {i}",
                description=f"Description {i}"
            )
            await message_bus.send_message(message)

        # 等待消息处理
        await asyncio.sleep(0.1)

        # 获取消息历史
        history = message_bus.get_message_history(limit=10)
        assert len(history) >= 3

        # 获取特定智能体的消息历史
        agent_history = message_bus.get_message_history(agent_id="agent")
        assert len(agent_history) >= 3

        # 获取特定类型的消息历史
        task_history = message_bus.get_message_history(message_type=MessageType.TASK_REQUEST)
        assert len(task_history) >= 3

    @pytest.mark.asyncio
    async def test_unregistered_agent_message(self, message_bus):
        """测试向未注册智能体发送消息"""
        message = MessageFactory.create_task_request(
            sender_id="sender",
            receiver_id="unregistered",
            task_id="task-1",
            title="Test",
            description="Test"
        )

        # 消息应该被发送但不应该有接收者
        await message_bus.send_message(message)
        await asyncio.sleep(0.1)

        # 消息应该在历史中但可能不会被处理
        history = message_bus.get_message_history()
        assert len(history) >= 1

    @pytest.mark.asyncio
    async def test_cleanup_expired_messages(self, message_bus):
        """测试清理过期消息"""
        # 发送一些消息
        handler = AsyncMock()
        await message_bus.register_agent("agent", handler)

        message = MessageFactory.create_task_request(
            sender_id="sender",
            receiver_id="agent",
            task_id="task-1",
            title="Test",
            description="Test"
        )

        await message_bus.send_message(message)
        await asyncio.sleep(0.1)

        # 验证消息历史不为空
        history_before = message_bus.get_message_history()
        assert len(history_before) > 0

        # 清理过期消息（使用很短的时间窗口）
        cleaned_count = await message_bus.cleanup_expired_messages(max_age_hours=0)

        # 清理应该移除一些消息
        assert cleaned_count >= 0

    @pytest.mark.asyncio
    async def test_send_message_with_response(self, message_bus):
        """测试发送并等待响应的消息"""
        # 注册智能体
        response_received = asyncio.Event()

        async def handler(message):
            # 发送响应
            response = MessageFactory.create_task_response(
                sender_id="receiver",
                receiver_id="sender",
                task_id="task-1",
                status="completed"
            )
            response.correlation_id = message.message_id
            await message_bus.send_message(response)
            response_received.set()

        await message_bus.register_agent("sender", Mock())
        await message_bus.register_agent("receiver", handler)

        # 发送消息并等待响应
        original_message = MessageFactory.create_task_request(
            sender_id="sender",
            receiver_id="receiver",
            task_id="task-1",
            title="Test",
            description="Test"
        )

        response = await message_bus.send_message(original_message, expect_response=True, timeout=1.0)

        # 等待响应处理
        await asyncio.wait_for(response_received.wait(), timeout=1.0)

        # 验证响应
        assert response is not None