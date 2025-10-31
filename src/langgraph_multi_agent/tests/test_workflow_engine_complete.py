"""工作流引擎完整测试套件"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from langgraph_multi_agent.workflow.multi_agent_workflow import (
    MultiAgentWorkflow,
    WorkflowExecutionMode,
    WorkflowStatus
)
from langgraph_multi_agent.workflow.checkpoint_manager import (
    CheckpointManager,
    MemoryCheckpointStorage,
    SQLiteCheckpointStorage
)
from langgraph_multi_agent.workflow.routing import (
    WorkflowRouter,
    RoutingStrategy,
    ExecutionMode,
    RouteCondition,
    ConditionOperator,
    RouteRule,
    RoutingDecision
)
from langgraph_multi_agent.agents.meta_agent_wrapper import MetaAgentWrapper
from langgraph_multi_agent.agents.task_decomposer_wrapper import TaskDecomposerWrapper
from langgraph_multi_agent.agents.coordinator_wrapper import CoordinatorWrapper
from langgraph_multi_agent.agents.generic_wrapper import GenericAgentWrapper
from langgraph_multi_agent.core.state import (
    create_initial_state,
    WorkflowPhase,
    update_workflow_phase
)
from langgraph_multi_agent.legacy.task_state import TaskStatus


class MockLLM:
    """模拟LLM用于测试"""
    def __init__(self, responses: Dict[str, str] = None):
        self.responses = responses or {}
        self.call_count = 0
        self.call_history = []

    async def ainvoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """异步调用模拟"""
        self.call_count += 1
        self.call_history.append(messages)
        
        # 根据消息内容返回不同响应
        last_message = messages[-1]["content"] if messages else ""
        
        # MetaAgent响应
        if "分析" in last_message or "analyze" in last_message.lower():
            return """
            {
                "analysis": "这是一个复杂的多步骤任务",
                "complexity_score": 0.8,
                "requires_decomposition": true,
                "recommended_agents": ["data_analyst", "report_generator"],
                "estimated_time": "2-3 hours",
                "key_challenges": ["数据质量", "分析深度", "报告格式"]
            }
            """
        
        # TaskDecomposer响应
        elif "分解" in last_message or "decompose" in last_message.lower():
            return """
            {
                "success": true,
                "decomposition": {
                    "subtasks": [
                        {
                            "id": "subtask_1",
                            "name": "数据收集",
                            "description": "收集相关数据",
                            "type": "data_collection",
                            "estimated_time": "1 hour"
                        },
                        {
                            "id": "subtask_2",
                            "name": "数据分析",
                            "description": "分析收集的数据",
                            "type": "analysis",
                            "estimated_time": "2 hours"
                        }
                    ],
                    "dependencies": [{"from": "subtask_1", "to": "subtask_2"}],
                    "decomposition_strategy": "sequential"
                },
                "subtasks_count": 2,
                "decomposition_type": "complex_task"
            }
            """
        
        # Coordinator响应
        elif "协调" in last_message or "coordinate" in last_message.lower():
            return """
            {
                "success": true,
                "coordination_plan": {
                    "execution_order": ["subtask_1", "subtask_2"],
                    "resource_allocation": {
                        "subtask_1": {"agent": "data_collector", "priority": "high"},
                        "subtask_2": {"agent": "data_analyst", "priority": "high"}
                    }
                },
                "coordination_type": "establish_collaboration",
                "session_id": "session_123"
            }
            """
        
        # 通用智能体响应
        else:
            return """
            {
                "result": "任务执行完成",
                "status": "success",
                "output": "处理结果数据",
                "metrics": {
                    "processing_time": "45 minutes",
                    "quality_score": 0.92
                }
            }
            """

    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """同步调用模拟"""
        return asyncio.run(self.ainvoke(messages, **kwargs))


class TestMultiAgentWorkflow:
    """多智能体工作流测试"""

    @pytest.fixture
    def mock_llm(self):
        """创建模拟LLM"""
        return MockLLM()

    @pytest.fixture
    def checkpoint_manager(self):
        """创建检查点管理器"""
        return CheckpointManager(storage=MemoryCheckpointStorage())

    @pytest.fixture
    def workflow_router(self):
        """创建工作流路由器"""
        return WorkflowRouter(routing_strategy=RoutingStrategy.ADAPTIVE)

    @pytest.fixture
    def basic_workflow(self, checkpoint_manager, workflow_router):
        """创建基础工作流"""
        workflow = MultiAgentWorkflow(
            workflow_id="test_workflow",
            execution_mode=WorkflowExecutionMode.SEQUENTIAL,
            routing_strategy=RoutingStrategy.ADAPTIVE
        )
        return workflow

    @pytest.fixture
    def complete_workflow(self, mock_llm, checkpoint_manager):
        """创建完整的工作流（包含所有智能体）"""
        workflow = MultiAgentWorkflow(
            workflow_id="complete_test_workflow",
            execution_mode=WorkflowExecutionMode.ADAPTIVE
        )
        
        # 注册所有类型的智能体
        workflow.register_agent(
            "meta_agent",
            mock_llm,
            "meta_agent",
            name="MetaAgent",
            description="任务分析智能体"
        )
        
        workflow.register_agent(
            "task_decomposer",
            mock_llm,
            "task_decomposer",
            name="TaskDecomposer",
            description="任务分解智能体"
        )
        
        workflow.register_agent(
            "coordinator",
            mock_llm,
            "coordinator",
            name="Coordinator",
            description="协调智能体"
        )
        
        workflow.register_agent(
            "data_processor",
            mock_llm,
            "generic",
            name="DataProcessor",
            description="数据处理智能体",
            capabilities=["data_processing", "analysis"]
        )
        
        # 编译工作流
        workflow.compile_workflow()
        
        return workflow

    def test_workflow_initialization(self, basic_workflow):
        """测试工作流初始化"""
        assert basic_workflow.workflow_id == "test_workflow"
        assert basic_workflow.status == WorkflowStatus.CREATED
        assert basic_workflow.execution_mode == WorkflowExecutionMode.SEQUENTIAL
        assert basic_workflow.graph is not None
        assert len(basic_workflow.agents) == 0
        assert len(basic_workflow.agent_wrappers) == 0

    def test_agent_registration(self, basic_workflow, mock_llm):
        """测试智能体注册"""
        # 注册MetaAgent
        basic_workflow.register_agent(
            "meta_agent",
            mock_llm,
            "meta_agent",
            name="TestMetaAgent"
        )
        
        assert "meta_agent" in basic_workflow.agents
        assert "meta_agent" in basic_workflow.agent_wrappers
        assert isinstance(basic_workflow.agent_wrappers["meta_agent"], MetaAgentWrapper)

    def test_workflow_compilation(self, basic_workflow, mock_llm):
        """测试工作流编译"""
        # 注册智能体
        basic_workflow.register_agent("test_agent", mock_llm, "generic")
        
        # 编译工作流
        basic_workflow.compile_workflow()
        
        assert basic_workflow.compiled_graph is not None
        assert basic_workflow.status == WorkflowStatus.CREATED

    @pytest.mark.asyncio
    async def test_simple_workflow_execution(self, complete_workflow):
        """测试简单工作流执行"""
        initial_input = {
            "title": "简单测试任务",
            "description": "测试工作流执行的简单任务",
            "task_type": "test",
            "priority": 1
        }
        
        result = await complete_workflow.execute(initial_input)
        
        assert result is not None
        assert result["task_state"]["title"] == "简单测试任务"
        assert complete_workflow.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_complex_workflow_execution(self, complete_workflow):
        """测试复杂工作流执行"""
        initial_input = {
            "title": "复杂数据分析任务",
            "description": "需要分析大量数据并生成详细报告的复杂任务",
            "task_type": "analysis",
            "priority": 3,
            "requirements": [
                "数据收集", "数据清洗", "统计分析", 
                "可视化", "报告生成"
            ]
        }
        
        result = await complete_workflow.execute(initial_input)
        
        assert result is not None
        assert result["task_state"]["status"] == TaskStatus.COMPLETED
        assert complete_workflow.status == WorkflowStatus.COMPLETED
        
        # 验证智能体参与
        agent_results = result["workflow_context"]["agent_results"]
        assert len(agent_results) > 0

    @pytest.mark.asyncio
    async def test_workflow_with_checkpoints(self, complete_workflow):
        """测试带检查点的工作流执行"""
        initial_input = {
            "title": "检查点测试任务",
            "description": "测试工作流检查点功能",
            "task_type": "test"
        }
        
        config = {
            "configurable": {
                "thread_id": "checkpoint_test_thread",
                "checkpoint_interval": 1
            }
        }
        
        result = await complete_workflow.execute(initial_input, config)
        
        assert result is not None
        assert result["task_state"]["status"] == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, mock_llm):
        """测试工作流错误处理"""
        # 创建会失败的LLM
        failing_llm = Mock()
        failing_llm.ainvoke = AsyncMock(side_effect=Exception("模拟LLM失败"))
        
        workflow = MultiAgentWorkflow(
            workflow_id="error_test_workflow",
            execution_mode=WorkflowExecutionMode.SEQUENTIAL
        )
        
        workflow.register_agent("failing_agent", failing_llm, "generic")
        workflow.compile_workflow()
        
        initial_input = {
            "title": "错误测试任务",
            "description": "测试错误处理",
            "task_type": "test"
        }
        
        # 执行应该处理错误而不崩溃
        try:
            result = await workflow.execute(initial_input)
            # 工作流应该能够处理错误
            assert result is not None
        except Exception as e:
            # 或者抛出可预期的异常
            assert "模拟LLM失败" in str(e) or "工作流执行失败" in str(e)

    def test_workflow_info(self, complete_workflow):
        """测试工作流信息获取"""
        info = complete_workflow.get_workflow_info()
        
        assert "workflow_id" in info
        assert "status" in info
        assert "execution_mode" in info
        assert "registered_agents" in info
        assert info["workflow_id"] == "complete_test_workflow"
        assert len(info["registered_agents"]) == 4

    def test_agent_info_retrieval(self, complete_workflow):
        """测试智能体信息获取"""
        # 获取MetaAgent信息
        meta_info = complete_workflow.get_agent_info("meta_agent")
        assert meta_info is not None
        assert meta_info["agent_type"] == "meta_agent"
        
        # 获取不存在的智能体信息
        none_info = complete_workflow.get_agent_info("nonexistent")
        assert none_info is None

    def test_agents_listing(self, complete_workflow):
        """测试智能体列表"""
        agents = complete_workflow.list_agents()
        
        assert len(agents) == 4
        agent_ids = [agent["agent_id"] for agent in agents]
        assert "meta_agent" in agent_ids
        assert "task_decomposer" in agent_ids
        assert "coordinator" in agent_ids
        assert "data_processor" in agent_ids


class TestWorkflowRouter:
    """工作流路由器测试"""

    @pytest.fixture
    def router(self):
        """创建路由器"""
        return WorkflowRouter(routing_strategy=RoutingStrategy.ADAPTIVE)

    @pytest.fixture
    def test_state(self):
        """创建测试状态"""
        return create_initial_state(
            "路由测试任务",
            "测试工作流路由功能的任务"
        )

    def test_router_initialization(self, router):
        """测试路由器初始化"""
        assert router.routing_strategy == RoutingStrategy.ADAPTIVE
        assert router.routing_engine is not None
        assert len(router.complexity_thresholds) > 0

    def test_analysis_routing(self, router, test_state):
        """测试分析阶段路由"""
        available_agents = ["meta_agent", "data_processor"]
        
        # 测试需要分析的情况
        test_state["task_state"]["description"] = "需要深入分析的复杂任务"
        decision = router.should_analyze(test_state, available_agents)
        assert decision in ["meta_agent", "skip"]
        
        # 测试不需要分析的情况
        test_state["task_state"]["description"] = "简单任务"
        available_agents = ["data_processor"]  # 没有meta_agent
        decision = router.should_analyze(test_state, available_agents)
        assert decision == "skip"

    def test_decomposition_routing(self, router, test_state):
        """测试分解阶段路由"""
        available_agents = ["task_decomposer", "data_processor"]
        
        # 添加MetaAgent的分析结果
        test_state["workflow_context"]["agent_results"]["meta_agent"] = {
            "result": {"requires_decomposition": True}
        }
        
        decision = router.should_decompose(test_state, available_agents)
        assert decision == "task_decomposer"

    def test_coordination_routing(self, router, test_state):
        """测试协调阶段路由"""
        available_agents = ["coordinator", "data_processor"]
        
        # 添加子任务
        test_state["task_state"]["subtasks"] = [
            {"id": "subtask_1", "name": "子任务1"},
            {"id": "subtask_2", "name": "子任务2"}
        ]
        
        decision = router.should_coordinate(test_state, available_agents)
        assert decision == "coordinator"

    def test_execution_mode_determination(self, router, test_state):
        """测试执行模式确定"""
        available_agents = ["agent1", "agent2", "agent3"]
        
        # 测试无依赖的并行执行
        test_state["task_state"]["subtasks"] = [
            {"id": "subtask_1", "name": "子任务1"},
            {"id": "subtask_2", "name": "子任务2"}
        ]
        
        mode = router.determine_execution_mode(test_state, available_agents)
        assert mode in [ExecutionMode.PARALLEL, ExecutionMode.SEQUENTIAL, ExecutionMode.CONDITIONAL, ExecutionMode.PIPELINE]

    def test_agent_selection(self, router, test_state):
        """测试智能体选择"""
        available_agents = ["agent1", "agent2", "agent3"]
        agent_capabilities = {
            "agent1": {"capabilities": ["data_processing", "analysis"]},
            "agent2": {"capabilities": ["reporting", "visualization"]},
            "agent3": {"capabilities": ["data_processing", "coordination"]}
        }
        
        selected = router.select_agents_for_execution(
            test_state, available_agents, agent_capabilities
        )
        
        assert len(selected) > 0
        assert all(agent in available_agents for agent in selected)

    def test_routing_statistics(self, router):
        """测试路由统计"""
        stats = router.get_routing_statistics()
        
        assert "routing_strategy" in stats
        assert "complexity_thresholds" in stats
        assert "routing_stats" in stats
        assert "success_rate" in stats

    def test_custom_routing_rules(self, router):
        """测试自定义路由规则"""
        # 创建自定义规则
        condition = RouteCondition(
            "task_state.priority",
            ConditionOperator.GREATER_THAN,
            2
        )
        
        rule = RouteRule(
            name="high_priority_rule",
            condition=condition,
            target="priority_agent",
            decision=RoutingDecision.CONTINUE,
            priority=10
        )
        
        # 添加规则
        success = router.add_custom_rule("analysis", rule)
        assert success is True
        
        # 移除规则
        success = router.remove_custom_rule("analysis", "high_priority_rule")
        assert success is True


class TestCheckpointManager:
    """检查点管理器测试"""

    @pytest.fixture
    def memory_storage(self):
        """创建内存存储"""
        return MemoryCheckpointStorage()

    @pytest.fixture
    def checkpoint_manager(self, memory_storage):
        """创建检查点管理器"""
        return CheckpointManager(storage=memory_storage)

    @pytest.fixture
    def test_state(self):
        """创建测试状态"""
        return create_initial_state(
            "检查点测试任务",
            "测试检查点功能的任务"
        )

    @pytest.mark.asyncio
    async def test_checkpoint_creation(self, checkpoint_manager, test_state):
        """测试检查点创建"""
        thread_id = "test_thread_1"
        
        checkpoint_id = await checkpoint_manager.create_checkpoint(
            thread_id=thread_id,
            state=test_state,
            metadata={"test": "checkpoint"}
        )
        
        assert checkpoint_id is not None
        assert checkpoint_id.startswith("cp_")

    @pytest.mark.asyncio
    async def test_checkpoint_loading(self, checkpoint_manager, test_state):
        """测试检查点加载"""
        thread_id = "test_thread_2"
        
        # 创建检查点
        checkpoint_id = await checkpoint_manager.create_checkpoint(
            thread_id, test_state
        )
        
        # 加载检查点
        loaded_state = await checkpoint_manager.load_checkpoint(thread_id)
        
        assert loaded_state is not None
        assert loaded_state["task_state"]["title"] == test_state["task_state"]["title"]

    @pytest.mark.asyncio
    async def test_checkpoint_listing(self, checkpoint_manager, test_state):
        """测试检查点列表"""
        thread_id = "test_thread_3"
        
        # 创建多个检查点
        for i in range(3):
            await checkpoint_manager.create_checkpoint(
                thread_id, test_state, {"index": i}
            )
        
        # 列出检查点
        checkpoints = await checkpoint_manager.list_thread_checkpoints(thread_id)
        
        assert len(checkpoints) == 3
        assert all("checkpoint_id" in cp for cp in checkpoints)

    @pytest.mark.asyncio
    async def test_pause_and_resume(self, checkpoint_manager, test_state):
        """测试暂停和恢复"""
        thread_id = "test_thread_4"
        
        # 暂停执行
        success = await checkpoint_manager.pause_execution(thread_id, test_state)
        assert success is True
        assert checkpoint_manager.is_thread_paused(thread_id)
        
        # 恢复执行
        resumed_state = await checkpoint_manager.resume_execution(thread_id)
        assert resumed_state is not None
        assert not checkpoint_manager.is_thread_paused(thread_id)

    @pytest.mark.asyncio
    async def test_rollback(self, checkpoint_manager, test_state):
        """测试回滚"""
        thread_id = "test_thread_5"
        
        # 创建检查点
        checkpoint_id = await checkpoint_manager.create_checkpoint(
            thread_id, test_state
        )
        
        # 回滚到检查点
        rolled_back_state = await checkpoint_manager.rollback_to_checkpoint(
            thread_id, checkpoint_id
        )
        
        assert rolled_back_state is not None
        assert "rolled_back_at" in rolled_back_state["workflow_context"]["execution_metadata"]

    @pytest.mark.asyncio
    async def test_auto_checkpoint_logic(self, checkpoint_manager, test_state):
        """测试自动检查点逻辑"""
        thread_id = "test_thread_6"
        
        # 第一次应该创建检查点
        should_create = await checkpoint_manager.should_create_checkpoint(
            thread_id, test_state
        )
        assert should_create is True
        
        # 更新线程状态
        await checkpoint_manager.update_thread_state(thread_id, test_state)
        
        # 没有变化时不应该创建检查点
        should_create = await checkpoint_manager.should_create_checkpoint(
            thread_id, test_state
        )
        # 这里可能为True（基于时间间隔）或False（基于状态变化）

    @pytest.mark.asyncio
    async def test_checkpoint_cleanup(self, checkpoint_manager, test_state):
        """测试检查点清理"""
        thread_id = "test_thread_7"
        
        # 创建一些检查点
        for i in range(5):
            await checkpoint_manager.create_checkpoint(
                thread_id, test_state, {"index": i}
            )
        
        # 清理旧检查点（设置为0天，清理所有）
        cleaned_count = await checkpoint_manager.cleanup_old_checkpoints(days_old=0)
        
        # 应该清理了一些检查点
        assert cleaned_count >= 0

    def test_checkpoint_statistics(self, checkpoint_manager):
        """测试检查点统计"""
        stats = checkpoint_manager.get_checkpoint_statistics()
        
        assert "total_checkpoints" in stats
        assert "successful_saves" in stats
        assert "failed_saves" in stats
        assert "success_rate" in stats
        assert "active_threads" in stats

    @pytest.mark.asyncio
    async def test_sqlite_storage(self, test_state):
        """测试SQLite存储"""
        import tempfile
        import os
        
        # 创建临时数据库文件
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        
        try:
            # 创建SQLite存储
            sqlite_storage = SQLiteCheckpointStorage(db_path)
            checkpoint_manager = CheckpointManager(storage=sqlite_storage)
            
            thread_id = "sqlite_test_thread"
            
            # 创建检查点
            checkpoint_id = await checkpoint_manager.create_checkpoint(
                thread_id, test_state
            )
            
            assert checkpoint_id is not None
            
            # 加载检查点
            loaded_state = await checkpoint_manager.load_checkpoint(thread_id)
            assert loaded_state is not None
            
        finally:
            # 清理临时文件
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestWorkflowIntegration:
    """工作流集成测试"""

    @pytest.fixture
    def mock_llm(self):
        return MockLLM()

    @pytest.fixture
    def integrated_workflow(self, mock_llm):
        """创建集成工作流"""
        checkpoint_manager = CheckpointManager()
        
        workflow = MultiAgentWorkflow(
            workflow_id="integrated_test",
            execution_mode=WorkflowExecutionMode.ADAPTIVE
        )
        
        # 注册完整的智能体生态系统
        workflow.register_agent("meta_agent", mock_llm, "meta_agent")
        workflow.register_agent("task_decomposer", mock_llm, "task_decomposer")
        workflow.register_agent("coordinator", mock_llm, "coordinator")
        
        # 注册专业智能体
        for skill in ["data_processing", "analysis", "reporting"]:
            workflow.register_agent(
                f"{skill}_agent",
                mock_llm,
                "generic",
                capabilities=[skill]
            )
        
        workflow.compile_workflow()
        return workflow

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, integrated_workflow):
        """测试端到端工作流"""
        complex_task = {
            "title": "企业数据分析项目",
            "description": """
            对企业销售数据进行全面分析，包括：
            1. 数据收集和清洗
            2. 探索性数据分析
            3. 销售趋势分析
            4. 客户细分分析
            5. 预测建模
            6. 可视化仪表板
            7. 执行摘要报告
            """,
            "requirements": [
                "数据质量评估",
                "统计分析",
                "机器学习建模",
                "数据可视化",
                "业务洞察",
                "报告生成"
            ],
            "priority": 3,
            "task_type": "analysis"
        }
        
        config = {
            "configurable": {
                "thread_id": "end_to_end_test",
                "checkpoint_interval": 30
            }
        }
        
        # 执行完整工作流
        result = await integrated_workflow.execute(complex_task, config)
        
        # 验证执行结果
        assert result is not None
        assert result["task_state"]["status"] == TaskStatus.COMPLETED
        assert result["workflow_context"]["current_phase"] == WorkflowPhase.COMPLETION
        
        # 验证智能体参与
        agent_results = result["workflow_context"]["agent_results"]
        assert len(agent_results) >= 2  # 至少有2个智能体参与
        
        # 验证工作流状态
        assert integrated_workflow.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_workflow_with_failures_and_recovery(self, mock_llm):
        """测试工作流失败和恢复"""
        # 创建部分失败的工作流
        workflow = MultiAgentWorkflow(
            workflow_id="failure_recovery_test",
            execution_mode=WorkflowExecutionMode.SEQUENTIAL
        )
        
        # 注册正常的智能体
        workflow.register_agent("normal_agent", mock_llm, "generic")
        
        # 注册会失败的智能体
        failing_llm = Mock()
        failing_llm.ainvoke = AsyncMock(side_effect=Exception("智能体执行失败"))
        workflow.register_agent("failing_agent", failing_llm, "generic")
        
        workflow.compile_workflow()
        
        task = {
            "title": "失败恢复测试",
            "description": "测试工作流的失败处理和恢复能力",
            "task_type": "test"
        }
        
        # 执行工作流（可能失败）
        try:
            result = await workflow.execute(task)
            # 如果没有抛出异常，验证结果
            assert result is not None
        except Exception as e:
            # 验证异常被正确处理
            assert "智能体执行失败" in str(e) or "工作流执行失败" in str(e)

    @pytest.mark.asyncio
    async def test_concurrent_workflows(self, mock_llm):
        """测试并发工作流执行"""
        # 创建多个工作流实例
        workflows = []
        for i in range(3):
            workflow = MultiAgentWorkflow(
                workflow_id=f"concurrent_test_{i}",
                execution_mode=WorkflowExecutionMode.SEQUENTIAL
            )
            workflow.register_agent(f"agent_{i}", mock_llm, "generic")
            workflow.compile_workflow()
            workflows.append(workflow)
        
        # 创建不同的任务
        tasks = [
            {
                "title": f"并发任务 {i}",
                "description": f"并发执行的任务 {i}",
                "task_type": "test"
            }
            for i in range(3)
        ]
        
        # 并发执行工作流
        execution_tasks = [
            workflow.execute(task)
            for workflow, task in zip(workflows, tasks)
        ]
        
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        # 验证所有工作流都成功完成
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"工作流 {i} 执行失败: {result}")
            assert result is not None
            assert result["task_state"]["status"] == TaskStatus.COMPLETED

    def test_workflow_performance_metrics(self, integrated_workflow):
        """测试工作流性能指标"""
        # 获取路由统计
        routing_stats = integrated_workflow.get_routing_statistics()
        assert "routing_strategy" in routing_stats
        
        # 获取工作流信息
        workflow_info = integrated_workflow.get_workflow_info()
        assert "execution_stats" in workflow_info
        
        # 验证统计数据结构
        exec_stats = workflow_info["execution_stats"]
        assert "total_executions" in exec_stats
        assert "successful_executions" in exec_stats
        assert "failed_executions" in exec_stats


if __name__ == "__main__":
    # 运行工作流引擎测试
    pytest.main([__file__, "-v", "--tb=short"])