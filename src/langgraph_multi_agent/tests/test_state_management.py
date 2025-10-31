"""状态管理测试"""

import pytest
from datetime import datetime
from langgraph_multi_agent.core.state import (
    LangGraphTaskState,
    create_initial_state,
    WorkflowPhase,
    update_workflow_phase,
    validate_state_transition,
    update_task_status,
    add_performance_metric,
    assign_agent_to_task,
    add_conflict,
    resolve_conflict,
    handle_error,
    is_state_valid,
    create_checkpoint
)
from langgraph_multi_agent.legacy.task_state import TaskStatus


class TestStateManagement:
    """状态管理测试类"""
    
    def test_state_transition_validation(self):
        """测试状态转换验证"""
        state = create_initial_state("测试任务", "测试描述")
        
        # 有效转换
        assert validate_state_transition(state, WorkflowPhase.ANALYSIS) is True
        assert validate_state_transition(state, WorkflowPhase.ERROR_HANDLING) is True
        
        # 无效转换
        assert validate_state_transition(state, WorkflowPhase.EXECUTION) is False
        assert validate_state_transition(state, WorkflowPhase.COMPLETION) is False
    
    def test_task_status_update(self):
        """测试任务状态更新"""
        state = create_initial_state("测试任务", "测试描述")
        
        # 更新到分析状态
        updated_state = update_task_status(state, TaskStatus.ANALYZING)
        
        assert updated_state["task_state"]["status"] == TaskStatus.ANALYZING
        assert updated_state["workflow_context"]["current_phase"] == WorkflowPhase.ANALYSIS
        assert isinstance(updated_state["task_state"]["updated_at"], datetime)
    
    def test_performance_metrics(self):
        """测试性能指标添加"""
        state = create_initial_state("测试任务", "测试描述")
        
        # 添加性能指标
        updated_state = add_performance_metric(state, "execution_time", 123.45)
        updated_state = add_performance_metric(updated_state, "memory_usage", 256)
        
        assert "execution_time" in updated_state["performance_metrics"]
        assert "memory_usage" in updated_state["performance_metrics"]
        assert updated_state["performance_metrics"]["execution_time"][0]["value"] == 123.45
        assert updated_state["performance_metrics"]["memory_usage"][0]["value"] == 256
    
    def test_agent_assignment(self):
        """测试智能体分配"""
        state = create_initial_state("测试任务", "测试描述")
        
        # 分配智能体
        updated_state = assign_agent_to_task(state, "meta_agent", ["task_1", "task_2"])
        updated_state = assign_agent_to_task(updated_state, "coordinator", ["task_3"])
        
        assert "meta_agent" in updated_state["coordination_state"]["active_agents"]
        assert "coordinator" in updated_state["coordination_state"]["active_agents"]
        assert updated_state["coordination_state"]["agent_assignments"]["meta_agent"] == ["task_1", "task_2"]
        assert updated_state["coordination_state"]["agent_assignments"]["coordinator"] == ["task_3"]
    
    def test_conflict_management(self):
        """测试冲突管理"""
        state = create_initial_state("测试任务", "测试描述")
        
        # 添加冲突
        updated_state = add_conflict(
            state,
            "resource_conflict",
            "两个智能体争夺同一资源",
            ["agent_1", "agent_2"]
        )
        
        assert len(updated_state["coordination_state"]["conflicts"]) == 1
        conflict = updated_state["coordination_state"]["conflicts"][0]
        assert conflict["conflict_type"] == "resource_conflict"
        assert conflict["involved_agents"] == ["agent_1", "agent_2"]
        assert conflict["resolved"] is False
        
        # 解决冲突
        conflict_id = conflict["conflict_id"]
        resolved_state = resolve_conflict(updated_state, conflict_id, "资源重新分配")
        
        resolved_conflict = resolved_state["coordination_state"]["conflicts"][0]
        assert resolved_conflict["resolved"] is True
        assert resolved_conflict["resolution"] == "资源重新分配"
    
    def test_error_handling(self):
        """测试错误处理"""
        state = create_initial_state("测试任务", "测试描述")
        
        # 模拟错误
        error = ValueError("测试错误")
        error_state = handle_error(state, error, "meta_agent", "meta_agent_001")
        
        assert error_state["error_state"] is not None
        assert error_state["error_state"]["error_type"] == "ValueError"
        assert error_state["error_state"]["error_message"] == "测试错误"
        assert error_state["error_state"]["failed_node"] == "meta_agent"
        assert error_state["error_state"]["failed_agent"] == "meta_agent_001"
        assert error_state["retry_count"] == 1
        assert error_state["workflow_context"]["current_phase"] == WorkflowPhase.ERROR_HANDLING
    
    def test_checkpoint_creation(self):
        """测试检查点创建"""
        state = create_initial_state("测试任务", "测试描述")
        state = update_workflow_phase(state, WorkflowPhase.ANALYSIS)
        
        # 创建检查点
        checkpoint_state = create_checkpoint(state, "test_checkpoint_001")
        
        assert checkpoint_state["checkpoint_data"] is not None
        checkpoint = checkpoint_state["checkpoint_data"]
        assert checkpoint["checkpoint_id"] == "test_checkpoint_001"
        assert checkpoint["workflow_phase"] == WorkflowPhase.ANALYSIS
        assert checkpoint["resumable"] is True
        assert "current_node" in checkpoint["metadata"]
    
    def test_state_validation(self):
        """测试状态验证"""
        # 有效状态
        valid_state = create_initial_state("测试任务", "测试描述")
        assert is_state_valid(valid_state) is True
        
        # 无效状态 - 缺少必需字段
        invalid_state = valid_state.copy()
        del invalid_state["task_state"]
        assert is_state_valid(invalid_state) is False
    
    def test_workflow_phase_progression(self):
        """测试工作流阶段进展"""
        state = create_initial_state("测试任务", "测试描述")
        
        # 完整的工作流进展
        phases = [
            WorkflowPhase.ANALYSIS,
            WorkflowPhase.DECOMPOSITION,
            WorkflowPhase.COORDINATION,
            WorkflowPhase.EXECUTION,
            WorkflowPhase.REVIEW,
            WorkflowPhase.COMPLETION
        ]
        
        current_state = state
        for phase in phases:
            assert validate_state_transition(current_state, phase) is True
            current_state = update_workflow_phase(current_state, phase)
            assert current_state["workflow_context"]["current_phase"] == phase
        
        # 验证阶段历史
        completed_phases = current_state["workflow_context"]["completed_phases"]
        assert WorkflowPhase.INITIALIZATION in completed_phases
        assert WorkflowPhase.ANALYSIS in completed_phases
        assert len(completed_phases) == len(phases)  # 不包括当前阶段


if __name__ == "__main__":
    pytest.main([__file__])