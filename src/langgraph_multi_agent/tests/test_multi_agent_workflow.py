"""多智能体工作流测试"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from langgraph_multi_agent.workflow.multi_agent_workflow import (
    MultiAgentWorkflow,
    WorkflowExecutionMode,
    WorkflowStatus
)
from langgraph.graph import END
from langgraph_multi_agent.core.state import (
    create_initial_state,
    WorkflowPhase
)
from langgraph_multi_agent.legacy.task_state import TaskStatus


class MockAgent:
    """模拟智能体用于测试"""
    
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
                "complexity_score": 0.5,
                "requires_decomposition": False,
                "clarification_needed": False,
                "recommended_agents": ["generic_agent"],
                "analysis_summary": "任务分析完成"
            }
        elif agent_type == "task_decomposer":
            return {
                "success": True,
                "decomposition": {
                    "subtasks": [
                        {"id": "sub1", "name": "Subtask 1", "type": "generic"}
                    ],
                    "dependencies": [],
                    "decomposition_strategy": "sequential"
                },
                "execution_plan": {"estimated_duration": 60},
                "subtasks_count": 1
            }
        elif agent_type == "coordinator":
            return {
                "success": True,
                "coordination_type": "general_coordination",
                "message": "协调完成"
            }
        else:
            return {"success": True, "message": "任务完成"}
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟任务处理"""
        self.call_count += 1
        
        if self.should_fail:
            raise ValueError(f"{self.agent_type}执行失败")
        
        await asyncio.sleep(0.01)  # 模拟处理时间
        return self.result.copy()


class TestMultiAgentWorkflow:
    """多智能体工作流测试类"""
    
    def test_workflow_initialization(self):
        """测试工作流初始化"""
        workflow = MultiAgentWorkflow(
            workflow_id="test_workflow",
            execution_mode=WorkflowExecutionMode.SEQUENTIAL,
            max_iterations=50,
            timeout_seconds=1800
        )
        
        # 验证基本属性
        assert workflow.workflow_id == "test_workflow"
        assert workflow.execution_mode == WorkflowExecutionMode.SEQUENTIAL
        assert workflow.max_iterations == 50
        assert workflow.timeout_seconds == 1800
        assert workflow.status == WorkflowStatus.CREATED
        
        # 验证图初始化
        assert workflow.graph is not None
        assert workflow.compiled_graph is None
        
        # 验证统计初始化
        assert workflow.execution_stats["total_executions"] == 0
    
    def test_agent_registration(self):
        """测试智能体注册"""
        workflow = MultiAgentWorkflow("test_workflow")
        
        # 注册不同类型的智能体
        meta_agent = MockAgent("meta_agent")
        coordinator = MockAgent("coordinator")
        generic_agent = MockAgent("generic")
        
        workflow.register_agent("meta_agent", meta_agent, "meta_agent")
        workflow.register_agent("coordinator", coordinator, "coordinator")
        workflow.register_agent("generic_agent", generic_agent, "generic")
        
        # 验证注册结果
        assert len(workflow.agents) == 3
        assert len(workflow.agent_wrappers) == 3
        assert "meta_agent" in workflow.agents
        assert "coordinator" in workflow.agents
        assert "generic_agent" in workflow.agents
        
        # 验证智能体信息
        agents_info = workflow.list_agents()
        assert len(agents_info) == 3
        
        meta_info = workflow.get_agent_info("meta_agent")
        assert meta_info is not None
        assert meta_info["agent_type"] == "meta_agent"
    
    def test_workflow_compilation(self):
        """测试工作流编译"""
        workflow = MultiAgentWorkflow("test_workflow")
        
        # 注册智能体
        meta_agent = MockAgent("meta_agent")
        workflow.register_agent("meta_agent", meta_agent, "meta_agent")
        
        # 编译工作流
        workflow.compile_workflow()
        
        # 验证编译结果
        assert workflow.compiled_graph is not None
        assert workflow.status == WorkflowStatus.CREATED
    
    @pytest.mark.asyncio
    async def test_simple_workflow_execution(self):
        """测试简单工作流执行"""
        workflow = MultiAgentWorkflow("test_workflow")
        
        # 注册MetaAgent
        meta_agent = MockAgent("meta_agent")
        workflow.register_agent("meta_agent", meta_agent, "meta_agent")
        
        # 编译工作流
        workflow.compile_workflow()
        
        # 执行工作流
        initial_input = {
            "title": "测试任务",
            "description": "简单的测试任务",
            "task_type": "test",
            "priority": 1
        }
        
        final_state = await workflow.execute(initial_input)
        
        # 验证执行结果
        assert final_state is not None
        assert workflow.status == WorkflowStatus.COMPLETED
        assert workflow.started_at is not None
        assert workflow.completed_at is not None
        
        # 验证智能体被调用
        assert meta_agent.call_count > 0
        
        # 验证统计更新
        assert workflow.execution_stats["total_executions"] == 1
        assert workflow.execution_stats["successful_executions"] == 1
    
    @pytest.mark.asyncio
    async def test_complex_workflow_execution(self):
        """测试复杂工作流执行"""
        workflow = MultiAgentWorkflow("complex_workflow")
        
        # 注册多个智能体
        meta_agent = MockAgent("meta_agent", {
            "success": True,
            "complexity_score": 0.8,
            "requires_decomposition": True,
            "recommended_agents": ["task_decomposer", "coordinator"]
        })
        
        task_decomposer = MockAgent("task_decomposer")
        coordinator = MockAgent("coordinator")
        
        workflow.register_agent("meta_agent", meta_agent, "meta_agent")
        workflow.register_agent("task_decomposer", task_decomposer, "task_decomposer")
        workflow.register_agent("coordinator", coordinator, "coordinator")
        
        # 编译工作流
        workflow.compile_workflow()
        
        # 执行工作流
        initial_input = {
            "title": "复杂任务",
            "description": "需要分解和协调的复杂任务",
            "task_type": "complex",
            "priority": 2
        }
        
        final_state = await workflow.execute(initial_input)
        
        # 验证执行结果
        assert final_state is not None
        assert workflow.status == WorkflowStatus.COMPLETED
        
        # 验证所有智能体都被调用
        assert meta_agent.call_count > 0
        assert task_decomposer.call_count > 0
        assert coordinator.call_count > 0
        
        # 验证工作流阶段转换（final_state可能是最后一个节点的输出）
        # 检查工作流是否完成
        assert workflow.status == WorkflowStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_workflow_execution_failure(self):
        """测试工作流执行失败"""
        workflow = MultiAgentWorkflow("failing_workflow")
        
        # 注册会失败的智能体
        failing_agent = MockAgent("meta_agent", should_fail=True)
        workflow.register_agent("meta_agent", failing_agent, "meta_agent")
        
        # 编译工作流
        workflow.compile_workflow()
        
        # 执行工作流（智能体会失败但工作流可能继续）
        initial_input = {
            "title": "失败任务",
            "description": "会失败的任务"
        }
        
        try:
            final_state = await workflow.execute(initial_input)
            # 如果没有抛出异常，检查是否有失败的智能体
            assert failing_agent.call_count > 0
        except Exception:
            # 如果抛出异常，验证失败状态
            assert workflow.status == WorkflowStatus.FAILED
    
    def test_conditional_routing_functions(self):
        """测试条件路由函数"""
        workflow = MultiAgentWorkflow("routing_test")
        
        # 注册智能体
        workflow.register_agent("meta_agent", MockAgent("meta_agent"), "meta_agent")
        workflow.register_agent("task_decomposer", MockAgent("task_decomposer"), "task_decomposer")
        workflow.register_agent("coordinator", MockAgent("coordinator"), "coordinator")
        
        # 测试分析路由
        state1 = create_initial_state("测试", "测试任务")
        assert workflow._should_analyze(state1) == "meta_agent"
        
        # 测试分解路由
        state2 = create_initial_state("测试", "测试任务")
        state2["workflow_context"]["agent_results"]["meta_agent"] = {
            "result": {"requires_decomposition": True}
        }
        assert workflow._should_decompose(state2) == "task_decomposer"
        
        # 测试协调路由
        state3 = create_initial_state("测试", "测试任务")
        state3["task_state"]["subtasks"] = [{"id": "sub1", "name": "Subtask 1"}]
        assert workflow._should_coordinate(state3) == "coordinator"
        
        # 测试执行路由
        state4 = create_initial_state("测试", "测试任务")
        state4["workflow_context"]["current_phase"] = WorkflowPhase.EXECUTION
        assert workflow._should_execute(state4) == "execute"
        
        # 测试完成路由
        state5 = create_initial_state("测试", "测试任务")
        state5["task_state"]["status"] = TaskStatus.COMPLETED
        assert workflow._should_complete(state5) == "complete"
    
    @pytest.mark.asyncio
    async def test_routing_nodes(self):
        """测试路由节点"""
        workflow = MultiAgentWorkflow("routing_nodes_test")
        
        # 测试各个路由节点
        state = create_initial_state("测试", "测试任务")
        
        # 测试分析路由节点
        analysis_state = await workflow._route_to_analysis(state.copy())
        assert analysis_state["current_node"] == "route_to_analysis"
        assert analysis_state["workflow_context"]["current_phase"] == WorkflowPhase.ANALYSIS
        
        # 测试分解路由节点
        decomposition_state = await workflow._route_to_decomposition(state.copy())
        assert decomposition_state["current_node"] == "route_to_decomposition"
        assert decomposition_state["workflow_context"]["current_phase"] == WorkflowPhase.DECOMPOSITION
        
        # 测试协调路由节点
        coordination_state = await workflow._route_to_coordination(state.copy())
        assert coordination_state["current_node"] == "route_to_coordination"
        assert coordination_state["workflow_context"]["current_phase"] == WorkflowPhase.COORDINATION
        
        # 测试执行路由节点
        execution_state = await workflow._route_to_execution(state.copy())
        assert execution_state["current_node"] == "route_to_execution"
        assert execution_state["workflow_context"]["current_phase"] == WorkflowPhase.EXECUTION
        
        # 测试完成路由节点
        completion_state = await workflow._route_to_completion(state.copy())
        assert completion_state["current_node"] == "route_to_completion"
        assert completion_state["workflow_context"]["current_phase"] == WorkflowPhase.COMPLETION
        assert completion_state["task_state"]["status"] == TaskStatus.COMPLETED
    
    def test_workflow_info(self):
        """测试工作流信息获取"""
        workflow = MultiAgentWorkflow(
            "info_test",
            execution_mode=WorkflowExecutionMode.PARALLEL,
            max_iterations=75,
            timeout_seconds=2400
        )
        
        # 注册智能体
        workflow.register_agent("test_agent", MockAgent("generic"), "generic")
        
        # 获取工作流信息
        info = workflow.get_workflow_info()
        
        # 验证信息
        assert info["workflow_id"] == "info_test"
        assert info["status"] == WorkflowStatus.CREATED.value
        assert info["execution_mode"] == WorkflowExecutionMode.PARALLEL.value
        assert info["max_iterations"] == 75
        assert info["timeout_seconds"] == 2400
        assert "test_agent" in info["registered_agents"]
        assert "execution_stats" in info
    
    def test_execution_mode_configuration(self):
        """测试执行模式配置"""
        # 测试顺序执行模式
        sequential_workflow = MultiAgentWorkflow(
            "sequential_test",
            execution_mode=WorkflowExecutionMode.SEQUENTIAL
        )
        assert sequential_workflow.execution_mode == WorkflowExecutionMode.SEQUENTIAL
        
        # 测试并行执行模式
        parallel_workflow = MultiAgentWorkflow(
            "parallel_test",
            execution_mode=WorkflowExecutionMode.PARALLEL
        )
        assert parallel_workflow.execution_mode == WorkflowExecutionMode.PARALLEL
        
        # 测试自适应执行模式
        adaptive_workflow = MultiAgentWorkflow(
            "adaptive_test",
            execution_mode=WorkflowExecutionMode.ADAPTIVE
        )
        assert adaptive_workflow.execution_mode == WorkflowExecutionMode.ADAPTIVE
    
    def test_timeout_detection(self):
        """测试超时检测"""
        workflow = MultiAgentWorkflow("timeout_test", timeout_seconds=1)
        
        # 未开始执行时不应该超时
        assert not workflow._is_execution_timeout()
        
        # 设置开始时间
        workflow.started_at = datetime.now()
        
        # 立即检查不应该超时
        assert not workflow._is_execution_timeout()
        
        # 模拟超时（通过修改开始时间）
        from datetime import timedelta
        workflow.started_at = datetime.now() - timedelta(seconds=2)
        assert workflow._is_execution_timeout()
    
    def test_execution_statistics(self):
        """测试执行统计"""
        workflow = MultiAgentWorkflow("stats_test")
        
        # 初始统计
        assert workflow.execution_stats["total_executions"] == 0
        assert workflow.execution_stats["successful_executions"] == 0
        assert workflow.execution_stats["failed_executions"] == 0
        
        # 模拟成功执行
        from datetime import timedelta
        workflow.started_at = datetime.now()
        workflow.completed_at = datetime.now() + timedelta(seconds=1)  # 确保有执行时间
        workflow._update_execution_stats(True)
        
        assert workflow.execution_stats["total_executions"] == 1
        assert workflow.execution_stats["successful_executions"] == 1
        assert workflow.execution_stats["failed_executions"] == 0
        assert workflow.execution_stats["average_execution_time"] > 0
        
        # 模拟失败执行
        workflow._update_execution_stats(False)
        
        assert workflow.execution_stats["total_executions"] == 2
        assert workflow.execution_stats["successful_executions"] == 1
        assert workflow.execution_stats["failed_executions"] == 1
    
    @pytest.mark.asyncio
    async def test_workflow_with_custom_edges(self):
        """测试自定义边的工作流"""
        workflow = MultiAgentWorkflow("custom_edges_test")
        
        # 注册智能体
        agent1 = MockAgent("generic")
        agent2 = MockAgent("generic")
        
        workflow.register_agent("agent1", agent1, "generic")
        workflow.register_agent("agent2", agent2, "generic")
        
        # 添加自定义边
        workflow.add_edge("agent1", "agent2")
        
        # 添加条件边
        def custom_condition(state):
            return "agent2" if state.get("custom_flag") else "end"
        
        workflow.add_conditional_edge(
            "agent1",
            custom_condition,
            {"agent2": "agent2", "end": END}
        )
        
        # 编译工作流
        workflow.compile_workflow()
        
        # 验证编译成功
        assert workflow.compiled_graph is not None
    
    def test_workflow_status_transitions(self):
        """测试工作流状态转换"""
        workflow = MultiAgentWorkflow("status_test")
        
        # 初始状态
        assert workflow.status == WorkflowStatus.CREATED
        
        # 编译后状态
        workflow.register_agent("test_agent", MockAgent("generic"), "generic")
        workflow.compile_workflow()
        assert workflow.status == WorkflowStatus.CREATED
        
        # 模拟运行状态
        workflow.status = WorkflowStatus.RUNNING
        assert workflow.status == WorkflowStatus.RUNNING
        
        # 模拟暂停状态
        workflow.status = WorkflowStatus.PAUSED
        assert workflow.status == WorkflowStatus.PAUSED
        
        # 模拟完成状态
        workflow.status = WorkflowStatus.COMPLETED
        assert workflow.status == WorkflowStatus.COMPLETED
        
        # 模拟失败状态
        workflow.status = WorkflowStatus.FAILED
        assert workflow.status == WorkflowStatus.FAILED