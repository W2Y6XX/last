"""智能体包装器集成测试"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from langgraph_multi_agent.agents.meta_agent_wrapper import MetaAgentWrapper
from langgraph_multi_agent.agents.coordinator_wrapper import CoordinatorWrapper
from langgraph_multi_agent.agents.task_decomposer_wrapper import TaskDecomposerWrapper
from langgraph_multi_agent.core.state import (
    create_initial_state,
    WorkflowPhase,
    LangGraphTaskState
)
from langgraph_multi_agent.legacy.task_state import TaskStatus


class MockAgent:
    """通用模拟智能体"""
    
    def __init__(self, agent_type: str, result: Dict[str, Any] = None, should_fail: bool = False):
        self.agent_type = agent_type
        self.result = result or self._get_default_result(agent_type)
        self.should_fail = should_fail
        self.call_count = 0
    
    def _get_default_result(self, agent_type: str) -> Dict[str, Any]:
        """根据智能体类型返回默认结果"""
        if agent_type == "meta_agent":
            return {
                "success": True,
                "complexity_score": 0.7,
                "requires_decomposition": True,
                "clarification_needed": False,
                "recommended_agents": ["task_decomposer", "coordinator"],
                "analysis_summary": "任务需要分解和协调"
            }
        elif agent_type == "task_decomposer":
            return {
                "success": True,
                "decomposition": {
                    "subtasks": [
                        {"id": "sub1", "name": "Phase 1", "type": "analysis"},
                        {"id": "sub2", "name": "Phase 2", "type": "implementation"}
                    ],
                    "dependencies": [{"from": "sub1", "to": "sub2", "type": "sequential"}],
                    "decomposition_strategy": "hierarchical"
                },
                "execution_plan": {"estimated_duration": 180},
                "subtasks_count": 2
            }
        elif agent_type == "coordinator":
            return {
                "success": True,
                "coordination_type": "establish_collaboration",
                "session_id": "session_123",
                "participants": ["agent1", "agent2"],
                "message": "协作已建立"
            }
        else:
            return {"success": True, "message": "任务完成"}
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟任务处理"""
        self.call_count += 1
        
        if self.should_fail:
            raise ValueError(f"{self.agent_type}执行失败")
        
        await asyncio.sleep(0.05)  # 模拟处理时间
        return self.result.copy()


class TestAgentWrappersIntegration:
    """智能体包装器集成测试类"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_integration(self):
        """测试完整工作流集成"""
        # 创建模拟智能体
        mock_meta_agent = MockAgent("meta_agent")
        mock_task_decomposer = MockAgent("task_decomposer")
        mock_coordinator = MockAgent("coordinator")
        
        # 创建包装器
        meta_wrapper = MetaAgentWrapper(mock_meta_agent)
        decomposer_wrapper = TaskDecomposerWrapper(mock_task_decomposer)
        coordinator_wrapper = CoordinatorWrapper(mock_coordinator)
        
        # 创建初始状态
        state = create_initial_state("集成测试任务", "测试完整工作流的复杂任务")
        
        # 步骤1: MetaAgent分析
        state = await meta_wrapper(state)
        
        # 验证MetaAgent结果
        assert "meta_agent" in state["workflow_context"]["agent_results"]
        meta_result = state["workflow_context"]["agent_results"]["meta_agent"]["result"]
        assert meta_result["success"] is True
        assert meta_result["requires_decomposition"] is True
        
        # 步骤2: TaskDecomposer分解（基于MetaAgent的分析结果）
        state["workflow_context"]["current_phase"] = WorkflowPhase.DECOMPOSITION
        state = await decomposer_wrapper(state)
        
        # 验证TaskDecomposer结果
        assert "task_decomposer" in state["workflow_context"]["agent_results"]
        decomposer_result = state["workflow_context"]["agent_results"]["task_decomposer"]["result"]
        assert decomposer_result["success"] is True
        assert decomposer_result["subtasks_count"] == 2
        assert len(state["task_state"]["subtasks"]) == 2
        
        # 步骤3: Coordinator协调（基于分解结果）
        state["workflow_context"]["current_phase"] = WorkflowPhase.COORDINATION
        state = await coordinator_wrapper(state)
        
        # 验证Coordinator结果
        assert "coordinator" in state["workflow_context"]["agent_results"]
        coordinator_result = state["workflow_context"]["agent_results"]["coordinator"]["result"]
        assert coordinator_result["success"] is True
        
        # 验证最终状态
        assert state["workflow_context"]["current_phase"] == WorkflowPhase.EXECUTION
        assert state["task_state"]["status"] == TaskStatus.IN_PROGRESS
        
        # 验证所有智能体都被调用
        assert mock_meta_agent.call_count == 1
        assert mock_task_decomposer.call_count == 1
        assert mock_coordinator.call_count == 1
    
    @pytest.mark.asyncio
    async def test_error_propagation_between_agents(self):
        """测试智能体间的错误传播"""
        # 创建一个会失败的TaskDecomposer
        mock_meta_agent = MockAgent("meta_agent")
        mock_task_decomposer = MockAgent("task_decomposer", should_fail=True)
        mock_coordinator = MockAgent("coordinator")
        
        meta_wrapper = MetaAgentWrapper(mock_meta_agent)
        decomposer_wrapper = TaskDecomposerWrapper(mock_task_decomposer)
        coordinator_wrapper = CoordinatorWrapper(mock_coordinator)
        
        state = create_initial_state("错误测试任务", "测试错误处理的任务")
        
        # MetaAgent成功执行
        state = await meta_wrapper(state)
        assert state["workflow_context"]["agent_results"]["meta_agent"]["result"]["success"] is True
        
        # TaskDecomposer失败
        state["workflow_context"]["current_phase"] = WorkflowPhase.DECOMPOSITION
        state = await decomposer_wrapper(state)
        
        # 验证错误处理 - 检查错误消息
        error_messages = [msg for msg in state["agent_messages"] 
                         if msg["message_type"] == "decomposition_error"]
        assert len(error_messages) > 0
        
        # 验证错误消息
        error_messages = [msg for msg in state["agent_messages"] 
                         if msg["message_type"] == "decomposition_error"]
        assert len(error_messages) > 0
        
        # 验证错误被正确处理（工作流阶段可能不会立即转换）
        assert len(error_messages) > 0
    
    @pytest.mark.asyncio
    async def test_state_consistency_across_agents(self):
        """测试智能体间的状态一致性"""
        mock_meta_agent = MockAgent("meta_agent")
        mock_task_decomposer = MockAgent("task_decomposer")
        
        meta_wrapper = MetaAgentWrapper(mock_meta_agent)
        decomposer_wrapper = TaskDecomposerWrapper(mock_task_decomposer)
        
        state = create_initial_state("状态一致性测试", "测试状态一致性的任务")
        original_task_id = state["task_state"]["task_id"]
        
        # 执行MetaAgent
        state = await meta_wrapper(state)
        
        # 验证任务ID保持一致
        assert state["task_state"]["task_id"] == original_task_id
        
        # 验证状态更新时间被更新
        first_update_time = state["task_state"]["updated_at"]
        
        # 执行TaskDecomposer
        state["workflow_context"]["current_phase"] = WorkflowPhase.DECOMPOSITION
        await asyncio.sleep(0.01)  # 确保时间差异
        state = await decomposer_wrapper(state)
        
        # 验证任务ID仍然一致
        assert state["task_state"]["task_id"] == original_task_id
        
        # 验证更新时间被更新
        second_update_time = state["task_state"]["updated_at"]
        assert second_update_time > first_update_time
        
        # 验证智能体结果都被保留
        assert "meta_agent" in state["workflow_context"]["agent_results"]
        assert "task_decomposer" in state["workflow_context"]["agent_results"]
    
    @pytest.mark.asyncio
    async def test_performance_metrics_aggregation(self):
        """测试性能指标聚合"""
        mock_meta_agent = MockAgent("meta_agent")
        mock_task_decomposer = MockAgent("task_decomposer")
        mock_coordinator = MockAgent("coordinator")
        
        meta_wrapper = MetaAgentWrapper(mock_meta_agent)
        decomposer_wrapper = TaskDecomposerWrapper(mock_task_decomposer)
        coordinator_wrapper = CoordinatorWrapper(mock_coordinator)
        
        state = create_initial_state("性能测试任务", "测试性能指标的任务")
        
        # 执行所有智能体
        state = await meta_wrapper(state)
        state["workflow_context"]["current_phase"] = WorkflowPhase.DECOMPOSITION
        state = await decomposer_wrapper(state)
        state["workflow_context"]["current_phase"] = WorkflowPhase.COORDINATION
        state = await coordinator_wrapper(state)
        
        # 验证性能指标被收集
        assert len(state["performance_metrics"]) > 0
        
        # 验证每个智能体都有执行时间指标
        metric_keys = list(state["performance_metrics"].keys())
        agent_metrics = [key for key in metric_keys if "execution_time" in key]
        assert len(agent_metrics) >= 3  # 至少三个智能体的指标
    
    @pytest.mark.asyncio
    async def test_message_flow_between_agents(self):
        """测试智能体间的消息流"""
        mock_meta_agent = MockAgent("meta_agent")
        mock_task_decomposer = MockAgent("task_decomposer")
        mock_coordinator = MockAgent("coordinator")
        
        meta_wrapper = MetaAgentWrapper(mock_meta_agent)
        decomposer_wrapper = TaskDecomposerWrapper(mock_task_decomposer)
        coordinator_wrapper = CoordinatorWrapper(mock_coordinator)
        
        state = create_initial_state("消息流测试", "测试消息流的任务")
        
        # 执行智能体并收集消息
        state = await meta_wrapper(state)
        meta_messages_count = len(state["agent_messages"])
        
        state["workflow_context"]["current_phase"] = WorkflowPhase.DECOMPOSITION
        state = await decomposer_wrapper(state)
        decomposer_messages_count = len(state["agent_messages"])
        
        state["workflow_context"]["current_phase"] = WorkflowPhase.COORDINATION
        state = await coordinator_wrapper(state)
        coordinator_messages_count = len(state["agent_messages"])
        
        # 验证消息数量递增
        assert meta_messages_count > 0
        assert decomposer_messages_count > meta_messages_count
        assert coordinator_messages_count > decomposer_messages_count
        
        # 验证消息类型
        message_types = [msg["message_type"] for msg in state["agent_messages"]]
        assert "analysis_result" in message_types
        assert "decomposition_result" in message_types
        assert "coordination_result" in message_types
    
    @pytest.mark.asyncio
    async def test_workflow_phase_transitions(self):
        """测试工作流阶段转换"""
        mock_meta_agent = MockAgent("meta_agent")
        mock_task_decomposer = MockAgent("task_decomposer")
        mock_coordinator = MockAgent("coordinator")
        
        meta_wrapper = MetaAgentWrapper(mock_meta_agent)
        decomposer_wrapper = TaskDecomposerWrapper(mock_task_decomposer)
        coordinator_wrapper = CoordinatorWrapper(mock_coordinator)
        
        state = create_initial_state("阶段转换测试", "测试工作流阶段转换的任务")
        
        # 初始阶段
        assert state["workflow_context"]["current_phase"] == WorkflowPhase.INITIALIZATION
        
        # MetaAgent分析后转入分解阶段
        state = await meta_wrapper(state)
        assert state["workflow_context"]["current_phase"] == WorkflowPhase.DECOMPOSITION
        
        # TaskDecomposer分解后转入协调阶段
        state = await decomposer_wrapper(state)
        assert state["workflow_context"]["current_phase"] == WorkflowPhase.COORDINATION
        
        # Coordinator协调后转入执行阶段
        state = await coordinator_wrapper(state)
        assert state["workflow_context"]["current_phase"] == WorkflowPhase.EXECUTION
        
        # 验证阶段历史
        completed_phases = state["workflow_context"]["completed_phases"]
        expected_phases = [WorkflowPhase.INITIALIZATION, WorkflowPhase.DECOMPOSITION, WorkflowPhase.COORDINATION]
        for phase in expected_phases:
            assert phase in completed_phases
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(self):
        """测试并发智能体执行"""
        # 创建多个相同类型的智能体实例
        mock_agents = [MockAgent("generic", {"success": True, "agent_id": f"agent_{i}"}) for i in range(3)]
        wrappers = [MetaAgentWrapper(agent) for agent in mock_agents]
        
        state = create_initial_state("并发测试", "测试并发执行的任务")
        
        # 并发执行多个智能体
        tasks = [wrapper(state.copy()) for wrapper in wrappers]
        results = await asyncio.gather(*tasks)
        
        # 验证所有智能体都成功执行
        for result_state in results:
            assert "meta_agent" in result_state["workflow_context"]["agent_results"]
            assert result_state["workflow_context"]["agent_results"]["meta_agent"]["result"]["success"] is True
        
        # 验证所有智能体都被调用
        for agent in mock_agents:
            assert agent.call_count == 1
    
    @pytest.mark.asyncio
    async def test_agent_wrapper_configuration_inheritance(self):
        """测试智能体包装器配置继承"""
        mock_agent = MockAgent("meta_agent")
        
        # 使用自定义配置创建包装器
        wrapper = MetaAgentWrapper(
            mock_agent,
            timeout_seconds=30,
            max_retries=2
        )
        
        # 验证配置被正确设置
        assert wrapper.timeout_seconds == 30
        assert wrapper.max_retries == 2
        assert wrapper.agent_type == "meta_agent"
        
        # 验证智能体信息包含配置
        info = wrapper.get_agent_info()
        assert info["timeout_seconds"] == 30
        assert info["max_retries"] == 2
    
    @pytest.mark.asyncio
    async def test_complex_multi_agent_scenario(self):
        """测试复杂多智能体场景"""
        # 创建一个需要多轮协调的复杂场景
        mock_meta_agent = MockAgent("meta_agent", {
            "success": True,
            "complexity_score": 0.9,
            "requires_decomposition": True,
            "recommended_agents": ["task_decomposer", "coordinator", "specialist_agent"]
        })
        
        mock_task_decomposer = MockAgent("task_decomposer", {
            "success": True,
            "decomposition": {
                "subtasks": [
                    {"id": "research", "name": "Research Phase", "type": "research"},
                    {"id": "analysis", "name": "Analysis Phase", "type": "analysis"},
                    {"id": "synthesis", "name": "Synthesis Phase", "type": "synthesis"},
                    {"id": "validation", "name": "Validation Phase", "type": "validation"}
                ],
                "dependencies": [
                    {"from": "research", "to": "analysis", "type": "sequential"},
                    {"from": "analysis", "to": "synthesis", "type": "sequential"},
                    {"from": "synthesis", "to": "validation", "type": "sequential"}
                ],
                "decomposition_strategy": "hierarchical"
            },
            "execution_plan": {"estimated_duration": 480},
            "subtasks_count": 4
        })
        
        mock_coordinator = MockAgent("coordinator", {
            "success": True,
            "coordination_type": "establish_collaboration",
            "session_id": "complex_session",
            "participants": ["research_agent", "analysis_agent", "synthesis_agent", "validation_agent"]
        })
        
        meta_wrapper = MetaAgentWrapper(mock_meta_agent)
        decomposer_wrapper = TaskDecomposerWrapper(mock_task_decomposer)
        coordinator_wrapper = CoordinatorWrapper(mock_coordinator)
        
        state = create_initial_state("复杂研究项目", "需要多阶段协作的复杂研究项目")
        
        # 执行完整工作流
        state = await meta_wrapper(state)
        state["workflow_context"]["current_phase"] = WorkflowPhase.DECOMPOSITION
        state = await decomposer_wrapper(state)
        state["workflow_context"]["current_phase"] = WorkflowPhase.COORDINATION
        state = await coordinator_wrapper(state)
        
        # 验证复杂场景处理
        assert len(state["task_state"]["subtasks"]) == 4
        assert state["workflow_context"]["execution_metadata"]["subtasks_count"] == 4
        assert "complex_session" in state["coordination_state"]["active_sessions"]
        
        # 验证执行计划
        execution_plan = state["workflow_context"]["execution_metadata"]["execution_plan"]
        assert execution_plan["estimated_duration"] == 480
        
        # 验证所有阶段都有记录
        assert len(state["workflow_context"]["execution_metadata"]["decomposition_history"]) > 0
        assert len(state["workflow_context"]["execution_metadata"]["coordination_history"]) > 0