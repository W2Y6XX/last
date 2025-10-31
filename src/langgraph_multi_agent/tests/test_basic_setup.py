"""基础设置测试"""

import pytest
from datetime import datetime
from langgraph_multi_agent.core.state import (
    LangGraphTaskState,
    create_initial_state,
    WorkflowPhase,
    update_workflow_phase,
    add_agent_message
)
from langgraph_multi_agent.utils.config import Config
from langgraph_multi_agent.utils.helpers import create_task_id, calculate_complexity_score


class TestBasicSetup:
    """基础设置测试类"""
    
    def test_config_creation(self):
        """测试配置创建"""
        config = Config()
        
        assert config.database.redis_url == "redis://localhost:6379/0"
        assert config.api.port == 8000
        assert config.agent.max_retries == 3
        assert config.langgraph.checkpoint_storage == "sqlite"
    
    def test_task_id_creation(self):
        """测试任务ID创建"""
        task_id1 = create_task_id()
        task_id2 = create_task_id()
        
        assert task_id1 != task_id2
        assert len(task_id1) == 36  # UUID长度
        assert len(task_id2) == 36
    
    def test_initial_state_creation(self):
        """测试初始状态创建"""
        state = create_initial_state(
            title="测试任务",
            description="这是一个测试任务",
            task_type="test",
            priority=2,
            input_data={"test_key": "test_value"}
        )
        
        # 验证基础任务状态
        assert state["task_state"]["title"] == "测试任务"
        assert state["task_state"]["description"] == "这是一个测试任务"
        assert state["task_state"]["task_type"] == "test"
        assert state["task_state"]["priority"] == 2
        assert state["task_state"]["input_data"]["test_key"] == "test_value"
        
        # 验证LangGraph特有字段
        assert state["current_node"] == "start"
        assert state["next_nodes"] == ["meta_agent"]
        assert state["should_continue"] is True
        assert state["workflow_context"]["current_phase"] == WorkflowPhase.INITIALIZATION
        assert state["retry_count"] == 0
        assert isinstance(state["execution_start_time"], datetime)
    
    def test_workflow_phase_update(self):
        """测试工作流阶段更新"""
        state = create_initial_state("测试任务", "测试描述")
        
        # 更新到分析阶段
        updated_state = update_workflow_phase(state, WorkflowPhase.ANALYSIS)
        
        assert updated_state["workflow_context"]["current_phase"] == WorkflowPhase.ANALYSIS
        assert WorkflowPhase.INITIALIZATION in updated_state["workflow_context"]["completed_phases"]
        assert WorkflowPhase.ANALYSIS.value in updated_state["workflow_context"]["phase_start_times"]
    
    def test_agent_message_addition(self):
        """测试智能体消息添加"""
        state = create_initial_state("测试任务", "测试描述")
        
        # 添加智能体消息
        updated_state = add_agent_message(
            state,
            sender_agent="meta_agent",
            content={"analysis_result": "complex_task"},
            message_type="analysis_result"
        )
        
        assert len(updated_state["agent_messages"]) == 1
        message = updated_state["agent_messages"][0]
        assert message["sender_agent"] == "meta_agent"
        assert message["content"]["analysis_result"] == "complex_task"
        assert message["message_type"] == "analysis_result"
    
    def test_complexity_score_calculation(self):
        """测试复杂度分数计算"""
        # 简单任务
        simple_task = {
            "description": "简单任务",
            "requirements": ["req1"],
            "input_data": {"key": "value"},
            "priority": 1
        }
        simple_score = calculate_complexity_score(simple_task)
        assert 0.0 <= simple_score <= 1.0
        
        # 复杂任务
        complex_task = {
            "description": "这是一个非常复杂的任务，需要大量的处理和分析。" * 20,
            "requirements": ["req1", "req2", "req3", "req4", "req5", "req6"],
            "input_data": {f"key{i}": f"value{i}" for i in range(15)},
            "priority": 5
        }
        complex_score = calculate_complexity_score(complex_task)
        assert complex_score > simple_score
        assert complex_score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__])