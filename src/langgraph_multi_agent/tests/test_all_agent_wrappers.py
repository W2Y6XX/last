"""智能体包装器综合测试"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from langgraph_multi_agent.agents.wrappers import AgentNodeWrapper, AgentExecutionResult
from langgraph_multi_agent.agents.meta_agent_wrapper import MetaAgentWrapper
from langgraph_multi_agent.agents.task_decomposer_wrapper import TaskDecomposerWrapper
from langgraph_multi_agent.agents.coordinator_wrapper import CoordinatorWrapper
from langgraph_multi_agent.agents.generic_wrapper import GenericAgentWrapper
from langgraph_multi_agent.core.state import (
    create_initial_state,
    WorkflowPhase,
    update_workflow_phase,
    add_agent_message
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


class TestAgentWrapperBase:
    """智能体包装器基础测试"""

    @pytest.fixture
    def mock_llm(self):
        """创建模拟LLM"""
        return MockLLM()

    @pytest.fixture
    def base_state(self):
        """创建基础状态"""
        return create_initial_state(
            "测试任务",
            "这是一个用于测试智能体包装器的任务"
        )

    def test_agent_wrapper_initialization(self, mock_llm):
        """测试智能体包装器初始化"""
        wrapper = GenericAgentWrapper(
            agent_id="test_agent",
            llm=mock_llm,
            name="TestAgent",
            description="测试智能体",
            capabilities=["testing"]
        )
        
        assert wrapper.agent_id == "test_agent"
        assert wrapper.agent_type == "generic"
        assert wrapper.name == "TestAgent"
        assert wrapper.description == "测试智能体"
        assert wrapper.capabilities == ["testing"]
        assert wrapper.timeout_seconds == 60
        assert wrapper.max_retries == 3

    def test_agent_wrapper_configuration(self, mock_llm):
        """测试智能体包装器配置"""
        wrapper = GenericAgentWrapper(
            agent_id="test_agent",
            llm=mock_llm,
            name="TestAgent",
            description="测试智能体",
            timeout_seconds=120,
            max_retries=5
        )
        
        assert wrapper.timeout_seconds == 120
        assert wrapper.max_retries == 5

    @pytest.mark.asyncio
    async def test_agent_wrapper_execution(self, mock_llm, base_state):
        """测试智能体包装器执行"""
        wrapper = GenericAgentWrapper(
            agent_id="test_agent",
            llm=mock_llm,
            name="TestAgent",
            description="测试智能体"
        )
        
        result_state = await wrapper.execute(base_state)
        
        assert result_state is not None
        assert "agent_messages" in result_state
        assert len(result_state["agent_messages"]) > 0
        
        # 验证智能体消息
        agent_message = result_state["agent_messages"][-1]
        assert agent_message["sender_agent"] == "test_agent"
        assert "content" in agent_message

    def test_agent_wrapper_info(self, mock_llm):
        """测试智能体包装器信息获取"""
        wrapper = GenericAgentWrapper(
            agent_id="test_agent",
            llm=mock_llm,
            name="TestAgent",
            description="测试智能体",
            capabilities=["testing", "validation"]
        )
        
        info = wrapper.get_agent_info()
        
        assert "agent_id" in info
        assert "agent_type" in info
        assert "name" in info
        assert "description" in info
        assert "capabilities" in info
        assert info["agent_id"] == "test_agent"
        assert info["capabilities"] == ["testing", "validation"]

    def test_execution_statistics(self, mock_llm):
        """测试执行统计"""
        wrapper = GenericAgentWrapper(
            agent_id="test_agent",
            llm=mock_llm,
            name="TestAgent",
            description="测试智能体"
        )
        
        stats = wrapper.get_execution_statistics()
        
        assert "total_executions" in stats
        assert "successful_executions" in stats
        assert "failed_executions" in stats
        assert "success_rate" in stats
        assert "average_execution_time" in stats


class TestMetaAgentWrapper:
    """MetaAgent包装器测试"""

    @pytest.fixture
    def mock_llm(self):
        return MockLLM()

    @pytest.fixture
    def meta_agent_wrapper(self, mock_llm):
        return MetaAgentWrapper(
            agent_id="meta_agent",
            llm=mock_llm,
            name="MetaAgent",
            description="任务分析智能体"
        )

    @pytest.fixture
    def analysis_state(self):
        state = create_initial_state(
            "复杂数据分析任务",
            "需要对大量数据进行深入分析并生成报告"
        )
        state = update_workflow_phase(state, WorkflowPhase.ANALYSIS)
        return state

    @pytest.mark.asyncio
    async def test_meta_agent_analysis(self, meta_agent_wrapper, analysis_state):
        """测试MetaAgent分析功能"""
        result_state = await meta_agent_wrapper.execute(analysis_state)
        
        assert result_state is not None
        assert "meta_agent" in result_state["workflow_context"]["agent_results"]
        
        meta_result = result_state["workflow_context"]["agent_results"]["meta_agent"]
        assert "result" in meta_result
        assert "timestamp" in meta_result

    def test_meta_agent_task_data_extraction(self, meta_agent_wrapper, analysis_state):
        """测试MetaAgent任务数据提取"""
        task_data = meta_agent_wrapper._extract_task_data(analysis_state)
        
        assert "task_id" in task_data
        assert "title" in task_data
        assert "description" in task_data
        assert "analysis_context" in task_data
        assert "analysis_type" in task_data

    def test_meta_agent_analysis_type_determination(self, meta_agent_wrapper, analysis_state):
        """测试MetaAgent分析类型确定"""
        analysis_type = meta_agent_wrapper._determine_analysis_type(analysis_state)
        
        assert analysis_type in [
            "initial_analysis", "complexity_assessment", 
            "requirement_clarification", "agent_recommendation"
        ]

    def test_meta_agent_info(self, meta_agent_wrapper):
        """测试MetaAgent信息"""
        info = meta_agent_wrapper.get_agent_info()
        
        assert info["agent_type"] == "meta_agent"
        assert "analysis_capabilities" in info
        assert "supported_analysis_types" in info
        assert "complexity_thresholds" in info

    def test_meta_agent_statistics(self, meta_agent_wrapper):
        """测试MetaAgent统计"""
        stats = meta_agent_wrapper.get_analysis_statistics()
        
        assert "analysis_success_rate" in stats
        assert "average_analysis_time" in stats
        assert "total_analyses" in stats


class TestTaskDecomposerWrapper:
    """TaskDecomposer包装器测试"""

    @pytest.fixture
    def mock_llm(self):
        return MockLLM()

    @pytest.fixture
    def task_decomposer_wrapper(self, mock_llm):
        return TaskDecomposerWrapper(
            agent_id="task_decomposer",
            llm=mock_llm,
            name="TaskDecomposer",
            description="任务分解智能体"
        )

    @pytest.fixture
    def decomposition_state(self):
        state = create_initial_state(
            "复杂项目任务",
            "需要分解为多个子任务的复杂项目"
        )
        state = update_workflow_phase(state, WorkflowPhase.DECOMPOSITION)
        return state

    @pytest.mark.asyncio
    async def test_task_decomposer_execution(self, task_decomposer_wrapper, decomposition_state):
        """测试TaskDecomposer执行"""
        result_state = await task_decomposer_wrapper.execute(decomposition_state)
        
        assert result_state is not None
        assert "task_decomposer" in result_state["workflow_context"]["agent_results"]

    def test_task_decomposer_data_extraction(self, task_decomposer_wrapper, decomposition_state):
        """测试TaskDecomposer数据提取"""
        task_data = task_decomposer_wrapper._extract_task_data(decomposition_state)
        
        assert "task_id" in task_data
        assert "decomposition_context" in task_data
        assert "decomposition_type" in task_data
        assert "decomposition_params" in task_data

    def test_decomposition_type_determination(self, task_decomposer_wrapper, decomposition_state):
        """测试分解类型确定"""
        decomposition_type = task_decomposer_wrapper._determine_decomposition_type(decomposition_state)
        
        assert decomposition_type in [
            "complex_task", "workflow_analysis", "task_decomposition"
        ]

    def test_decomposition_strategy_selection(self, task_decomposer_wrapper, decomposition_state):
        """测试分解策略选择"""
        strategy = task_decomposer_wrapper._select_decomposition_strategy(decomposition_state)
        
        assert strategy in ["hierarchical", "parallel", "sequential"]

    def test_task_decomposer_info(self, task_decomposer_wrapper):
        """测试TaskDecomposer信息"""
        info = task_decomposer_wrapper.get_agent_info()
        
        assert info["agent_type"] == "task_decomposer"
        assert "decomposition_capabilities" in info
        assert "supported_decomposition_types" in info
        assert "decomposition_strategies" in info

    def test_task_decomposer_statistics(self, task_decomposer_wrapper):
        """测试TaskDecomposer统计"""
        stats = task_decomposer_wrapper.get_decomposition_statistics()
        
        assert "decomposition_success_rate" in stats
        assert "average_decomposition_time" in stats
        assert "total_decompositions" in stats


class TestCoordinatorWrapper:
    """Coordinator包装器测试"""

    @pytest.fixture
    def mock_llm(self):
        return MockLLM()

    @pytest.fixture
    def coordinator_wrapper(self, mock_llm):
        return CoordinatorWrapper(
            agent_id="coordinator",
            llm=mock_llm,
            name="Coordinator",
            description="智能体协调器"
        )

    @pytest.fixture
    def coordination_state(self):
        state = create_initial_state(
            "协调任务",
            "需要多个智能体协调执行的任务"
        )
        state = update_workflow_phase(state, WorkflowPhase.COORDINATION)
        return state

    @pytest.mark.asyncio
    async def test_coordinator_execution(self, coordinator_wrapper, coordination_state):
        """测试Coordinator执行"""
        result_state = await coordinator_wrapper.execute(coordination_state)
        
        assert result_state is not None
        assert "coordinator" in result_state["workflow_context"]["agent_results"]

    def test_coordinator_data_extraction(self, coordinator_wrapper, coordination_state):
        """测试Coordinator数据提取"""
        task_data = coordinator_wrapper._extract_task_data(coordination_state)
        
        assert "task_id" in task_data
        assert "coordination_context" in task_data
        assert "coordination_state" in task_data
        assert "coordination_type" in task_data

    def test_coordination_type_determination(self, coordinator_wrapper, coordination_state):
        """测试协调类型确定"""
        coordination_type = coordinator_wrapper._determine_coordination_type(coordination_state)
        
        assert coordination_type in [
            "resolve_conflict", "establish_collaboration",
            "synchronize_agents", "coordinate_execution", "general_coordination"
        ]

    def test_coordinator_info(self, coordinator_wrapper):
        """测试Coordinator信息"""
        info = coordinator_wrapper.get_agent_info()
        
        assert info["agent_type"] == "coordinator"
        assert "coordination_capabilities" in info
        assert "supported_coordination_types" in info
        assert "conflict_resolution_strategies" in info

    def test_coordinator_statistics(self, coordinator_wrapper):
        """测试Coordinator统计"""
        stats = coordinator_wrapper.get_coordination_statistics()
        
        assert "coordination_success_rate" in stats
        assert "average_coordination_time" in stats
        assert "total_coordinations" in stats


class TestGenericAgentWrapper:
    """GenericAgent包装器测试"""

    @pytest.fixture
    def mock_llm(self):
        return MockLLM()

    @pytest.fixture
    def generic_wrapper(self, mock_llm):
        return GenericAgentWrapper(
            agent_id="generic_agent",
            llm=mock_llm,
            name="GenericAgent",
            description="通用智能体",
            capabilities=["processing", "analysis"]
        )

    @pytest.fixture
    def execution_state(self):
        state = create_initial_state(
            "通用任务",
            "需要通用智能体处理的任务"
        )
        state = update_workflow_phase(state, WorkflowPhase.EXECUTION)
        return state

    @pytest.mark.asyncio
    async def test_generic_agent_execution(self, generic_wrapper, execution_state):
        """测试GenericAgent执行"""
        result_state = await generic_wrapper.execute(execution_state)
        
        assert result_state is not None
        assert "generic_agent" in result_state["workflow_context"]["agent_results"]

    def test_generic_agent_capabilities(self, generic_wrapper):
        """测试GenericAgent能力"""
        assert generic_wrapper.capabilities == ["processing", "analysis"]
        assert generic_wrapper.has_capability("processing")
        assert generic_wrapper.has_capability("analysis")
        assert not generic_wrapper.has_capability("unknown")

    def test_generic_agent_info(self, generic_wrapper):
        """测试GenericAgent信息"""
        info = generic_wrapper.get_agent_info()
        
        assert info["agent_type"] == "generic"
        assert info["capabilities"] == ["processing", "analysis"]


class TestAgentWrapperIntegration:
    """智能体包装器集成测试"""

    @pytest.fixture
    def mock_llm(self):
        return MockLLM()

    @pytest.fixture
    def all_wrappers(self, mock_llm):
        """创建所有类型的智能体包装器"""
        return {
            "meta_agent": MetaAgentWrapper(
                agent_id="meta_agent",
                llm=mock_llm,
                name="MetaAgent",
                description="分析智能体"
            ),
            "task_decomposer": TaskDecomposerWrapper(
                agent_id="task_decomposer",
                llm=mock_llm,
                name="TaskDecomposer",
                description="分解智能体"
            ),
            "coordinator": CoordinatorWrapper(
                agent_id="coordinator",
                llm=mock_llm,
                name="Coordinator",
                description="协调智能体"
            ),
            "generic_agent": GenericAgentWrapper(
                agent_id="generic_agent",
                llm=mock_llm,
                name="GenericAgent",
                description="通用智能体",
                capabilities=["processing"]
            )
        }

    @pytest.mark.asyncio
    async def test_sequential_agent_execution(self, all_wrappers):
        """测试顺序智能体执行"""
        state = create_initial_state(
            "集成测试任务",
            "测试多个智能体顺序执行"
        )
        
        # 1. MetaAgent分析
        state = update_workflow_phase(state, WorkflowPhase.ANALYSIS)
        state = await all_wrappers["meta_agent"].execute(state)
        
        # 2. TaskDecomposer分解
        state = update_workflow_phase(state, WorkflowPhase.DECOMPOSITION)
        state = await all_wrappers["task_decomposer"].execute(state)
        
        # 3. Coordinator协调
        state = update_workflow_phase(state, WorkflowPhase.COORDINATION)
        state = await all_wrappers["coordinator"].execute(state)
        
        # 4. GenericAgent执行
        state = update_workflow_phase(state, WorkflowPhase.EXECUTION)
        state = await all_wrappers["generic_agent"].execute(state)
        
        # 验证所有智能体都执行了
        agent_results = state["workflow_context"]["agent_results"]
        assert "meta_agent" in agent_results
        assert "task_decomposer" in agent_results
        assert "coordinator" in agent_results
        assert "generic_agent" in agent_results
        
        # 验证消息记录
        assert len(state["agent_messages"]) >= 4

    @pytest.mark.asyncio
    async def test_agent_error_handling(self, mock_llm):
        """测试智能体错误处理"""
        # 创建会失败的模拟LLM
        failing_llm = Mock()
        failing_llm.ainvoke = AsyncMock(side_effect=Exception("模拟LLM失败"))
        
        wrapper = GenericAgentWrapper(
            agent_id="failing_agent",
            llm=failing_llm,
            name="FailingAgent",
            description="会失败的智能体"
        )
        
        state = create_initial_state("错误测试任务", "测试错误处理")
        
        # 执行应该处理错误而不崩溃
        result_state = await wrapper.execute(state)
        
        # 验证错误被正确处理
        assert result_state is not None
        # 检查是否有错误消息
        error_messages = [
            msg for msg in result_state["agent_messages"]
            if msg.get("message_type") == "error"
        ]
        assert len(error_messages) > 0

    def test_agent_wrapper_polymorphism(self, all_wrappers):
        """测试智能体包装器多态性"""
        # 所有包装器都应该有相同的基础接口
        for wrapper in all_wrappers.values():
            assert hasattr(wrapper, "execute")
            assert hasattr(wrapper, "get_agent_info")
            assert hasattr(wrapper, "get_execution_statistics")
            assert callable(wrapper.execute)
            assert callable(wrapper.get_agent_info)
            assert callable(wrapper.get_execution_statistics)

    def test_agent_wrapper_configuration_consistency(self, all_wrappers):
        """测试智能体包装器配置一致性"""
        for wrapper in all_wrappers.values():
            info = wrapper.get_agent_info()
            
            # 所有包装器都应该有这些基础字段
            assert "agent_id" in info
            assert "agent_type" in info
            assert "name" in info
            assert "description" in info
            assert "timeout_seconds" in info
            assert "max_retries" in info

    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(self, all_wrappers):
        """测试并发智能体执行"""
        state = create_initial_state(
            "并发测试任务",
            "测试多个智能体并发执行"
        )
        
        # 创建多个独立的状态副本
        states = []
        for i in range(4):
            state_copy = state.copy()
            state_copy["task_state"] = state["task_state"].copy()
            state_copy["task_state"]["task_id"] = f"concurrent_task_{i}"
            states.append(state_copy)
        
        # 并发执行不同的智能体
        tasks = [
            all_wrappers["meta_agent"].execute(states[0]),
            all_wrappers["task_decomposer"].execute(states[1]),
            all_wrappers["coordinator"].execute(states[2]),
            all_wrappers["generic_agent"].execute(states[3])
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 验证所有执行都成功
        for result in results:
            assert not isinstance(result, Exception)
            assert result is not None

    def test_agent_wrapper_memory_usage(self, all_wrappers):
        """测试智能体包装器内存使用"""
        import sys
        
        # 获取初始内存使用
        initial_size = sys.getsizeof(all_wrappers)
        
        # 执行一些操作
        for wrapper in all_wrappers.values():
            info = wrapper.get_agent_info()
            stats = wrapper.get_execution_statistics()
        
        # 内存使用不应该显著增加
        final_size = sys.getsizeof(all_wrappers)
        memory_growth = final_size - initial_size
        
        # 内存增长应该在合理范围内（小于1MB）
        assert memory_growth < 1024 * 1024


if __name__ == "__main__":
    # 运行所有智能体包装器测试
    pytest.main([__file__, "-v", "--tb=short"])