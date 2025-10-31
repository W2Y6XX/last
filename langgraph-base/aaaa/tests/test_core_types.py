"""
核心类型单元测试
"""

import pytest
from datetime import datetime
from src.core.types import (
    AgentType, TaskStatus, MessageType, Priority,
    AgentInfo, TaskInfo, MessageContent
)


class TestAgentType:
    """测试 AgentType 枚举"""

    def test_agent_type_values(self):
        """测试智能体类型枚举值"""
        assert AgentType.META.value == "meta"
        assert AgentType.COORDINATOR.value == "coordinator"
        assert AgentType.TASK_DECOMPOSER.value == "task_decomposer"
        assert AgentType.HUMAN.value == "human"
        assert AgentType.CUSTOM.value == "custom"

    def test_agent_type_comparison(self):
        """测试智能体类型比较"""
        assert AgentType.META == AgentType.META
        assert AgentType.META != AgentType.COORDINATOR


class TestTaskStatus:
    """测试 TaskStatus 枚举"""

    def test_task_status_values(self):
        """测试任务状态枚举值"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_comparison(self):
        """测试任务状态比较"""
        assert TaskStatus.PENDING == TaskStatus.PENDING
        assert TaskStatus.PENDING != TaskStatus.COMPLETED


class TestMessageType:
    """测试 MessageType 枚举"""

    def test_message_type_values(self):
        """测试消息类型枚举值"""
        assert MessageType.TASK_REQUEST.value == "task_request"
        assert MessageType.TASK_RESPONSE.value == "task_response"
        assert MessageType.STATUS_UPDATE.value == "status_update"
        assert MessageType.ERROR.value == "error"
        assert MessageType.HEARTBEAT.value == "heartbeat"
        assert MessageType.BROADCAST.value == "broadcast"


class TestPriority:
    """测试 Priority 枚举"""

    def test_priority_values(self):
        """测试优先级枚举值"""
        assert Priority.LOW.value == "low"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.HIGH.value == "high"
        assert Priority.CRITICAL.value == "critical"

    def test_priority_ordering(self):
        """测试优先级排序"""
        priorities = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]
        assert priorities == sorted(priorities)


class TestAgentInfo:
    """测试 AgentInfo 数据类"""

    def test_agent_info_creation(self):
        """测试智能体信息创建"""
        agent_info = AgentInfo(
            agent_id="test-agent",
            agent_type=AgentType.META,
            name="Test Agent",
            description="A test agent",
            capabilities=[]
        )

        assert agent_info.agent_id == "test-agent"
        assert agent_info.agent_type == AgentType.META
        assert agent_info.name == "Test Agent"
        assert agent_info.description == "A test agent"
        assert agent_info.capabilities == []
        assert agent_info.status == "active"

    def test_agent_info_with_capabilities(self):
        """测试带能力的智能体信息"""
        from src.core.types import AgentCapability

        capabilities = [
            AgentCapability(
                name="task_analysis",
                description="Analyze tasks",
                parameters={}
            )
        ]

        agent_info = AgentInfo(
            agent_id="test-agent",
            agent_type=AgentType.META,
            name="Test Agent",
            description="A test agent",
            capabilities=capabilities
        )

        assert len(agent_info.capabilities) == 1
        assert agent_info.capabilities[0].name == "task_analysis"

    def test_agent_info_serialization(self):
        """测试智能体信息序列化"""
        agent_info = AgentInfo(
            agent_id="test-agent",
            agent_type=AgentType.META,
            name="Test Agent",
            description="A test agent",
            capabilities=[]
        )

        # 测试字典转换
        agent_dict = agent_info.dict()
        assert agent_dict["agent_id"] == "test-agent"
        assert agent_dict["agent_type"] == "meta"


class TestTaskInfo:
    """测试 TaskInfo 数据类"""

    def test_task_info_creation(self):
        """测试任务信息创建"""
        task_info = TaskInfo(
            task_id="test-task",
            title="Test Task",
            description="A test task"
        )

        assert task_info.task_id == "test-task"
        assert task_info.title == "Test Task"
        assert task_info.description == "A test task"
        assert task_info.status == TaskStatus.PENDING
        assert task_info.priority == Priority.MEDIUM

    def test_task_info_with_dependencies(self):
        """测试带依赖的任务信息"""
        task_info = TaskInfo(
            task_id="test-task",
            title="Test Task",
            description="A test task",
            dependencies=["dep-1", "dep-2"]
        )

        assert len(task_info.dependencies) == 2
        assert "dep-1" in task_info.dependencies
        assert "dep-2" in task_info.dependencies

    def test_task_info_timestamps(self):
        """测试任务信息时间戳"""
        before_creation = datetime.now()

        task_info = TaskInfo(
            task_id="test-task",
            title="Test Task",
            description="A test task"
        )

        after_creation = datetime.now()

        assert before_creation <= task_info.created_at <= after_creation
        assert before_creation <= task_info.updated_at <= after_creation

    def test_task_info_status_update(self):
        """测试任务信息状态更新"""
        task_info = TaskInfo(
            task_id="test-task",
            title="Test Task",
            description="A test task"
        )

        original_updated_at = task_info.updated_at

        # 模拟状态更新
        task_info.status = TaskStatus.IN_PROGRESS
        task_info.updated_at = datetime.now()

        assert task_info.status == TaskStatus.IN_PROGRESS
        assert task_info.updated_at > original_updated_at


class TestMessageContent:
    """测试 MessageContent 数据类"""

    def test_message_content_creation(self):
        """测试消息内容创建"""
        message = MessageContent(
            message_type=MessageType.TASK_REQUEST,
            sender_id="agent-1",
            receiver_id="agent-2",
            content="Test message"
        )

        assert message.message_type == MessageType.TASK_REQUEST
        assert message.sender_id == "agent-1"
        assert message.receiver_id == "agent-2"
        assert message.content == "Test message"
        assert message.priority == Priority.MEDIUM

    def test_message_content_broadcast(self):
        """测试广播消息"""
        message = MessageContent(
            message_type=MessageType.BROADCAST,
            sender_id="agent-1",
            receiver_id=None,  # 广播消息没有特定接收者
            content="Broadcast message"
        )

        assert message.message_type == MessageType.BROADCAST
        assert message.sender_id == "agent-1"
        assert message.receiver_id is None

    def test_message_content_with_correlation(self):
        """测试带关联ID的消息"""
        message = MessageContent(
            message_type=MessageType.TASK_RESPONSE,
            sender_id="agent-2",
            receiver_id="agent-1",
            content="Response",
            correlation_id="req-123"
        )

        assert message.correlation_id == "req-123"

    def test_message_content_priority(self):
        """测试消息优先级"""
        message = MessageContent(
            message_type=MessageType.ERROR,
            sender_id="system",
            receiver_id="agent-1",
            content="Error message",
            priority=Priority.CRITICAL
        )

        assert message.priority == Priority.CRITICAL