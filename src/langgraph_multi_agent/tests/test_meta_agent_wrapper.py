"""MetaAgent包装器测试"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from langgraph_multi_agent.agents.meta_agent_wrapper import MetaAgentWrapper
from langgraph_multi_agent.core.state import (
    create_initial_state,
    WorkflowPhase,
    LangGraphTaskState
)
from langgraph_multi_agent.legacy.task_state import TaskStatus


class MockMetaAgent:
    """模拟MetaAgent用于测试"""
    
    def __init__(self, analysis_result: Dict[str, Any] = None, should_fail: bool = False):
        self.analysis_result = analysis_result or {
            "success": True,
            "complexity_score": 0.5,
            "requires_decomposition": False,
            "clarification_needed": False,
            "recommended_agents": ["research_agent"],
            "analysis_summary": "任务分析完成",
            "next_steps": ["分配给研究智能体"],
            "coordination_strategy": "sequential"
        }
        self.should_fail = should_fail
        self.call_count = 0
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟任务处理"""
        self.call_count += 1
        
        if self.should_fail:
            raise ValueError("MetaAgent分析失败")
        
        # 模拟分析时间
        await asyncio.sleep(0.1)
        
        return self.analysis_result


class TestMetaAgentWrapper:
    """MetaAgent包装器测试类"""
    
    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        """测试成功的任务分析"""
        mock_meta_agent = MockMetaAgent()
        wrapper = MetaAgentWrapper(mock_meta_agent)
        
        # 创建测试状态
        state = create_initial_state("测试任务", "这是一个测试任务")
        
        # 执行分析
        updated_state = await wrapper(state)
        
        # 验证结果
        assert len(updated_state["agent_messages"]) > 0
        assert updated_state["workflow_context"]["agent_results"]["meta_agent"]["result"]["success"] is True
        assert "meta_agent" in updated_state["task_state"]["output_data"]
        assert updated_state["task_state"]["output_data"]["meta_agent"]["analysis_completed"] is True
        
        # 验证工作流阶段转换
        assert updated_state["workflow_context"]["current_phase"] == WorkflowPhase.COORDINATION
        
        # 验证性能指标存在
        assert len(updated_state["performance_metrics"]) > 0
    
    @pytest.mark.asyncio
    async def test_clarification_needed_analysis(self):
        """测试需要澄清的任务分析"""
        analysis_result = {
            "success": True,
            "complexity_score": 0.4,
            "requires_decomposition": False,
            "clarification_needed": True,
            "clarification_questions": ["请明确具体需求", "预期输出格式是什么？"],
            "analysis_summary": "任务需要进一步澄清"
        }
        
        mock_meta_agent = MockMetaAgent(analysis_result)
        wrapper = MetaAgentWrapper(mock_meta_agent)
        
        # 创建测试状态
        state = create_initial_state("模糊任务", "请帮我处理一些东西")
        
        # 执行分析
        updated_state = await wrapper(state)
        
        # 验证澄清流程
        assert updated_state["workflow_context"]["current_phase"] == WorkflowPhase.ANALYSIS
        assert updated_state["workflow_context"]["execution_metadata"]["clarification_required"] is True
        assert len(updated_state["workflow_context"]["execution_metadata"]["clarification_questions"]) == 2
    
    @pytest.mark.asyncio
    async def test_decomposition_needed_analysis(self):
        """测试需要拆解的复杂任务分析"""
        analysis_result = {
            "success": True,
            "complexity_score": 0.8,
            "requires_decomposition": True,
            "clarification_needed": False,
            "decomposition_strategy": "parallel",
            "estimated_subtasks": 3,
            "analysis_summary": "复杂任务需要拆解"
        }
        
        mock_meta_agent = MockMetaAgent(analysis_result)
        wrapper = MetaAgentWrapper(mock_meta_agent)
        
        # 创建测试状态
        state = create_initial_state("复杂任务", "这是一个需要多步骤处理的复杂任务")
        
        # 执行分析
        updated_state = await wrapper(state)
        
        # 验证拆解流程
        assert updated_state["workflow_context"]["current_phase"] == WorkflowPhase.DECOMPOSITION
        assert updated_state["workflow_context"]["execution_metadata"]["decomposition_strategy"] == "parallel"
        assert updated_state["workflow_context"]["execution_metadata"]["subtask_count"] == 3
    
    @pytest.mark.asyncio
    async def test_simple_task_analysis(self):
        """测试简单任务分析"""
        analysis_result = {
            "success": True,
            "complexity_score": 0.1,
            "requires_decomposition": False,
            "clarification_needed": False,
            "recommended_agents": [],
            "analysis_summary": "简单任务可直接执行"
        }
        
        mock_meta_agent = MockMetaAgent(analysis_result)
        wrapper = MetaAgentWrapper(mock_meta_agent)
        
        # 创建测试状态
        state = create_initial_state("简单任务", "计算1+1")
        
        # 执行分析
        updated_state = await wrapper(state)
        
        # 验证直接执行流程
        assert updated_state["workflow_context"]["current_phase"] == WorkflowPhase.EXECUTION
        assert updated_state["task_state"]["status"] == TaskStatus.IN_PROGRESS
    
    @pytest.mark.asyncio
    async def test_analysis_failure(self):
        """测试分析失败处理"""
        mock_meta_agent = MockMetaAgent(should_fail=True)
        wrapper = MetaAgentWrapper(mock_meta_agent)
        
        # 创建测试状态
        state = create_initial_state("测试任务", "测试任务描述")
        
        # 执行分析
        updated_state = await wrapper(state)
        
        # 验证错误处理 - 检查是否有错误消息
        error_messages = [msg for msg in updated_state["agent_messages"] 
                         if msg["message_type"] == "analysis_error"]
        assert len(error_messages) > 0
        
        # 验证执行失败 - 检查是否有错误消息
        error_messages = [msg for msg in updated_state["agent_messages"] 
                         if msg["message_type"] == "analysis_error"]
        assert len(error_messages) > 0
    
    @pytest.mark.asyncio
    async def test_task_data_extraction(self):
        """测试任务数据提取"""
        mock_meta_agent = MockMetaAgent()
        wrapper = MetaAgentWrapper(mock_meta_agent)
        
        # 创建测试状态
        state = create_initial_state("测试任务", "测试任务描述")
        state["task_state"]["requirements"] = ["需求1", "需求2"]
        state["task_state"]["priority"] = 2
        
        # 提取任务数据
        task_data = wrapper._extract_task_data(state)
        
        # 验证数据提取
        assert task_data["title"] == "测试任务"
        assert task_data["description"] == "测试任务描述"
        assert task_data["requirements"] == ["需求1", "需求2"]
        assert task_data["priority"] == 2
        assert "initial_complexity" in task_data
        assert task_data["analysis_mode"] == "comprehensive"
        assert task_data["include_recommendations"] is True
        assert task_data["clarification_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """测试性能指标记录"""
        analysis_result = {
            "success": True,
            "complexity_score": 0.6,
            "requires_decomposition": True,
            "recommended_agents": ["agent1", "agent2"],
            "clarification_needed": False
        }
        
        mock_meta_agent = MockMetaAgent(analysis_result)
        wrapper = MetaAgentWrapper(mock_meta_agent)
        
        # 创建测试状态
        state = create_initial_state("测试任务", "测试任务描述")
        
        # 执行分析
        updated_state = await wrapper(state)
        
        # 验证性能指标存在
        assert len(updated_state["performance_metrics"]) > 0
        # 检查是否有执行时间指标
        assert any("execution_time" in key for key in updated_state["performance_metrics"].keys())
    
    @pytest.mark.asyncio
    async def test_agent_info(self):
        """测试智能体信息获取"""
        mock_meta_agent = MockMetaAgent()
        wrapper = MetaAgentWrapper(mock_meta_agent)
        
        # 获取智能体信息
        info = wrapper.get_agent_info()
        
        # 验证基本信息
        assert info["agent_type"] == "meta_agent"
        assert info["complexity_threshold"] == 0.6
        assert info["decomposition_threshold"] == 0.7
        assert info["max_clarification_rounds"] == 3
        
        # 验证能力信息
        assert "analysis_capabilities" in info
        assert "task_complexity_assessment" in info["analysis_capabilities"]
        assert "requirement_clarification" in info["analysis_capabilities"]
        
        # 验证支持的任务类型
        assert "supported_task_types" in info
        assert "general" in info["supported_task_types"]
        assert "complex_workflow" in info["supported_task_types"]
    
    @pytest.mark.asyncio
    async def test_configuration_parameters(self):
        """测试配置参数"""
        mock_meta_agent = MockMetaAgent()
        
        # 使用自定义配置创建包装器
        wrapper = MetaAgentWrapper(
            mock_meta_agent,
            timeout_seconds=30,
            max_retries=2
        )
        
        # 验证配置
        assert wrapper.timeout_seconds == 30
        assert wrapper.max_retries == 2
        assert wrapper.complexity_threshold == 0.6
        assert wrapper.requires_decomposition_threshold == 0.7
        assert wrapper.max_clarification_rounds == 3
    
    @pytest.mark.asyncio
    async def test_complex_workflow_handling(self):
        """测试复杂工作流处理"""
        analysis_result = {
            "success": True,
            "complexity_score": 0.9,
            "requires_decomposition": True,
            "clarification_needed": False,
            "recommended_agents": ["research_agent", "analysis_agent", "synthesis_agent"],
            "decomposition_strategy": "hierarchical",
            "coordination_strategy": "collaborative",
            "estimated_subtasks": 5,
            "analysis_summary": "高复杂度任务需要多智能体协作"
        }
        
        mock_meta_agent = MockMetaAgent(analysis_result)
        wrapper = MetaAgentWrapper(mock_meta_agent)
        
        # 创建测试状态
        state = create_initial_state("复杂工作流", "需要多步骤协作的复杂任务")
        
        # 执行分析
        updated_state = await wrapper(state)
        
        # 验证复杂工作流处理
        assert updated_state["workflow_context"]["current_phase"] == WorkflowPhase.DECOMPOSITION
        assert updated_state["workflow_context"]["execution_metadata"]["decomposition_strategy"] == "hierarchical"
        assert updated_state["workflow_context"]["execution_metadata"]["subtask_count"] == 5
        
        # 验证分析结果记录
        meta_analysis = updated_state["workflow_context"]["execution_metadata"]["meta_analysis"]
        assert meta_analysis["complexity_score"] == 0.9
        assert meta_analysis["requires_decomposition"] is True