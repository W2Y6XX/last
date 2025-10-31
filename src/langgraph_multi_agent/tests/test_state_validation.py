"""状态验证和转换测试"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from langgraph_multi_agent.core.state import (
    create_initial_state, WorkflowPhase, LangGraphTaskState,
    update_workflow_phase, add_agent_message, create_checkpoint,
    assign_agent_to_task, add_conflict, handle_error
)
from langgraph_multi_agent.core.state_validation import (
    StateValidator, StateTransitionManager, StateValidationError,
    validate_state, safe_transition_to_phase, safe_update_task_status
)
from langgraph_multi_agent.legacy.task_state import TaskStatus


class TestStateValidator:
    """状态验证器测试"""
    
    @pytest.fixture
    def validator(self):
        """创建状态验证器"""
        return StateValidator()
    
    @pytest.fixture
    def valid_state(self):
        """创建有效状态"""
        return create_initial_state(
            title="测试任务",
            description="状态验证测试任务",
            task_type="test",
            priority=1
        )
    
    def test_validate_valid_state(self, validator, valid_state):
        """测试验证有效状态"""
        is_valid, errors = validator.validate_state(valid_state)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_missing_required_fields(self, validator, valid_state):
        """测试验证缺失必需字段"""
        # 删除必需字段
        del valid_state["task_state"]
        
        is_valid, errors = validator.validate_state(valid_state)
        assert is_valid is False
        assert any("缺少必需字段: task_state" in error for error in errors)
    
    def test_validate_workflow_phase_constraints(self, validator, valid_state):
        """测试验证工作流阶段约束"""
        # 设置不匹配的阶段和状态
        valid_state["workflow_context"]["current_phase"] = WorkflowPhase.COMPLETION
        valid_state["task_state"]["status"] = TaskStatus.PENDING
        
        is_valid, errors = validator.validate_state(valid_state)
        assert is_valid is False
        assert any("不允许任务状态" in error for error in errors)
    
    def test_validate_excessive_retry_count(self, validator, valid_state):
        """测试验证过多重试次数"""
        valid_state["retry_count"] = 15  # 超过最大限制
        
        is_valid, errors = validator.validate_state(valid_state)
        assert is_valid is False
        assert any("重试次数" in error and "超过最大限制" in error for error in errors)
    
    def test_validate_too_many_messages(self, validator, valid_state):
        """测试验证消息过多"""
        # 添加过多消息
        for i in range(1001):  # 超过最大限制1000
            add_agent_message(
                valid_state,
                sender_agent=f"agent_{i % 10}",
                content={"test": f"message_{i}"},
                message_type="test"
            )
        
        is_valid, errors = validator.validate_state(valid_state)
        assert is_valid is False
        assert any("消息总数" in error and "超过最大限制" in error for error in errors)
    
    def test_validate_execution_time_limit(self, validator, valid_state):
        """测试验证执行时间限制"""
        # 设置超长执行时间
        valid_state["execution_start_time"] = datetime.now() - timedelta(hours=25)
        
        is_valid, errors = validator.validate_state(valid_state)
        assert is_valid is False
        assert any("执行时间" in error and "超过最大限制" in error for error in errors)
    
    def test_validate_data_consistency(self, validator, valid_state):
        """测试验证数据一致性"""
        # 设置不一致的时间戳
        valid_state["execution_start_time"] = datetime.now()
        valid_state["execution_end_time"] = datetime.now() - timedelta(hours=1)
        
        is_valid, errors = validator.validate_state(valid_state)
        assert is_valid is False
        assert any("执行结束时间早于开始时间" in error for error in errors)
    
    def test_validate_agent_consistency(self, validator, valid_state):
        """测试验证智能体一致性"""
        # 分配任务给不活跃的智能体
        valid_state["coordination_state"]["agent_assignments"]["inactive_agent"] = ["task_1"]
        # 但不将其添加到活跃列表中
        
        is_valid, errors = validator.validate_state(valid_state)
        assert is_valid is False
        assert any("已分配任务但不在活跃列表中" in error for error in errors)
    
    def test_validate_message_field_completeness(self, validator, valid_state):
        """测试验证消息字段完整性"""
        # 添加不完整的消息
        incomplete_message = {
            "message_id": "test_msg",
            "sender_agent": "test_agent"
            # 缺少timestamp和content字段
        }
        valid_state["agent_messages"].append(incomplete_message)
        
        is_valid, errors = validator.validate_state(valid_state)
        assert is_valid is False
        assert any("缺少必需字段" in error for error in errors)


class TestStateTransitionManager:
    """状态转换管理器测试"""
    
    @pytest.fixture
    def transition_manager(self):
        """创建状态转换管理器"""
        return StateTransitionManager()
    
    @pytest.fixture
    def valid_state(self):
        """创建有效状态"""
        return create_initial_state(
            title="转换测试任务",
            description="状态转换测试任务",
            task_type="test",
            priority=1
        )
    
    def test_safe_transition_valid(self, transition_manager, valid_state):
        """测试有效的状态转换"""
        # 从INITIALIZATION转换到ANALYSIS
        new_state, success, errors = transition_manager.safe_transition_to_phase(
            valid_state, WorkflowPhase.ANALYSIS
        )
        
        assert success is True
        assert len(errors) == 0
        assert new_state["workflow_context"]["current_phase"] == WorkflowPhase.ANALYSIS
        assert WorkflowPhase.INITIALIZATION in new_state["workflow_context"]["completed_phases"]
    
    def test_safe_transition_invalid(self, transition_manager, valid_state):
        """测试无效的状态转换"""
        # 尝试从INITIALIZATION直接转换到EXECUTION（无效）
        new_state, success, errors = transition_manager.safe_transition_to_phase(
            valid_state, WorkflowPhase.EXECUTION
        )
        
        assert success is False
        assert len(errors) > 0
        assert any("无效的状态转换" in error for error in errors)
        assert new_state["workflow_context"]["current_phase"] == WorkflowPhase.INITIALIZATION
    
    def test_safe_transition_force(self, transition_manager, valid_state):
        """测试强制状态转换"""
        # 强制执行无效转换
        new_state, success, errors = transition_manager.safe_transition_to_phase(
            valid_state, WorkflowPhase.EXECUTION, force=True
        )
        
        assert success is True
        assert len(errors) == 0
        assert new_state["workflow_context"]["current_phase"] == WorkflowPhase.EXECUTION
    
    def test_safe_update_task_status_valid(self, transition_manager, valid_state):
        """测试有效的任务状态更新"""
        new_state, success, errors = transition_manager.safe_update_task_status(
            valid_state, TaskStatus.ANALYZING
        )
        
        assert success is True
        assert len(errors) == 0
        assert new_state["task_state"]["status"] == TaskStatus.ANALYZING
    
    def test_safe_update_task_status_with_phase_sync(self, transition_manager, valid_state):
        """测试任务状态更新与阶段同步"""
        new_state, success, errors = transition_manager.safe_update_task_status(
            valid_state, TaskStatus.ANALYZING
        )
        
        assert success is True
        assert new_state["task_state"]["status"] == TaskStatus.ANALYZING
        assert new_state["workflow_context"]["current_phase"] == WorkflowPhase.ANALYSIS
    
    def test_transition_hooks(self, transition_manager, valid_state):
        """测试状态转换钩子"""
        hook_called = {"before": False, "after": False}
        
        def test_hook(state, timing):
            hook_called[timing] = True
            return state
        
        # 注册钩子
        transition_manager.register_transition_hook(WorkflowPhase.ANALYSIS, test_hook)
        
        # 执行转换
        new_state, success, errors = transition_manager.safe_transition_to_phase(
            valid_state, WorkflowPhase.ANALYSIS
        )
        
        assert success is True
        assert hook_called["before"] is True
        assert hook_called["after"] is True
    
    def test_validate_and_repair_state(self, transition_manager):
        """测试状态验证和修复"""
        # 创建有问题的状态
        broken_state = create_initial_state("修复测试", "测试状态修复")
        
        # 删除必需字段
        del broken_state["agent_messages"]
        
        # 设置不一致的时间戳
        broken_state["execution_start_time"] = datetime.now()
        broken_state["execution_end_time"] = datetime.now() - timedelta(hours=1)
        
        # 尝试修复
        repaired_state, is_valid, errors = transition_manager.validate_and_repair_state(broken_state)
        
        # 验证修复结果
        assert "agent_messages" in repaired_state
        assert repaired_state["execution_end_time"] is None  # 应该被修复
    
    def test_repair_missing_fields(self, transition_manager):
        """测试修复缺失字段"""
        state = create_initial_state("字段修复测试", "测试缺失字段修复")
        
        # 删除一些字段
        del state["agent_messages"]
        del state["performance_metrics"]
        
        repaired_state, is_valid, errors = transition_manager.validate_and_repair_state(state)
        
        assert "agent_messages" in repaired_state
        assert "performance_metrics" in repaired_state
        assert isinstance(repaired_state["agent_messages"], list)
        assert isinstance(repaired_state["performance_metrics"], dict)
    
    def test_repair_agent_consistency(self, transition_manager):
        """测试修复智能体一致性"""
        state = create_initial_state("智能体修复测试", "测试智能体一致性修复")
        
        # 创建不一致的智能体分配
        state["coordination_state"]["agent_assignments"]["inactive_agent"] = ["task_1"]
        # 不将其添加到活跃列表
        
        repaired_state, is_valid, errors = transition_manager.validate_and_repair_state(state)
        
        # 验证不活跃的智能体分配被清理
        assert "inactive_agent" not in repaired_state["coordination_state"]["agent_assignments"]


class TestStateTransitionScenarios:
    """状态转换场景测试"""
    
    @pytest.fixture
    def state(self):
        """创建测试状态"""
        return create_initial_state(
            title="场景测试任务",
            description="状态转换场景测试",
            task_type="scenario_test",
            priority=2
        )
    
    def test_complete_workflow_transition(self, state):
        """测试完整工作流转换"""
        # 模拟完整的工作流转换序列
        transitions = [
            (WorkflowPhase.ANALYSIS, TaskStatus.ANALYZING),
            (WorkflowPhase.DECOMPOSITION, TaskStatus.DECOMPOSED),
            (WorkflowPhase.COORDINATION, TaskStatus.IN_PROGRESS),
            (WorkflowPhase.EXECUTION, TaskStatus.IN_PROGRESS),
            (WorkflowPhase.REVIEW, TaskStatus.REVIEWING),
            (WorkflowPhase.COMPLETION, TaskStatus.COMPLETED)
        ]
        
        current_state = state
        for target_phase, target_status in transitions:
            # 转换阶段
            current_state, success, errors = safe_transition_to_phase(
                current_state, target_phase
            )
            assert success is True, f"阶段转换失败: {target_phase}, 错误: {errors}"
            
            # 更新任务状态
            current_state, success, errors = safe_update_task_status(
                current_state, target_status
            )
            assert success is True, f"状态更新失败: {target_status}, 错误: {errors}"
            
            # 验证状态一致性
            is_valid, validation_errors = validate_state(current_state)
            assert is_valid is True, f"状态验证失败: {validation_errors}"
        
        # 验证最终状态
        assert current_state["workflow_context"]["current_phase"] == WorkflowPhase.COMPLETION
        assert current_state["task_state"]["status"] == TaskStatus.COMPLETED
        assert len(current_state["workflow_context"]["completed_phases"]) == 5
    
    def test_error_handling_transition(self, state):
        """测试错误处理转换"""
        # 先转换到执行阶段
        state, success, errors = safe_transition_to_phase(state, WorkflowPhase.ANALYSIS)
        assert success is True
        
        state, success, errors = safe_transition_to_phase(state, WorkflowPhase.EXECUTION)
        assert success is True
        
        # 模拟错误发生
        error = Exception("模拟执行错误")
        state = handle_error(state, error, "execution_node", "test_agent")
        
        # 验证错误状态
        assert state["error_state"] is not None
        assert state["error_state"]["error_type"] == "Exception"
        assert state["error_state"]["error_message"] == "模拟执行错误"
        assert state["workflow_context"]["current_phase"] == WorkflowPhase.ERROR_HANDLING
        
        # 验证可以从错误状态恢复
        state, success, errors = safe_transition_to_phase(state, WorkflowPhase.EXECUTION)
        assert success is True
    
    def test_parallel_agent_coordination(self, state):
        """测试并行智能体协调"""
        # 转换到协调阶段
        state, success, errors = safe_transition_to_phase(state, WorkflowPhase.ANALYSIS)
        assert success is True
        
        state, success, errors = safe_transition_to_phase(state, WorkflowPhase.COORDINATION)
        assert success is True
        
        # 分配多个智能体
        agents = ["agent_1", "agent_2", "agent_3"]
        for agent in agents:
            state = assign_agent_to_task(state, agent, [f"task_{agent}"])
        
        # 验证智能体分配
        assert len(state["coordination_state"]["active_agents"]) == 3
        assert all(agent in state["coordination_state"]["active_agents"] for agent in agents)
        
        # 添加智能体消息
        for agent in agents:
            state = add_agent_message(
                state,
                sender_agent=agent,
                content={"status": "working", "progress": 0.5},
                message_type="progress_update"
            )
        
        # 验证状态仍然有效
        is_valid, validation_errors = validate_state(state)
        assert is_valid is True, f"并行协调状态无效: {validation_errors}"
    
    def test_checkpoint_and_recovery(self, state):
        """测试检查点和恢复"""
        # 转换到执行阶段
        state, success, errors = safe_transition_to_phase(state, WorkflowPhase.ANALYSIS)
        assert success is True
        
        state, success, errors = safe_transition_to_phase(state, WorkflowPhase.EXECUTION)
        assert success is True
        
        # 创建检查点
        checkpoint_id = "test_checkpoint_001"
        state = create_checkpoint(state, checkpoint_id)
        
        # 验证检查点数据
        assert state["checkpoint_data"] is not None
        assert state["checkpoint_data"]["checkpoint_id"] == checkpoint_id
        assert state["checkpoint_data"]["workflow_phase"] == WorkflowPhase.EXECUTION
        assert state["checkpoint_data"]["resumable"] is True
        
        # 验证检查点状态快照
        snapshot = state["checkpoint_data"]["state_snapshot"]
        assert "task_status" in snapshot
        assert "workflow_phase" in snapshot
        assert "active_agents" in snapshot
        
        # 验证状态仍然有效
        is_valid, validation_errors = validate_state(state)
        assert is_valid is True, f"检查点状态无效: {validation_errors}"
    
    def test_conflict_resolution(self, state):
        """测试冲突解决"""
        # 转换到协调阶段
        state, success, errors = safe_transition_to_phase(state, WorkflowPhase.COORDINATION)
        assert success is True
        
        # 分配智能体
        agents = ["agent_1", "agent_2"]
        for agent in agents:
            state = assign_agent_to_task(state, agent, ["shared_task"])
        
        # 添加冲突
        state = add_conflict(
            state,
            conflict_type="resource_conflict",
            description="两个智能体争夺同一资源",
            involved_agents=agents
        )
        
        # 验证冲突记录
        conflicts = state["coordination_state"]["conflicts"]
        assert len(conflicts) == 1
        assert conflicts[0]["conflict_type"] == "resource_conflict"
        assert conflicts[0]["resolved"] is False
        assert set(conflicts[0]["involved_agents"]) == set(agents)
        
        # 验证状态仍然有效
        is_valid, validation_errors = validate_state(state)
        assert is_valid is True, f"冲突状态无效: {validation_errors}"


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def test_validate_state_function(self):
        """测试validate_state便捷函数"""
        state = create_initial_state("便捷函数测试", "测试便捷函数")
        
        is_valid, errors = validate_state(state)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_safe_transition_function(self):
        """测试safe_transition_to_phase便捷函数"""
        state = create_initial_state("转换函数测试", "测试转换便捷函数")
        
        new_state, success, errors = safe_transition_to_phase(state, WorkflowPhase.ANALYSIS)
        assert success is True
        assert len(errors) == 0
        assert new_state["workflow_context"]["current_phase"] == WorkflowPhase.ANALYSIS
    
    def test_safe_update_status_function(self):
        """测试safe_update_task_status便捷函数"""
        state = create_initial_state("状态函数测试", "测试状态更新便捷函数")
        
        new_state, success, errors = safe_update_task_status(state, TaskStatus.ANALYZING)
        assert success is True
        assert len(errors) == 0
        assert new_state["task_state"]["status"] == TaskStatus.ANALYZING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])