"""智能体包装器测试"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from langgraph_multi_agent.agents.wrappers import AgentNodeWrapper, AgentExecutionResult
from langgraph_multi_agent.agents.generic_wrapper import GenericAgentWrapper
from langgraph_multi_agent.core.state import (
    create_initial_state,
    WorkflowPhase,
    update_workflow_phase
)


class MockAgent:
    """模拟智能体"""
    
    def __init__(self, should_fail: bool = False, execution_time: float = 0.1):
        self.should_fail = should_fail
        self.execution_time = execution_time
        self.call_count = 0
        self.capabilities = ["test_capability"]
        self.specializations = ["test_specialization"]
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟任务处理"""
        self.call_count += 1
        
        if self.execution_time > 0:
            await asyncio.sleep(self.execution_time)
        
        if self.should_fail:
            raise ValueError("模拟智能体执行失败")
        
        return {
            "success": True,
            "result": f"处理了任务: {task_data.get('title', 'unknown')}",
            "call_count": self.call_count,
            "output_data": {
                "processed_at": datetime.now().isoformat(),
                "task_id": task_data.get("task_id")
            }
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "status": "active",
            "call_count": self.call_count,
            "last_call": datetime.now().isoformat()
        }


class TestAgentExecutionResult:
    """智能体执行结果测试类"""
    
    def test_successful_result(self):
        """测试成功结果"""
        result = AgentExecutionResult(
            success=True,
            result={"data": "test"},
            execution_time=1.5,
            retry_count=0
        )
        
        assert result.success is True
        assert result.result["data"] == "test"
        assert result.execution_time == 1.5
        assert result.retry_count == 0
        assert result.error is None
        assert isinstance(result.timestamp, datetime)
    
    def test_failed_result(self):
        """测试失败结果"""
        error = ValueError("测试错误")
        result = AgentExecutionResult(
            success=False,
            error=error,
            retry_count=2
        )
        
        assert result.success is False
        assert result.error == error
        assert result.retry_count == 2
        assert result.result == {}


class TestGenericAgentWrapper:
    """通用智能体包装器测试类"""
    
    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """测试成功执行"""
        mock_agent = MockAgent()
        wrapper = GenericAgentWrapper(mock_agent, "test_agent")
        
        # 创建测试状态
        state = create_initial_state("测试任务", "测试任务描述")
        
        # 执行智能体
        updated_state = await wrapper(state)
        
        # 验证结果
        assert len(updated_state["agent_messages"]) > 0
        assert updated_state["workflow_context"]["agent_results"]["test_agent"]["result"]["success"] is True
        assert "test_agent" in updated_state["task_state"]["output_data"]
        assert mock_agent.call_count == 1
    
    @pytest.mark.asyncio
    async def test_failed_execution(self):
        """测试执行失败"""
        mock_agent = MockAgent(should_fail=True)
        wrapper = GenericAgentWrapper(mock_agent, "test_agent", max_retries=2)
        
        # 创建测试状态
        state = create_initial_state("测试任务", "测试任务描述")
        
        # 执行智能体
        updated_state = await wrapper(state)
        
        # 验证错误处理
        assert updated_state["error_state"] is not None
        assert updated_state["error_state"]["error_type"] == "ValueError"
        assert updated_state["retry_count"] > 0
        assert updated_state["workflow_context"]["current_phase"] == WorkflowPhase.ERROR_HANDLING
        assert mock_agent.call_count == 3  # 1次初始执行 + 2次重试
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """测试超时处理"""
        mock_agent = MockAgent(execution_time=2.0)  # 2秒执行时间
        wrapper = GenericAgentWrapper(mock_agent, "test_agent", timeout_seconds=1)  # 1秒超时
        
        # 创建测试状态
        state = create_initial_state("测试任务", "测试任务描述")
        
        # 执行智能体
        updated_state = await wrapper(state)
        
        # 验证超时错误
        assert updated_state["error_state"] is not None
        assert "TimeoutError" in updated_state["error_state"]["error_type"]
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """测试重试机制"""
        # 创建一个前两次失败，第三次成功的智能体
        call_count = 0
        
        class RetryTestAgent:
            async def process_task(self, task_data):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise ValueError(f"失败尝试 {call_count}")
                return {"success": True, "attempt": call_count}
        
        retry_agent = RetryTestAgent()
        wrapper = GenericAgentWrapper(retry_agent, "retry_test_agent", max_retries=3)
        
        # 创建测试状态
        state = create_initial_state("测试任务", "测试任务描述")
        
        # 执行智能体
        updated_state = await wrapper(state)
        
        # 验证重试成功
        assert call_count == 3
        assert updated_state["workflow_context"]["agent_results"]["retry_test_agent"]["result"]["success"] is True
        assert updated_state["workflow_context"]["agent_results"]["retry_test_agent"]["result"]["attempt"] == 3
    
    def test_task_data_extraction(self):
        """测试任务数据提取"""
        mock_agent = MockAgent()
        wrapper = GenericAgentWrapper(mock_agent, "test_agent")
        
        # 创建复杂的测试状态
        state = create_initial_state(
            "复杂任务",
            "这是一个复杂的任务描述",
            task_type="complex",
            priority=3,
            input_data={"key1": "value1", "key2": "value2"}
        )
        state = update_workflow_phase(state, WorkflowPhase.ANALYSIS)
        state["workflow_context"]["agent_results"]["previous_agent"] = {
            "result": {"analysis": "completed"}
        }
        
        # 提取任务数据
        task_data = wrapper._extract_task_data(state)
        
        # 验证提取的数据
        assert task_data["title"] == "复杂任务"
        assert task_data["description"] == "这是一个复杂的任务描述"
        assert task_data["task_type"] == "complex"
        assert task_data["priority"] == 3
        assert task_data["input_data"]["key1"] == "value1"
        assert task_data["workflow_context"]["current_phase"] == WorkflowPhase.ANALYSIS.value
        assert "previous_agent" in task_data["workflow_context"]["agent_results"]
    
    def test_execution_statistics(self):
        """测试执行统计"""
        mock_agent = MockAgent()
        wrapper = GenericAgentWrapper(mock_agent, "test_agent")
        
        # 初始统计
        stats = wrapper.get_execution_statistics()
        assert stats["execution_count"] == 0
        assert stats["success_count"] == 0
        assert stats["error_count"] == 0
        assert stats["success_rate"] == 0
        
        # 模拟一些执行
        wrapper.execution_count = 10
        wrapper.success_count = 8
        wrapper.error_count = 2
        wrapper.total_execution_time = 50.0
        
        stats = wrapper.get_execution_statistics()
        assert stats["execution_count"] == 10
        assert stats["success_count"] == 8
        assert stats["error_count"] == 2
        assert stats["success_rate"] == 0.8
        assert stats["average_execution_time"] == 5.0
    
    def test_callback_registration(self):
        """测试回调注册"""
        mock_agent = MockAgent()
        wrapper = GenericAgentWrapper(mock_agent, "test_agent")
        
        def pre_callback(agent_type, state):
            pass
        
        def post_callback(agent_type, state):
            pass
        
        def error_callback(agent_type, state, error=None):
            pass
        
        # 注册回调
        wrapper.register_pre_execution_callback(pre_callback)
        wrapper.register_post_execution_callback(post_callback)
        wrapper.register_error_callback(error_callback)
        
        assert len(wrapper.pre_execution_callbacks) == 1
        assert len(wrapper.post_execution_callbacks) == 1
        assert len(wrapper.error_callbacks) == 1
    
    @pytest.mark.asyncio
    async def test_callback_execution(self):
        """测试回调执行"""
        mock_agent = MockAgent()
        wrapper = GenericAgentWrapper(mock_agent, "test_agent")
        
        callback_calls = []
        
        def pre_callback(agent_type, state):
            callback_calls.append(("pre", agent_type))
        
        def post_callback(agent_type, state):
            callback_calls.append(("post", agent_type))
        
        # 注册回调
        wrapper.register_pre_execution_callback(pre_callback)
        wrapper.register_post_execution_callback(post_callback)
        
        # 创建测试状态并执行
        state = create_initial_state("测试任务", "测试任务描述")
        await wrapper(state)
        
        # 验证回调被调用
        assert len(callback_calls) == 2
        assert ("pre", "test_agent") in callback_calls
        assert ("post", "test_agent") in callback_calls
    
    def test_agent_interface_validation(self):
        """测试智能体接口验证"""
        # 有效的智能体
        valid_agent = MockAgent()
        wrapper = GenericAgentWrapper(valid_agent, "valid_agent")
        assert wrapper.validate_agent_interface() is True
        
        # 无效的智能体（缺少process_task方法）
        invalid_agent = Mock()
        del invalid_agent.process_task  # 删除process_task方法
        wrapper = GenericAgentWrapper(invalid_agent, "invalid_agent")
        assert wrapper.validate_agent_interface() is False
    
    def test_agent_info(self):
        """测试智能体信息获取"""
        mock_agent = MockAgent()
        wrapper = GenericAgentWrapper(mock_agent, "test_agent")
        
        info = wrapper.get_agent_info()
        
        assert info["agent_type"] == "test_agent"
        assert info["agent_class"] == "MockAgent"
        assert info["has_process_task"] is True
        assert info["capabilities"] == ["test_capability"]
        assert info["specializations"] == ["test_specialization"]
        assert info["agent_status"]["status"] == "active"


if __name__ == "__main__":
    pytest.main([__file__])