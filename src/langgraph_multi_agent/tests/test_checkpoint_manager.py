"""检查点管理器测试"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from langgraph_multi_agent.workflow.checkpoint_manager import (
    CheckpointManager,
    MemoryCheckpointStorage,
    SQLiteCheckpointStorage,
    CheckpointStorage,
    CheckpointData
)
from langgraph_multi_agent.core.state import (
    create_initial_state,
    LangGraphTaskState,
    WorkflowPhase
)

from langgraph_multi_agent.legacy.task_state import TaskStatus


class TestMemoryCheckpointStorage:
    """内存检查点存储测试"""
    
    @pytest.mark.asyncio
    async def test_storage_initialization(self):
        """测试存储初始化"""
        storage = MemoryCheckpointStorage()
        
        assert len(storage.checkpoints) == 0
        assert storage.lock is not None
    
    @pytest.mark.asyncio
    async def test_save_and_load_checkpoint(self):
        """测试保存和加载检查点"""
        storage = MemoryCheckpointStorage()
        thread_id = "test_thread_123"
        
        # 创建测试状态
        state = create_initial_state("测试任务", "测试描述")
        checkpoint_data = CheckpointData(
            checkpoint_id="checkpoint_001",
            timestamp=datetime.now(),
            state=state,
            metadata={"test": "data"}
        )
        
        # 保存检查点
        success = await storage.save_checkpoint(thread_id, checkpoint_data)
        assert success is True
        assert thread_id in storage.checkpoints
        assert len(storage.checkpoints[thread_id]) == 1
        
        # 加载最新检查点
        loaded_checkpoint = await storage.load_checkpoint(thread_id)
        assert loaded_checkpoint is not None
        assert loaded_checkpoint.checkpoint_id == "checkpoint_001"
        assert loaded_checkpoint.state["task_state"]["title"] == "测试任务"
        assert loaded_checkpoint.metadata["test"] == "data"
        
        # 加载指定检查点
        specific_checkpoint = await storage.load_checkpoint(thread_id, "checkpoint_001")
        assert specific_checkpoint is not None
        assert specific_checkpoint.checkpoint_id == "checkpoint_001"
    
    @pytest.mark.asyncio
    async def test_multiple_checkpoints(self):
        """测试多个检查点"""
        storage = MemoryCheckpointStorage()
        thread_id = "test_thread_456"
        
        # 保存多个检查点
        for i in range(5):
            state = create_initial_state(f"任务{i}", f"描述{i}")
            checkpoint_data = CheckpointData(
                checkpoint_id=f"checkpoint_{i:03d}",
                timestamp=datetime.now(),
                state=state,
                metadata={"index": i}
            )
            
            success = await storage.save_checkpoint(thread_id, checkpoint_data)
            assert success is True
        
        # 验证检查点数量
        assert len(storage.checkpoints[thread_id]) == 5
        
        # 列出检查点
        checkpoints = await storage.list_checkpoints(thread_id, limit=3)
        assert len(checkpoints) == 3
        
        # 验证顺序（最新的在前）
        assert checkpoints[0].checkpoint_id == "checkpoint_004"
        assert checkpoints[1].checkpoint_id == "checkpoint_003"
        assert checkpoints[2].checkpoint_id == "checkpoint_002"
    
    @pytest.mark.asyncio
    async def test_checkpoint_limit(self):
        """测试检查点数量限制"""
        storage = MemoryCheckpointStorage()
        thread_id = "test_thread_limit"
        
        # 保存超过限制的检查点
        for i in range(15):
            state = create_initial_state(f"任务{i}", f"描述{i}")
            checkpoint_data = CheckpointData(
                checkpoint_id=f"checkpoint_{i:03d}",
                timestamp=datetime.now(),
                state=state,
                metadata={"index": i}
            )
            
            await storage.save_checkpoint(thread_id, checkpoint_data)
        
        # 验证只保留最新的10个
        assert len(storage.checkpoints[thread_id]) == 10
        assert storage.checkpoints[thread_id][0].checkpoint_id == "checkpoint_005"
        assert storage.checkpoints[thread_id][-1].checkpoint_id == "checkpoint_014"
    
    @pytest.mark.asyncio
    async def test_delete_checkpoint(self):
        """测试删除检查点"""
        storage = MemoryCheckpointStorage()
        thread_id = "test_thread_delete"
        
        # 保存检查点
        state = create_initial_state("测试任务", "测试描述")
        checkpoint_data = CheckpointData(
            checkpoint_id="checkpoint_to_delete",
            timestamp=datetime.now(),
            state=state,
            metadata={}
        )
        
        await storage.save_checkpoint(thread_id, checkpoint_data)
        assert len(storage.checkpoints[thread_id]) == 1
        
        # 删除检查点
        success = await storage.delete_checkpoint(thread_id, "checkpoint_to_delete")
        assert success is True
        assert len(storage.checkpoints[thread_id]) == 0
        
        # 删除不存在的检查点
        success = await storage.delete_checkpoint(thread_id, "nonexistent")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_cleanup_old_checkpoints(self):
        """测试清理旧检查点"""
        storage = MemoryCheckpointStorage()
        
        # 创建新旧检查点
        old_time = datetime.now() - timedelta(days=2)
        new_time = datetime.now()
        
        # 旧检查点
        old_state = create_initial_state("旧任务", "旧描述")
        old_checkpoint = CheckpointData(
            checkpoint_id="old_checkpoint",
            timestamp=old_time,
            state=old_state,
            metadata={}
        )
        
        # 新检查点
        new_state = create_initial_state("新任务", "新描述")
        new_checkpoint = CheckpointData(
            checkpoint_id="new_checkpoint",
            timestamp=new_time,
            state=new_state,
            metadata={}
        )
        
        await storage.save_checkpoint("thread1", old_checkpoint)
        await storage.save_checkpoint("thread2", new_checkpoint)
        
        # 清理1天前的检查点
        cutoff_time = datetime.now() - timedelta(days=1)
        cleaned_count = await storage.cleanup_old_checkpoints(cutoff_time)
        
        assert cleaned_count == 1
        assert len(storage.checkpoints["thread1"]) == 0
        assert len(storage.checkpoints["thread2"]) == 1


class TestSQLiteCheckpointStorage:
    """SQLite检查点存储测试"""
    
    @pytest.mark.asyncio
    async def test_storage_initialization(self):
        """测试存储初始化"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            storage = SQLiteCheckpointStorage(db_path)
            
            # 验证数据库文件存在
            assert os.path.exists(db_path)
            
            # 验证表结构
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='checkpoints'
                """)
                assert cursor.fetchone() is not None
                
        finally:
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except PermissionError:
                # Windows文件锁定问题，忽略
                pass
    
    @pytest.mark.asyncio
    async def test_save_and_load_checkpoint(self):
        """测试保存和加载检查点"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            storage = SQLiteCheckpointStorage(db_path)
            thread_id = "sqlite_test_thread"
            
            # 创建测试状态
            state = create_initial_state("SQLite测试任务", "SQLite测试描述")
            checkpoint_data = CheckpointData(
                checkpoint_id="sqlite_checkpoint_001",
                timestamp=datetime.now(),
                state=state,
                metadata={"storage": "sqlite", "test": True}
            )
            
            # 保存检查点
            success = await storage.save_checkpoint(thread_id, checkpoint_data)
            assert success is True
            
            # 加载检查点
            loaded_checkpoint = await storage.load_checkpoint(thread_id)
            assert loaded_checkpoint is not None
            assert loaded_checkpoint.checkpoint_id == "sqlite_checkpoint_001"
            assert loaded_checkpoint.state["task_state"]["title"] == "SQLite测试任务"
            assert loaded_checkpoint.metadata["storage"] == "sqlite"
            assert loaded_checkpoint.metadata["test"] is True
            
        finally:
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except PermissionError:
                # Windows文件锁定问题，忽略
                pass
    
    @pytest.mark.asyncio
    async def test_checkpoint_replacement(self):
        """测试检查点替换"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            storage = SQLiteCheckpointStorage(db_path)
            thread_id = "replacement_test"
            checkpoint_id = "same_checkpoint_id"
            
            # 保存第一个检查点
            state1 = create_initial_state("任务1", "描述1")
            checkpoint1 = CheckpointData(
                checkpoint_id=checkpoint_id,
                timestamp=datetime.now(),
                state=state1,
                metadata={"version": 1}
            )
            
            await storage.save_checkpoint(thread_id, checkpoint1)
            
            # 保存相同ID的检查点（应该替换）
            state2 = create_initial_state("任务2", "描述2")
            checkpoint2 = CheckpointData(
                checkpoint_id=checkpoint_id,
                timestamp=datetime.now(),
                state=state2,
                metadata={"version": 2}
            )
            
            await storage.save_checkpoint(thread_id, checkpoint2)
            
            # 验证只有最新的检查点
            loaded = await storage.load_checkpoint(thread_id, checkpoint_id)
            assert loaded is not None
            assert loaded.state["task_state"]["title"] == "任务2"
            assert loaded.metadata["version"] == 2
            
            # 验证检查点列表只有一个
            checkpoints = await storage.list_checkpoints(thread_id)
            assert len(checkpoints) == 1
            
        finally:
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except PermissionError:
                # Windows文件锁定问题，忽略
                pass


class TestCheckpointManager:
    """检查点管理器测试"""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = CheckpointManager()
        
        assert isinstance(manager.storage, MemoryCheckpointStorage)
        assert manager.auto_checkpoint_interval == 300
        assert manager.max_checkpoints_per_thread == 50
        assert len(manager.active_threads) == 0
        assert len(manager.paused_threads) == 0
        assert manager.checkpoint_stats["total_checkpoints"] == 0
    
    @pytest.mark.asyncio
    async def test_create_and_load_checkpoint(self):
        """测试创建和加载检查点"""
        manager = CheckpointManager()
        thread_id = "manager_test_thread"
        
        # 创建测试状态
        state = create_initial_state("管理器测试任务", "管理器测试描述")
        state["task_state"]["status"] = TaskStatus.IN_PROGRESS
        
        # 创建检查点
        checkpoint_id = await manager.create_checkpoint(
            thread_id=thread_id,
            state=state,
            metadata={"test": "manager"}
        )
        
        assert checkpoint_id is not None
        assert manager.checkpoint_stats["total_checkpoints"] == 1
        assert manager.checkpoint_stats["successful_saves"] == 1
        assert thread_id in manager.last_checkpoint_times
        
        # 加载检查点
        loaded_state = await manager.load_checkpoint(thread_id)
        assert loaded_state is not None
        assert loaded_state["task_state"]["title"] == "管理器测试任务"
        assert loaded_state["task_state"]["status"] == TaskStatus.IN_PROGRESS
        assert manager.checkpoint_stats["successful_loads"] == 1
    
    @pytest.mark.asyncio
    async def test_pause_and_resume_execution(self):
        """测试暂停和恢复执行"""
        manager = CheckpointManager()
        thread_id = "pause_resume_test"
        
        # 创建测试状态
        state = create_initial_state("暂停恢复测试", "测试暂停和恢复功能")
        state["workflow_context"]["current_phase"] = WorkflowPhase.EXECUTION
        
        # 暂停执行
        success = await manager.pause_execution(thread_id, state)
        assert success is True
        assert manager.is_thread_paused(thread_id) is True
        assert thread_id in manager.get_paused_threads()
        
        # 恢复执行
        resumed_state = await manager.resume_execution(thread_id)
        assert resumed_state is not None
        assert resumed_state["task_state"]["title"] == "暂停恢复测试"
        assert "resumed_at" in resumed_state["workflow_context"]["execution_metadata"]
        assert manager.is_thread_paused(thread_id) is False
        assert manager.checkpoint_stats["recovery_operations"] == 1
    
    @pytest.mark.asyncio
    async def test_rollback_to_checkpoint(self):
        """测试回滚到检查点"""
        manager = CheckpointManager()
        thread_id = "rollback_test"
        
        # 创建初始状态
        initial_state = create_initial_state("回滚测试", "初始状态")
        initial_state["task_state"]["status"] = TaskStatus.PENDING
        
        # 创建第一个检查点
        checkpoint_id_1 = await manager.create_checkpoint(thread_id, initial_state)
        assert checkpoint_id_1 is not None
        
        # 修改状态并创建第二个检查点
        import copy
        modified_state = copy.deepcopy(initial_state)
        modified_state["task_state"]["status"] = TaskStatus.IN_PROGRESS
        modified_state["task_state"]["description"] = "修改后的状态"
        
        checkpoint_id_2 = await manager.create_checkpoint(thread_id, modified_state)
        assert checkpoint_id_2 is not None
        
        # 回滚到第一个检查点
        rolled_back_state = await manager.rollback_to_checkpoint(thread_id, checkpoint_id_1)
        assert rolled_back_state is not None
        assert rolled_back_state["task_state"]["status"] == TaskStatus.PENDING
        assert rolled_back_state["task_state"]["description"] == "初始状态"
        assert "rolled_back_at" in rolled_back_state["workflow_context"]["execution_metadata"]
        assert manager.checkpoint_stats["recovery_operations"] == 1
    
    @pytest.mark.asyncio
    async def test_should_create_checkpoint(self):
        """测试检查点创建判断"""
        manager = CheckpointManager(auto_checkpoint_interval=60)  # 1分钟间隔
        thread_id = "checkpoint_decision_test"
        
        # 创建测试状态
        state = create_initial_state("检查点判断测试", "测试描述")
        state["workflow_context"]["current_phase"] = WorkflowPhase.ANALYSIS
        
        # 第一次应该创建检查点（没有历史记录）
        should_create = await manager.should_create_checkpoint(thread_id, state)
        assert should_create is True
        
        # 更新线程状态
        await manager.update_thread_state(thread_id, state)
        manager.last_checkpoint_times[thread_id] = datetime.now()
        
        # 短时间内不应该创建检查点
        should_create = await manager.should_create_checkpoint(thread_id, state)
        assert should_create is False
        
        # 阶段变化应该创建检查点
        state["workflow_context"]["current_phase"] = WorkflowPhase.DECOMPOSITION
        should_create = await manager.should_create_checkpoint(thread_id, state)
        assert should_create is True
        
        # 更新状态
        await manager.update_thread_state(thread_id, state)
        
        # 任务状态变化应该创建检查点
        state["task_state"]["status"] = TaskStatus.IN_PROGRESS
        should_create = await manager.should_create_checkpoint(thread_id, state)
        assert should_create is True
    
    @pytest.mark.asyncio
    async def test_list_and_delete_checkpoints(self):
        """测试列出和删除检查点"""
        manager = CheckpointManager()
        thread_id = "list_delete_test"
        
        # 创建多个检查点
        checkpoint_ids = []
        for i in range(3):
            state = create_initial_state(f"任务{i}", f"描述{i}")
            checkpoint_id = await manager.create_checkpoint(
                thread_id=thread_id,
                state=state,
                metadata={"index": i}
            )
            checkpoint_ids.append(checkpoint_id)
        
        # 列出检查点
        checkpoints = await manager.list_thread_checkpoints(thread_id)
        assert len(checkpoints) == 3
        
        # 验证检查点信息
        for i, checkpoint in enumerate(checkpoints):
            assert "checkpoint_id" in checkpoint
            assert "timestamp" in checkpoint
            assert "metadata" in checkpoint
            assert checkpoint["metadata"]["index"] in [0, 1, 2]
        
        # 删除一个检查点
        success = await manager.delete_thread_checkpoint(thread_id, checkpoint_ids[0])
        assert success is True
        
        # 验证删除后的列表
        remaining_checkpoints = await manager.list_thread_checkpoints(thread_id)
        assert len(remaining_checkpoints) == 2
    
    @pytest.mark.asyncio
    async def test_cleanup_old_checkpoints(self):
        """测试清理旧检查点"""
        manager = CheckpointManager()
        
        # 使用mock来模拟旧检查点
        with patch.object(manager.storage, 'cleanup_old_checkpoints', return_value=5):
            cleaned_count = await manager.cleanup_old_checkpoints(days_old=7)
            assert cleaned_count == 5
    
    def test_checkpoint_statistics(self):
        """测试检查点统计"""
        manager = CheckpointManager()
        
        # 模拟一些统计数据
        manager.checkpoint_stats["total_checkpoints"] = 10
        manager.checkpoint_stats["successful_saves"] = 9
        manager.checkpoint_stats["failed_saves"] = 1
        manager.checkpoint_stats["successful_loads"] = 8
        manager.checkpoint_stats["failed_loads"] = 2
        manager.checkpoint_stats["recovery_operations"] = 3
        
        manager.active_threads["thread1"] = {}
        manager.active_threads["thread2"] = {}
        manager.paused_threads["thread3"] = Mock()
        
        stats = manager.get_checkpoint_statistics()
        
        assert stats["total_checkpoints"] == 10
        assert stats["successful_saves"] == 9
        assert stats["failed_saves"] == 1
        assert stats["active_threads"] == 2
        assert stats["paused_threads"] == 1
        assert stats["success_rate"] == 0.9
        assert stats["load_success_rate"] == 0.8
        assert stats["recovery_operations"] == 3
    
    @pytest.mark.asyncio
    async def test_thread_state_management(self):
        """测试线程状态管理"""
        manager = CheckpointManager()
        thread_id = "state_management_test"
        
        # 创建测试状态
        state = create_initial_state("状态管理测试", "测试描述")
        state["workflow_context"]["current_phase"] = WorkflowPhase.ANALYSIS
        state["task_state"]["status"] = TaskStatus.IN_PROGRESS
        state["workflow_context"]["agent_results"]["agent1"] = {"result": "test"}
        
        # 更新线程状态
        await manager.update_thread_state(thread_id, state)
        
        # 验证状态记录
        assert thread_id in manager.active_threads
        thread_state = manager.active_threads[thread_id]
        assert thread_state["last_phase"] == WorkflowPhase.ANALYSIS
        assert thread_state["last_status"] == TaskStatus.IN_PROGRESS
        assert thread_state["agent_count"] == 1
        assert "last_update" in thread_state
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理"""
        # 使用会失败的存储
        failing_storage = Mock(spec=CheckpointStorage)
        failing_storage.save_checkpoint.return_value = False
        failing_storage.load_checkpoint.return_value = None
        
        manager = CheckpointManager(storage=failing_storage)
        thread_id = "error_test"
        
        # 测试保存失败
        state = create_initial_state("错误测试", "测试描述")
        checkpoint_id = await manager.create_checkpoint(thread_id, state)
        assert checkpoint_id is None
        assert manager.checkpoint_stats["failed_saves"] == 1
        
        # 测试加载失败
        loaded_state = await manager.load_checkpoint(thread_id)
        assert loaded_state is None
        assert manager.checkpoint_stats["failed_loads"] == 1


class TestIntegrationScenarios:
    """集成场景测试"""
    
    @pytest.mark.asyncio
    async def test_workflow_checkpoint_integration(self):
        """测试工作流检查点集成"""
        manager = CheckpointManager(auto_checkpoint_interval=1)  # 1秒间隔
        thread_id = "workflow_integration_test"
        
        # 模拟工作流执行过程
        # 1. 分析阶段
        state = create_initial_state("集成测试工作流", "测试完整的工作流检查点")
        state["workflow_context"]["current_phase"] = WorkflowPhase.ANALYSIS
        state["task_state"]["status"] = TaskStatus.IN_PROGRESS
        
        # 创建分析阶段检查点
        analysis_checkpoint = await manager.create_checkpoint(thread_id, state, {"phase": "analysis"})
        assert analysis_checkpoint is not None
        
        # 更新线程状态
        await manager.update_thread_state(thread_id, state)
        
        # 2. 分解阶段
        import copy
        state = copy.deepcopy(state)
        state["workflow_context"]["current_phase"] = WorkflowPhase.DECOMPOSITION
        state["workflow_context"]["agent_results"]["meta_agent"] = {
            "result": {"analysis": "complex task", "requires_decomposition": True}
        }
        
        # 应该创建检查点（阶段变化）
        should_create = await manager.should_create_checkpoint(thread_id, state)
        assert should_create is True
        
        decomposition_checkpoint = await manager.create_checkpoint(thread_id, state, {"phase": "decomposition"})
        assert decomposition_checkpoint is not None
        
        # 3. 协调阶段
        state = copy.deepcopy(state)
        state["workflow_context"]["current_phase"] = WorkflowPhase.COORDINATION
        state["task_state"]["subtasks"] = [
            {"id": "subtask1", "title": "子任务1", "status": "pending"},
            {"id": "subtask2", "title": "子任务2", "status": "pending"}
        ]
        
        coordination_checkpoint = await manager.create_checkpoint(thread_id, state, {"phase": "coordination"})
        assert coordination_checkpoint is not None
        
        # 4. 执行阶段
        state = copy.deepcopy(state)
        state["workflow_context"]["current_phase"] = WorkflowPhase.EXECUTION
        state["workflow_context"]["agent_results"]["coordinator"] = {
            "result": {"coordination_plan": "parallel execution"}
        }
        
        execution_checkpoint = await manager.create_checkpoint(thread_id, state, {"phase": "execution"})
        assert execution_checkpoint is not None
        
        # 验证检查点历史
        checkpoints = await manager.list_thread_checkpoints(thread_id)
        assert len(checkpoints) == 4
        
        # 验证可以回滚到任意阶段
        analysis_state = await manager.rollback_to_checkpoint(thread_id, analysis_checkpoint)
        assert analysis_state is not None
        assert analysis_state["workflow_context"]["current_phase"] == WorkflowPhase.ANALYSIS
        
        # 验证统计信息
        stats = manager.get_checkpoint_statistics()
        assert stats["total_checkpoints"] == 4
        assert stats["recovery_operations"] == 1
    
    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self):
        """测试错误恢复场景"""
        manager = CheckpointManager()
        thread_id = "error_recovery_test"
        
        # 1. 正常执行并创建检查点
        state = create_initial_state("错误恢复测试", "测试错误恢复机制")
        state["workflow_context"]["current_phase"] = WorkflowPhase.EXECUTION
        state["task_state"]["status"] = TaskStatus.IN_PROGRESS
        
        good_checkpoint = await manager.create_checkpoint(thread_id, state, {"status": "good"})
        assert good_checkpoint is not None
        
        # 2. 模拟错误状态
        import copy
        error_state = copy.deepcopy(state)
        error_state["task_state"]["status"] = TaskStatus.FAILED
        error_state["error_state"] = {
            "error": "执行失败",
            "timestamp": datetime.now().isoformat(),
            "retry_count": 0
        }
        
        error_checkpoint = await manager.create_checkpoint(thread_id, error_state, {"status": "error"})
        assert error_checkpoint is not None
        
        # 3. 恢复到正常状态
        recovered_state = await manager.rollback_to_checkpoint(thread_id, good_checkpoint)
        assert recovered_state is not None
        assert recovered_state["task_state"]["status"] == TaskStatus.IN_PROGRESS
        assert "error_state" not in recovered_state or not recovered_state.get("error_state")
        
        # 4. 验证恢复信息
        assert "rolled_back_at" in recovered_state["workflow_context"]["execution_metadata"]
        assert recovered_state["workflow_context"]["execution_metadata"]["rollback_to_checkpoint"] == good_checkpoint
    
    @pytest.mark.asyncio
    async def test_concurrent_checkpoint_operations(self):
        """测试并发检查点操作"""
        manager = CheckpointManager()
        
        # 创建多个并发任务
        async def create_checkpoints_for_thread(thread_id: str, count: int):
            checkpoints = []
            for i in range(count):
                state = create_initial_state(f"并发任务{thread_id}_{i}", f"描述{i}")
                checkpoint_id = await manager.create_checkpoint(
                    thread_id=thread_id,
                    state=state,
                    metadata={"thread": thread_id, "index": i}
                )
                if checkpoint_id:
                    checkpoints.append(checkpoint_id)
                # 小延迟模拟真实场景
                await asyncio.sleep(0.01)
            return checkpoints
        
        # 并发执行
        tasks = [
            create_checkpoints_for_thread(f"thread_{i}", 5)
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 验证结果
        for i, checkpoints in enumerate(results):
            assert len(checkpoints) == 5
            thread_id = f"thread_{i}"
            
            # 验证每个线程的检查点
            thread_checkpoints = await manager.list_thread_checkpoints(thread_id)
            assert len(thread_checkpoints) == 5
        
        # 验证总统计
        stats = manager.get_checkpoint_statistics()
        assert stats["total_checkpoints"] == 15
        assert stats["successful_saves"] == 15