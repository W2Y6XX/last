"""集成测试 - 测试与现有系统的集成功能"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from langgraph_multi_agent.integration.state_adapter import StateAdapter
from langgraph_multi_agent.integration.message_adapter import MessageBusAdapter
from langgraph_multi_agent.integration.legacy_bridge import LegacySystemBridge
from langgraph_multi_agent.core.state import (
    create_initial_state,
    WorkflowPhase,
    update_workflow_phase,
    add_agent_message
)
from langgraph_multi_agent.legacy.task_state import TaskStatus


class TestStateAdapter:
    """状态适配器测试类"""
    
    def test_langgraph_to_legacy_conversion(self):
        """测试LangGraph状态转换为现有系统状态"""
        adapter = StateAdapter()
        
        # 创建LangGraph状态
        langgraph_state = create_initial_state("测试任务", "测试描述")
        langgraph_state = update_workflow_phase(langgraph_state, WorkflowPhase.ANALYSIS)
        
        # 转换为现有系统状态
        legacy_state = adapter.langgraph_to_legacy(langgraph_state)
        
        assert legacy_state["title"] == "测试任务"
        assert legacy_state["description"] == "测试描述"
        assert legacy_state["status"] == TaskStatus.ANALYZING
        assert "langgraph_metadata" in legacy_state["metadata"]
        assert legacy_state["metadata"]["langgraph_metadata"]["workflow_phase"] == WorkflowPhase.ANALYSIS.value
    
    def test_legacy_to_langgraph_conversion(self):
        """测试现有系统状态转换为LangGraph状态"""
        adapter = StateAdapter()
        
        # 创建现有系统状态
        from langgraph_multi_agent.legacy.task_state import TaskState
        legacy_state = TaskState.create_new(
            title="测试任务",
            description="测试描述",
            task_type="test"
        )
        legacy_state["status"] = TaskStatus.IN_PROGRESS
        
        # 转换为LangGraph状态
        langgraph_state = adapter.legacy_to_langgraph(legacy_state)
        
        assert langgraph_state["task_state"]["title"] == "测试任务"
        assert langgraph_state["task_state"]["description"] == "测试描述"
        assert langgraph_state["workflow_context"]["current_phase"] == WorkflowPhase.EXECUTION
    
    @pytest.mark.asyncio
    async def test_state_synchronization(self):
        """测试状态同步"""
        adapter = StateAdapter()
        sync_called = False
        sync_data = None
        
        def sync_callback(task_id, legacy_state):
            nonlocal sync_called, sync_data
            sync_called = True
            sync_data = (task_id, legacy_state)
        
        adapter.register_sync_callback(sync_callback)
        
        # 创建并同步状态
        langgraph_state = create_initial_state("测试任务", "测试描述")
        success = await adapter.sync_to_legacy_system(langgraph_state)
        
        assert success is True
        assert sync_called is True
        assert sync_data[0] == langgraph_state["task_state"]["task_id"]
        assert sync_data[1]["title"] == "测试任务"
    
    def test_state_consistency_validation(self):
        """测试状态一致性验证"""
        adapter = StateAdapter()
        
        # 创建一致的状态
        langgraph_state = create_initial_state("测试任务", "测试描述")
        legacy_state = adapter.langgraph_to_legacy(langgraph_state)
        
        # 验证一致性
        result = adapter.validate_state_consistency(langgraph_state, legacy_state)
        
        assert result["consistent"] is True
        assert len(result["inconsistencies"]) == 0
        
        # 创建不一致的状态
        legacy_state["title"] = "不同的标题"
        result = adapter.validate_state_consistency(langgraph_state, legacy_state)
        
        assert result["consistent"] is False
        assert len(result["inconsistencies"]) > 0


class TestMessageAdapter:
    """消息适配器测试类"""
    
    def test_message_handler_registration(self):
        """测试消息处理器注册"""
        adapter = MessageBusAdapter()
        
        def test_handler(message):
            pass
        
        adapter.register_message_handler("test_message", test_handler)
        
        assert "test_message" in adapter.message_handlers
        assert len(adapter.message_handlers["test_message"]) == 1
    
    @pytest.mark.asyncio
    async def test_send_to_legacy_system(self):
        """测试发送消息到现有系统"""
        adapter = MessageBusAdapter()
        
        # 模拟现有消息总线
        mock_bus = Mock()
        mock_bus.send_message = AsyncMock()
        adapter.set_legacy_message_bus(mock_bus)
        
        # 发送消息
        success = await adapter.send_to_legacy_system(
            "test_message",
            {"data": "test"},
            "sender_001",
            "recipient_001"
        )
        
        assert success is True
        mock_bus.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_receive_from_legacy_system(self):
        """测试接收现有系统消息"""
        adapter = MessageBusAdapter()
        received_message = None
        
        def test_handler(message):
            nonlocal received_message
            received_message = message
        
        adapter.register_message_handler("test_message", test_handler)
        
        # 模拟接收消息
        legacy_message = {
            "message_id": "msg_001",
            "message_type": "test_message",
            "sender_id": "sender_001",
            "content": {"data": "test"},
            "timestamp": datetime.now().isoformat()
        }
        
        success = await adapter.receive_from_legacy_system(legacy_message)
        
        assert success is True
        assert received_message is not None
        assert received_message["sender_agent"] == "sender_001"
        assert received_message["content"]["data"] == "test"
    
    def test_message_conversion(self):
        """测试消息格式转换"""
        adapter = MessageBusAdapter()
        
        # 创建LangGraph消息
        from langgraph_multi_agent.core.state import AgentMessage
        agent_message = AgentMessage(
            message_id="msg_001",
            sender_agent="meta_agent",
            receiver_agent="coordinator",
            message_type="analysis_result",
            content={"complexity": 0.8},
            timestamp=datetime.now(),
            priority=1,
            requires_response=False
        )
        
        # 转换为现有系统格式
        legacy_message = adapter.convert_langgraph_message_to_legacy(agent_message)
        
        assert legacy_message["message_id"] == "msg_001"
        assert legacy_message["sender_id"] == "meta_agent"
        assert legacy_message["recipient_id"] == "coordinator"
        assert legacy_message["message_type"] == "analysis_result"
        assert legacy_message["content"]["complexity"] == 0.8
    
    def test_message_statistics(self):
        """测试消息统计"""
        adapter = MessageBusAdapter()
        
        # 添加一些消息历史
        adapter._record_message({
            "message_id": "msg_001",
            "message_type": "test",
            "sender_id": "sender_001"
        }, "outgoing")
        
        adapter._record_message({
            "message_id": "msg_002", 
            "message_type": "test",
            "sender_id": "sender_002"
        }, "incoming")
        
        stats = adapter.get_message_statistics()
        
        assert stats["total_messages"] == 2
        assert stats["outgoing_messages"] == 1
        assert stats["incoming_messages"] == 1
        assert "test" in stats["message_types"]
        assert stats["message_types"]["test"] == 2


class TestLegacySystemBridge:
    """现有系统桥接器测试类"""
    
    @pytest.mark.asyncio
    async def test_bridge_initialization(self):
        """测试桥接器初始化"""
        bridge = LegacySystemBridge()
        
        success = await bridge.initialize_bridge()
        assert success is True
        
        # 清理
        await bridge.shutdown_bridge()
    
    def test_legacy_agent_registration(self):
        """测试现有智能体注册"""
        bridge = LegacySystemBridge()
        
        # 模拟现有智能体
        mock_agent = Mock()
        mock_agent.process_task = Mock(return_value={"result": "success"})
        
        bridge.register_legacy_agent("test_agent", mock_agent)
        
        assert "test_agent" in bridge.legacy_agents
        assert bridge.legacy_agents["test_agent"] == mock_agent
    
    @pytest.mark.asyncio
    async def test_execute_legacy_agent(self):
        """测试执行现有智能体"""
        bridge = LegacySystemBridge()
        
        # 模拟现有智能体
        mock_agent = Mock()
        mock_agent.process_task = AsyncMock(return_value={"result": "success"})
        
        bridge.register_legacy_agent("test_agent", mock_agent)
        
        # 执行智能体
        result = await bridge.execute_legacy_agent("test_agent", {"task": "test"})
        
        assert result is not None
        assert result["result"] == "success"
        mock_agent.process_task.assert_called_once_with({"task": "test"})
    
    @pytest.mark.asyncio
    async def test_state_synchronization(self):
        """测试状态同步"""
        bridge = LegacySystemBridge()
        await bridge.initialize_bridge()
        
        # 创建测试状态
        langgraph_state = create_initial_state("测试任务", "测试描述")
        
        # 同步状态
        success = await bridge.sync_state_to_legacy(langgraph_state)
        assert success is True
        
        # 清理
        await bridge.shutdown_bridge()
    
    @pytest.mark.asyncio
    async def test_integration_consistency_validation(self):
        """测试集成一致性验证"""
        bridge = LegacySystemBridge()
        await bridge.initialize_bridge()
        
        # 创建测试状态
        langgraph_state = create_initial_state("测试任务", "测试描述")
        
        # 验证一致性
        result = await bridge.validate_integration_consistency(langgraph_state)
        
        assert "state_consistency" in result
        assert "message_statistics" in result
        assert "sync_statistics" in result
        assert "bridge_status" in result
        
        # 清理
        await bridge.shutdown_bridge()
    
    def test_integration_callback_registration(self):
        """测试集成回调注册"""
        bridge = LegacySystemBridge()
        callback_called = False
        
        def test_callback(event_type, data):
            nonlocal callback_called
            callback_called = True
        
        bridge.register_integration_callback("test_event", test_callback)
        
        assert "test_event" in bridge.integration_callbacks
        assert len(bridge.integration_callbacks["test_event"]) == 1
    
    def test_bridge_status(self):
        """测试桥接器状态"""
        bridge = LegacySystemBridge()
        
        # 注册一些组件
        mock_agent = Mock()
        bridge.register_legacy_agent("test_agent", mock_agent)
        
        def test_callback(event_type, data):
            pass
        
        bridge.register_integration_callback("test_event", test_callback)
        
        # 获取状态
        status = bridge.get_bridge_status()
        
        assert status["bridge_enabled"] is True
        assert "test_agent" in status["registered_agents"]
        assert status["integration_callbacks"]["test_event"] == 1


if __name__ == "__main__":
    pytest.main([__file__])