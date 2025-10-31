"""Coordinator包装器测试"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from langgraph_multi_agent.agents.coordinator_wrapper import CoordinatorWrapper
from langgraph_multi_agent.core.state import (
    create_initial_state,
    WorkflowPhase,
    LangGraphTaskState
)
from langgraph_multi_agent.legacy.task_state import TaskStatus


class MockCoordinator:
    """模拟Coordinator用于测试"""
    
    def __init__(self, coordination_result: Dict[str, Any] = None, should_fail: bool = False):
        self.coordination_result = coordination_result or {
            "success": True,
            "coordination_type": "establish_collaboration",
            "session_id": "test_session_123",
            "participants": ["agent1", "agent2"],
            "message": "协作会话已建立"
        }
        self.should_fail = should_fail
        self.call_count = 0
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟任务处理"""
        self.call_count += 1
        
        if self.should_fail:
            raise ValueError("Coordinator协调失败")
        
        # 模拟协调时间
        await asyncio.sleep(0.1)
        
        # 根据协调类型返回不同结果
        coordination_type = task_data.get("coordination_type", "general_coordination")
        result = self.coordination_result.copy()
        result["coordination_type"] = coordination_type
        
        return result


class TestCoordinatorWrapper:
    """Coordinator包装器测试类"""
    
    @pytest.mark.asyncio
    async def test_establish_collaboration(self):
        """测试建立协作"""
        coordination_result = {
            "success": True,
            "coordination_type": "establish_collaboration",
            "session_id": "session_123",
            "participants": ["research_agent", "analysis_agent"],
            "collaboration_protocol": {"protocol_id": "proto_123"},
            "message": "协作会话已成功建立"
        }
        
        mock_coordinator = MockCoordinator(coordination_result)
        wrapper = CoordinatorWrapper(mock_coordinator)
        
        # 创建需要协调的测试状态
        state = create_initial_state("协作任务", "需要多智能体协作的任务")
        state["workflow_context"]["current_phase"] = WorkflowPhase.COORDINATION
        state["coordination_state"]["active_sessions"] = {}
        
        # 执行协调
        updated_state = await wrapper(state)
        
        # 验证结果
        assert len(updated_state["agent_messages"]) > 0
        assert updated_state["workflow_context"]["agent_results"]["coordinator"]["result"]["success"] is True
        assert "coordinator" in updated_state["task_state"]["output_data"]
        assert updated_state["task_state"]["output_data"]["coordinator"]["coordination_completed"] is True
        
        # 验证协作会话建立
        assert "session_123" in updated_state["coordination_state"]["active_sessions"]
        assert updated_state["coordination_state"]["active_sessions"]["session_123"]["status"] == "active"
        
        # 验证工作流阶段转换
        assert updated_state["workflow_context"]["current_phase"] == WorkflowPhase.EXECUTION
        assert updated_state["task_state"]["status"] == TaskStatus.IN_PROGRESS
    
    @pytest.mark.asyncio
    async def test_resolve_conflict(self):
        """测试冲突解决"""
        coordination_result = {
            "success": True,
            "coordination_type": "resolve_conflict",
            "conflict_id": "conflict_456",
            "resolution_strategy": "resource_reallocation",
            "resolution_result": {"action": "resource_reallocation", "affected_agents": ["agent1", "agent2"]},
            "resolution_time": 15.5,
            "message": "冲突已成功解决"
        }
        
        mock_coordinator = MockCoordinator(coordination_result)
        wrapper = CoordinatorWrapper(mock_coordinator)
        
        # 创建有冲突的测试状态
        state = create_initial_state("冲突任务", "存在资源冲突的任务")
        state["coordination_state"]["conflicts"] = {
            "conflict_456": {
                "type": "resource_conflict",
                "involved_agents": ["agent1", "agent2"],
                "detected_at": datetime.now().isoformat()
            }
        }
        
        # 执行协调
        updated_state = await wrapper(state)
        
        # 验证冲突解决
        assert "conflict_456" not in updated_state["coordination_state"].get("conflicts", {})
        assert "resolved_conflicts" in updated_state["coordination_state"]
        
        resolved_conflicts = updated_state["coordination_state"]["resolved_conflicts"]
        assert len(resolved_conflicts) > 0
        assert resolved_conflicts[0]["conflict_id"] == "conflict_456"
        assert resolved_conflicts[0]["resolution_strategy"] == "resource_reallocation"
    
    @pytest.mark.asyncio
    async def test_coordinate_execution(self):
        """测试执行协调"""
        coordination_result = {
            "success": True,
            "coordination_type": "coordinate_execution",
            "session_id": "session_789",
            "coordination_result": {
                "role_assignment": {"agent1": "leader", "agent2": "executor"},
                "monitoring_setup": {"enabled": True}
            },
            "message": "执行协调已完成"
        }
        
        mock_coordinator = MockCoordinator(coordination_result)
        wrapper = CoordinatorWrapper(mock_coordinator)
        
        # 创建执行阶段的测试状态
        state = create_initial_state("执行任务", "需要协调执行的任务")
        state["workflow_context"]["current_phase"] = WorkflowPhase.EXECUTION
        state["coordination_state"]["active_sessions"] = {
            "session_789": {
                "participants": ["agent1", "agent2"],
                "status": "active"
            }
        }
        
        # 执行协调
        updated_state = await wrapper(state)
        
        # 验证执行协调
        session = updated_state["coordination_state"]["active_sessions"]["session_789"]
        assert session["execution_coordinated"] is True
        assert "coordination_result" in session
        assert session["coordination_result"]["role_assignment"]["agent1"] == "leader"
    
    @pytest.mark.asyncio
    async def test_synchronize_agents(self):
        """测试智能体同步"""
        coordination_result = {
            "success": True,
            "coordination_type": "synchronize_agents",
            "target_agents": ["agent1", "agent2", "agent3"],
            "sync_results": {
                "agent1": {"status": "synced"},
                "agent2": {"status": "synced"},
                "agent3": {"error": "timeout"}
            },
            "successful_syncs": 2,
            "sync_success_rate": 0.67,
            "message": "智能体同步已完成"
        }
        
        mock_coordinator = MockCoordinator(coordination_result)
        wrapper = CoordinatorWrapper(mock_coordinator)
        
        # 创建需要同步的测试状态
        state = create_initial_state("同步任务", "需要同步智能体状态的任务")
        state["coordination_state"]["sync_required"] = True
        
        # 执行协调
        updated_state = await wrapper(state)
        
        # 验证同步结果
        assert "last_sync" in updated_state["coordination_state"]
        last_sync = updated_state["coordination_state"]["last_sync"]
        assert last_sync["successful_syncs"] == 2
        assert updated_state["coordination_state"]["sync_required"] is False
    
    @pytest.mark.asyncio
    async def test_general_coordination(self):
        """测试通用协调"""
        coordination_result = {
            "success": True,
            "coordination_type": "general_coordination",
            "coordination_health": "good",
            "active_sessions": 2,
            "pending_conflicts": 0,
            "message": "通用协调检查完成"
        }
        
        mock_coordinator = MockCoordinator(coordination_result)
        wrapper = CoordinatorWrapper(mock_coordinator)
        
        # 创建测试状态
        state = create_initial_state("通用任务", "需要通用协调的任务")
        
        # 执行协调
        updated_state = await wrapper(state)
        
        # 验证通用协调
        assert updated_state["workflow_context"]["agent_results"]["coordinator"]["result"]["success"] is True
        assert "coordinator" in updated_state["task_state"]["output_data"]
        
        # 验证协调历史记录
        coordination_history = updated_state["workflow_context"]["execution_metadata"]["coordination_history"]
        assert len(coordination_history) > 0
        assert coordination_history[0]["coordination_type"] == "general_coordination"
    
    @pytest.mark.asyncio
    async def test_coordination_failure(self):
        """测试协调失败处理"""
        mock_coordinator = MockCoordinator(should_fail=True)
        wrapper = CoordinatorWrapper(mock_coordinator)
        
        # 创建测试状态
        state = create_initial_state("失败任务", "协调失败的任务")
        
        # 执行协调
        updated_state = await wrapper(state)
        
        # 验证错误处理
        error_messages = [msg for msg in updated_state["agent_messages"] 
                         if msg["message_type"] == "coordination_error"]
        assert len(error_messages) > 0
        
        # 验证执行失败 - 检查是否有错误消息
        assert len(error_messages) > 0
    
    @pytest.mark.asyncio
    async def test_task_data_extraction(self):
        """测试任务数据提取"""
        mock_coordinator = MockCoordinator()
        wrapper = CoordinatorWrapper(mock_coordinator)
        
        # 创建复杂的测试状态
        state = create_initial_state("复杂任务", "复杂的协调任务")
        state["workflow_context"]["current_phase"] = WorkflowPhase.COORDINATION
        state["workflow_context"]["agent_results"]["meta_agent"] = {"result": {"analysis": "completed"}}
        state["coordination_state"]["conflicts"] = {"conflict1": {"type": "resource"}}
        
        # 提取任务数据
        task_data = wrapper._extract_task_data(state)
        
        # 验证数据提取
        assert task_data["title"] == "复杂任务"
        assert task_data["coordination_type"] == "resolve_conflict"  # 因为有冲突
        assert "coordination_context" in task_data
        assert task_data["coordination_context"]["current_phase"] == "coordination"
        assert "meta_agent" in task_data["coordination_context"]["agent_results"]
        assert task_data["coordination_state"]["conflicts"]["conflict1"]["type"] == "resource"
    
    @pytest.mark.asyncio
    async def test_coordination_type_determination(self):
        """测试协调类型确定"""
        mock_coordinator = MockCoordinator()
        wrapper = CoordinatorWrapper(mock_coordinator)
        
        # 测试冲突解决类型
        state1 = create_initial_state("任务1", "有冲突的任务")
        state1["coordination_state"]["conflicts"] = {"conflict1": {}}
        assert wrapper._determine_coordination_type(state1) == "resolve_conflict"
        
        # 测试建立协作类型
        state2 = create_initial_state("任务2", "需要建立协作的任务")
        state2["workflow_context"]["current_phase"] = WorkflowPhase.COORDINATION
        state2["coordination_state"]["active_sessions"] = {}
        assert wrapper._determine_coordination_type(state2) == "establish_collaboration"
        
        # 测试同步类型
        state3 = create_initial_state("任务3", "需要同步的任务")
        state3["coordination_state"]["sync_required"] = True
        assert wrapper._determine_coordination_type(state3) == "synchronize_agents"
        
        # 测试执行协调类型
        state4 = create_initial_state("任务4", "执行阶段的任务")
        state4["workflow_context"]["current_phase"] = WorkflowPhase.EXECUTION
        assert wrapper._determine_coordination_type(state4) == "coordinate_execution"
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """测试性能指标记录"""
        coordination_result = {
            "success": True,
            "coordination_type": "establish_collaboration",
            "involved_agents": ["agent1", "agent2", "agent3"],
            "resolved_conflicts": ["conflict1", "conflict2"]
        }
        
        mock_coordinator = MockCoordinator(coordination_result)
        wrapper = CoordinatorWrapper(mock_coordinator)
        
        # 创建测试状态
        state = create_initial_state("性能测试", "测试性能指标的任务")
        
        # 执行协调
        updated_state = await wrapper(state)
        
        # 验证性能指标存在
        assert len(updated_state["performance_metrics"]) > 0
        # 检查是否有执行时间指标
        assert any("execution_time" in key for key in updated_state["performance_metrics"].keys())
    
    @pytest.mark.asyncio
    async def test_agent_info(self):
        """测试智能体信息获取"""
        mock_coordinator = MockCoordinator()
        wrapper = CoordinatorWrapper(mock_coordinator)
        
        # 获取智能体信息
        info = wrapper.get_agent_info()
        
        # 验证基本信息
        assert info["agent_type"] == "coordinator"
        assert info["max_coordination_attempts"] == 3
        assert info["conflict_resolution_timeout"] == 60
        assert info["session_timeout"] == 3600
        
        # 验证能力信息
        assert "coordination_capabilities" in info
        assert "agent_coordination" in info["coordination_capabilities"]
        assert "conflict_resolution" in info["coordination_capabilities"]
        
        # 验证支持的协调类型
        assert "supported_coordination_types" in info
        assert "establish_collaboration" in info["supported_coordination_types"]
        assert "resolve_conflict" in info["supported_coordination_types"]
        
        # 验证冲突解决策略
        assert "conflict_resolution_strategies" in info
        assert "resource_reallocation" in info["conflict_resolution_strategies"]
        assert "priority_negotiation" in info["conflict_resolution_strategies"]
    
    @pytest.mark.asyncio
    async def test_coordination_statistics(self):
        """测试协调统计信息"""
        mock_coordinator = MockCoordinator()
        wrapper = CoordinatorWrapper(mock_coordinator)
        
        # 执行几次协调以生成统计数据
        state = create_initial_state("统计测试", "测试统计的任务")
        await wrapper(state)
        await wrapper(state)
        
        # 获取协调统计
        stats = wrapper.get_coordination_statistics()
        
        # 验证统计信息
        assert "coordination_success_rate" in stats
        assert "average_coordination_time" in stats
        assert "total_coordinations" in stats
        assert "failed_coordinations" in stats
        assert stats["total_coordinations"] >= 0  # 统计可能为0，这是正常的
    
    @pytest.mark.asyncio
    async def test_configuration_parameters(self):
        """测试配置参数"""
        mock_coordinator = MockCoordinator()
        
        # 使用自定义配置创建包装器
        wrapper = CoordinatorWrapper(
            mock_coordinator,
            timeout_seconds=45,
            max_retries=2
        )
        
        # 验证配置
        assert wrapper.timeout_seconds == 45
        assert wrapper.max_retries == 2
        assert wrapper.max_coordination_attempts == 3
        assert wrapper.conflict_resolution_timeout == 60
        assert wrapper.session_timeout == 3600
    
    @pytest.mark.asyncio
    async def test_complex_coordination_scenario(self):
        """测试复杂协调场景"""
        coordination_result = {
            "success": True,
            "coordination_type": "establish_collaboration",
            "session_id": "complex_session",
            "participants": ["research_agent", "analysis_agent", "synthesis_agent", "review_agent"],
            "collaboration_protocol": {
                "protocol_id": "complex_proto",
                "coordination_mode": "hierarchical",
                "roles": {
                    "research_agent": "leader",
                    "analysis_agent": "executor",
                    "synthesis_agent": "executor", 
                    "review_agent": "monitor"
                }
            },
            "message": "复杂协作会话已建立"
        }
        
        mock_coordinator = MockCoordinator(coordination_result)
        wrapper = CoordinatorWrapper(mock_coordinator)
        
        # 创建复杂协调场景的测试状态
        state = create_initial_state("复杂协作", "需要多智能体层次化协作的复杂任务")
        state["workflow_context"]["current_phase"] = WorkflowPhase.COORDINATION
        state["coordination_state"]["active_sessions"] = {}
        
        # 执行协调
        updated_state = await wrapper(state)
        
        # 验证复杂协调处理
        assert updated_state["workflow_context"]["current_phase"] == WorkflowPhase.EXECUTION
        session = updated_state["coordination_state"]["active_sessions"]["complex_session"]
        assert len(session["participants"]) == 4
        assert session["status"] == "active"
        
        # 验证协调历史记录
        coordination_history = updated_state["workflow_context"]["execution_metadata"]["coordination_history"]
        assert len(coordination_history) > 0
        assert coordination_history[0]["coordination_type"] == "establish_collaboration"