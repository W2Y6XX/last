"""TaskDecomposer包装器测试"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from langgraph_multi_agent.agents.task_decomposer_wrapper import TaskDecomposerWrapper
from langgraph_multi_agent.core.state import (
    create_initial_state,
    WorkflowPhase,
    LangGraphTaskState
)
from langgraph_multi_agent.legacy.task_state import TaskStatus


class MockTaskDecomposer:
    """模拟TaskDecomposer用于测试"""
    
    def __init__(self, decomposition_result: Dict[str, Any] = None, should_fail: bool = False):
        self.decomposition_result = decomposition_result or {
            "success": True,
            "decomposition": {
                "original_task": {"id": "task_123", "name": "Test Task"},
                "decomposition_strategy": "hierarchical",
                "subtasks": [
                    {
                        "id": "subtask_1",
                        "name": "Data Collection",
                        "description": "Collect required data",
                        "type": "data_collection"
                    },
                    {
                        "id": "subtask_2", 
                        "name": "Data Analysis",
                        "description": "Analyze collected data",
                        "type": "analysis"
                    }
                ],
                "dependencies": [
                    {"from": "subtask_1", "to": "subtask_2", "type": "sequential"}
                ],
                "metadata": {
                    "depth": 1,
                    "created_at": datetime.now().isoformat()
                }
            },
            "execution_plan": {
                "execution_order": ["subtask_1", "subtask_2"],
                "estimated_duration": 120,
                "resource_plan": {"human_resources": 2},
                "risk_assessment": {"overall_risk_level": "low"}
            },
            "subtasks_count": 2,
            "estimated_duration": 120
        }
        self.should_fail = should_fail
        self.call_count = 0
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟任务处理"""
        self.call_count += 1
        
        if self.should_fail:
            raise ValueError("TaskDecomposer分解失败")
        
        # 模拟分解时间
        await asyncio.sleep(0.1)
        
        # 根据分解类型返回不同结果
        decomposition_type = task_data.get("decomposition_type", "complex_task")
        result = self.decomposition_result.copy()
        result["decomposition_type"] = decomposition_type
        
        return result


class TestTaskDecomposerWrapper:
    """TaskDecomposer包装器测试类"""
    
    @pytest.mark.asyncio
    async def test_complex_task_decomposition(self):
        """测试复杂任务分解"""
        decomposition_result = {
            "success": True,
            "decomposition_type": "complex_task",
            "decomposition": {
                "original_task": {"id": "complex_123", "name": "Complex Analysis Task"},
                "decomposition_strategy": "hierarchical",
                "subtasks": [
                    {"id": "sub1", "name": "Data Collection", "type": "data_collection"},
                    {"id": "sub2", "name": "Data Processing", "type": "data_processing"},
                    {"id": "sub3", "name": "Analysis", "type": "analysis"},
                    {"id": "sub4", "name": "Reporting", "type": "reporting"}
                ],
                "dependencies": [
                    {"from": "sub1", "to": "sub2", "type": "sequential"},
                    {"from": "sub2", "to": "sub3", "type": "sequential"},
                    {"from": "sub3", "to": "sub4", "type": "sequential"}
                ],
                "metadata": {"depth": 2}
            },
            "execution_plan": {
                "execution_order": ["sub1", "sub2", "sub3", "sub4"],
                "estimated_duration": 240,
                "resource_plan": {"human_resources": 3}
            },
            "subtasks_count": 4,
            "estimated_duration": 240
        }
        
        mock_decomposer = MockTaskDecomposer(decomposition_result)
        wrapper = TaskDecomposerWrapper(mock_decomposer)
        
        # 创建复杂任务的测试状态
        state = create_initial_state("复杂分析任务", "需要多步骤分析的复杂任务")
        state["workflow_context"]["current_phase"] = WorkflowPhase.DECOMPOSITION
        
        # 执行分解
        updated_state = await wrapper(state)
        
        # 验证结果
        assert len(updated_state["agent_messages"]) > 0
        assert updated_state["workflow_context"]["agent_results"]["task_decomposer"]["result"]["success"] is True
        assert "task_decomposer" in updated_state["task_state"]["output_data"]
        assert updated_state["task_state"]["output_data"]["task_decomposer"]["decomposition_completed"] is True
        
        # 验证子任务生成
        assert len(updated_state["task_state"]["subtasks"]) == 4
        assert updated_state["task_state"]["subtasks"][0]["name"] == "Data Collection"
        assert updated_state["task_state"]["subtasks"][0]["status"] == "pending"
        
        # 验证工作流阶段转换
        assert updated_state["workflow_context"]["current_phase"] == WorkflowPhase.COORDINATION
        assert updated_state["task_state"]["status"] == TaskStatus.IN_PROGRESS
        
        # 验证执行元数据
        assert updated_state["workflow_context"]["execution_metadata"]["subtasks_generated"] is True
        assert updated_state["workflow_context"]["execution_metadata"]["subtasks_count"] == 4
        assert "execution_plan" in updated_state["workflow_context"]["execution_metadata"]
    
    @pytest.mark.asyncio
    async def test_workflow_analysis(self):
        """测试工作流分析"""
        analysis_result = {
            "success": True,
            "decomposition_type": "workflow_analysis",
            "analysis": {
                "workflow_id": "workflow_456",
                "bottlenecks": [
                    {"task_id": "task1", "type": "long_duration", "description": "Task takes too long"}
                ],
                "optimization_suggestions": [
                    {"type": "parallelization", "description": "Consider parallel execution"}
                ],
                "critical_path": ["task1", "task2", "task3"],
                "resource_requirements": {"cpu_cores": 4, "memory_gb": 8}
            },
            "subtasks_count": 0,
            "estimated_duration": 60
        }
        
        mock_decomposer = MockTaskDecomposer(analysis_result)
        wrapper = TaskDecomposerWrapper(mock_decomposer)
        
        # 创建工作流分析的测试状态
        state = create_initial_state("工作流分析", "分析现有工作流的效率和瓶颈")
        state["task_state"]["task_type"] = "analysis"
        
        # 执行分析
        updated_state = await wrapper(state)
        
        # 验证分析结果
        result = updated_state["workflow_context"]["agent_results"]["task_decomposer"]["result"]
        assert result["success"] is True
        assert "analysis" in result
        assert len(result["analysis"]["bottlenecks"]) > 0
        assert len(result["analysis"]["optimization_suggestions"]) > 0
        
        # 验证没有子任务时直接转入执行阶段
        assert updated_state["workflow_context"]["current_phase"] == WorkflowPhase.EXECUTION
    
    @pytest.mark.asyncio
    async def test_parallel_decomposition(self):
        """测试并行分解策略"""
        parallel_result = {
            "success": True,
            "decomposition_type": "task_decomposition",
            "decomposition": {
                "decomposition_strategy": "parallel",
                "subtasks": [
                    {"id": "parallel1", "name": "Component A", "type": "development"},
                    {"id": "parallel2", "name": "Component B", "type": "development"},
                    {"id": "parallel3", "name": "Component C", "type": "development"}
                ],
                "dependencies": [],  # 并行任务无依赖
                "parallel_groups": [
                    {"name": "Development Group", "components": ["parallel1", "parallel2", "parallel3"]}
                ]
            },
            "execution_plan": {
                "execution_order": ["parallel1", "parallel2", "parallel3"],
                "estimated_duration": 90
            },
            "subtasks_count": 3
        }
        
        mock_decomposer = MockTaskDecomposer(parallel_result)
        wrapper = TaskDecomposerWrapper(mock_decomposer)
        
        # 创建并行任务的测试状态
        state = create_initial_state("并行开发", "可以并行开发的多个组件")
        
        # 执行分解
        updated_state = await wrapper(state)
        
        # 验证并行分解
        decomposition = updated_state["workflow_context"]["agent_results"]["task_decomposer"]["result"]["decomposition"]
        assert decomposition["decomposition_strategy"] == "parallel"
        assert len(decomposition["dependencies"]) == 0  # 并行任务无依赖
        assert len(updated_state["task_state"]["subtasks"]) == 3
    
    @pytest.mark.asyncio
    async def test_sequential_decomposition(self):
        """测试顺序分解策略"""
        sequential_result = {
            "success": True,
            "decomposition_type": "task_decomposition",
            "decomposition": {
                "decomposition_strategy": "sequential",
                "subtasks": [
                    {"id": "step1", "name": "Step 1", "type": "preparation"},
                    {"id": "step2", "name": "Step 2", "type": "execution"},
                    {"id": "step3", "name": "Step 3", "type": "completion"}
                ],
                "dependencies": [
                    {"from": "step1", "to": "step2", "type": "sequential"},
                    {"from": "step2", "to": "step3", "type": "sequential"}
                ],
                "execution_order": ["step1", "step2", "step3"]
            },
            "execution_plan": {
                "execution_order": ["step1", "step2", "step3"],
                "estimated_duration": 150
            },
            "subtasks_count": 3
        }
        
        mock_decomposer = MockTaskDecomposer(sequential_result)
        wrapper = TaskDecomposerWrapper(mock_decomposer)
        
        # 创建顺序任务的测试状态
        state = create_initial_state("顺序流程", "需要按步骤顺序执行的流程")
        
        # 执行分解
        updated_state = await wrapper(state)
        
        # 验证顺序分解
        decomposition = updated_state["workflow_context"]["agent_results"]["task_decomposer"]["result"]["decomposition"]
        assert decomposition["decomposition_strategy"] == "sequential"
        assert len(decomposition["dependencies"]) == 2  # 顺序任务有依赖
        
        # 验证依赖关系存储
        assert "task_dependencies" in updated_state["workflow_context"]["execution_metadata"]
        dependencies = updated_state["workflow_context"]["execution_metadata"]["task_dependencies"]
        assert len(dependencies) == 2
    
    @pytest.mark.asyncio
    async def test_decomposition_failure(self):
        """测试分解失败处理"""
        mock_decomposer = MockTaskDecomposer(should_fail=True)
        wrapper = TaskDecomposerWrapper(mock_decomposer)
        
        # 创建测试状态
        state = create_initial_state("失败任务", "分解失败的任务")
        
        # 执行分解
        updated_state = await wrapper(state)
        
        # 验证错误处理
        error_messages = [msg for msg in updated_state["agent_messages"] 
                         if msg["message_type"] == "decomposition_error"]
        assert len(error_messages) > 0
        
        # 验证执行失败 - 检查是否有错误消息
        assert len(error_messages) > 0
    
    @pytest.mark.asyncio
    async def test_task_data_extraction(self):
        """测试任务数据提取"""
        mock_decomposer = MockTaskDecomposer()
        wrapper = TaskDecomposerWrapper(mock_decomposer)
        
        # 创建复杂的测试状态
        state = create_initial_state("复杂任务", "复杂的分解任务")
        state["workflow_context"]["current_phase"] = WorkflowPhase.DECOMPOSITION
        state["workflow_context"]["agent_results"]["meta_agent"] = {
            "result": {"requires_decomposition": True, "complexity_score": 0.8}
        }
        state["workflow_context"]["execution_metadata"]["meta_analysis"] = {"complexity_score": 0.8}
        
        # 提取任务数据
        task_data = wrapper._extract_task_data(state)
        
        # 验证数据提取
        assert task_data["title"] == "复杂任务"
        assert task_data["decomposition_type"] == "complex_task"
        assert task_data["decomposition_params"]["strategy"] == "hierarchical"
        assert task_data["decomposition_params"]["max_depth"] == 5
        assert "decomposition_context" in task_data
        assert task_data["decomposition_context"]["current_phase"] == "decomposition"
    
    @pytest.mark.asyncio
    async def test_decomposition_type_determination(self):
        """测试分解类型确定"""
        mock_decomposer = MockTaskDecomposer()
        wrapper = TaskDecomposerWrapper(mock_decomposer)
        
        # 测试复杂任务类型
        state1 = create_initial_state("任务1", "复杂任务")
        state1["workflow_context"]["agent_results"]["meta_agent"] = {
            "result": {"requires_decomposition": True}
        }
        assert wrapper._determine_decomposition_type(state1) == "complex_task"
        
        # 测试分析类型
        state2 = create_initial_state("任务2", "分析任务")
        state2["task_state"]["task_type"] = "analysis"
        assert wrapper._determine_decomposition_type(state2) == "workflow_analysis"
        
        # 测试开发类型
        state3 = create_initial_state("任务3", "开发任务")
        state3["task_state"]["task_type"] = "development"
        assert wrapper._determine_decomposition_type(state3) == "task_decomposition"
    
    @pytest.mark.asyncio
    async def test_decomposition_strategy_selection(self):
        """测试分解策略选择"""
        mock_decomposer = MockTaskDecomposer()
        wrapper = TaskDecomposerWrapper(mock_decomposer)
        
        # 测试高复杂度选择层次分解
        state1 = create_initial_state("高复杂度任务", "非常复杂的任务")
        state1["workflow_context"]["execution_metadata"]["meta_analysis"] = {"complexity_score": 0.9}
        assert wrapper._select_decomposition_strategy(state1) == "hierarchical"
        
        # 测试并行关键词选择并行分解
        state2 = create_initial_state("并行任务", "可以parallel处理的任务")
        assert wrapper._select_decomposition_strategy(state2) == "parallel"
        
        # 测试步骤关键词选择顺序分解
        state3 = create_initial_state("步骤任务", "需要按step顺序执行的任务")
        assert wrapper._select_decomposition_strategy(state3) == "sequential"
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """测试性能指标记录"""
        decomposition_result = {
            "success": True,
            "decomposition_type": "complex_task",
            "subtasks_count": 5,
            "estimated_duration": 300,
            "decomposition": {"metadata": {"depth": 3}}
        }
        
        mock_decomposer = MockTaskDecomposer(decomposition_result)
        wrapper = TaskDecomposerWrapper(mock_decomposer)
        
        # 创建测试状态
        state = create_initial_state("性能测试", "测试性能指标的任务")
        
        # 执行分解
        updated_state = await wrapper(state)
        
        # 验证性能指标存在
        assert len(updated_state["performance_metrics"]) > 0
        # 检查是否有执行时间指标
        assert any("execution_time" in key for key in updated_state["performance_metrics"].keys())
    
    @pytest.mark.asyncio
    async def test_agent_info(self):
        """测试智能体信息获取"""
        mock_decomposer = MockTaskDecomposer()
        wrapper = TaskDecomposerWrapper(mock_decomposer)
        
        # 获取智能体信息
        info = wrapper.get_agent_info()
        
        # 验证基本信息
        assert info["agent_type"] == "task_decomposer"
        assert info["max_decomposition_depth"] == 5
        assert info["decomposition_timeout"] == 300
        assert info["min_subtask_complexity"] == 0.1
        
        # 验证能力信息
        assert "decomposition_capabilities" in info
        assert "task_decomposition" in info["decomposition_capabilities"]
        assert "dependency_analysis" in info["decomposition_capabilities"]
        
        # 验证支持的分解类型
        assert "supported_decomposition_types" in info
        assert "complex_task" in info["supported_decomposition_types"]
        assert "workflow_analysis" in info["supported_decomposition_types"]
        
        # 验证分解策略
        assert "decomposition_strategies" in info
        assert "hierarchical" in info["decomposition_strategies"]
        assert "parallel" in info["decomposition_strategies"]
        assert "sequential" in info["decomposition_strategies"]
        
        # 验证分析特性
        assert "analysis_features" in info
        assert "bottleneck_identification" in info["analysis_features"]
        assert "critical_path_calculation" in info["analysis_features"]
    
    @pytest.mark.asyncio
    async def test_decomposition_statistics(self):
        """测试分解统计信息"""
        mock_decomposer = MockTaskDecomposer()
        wrapper = TaskDecomposerWrapper(mock_decomposer)
        
        # 执行几次分解以生成统计数据
        state = create_initial_state("统计测试", "测试统计的任务")
        await wrapper(state)
        await wrapper(state)
        
        # 获取分解统计
        stats = wrapper.get_decomposition_statistics()
        
        # 验证统计信息
        assert "decomposition_success_rate" in stats
        assert "average_decomposition_time" in stats
        assert "total_decompositions" in stats
        assert "failed_decompositions" in stats
        assert stats["total_decompositions"] >= 0
    
    @pytest.mark.asyncio
    async def test_configuration_parameters(self):
        """测试配置参数"""
        mock_decomposer = MockTaskDecomposer()
        
        # 使用自定义配置创建包装器
        wrapper = TaskDecomposerWrapper(
            mock_decomposer,
            timeout_seconds=60,
            max_retries=2
        )
        
        # 验证配置
        assert wrapper.timeout_seconds == 60
        assert wrapper.max_retries == 2
        assert wrapper.max_decomposition_depth == 5
        assert wrapper.decomposition_timeout == 300
        assert wrapper.min_subtask_complexity == 0.1
    
    @pytest.mark.asyncio
    async def test_complex_hierarchical_decomposition(self):
        """测试复杂层次分解场景"""
        hierarchical_result = {
            "success": True,
            "decomposition_type": "complex_task",
            "decomposition": {
                "decomposition_strategy": "hierarchical",
                "subtasks": [
                    {"id": "phase1", "name": "Phase 1: Planning", "type": "planning"},
                    {"id": "phase2", "name": "Phase 2: Development", "type": "development"},
                    {"id": "phase3", "name": "Phase 3: Testing", "type": "testing"},
                    {"id": "phase4", "name": "Phase 4: Deployment", "type": "deployment"}
                ],
                "dependencies": [
                    {"from": "phase1", "to": "phase2", "type": "sequential"},
                    {"from": "phase2", "to": "phase3", "type": "sequential"},
                    {"from": "phase3", "to": "phase4", "type": "sequential"}
                ],
                "decomposition_tree": {
                    "root": "complex_task",
                    "children": ["phase1", "phase2", "phase3", "phase4"]
                },
                "metadata": {"depth": 2}
            },
            "execution_plan": {
                "execution_order": ["phase1", "phase2", "phase3", "phase4"],
                "estimated_duration": 480,
                "resource_plan": {"human_resources": 4, "computational_resources": 8},
                "risk_assessment": {"overall_risk_level": "medium"},
                "monitoring_points": [
                    {"task_id": "phase1", "type": "milestone"},
                    {"task_id": "phase3", "type": "milestone"}
                ]
            },
            "subtasks_count": 4,
            "estimated_duration": 480
        }
        
        mock_decomposer = MockTaskDecomposer(hierarchical_result)
        wrapper = TaskDecomposerWrapper(mock_decomposer)
        
        # 创建复杂层次分解场景的测试状态
        state = create_initial_state("大型项目", "需要多阶段层次化分解的大型项目")
        state["workflow_context"]["current_phase"] = WorkflowPhase.DECOMPOSITION
        
        # 执行分解
        updated_state = await wrapper(state)
        
        # 验证复杂层次分解处理
        assert updated_state["workflow_context"]["current_phase"] == WorkflowPhase.COORDINATION
        assert len(updated_state["task_state"]["subtasks"]) == 4
        
        # 验证执行计划
        execution_plan = updated_state["workflow_context"]["execution_metadata"]["execution_plan"]
        assert execution_plan["estimated_duration"] == 480
        assert len(execution_plan["execution_order"]) == 4
        assert "monitoring_points" in execution_plan
        
        # 验证分解历史记录
        decomposition_history = updated_state["workflow_context"]["execution_metadata"]["decomposition_history"]
        assert len(decomposition_history) > 0
        assert decomposition_history[0]["decomposition_type"] == "complex_task"
        assert decomposition_history[0]["subtasks_count"] == 4