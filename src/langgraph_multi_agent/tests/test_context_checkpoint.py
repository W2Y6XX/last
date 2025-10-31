"""工作流上下文和检查点测试"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from langgraph_multi_agent.core.context import WorkflowContextManager, PhaseMetrics
from langgraph_multi_agent.core.checkpoint import (
    CheckpointManager,
    MemoryCheckpointStorage,
    SQLiteCheckpointStorage
)
from langgraph_multi_agent.core.state import (
    create_initial_state,
    WorkflowPhase
)


class TestWorkflowContext:
    """工作流上下文测试类"""
    
    def test_context_creation(self):
        """测试上下文创建"""
        manager = WorkflowContextManager()
        context = manager.create_context(WorkflowPhase.INITIALIZATION)
        
        assert context["current_phase"] == WorkflowPhase.INITIALIZATION
        assert len(context["completed_phases"]) == 0
        assert len(context["agent_results"]) == 0
        assert context["coordination_plan"] is None
        assert WorkflowPhase.INITIALIZATION.value in context["phase_start_times"]
    
    def test_phase_transition(self):
        """测试阶段转换"""
        manager = WorkflowContextManager()
        context = manager.create_context(WorkflowPhase.INITIALIZATION)
        
        # 转换到分析阶段
        updated_context = manager.transition_phase(
            context,
            WorkflowPhase.ANALYSIS,
            {"transition_reason": "task_complexity_analysis"}
        )
        
        assert updated_context["current_phase"] == WorkflowPhase.ANALYSIS
        assert WorkflowPhase.INITIALIZATION in updated_context["completed_phases"]
        assert WorkflowPhase.ANALYSIS.value in updated_context["phase_start_times"]
        assert WorkflowPhase.INITIALIZATION.value in updated_context["phase_durations"]
        assert updated_context["execution_metadata"]["transition_reason"] == "task_complexity_analysis"
    
    def test_agent_result_addition(self):
        """测试智能体结果添加"""
        manager = WorkflowContextManager()
        context = manager.create_context(WorkflowPhase.ANALYSIS)
        
        # 添加智能体结果
        result = {"complexity_score": 0.8, "requires_decomposition": True}
        updated_context = manager.add_agent_result(
            context,
            "meta_agent",
            result,
            execution_time=12.5
        )
        
        assert "meta_agent" in updated_context["agent_results"]
        agent_result = updated_context["agent_results"]["meta_agent"]
        assert agent_result["result"] == result
        assert agent_result["execution_time"] == 12.5
        assert agent_result["phase"] == WorkflowPhase.ANALYSIS.value
    
    def test_coordination_plan(self):
        """测试协调计划设置"""
        manager = WorkflowContextManager()
        context = manager.create_context(WorkflowPhase.COORDINATION)
        
        plan = {
            "strategy": "parallel_execution",
            "agents": ["agent_1", "agent_2"],
            "estimated_duration": 300
        }
        
        updated_context = manager.set_coordination_plan(context, plan)
        
        assert updated_context["coordination_plan"] is not None
        assert updated_context["coordination_plan"]["strategy"] == "parallel_execution"
        assert "created_at" in updated_context["coordination_plan"]
        assert updated_context["coordination_plan"]["phase"] == WorkflowPhase.COORDINATION.value
    
    def test_error_recording(self):
        """测试错误记录"""
        manager = WorkflowContextManager()
        context = manager.create_context(WorkflowPhase.EXECUTION)
        
        updated_context = manager.record_error(
            context,
            "AgentTimeoutError",
            "智能体执行超时"
        )
        
        assert "errors" in updated_context["execution_metadata"]
        errors = updated_context["execution_metadata"]["errors"]
        assert len(errors) == 1
        assert errors[0]["error_type"] == "AgentTimeoutError"
        assert errors[0]["phase"] == WorkflowPhase.EXECUTION.value
    
    def test_efficiency_metrics(self):
        """测试效率指标计算"""
        manager = WorkflowContextManager()
        context = manager.create_context(WorkflowPhase.INITIALIZATION)
        
        # 模拟完整的工作流程
        context = manager.transition_phase(context, WorkflowPhase.ANALYSIS)
        context = manager.add_agent_result(context, "meta_agent", {"result": "analysis_done"}, 10.0)
        
        context = manager.transition_phase(context, WorkflowPhase.EXECUTION)
        context = manager.add_agent_result(context, "executor", {"result": "execution_done"}, 20.0)
        
        metrics = manager.calculate_efficiency_metrics(context)
        
        assert "total_duration" in metrics
        assert "average_phase_duration" in metrics
        assert "agent_efficiency" in metrics
        assert metrics["total_duration"] > 0
        assert metrics["agent_efficiency"] > 0
    
    def test_phase_summary(self):
        """测试阶段摘要"""
        manager = WorkflowContextManager()
        context = manager.create_context(WorkflowPhase.INITIALIZATION)
        
        # 添加一些数据
        context = manager.transition_phase(context, WorkflowPhase.ANALYSIS)
        context = manager.add_agent_result(context, "meta_agent", {"result": "done"})
        context = manager.set_coordination_plan(context, {"strategy": "test"})
        
        summary = manager.get_phase_summary(context)
        
        assert summary["current_phase"] == WorkflowPhase.ANALYSIS.value
        assert len(summary["completed_phases"]) == 1
        assert summary["agent_results_count"] == 1
        assert summary["has_coordination_plan"] is True
        assert "phase_details" in summary


class TestCheckpointStorage:
    """检查点存储测试类"""
    
    @pytest.mark.asyncio
    async def test_memory_storage(self):
        """测试内存存储"""
        storage = MemoryCheckpointStorage()
        state = create_initial_state("测试任务", "测试描述")
        
        # 保存检查点
        success = await storage.save_checkpoint("test_cp_001", state, {"test": "metadata"})
        assert success is True
        
        # 加载检查点
        loaded_state = await storage.load_checkpoint("test_cp_001")
        assert loaded_state is not None
        assert loaded_state["task_state"]["title"] == "测试任务"
        
        # 列出检查点
        checkpoints = await storage.list_checkpoints()
        assert len(checkpoints) == 1
        assert checkpoints[0]["checkpoint_id"] == "test_cp_001"
        
        # 删除检查点
        deleted = await storage.delete_checkpoint("test_cp_001")
        assert deleted is True
        
        # 验证删除
        loaded_state = await storage.load_checkpoint("test_cp_001")
        assert loaded_state is None
    
    @pytest.mark.asyncio
    async def test_sqlite_storage(self):
        """测试SQLite存储"""
        # 使用临时目录
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_checkpoints.db")
        
        try:
            storage = SQLiteCheckpointStorage(db_path)
            state = create_initial_state("测试任务", "测试描述")
            
            # 保存检查点
            success = await storage.save_checkpoint("test_cp_002", state, {"test": "metadata"})
            assert success is True
            
            # 加载检查点
            loaded_state = await storage.load_checkpoint("test_cp_002")
            assert loaded_state is not None
            assert loaded_state["task_state"]["title"] == "测试任务"
            
            # 列出检查点
            checkpoints = await storage.list_checkpoints()
            assert len(checkpoints) == 1
            assert checkpoints[0]["checkpoint_id"] == "test_cp_002"
            
            # 删除检查点
            deleted = await storage.delete_checkpoint("test_cp_002")
            assert deleted is True
            
        finally:
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


class TestCheckpointManager:
    """检查点管理器测试类"""
    
    @pytest.mark.asyncio
    async def test_checkpoint_creation(self):
        """测试检查点创建"""
        manager = CheckpointManager("memory")
        state = create_initial_state("测试任务", "测试描述")
        
        # 创建检查点
        checkpoint_id = await manager.create_checkpoint(
            state,
            metadata={"created_by": "test"}
        )
        
        assert checkpoint_id is not None
        assert state["checkpoint_data"] is not None
        assert state["checkpoint_data"]["checkpoint_id"] == checkpoint_id
    
    @pytest.mark.asyncio
    async def test_checkpoint_restoration(self):
        """测试检查点恢复"""
        manager = CheckpointManager("memory")
        state = create_initial_state("测试任务", "测试描述")
        
        # 创建检查点
        checkpoint_id = await manager.create_checkpoint(state)
        
        # 恢复检查点
        restored_state = await manager.restore_checkpoint(checkpoint_id)
        
        assert restored_state is not None
        assert restored_state["task_state"]["title"] == "测试任务"
        assert restored_state["checkpoint_data"]["checkpoint_id"] == checkpoint_id
    
    @pytest.mark.asyncio
    async def test_checkpoint_listing(self):
        """测试检查点列表"""
        manager = CheckpointManager("memory")
        state = create_initial_state("测试任务", "测试描述")
        task_id = state["task_state"]["task_id"]
        
        # 创建多个检查点
        cp1 = await manager.create_checkpoint(state, metadata={"version": 1})
        cp2 = await manager.create_checkpoint(state, metadata={"version": 2})
        
        # 列出检查点
        checkpoints = await manager.list_task_checkpoints(task_id)
        
        assert len(checkpoints) == 2
        checkpoint_ids = [cp["checkpoint_id"] for cp in checkpoints]
        assert cp1 in checkpoint_ids
        assert cp2 in checkpoint_ids
    
    @pytest.mark.asyncio
    async def test_auto_checkpoint_decision(self):
        """测试自动检查点决策"""
        manager = CheckpointManager("memory")
        state = create_initial_state("测试任务", "测试描述")
        
        # 在关键阶段应该创建检查点
        from langgraph_multi_agent.core.state import update_workflow_phase
        state = update_workflow_phase(state, WorkflowPhase.ANALYSIS)
        
        should_create = await manager.should_create_checkpoint(state)
        assert should_create is True
        
        # 创建检查点后，短时间内不应该再创建
        await manager.create_checkpoint(state)
        should_create_again = await manager.should_create_checkpoint(state)
        assert should_create_again is False


if __name__ == "__main__":
    pytest.main([__file__])