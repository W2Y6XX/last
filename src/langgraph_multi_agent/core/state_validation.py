"""状态验证和转换逻辑"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

from .state import (
    LangGraphTaskState, WorkflowPhase, TaskStatus,
    validate_state_transition, update_workflow_phase,
    update_task_status, is_state_valid
)

logger = logging.getLogger(__name__)


class StateValidationError(Exception):
    """状态验证错误"""
    pass


class StateTransitionError(Exception):
    """状态转换错误"""
    pass


class StateValidator:
    """状态验证器"""
    
    def __init__(self):
        self.validation_rules = self._initialize_validation_rules()
    
    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """初始化验证规则"""
        return {
            "required_fields": [
                "task_state", "current_node", "workflow_context",
                "coordination_state", "agent_messages", "performance_metrics"
            ],
            "workflow_phase_constraints": {
                WorkflowPhase.INITIALIZATION: {
                    "required_agents": 0,
                    "max_retry_count": 0,
                    "allowed_task_statuses": [TaskStatus.PENDING]
                },
                WorkflowPhase.ANALYSIS: {
                    "required_agents": 1,
                    "max_retry_count": 3,
                    "allowed_task_statuses": [TaskStatus.ANALYZING, TaskStatus.PENDING]
                },
                WorkflowPhase.DECOMPOSITION: {
                    "required_agents": 1,
                    "max_retry_count": 3,
                    "allowed_task_statuses": [TaskStatus.DECOMPOSED, TaskStatus.ANALYZING]
                },
                WorkflowPhase.COORDINATION: {
                    "required_agents": 1,
                    "max_retry_count": 3,
                    "allowed_task_statuses": [TaskStatus.IN_PROGRESS, TaskStatus.DECOMPOSED]
                },
                WorkflowPhase.EXECUTION: {
                    "required_agents": 1,
                    "max_retry_count": 5,
                    "allowed_task_statuses": [TaskStatus.IN_PROGRESS]
                },
                WorkflowPhase.REVIEW: {
                    "required_agents": 0,
                    "max_retry_count": 2,
                    "allowed_task_statuses": [TaskStatus.REVIEWING, TaskStatus.IN_PROGRESS]
                },
                WorkflowPhase.COMPLETION: {
                    "required_agents": 0,
                    "max_retry_count": 0,
                    "allowed_task_statuses": [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
                },
                WorkflowPhase.ERROR_HANDLING: {
                    "required_agents": 0,
                    "max_retry_count": 10,
                    "allowed_task_statuses": [TaskStatus.FAILED, TaskStatus.IN_PROGRESS, TaskStatus.ANALYZING]
                }
            },
            "agent_message_constraints": {
                "max_messages_per_agent": 100,
                "max_total_messages": 1000,
                "required_message_fields": ["message_id", "sender_agent", "timestamp", "content"]
            },
            "performance_constraints": {
                "max_execution_time_hours": 24,
                "max_retry_count": 10,
                "max_active_agents": 50
            }
        }
    
    def validate_state(self, state: LangGraphTaskState) -> Tuple[bool, List[str]]:
        """验证状态完整性"""
        errors = []
        
        try:
            # 基础结构验证
            if not self._validate_basic_structure(state):
                errors.append("基础状态结构无效")
            
            # 字段完整性验证
            missing_fields = self._validate_required_fields(state)
            if missing_fields:
                errors.extend([f"缺少必需字段: {field}" for field in missing_fields])
            
            # 工作流阶段验证
            phase_errors = self._validate_workflow_phase(state)
            errors.extend(phase_errors)
            
            # 智能体消息验证
            message_errors = self._validate_agent_messages(state)
            errors.extend(message_errors)
            
            # 性能约束验证
            performance_errors = self._validate_performance_constraints(state)
            errors.extend(performance_errors)
            
            # 数据一致性验证
            consistency_errors = self._validate_data_consistency(state)
            errors.extend(consistency_errors)
            
        except Exception as e:
            errors.append(f"验证过程中发生错误: {str(e)}")
            logger.error(f"状态验证异常: {e}", exc_info=True)
        
        return len(errors) == 0, errors
    
    def _validate_basic_structure(self, state: LangGraphTaskState) -> bool:
        """验证基础结构"""
        return is_state_valid(state)
    
    def _validate_required_fields(self, state: LangGraphTaskState) -> List[str]:
        """验证必需字段"""
        missing_fields = []
        
        for field in self.validation_rules["required_fields"]:
            if field not in state:
                missing_fields.append(field)
        
        return missing_fields
    
    def _validate_workflow_phase(self, state: LangGraphTaskState) -> List[str]:
        """验证工作流阶段"""
        errors = []
        
        try:
            current_phase = state["workflow_context"]["current_phase"]
            constraints = self.validation_rules["workflow_phase_constraints"].get(current_phase, {})
            
            # 验证智能体数量
            active_agents = len(state["coordination_state"]["active_agents"])
            required_agents = constraints.get("required_agents", 0)
            if active_agents < required_agents:
                errors.append(f"阶段 {current_phase.value} 需要至少 {required_agents} 个智能体，当前只有 {active_agents} 个")
            
            # 验证重试次数
            max_retry = constraints.get("max_retry_count", 10)
            if state["retry_count"] > max_retry:
                errors.append(f"阶段 {current_phase.value} 重试次数 {state['retry_count']} 超过最大限制 {max_retry}")
            
            # 验证任务状态匹配
            allowed_statuses = constraints.get("allowed_task_statuses", [])
            current_status = state["task_state"]["status"]
            if allowed_statuses and current_status not in allowed_statuses:
                errors.append(f"阶段 {current_phase.value} 不允许任务状态 {current_status}")
            
        except Exception as e:
            errors.append(f"工作流阶段验证错误: {str(e)}")
        
        return errors
    
    def _validate_agent_messages(self, state: LangGraphTaskState) -> List[str]:
        """验证智能体消息"""
        errors = []
        
        try:
            messages = state["agent_messages"]
            constraints = self.validation_rules["agent_message_constraints"]
            
            # 验证消息总数
            max_total = constraints["max_total_messages"]
            if len(messages) > max_total:
                errors.append(f"消息总数 {len(messages)} 超过最大限制 {max_total}")
            
            # 验证每个智能体的消息数量
            agent_message_counts = {}
            for message in messages:
                sender = message.get("sender_agent", "unknown")
                agent_message_counts[sender] = agent_message_counts.get(sender, 0) + 1
            
            max_per_agent = constraints["max_messages_per_agent"]
            for agent, count in agent_message_counts.items():
                if count > max_per_agent:
                    errors.append(f"智能体 {agent} 的消息数量 {count} 超过最大限制 {max_per_agent}")
            
            # 验证消息字段完整性
            required_fields = constraints["required_message_fields"]
            for i, message in enumerate(messages):
                for field in required_fields:
                    if field not in message:
                        errors.append(f"消息 {i} 缺少必需字段: {field}")
            
        except Exception as e:
            errors.append(f"智能体消息验证错误: {str(e)}")
        
        return errors
    
    def _validate_performance_constraints(self, state: LangGraphTaskState) -> List[str]:
        """验证性能约束"""
        errors = []
        
        try:
            constraints = self.validation_rules["performance_constraints"]
            
            # 验证执行时间
            if state["execution_start_time"]:
                current_time = datetime.now()
                execution_hours = (current_time - state["execution_start_time"]).total_seconds() / 3600
                max_hours = constraints["max_execution_time_hours"]
                if execution_hours > max_hours:
                    errors.append(f"执行时间 {execution_hours:.2f} 小时超过最大限制 {max_hours} 小时")
            
            # 验证重试次数
            max_retries = constraints["max_retry_count"]
            if state["retry_count"] > max_retries:
                errors.append(f"重试次数 {state['retry_count']} 超过最大限制 {max_retries}")
            
            # 验证活跃智能体数量
            active_agents = len(state["coordination_state"]["active_agents"])
            max_agents = constraints["max_active_agents"]
            if active_agents > max_agents:
                errors.append(f"活跃智能体数量 {active_agents} 超过最大限制 {max_agents}")
            
        except Exception as e:
            errors.append(f"性能约束验证错误: {str(e)}")
        
        return errors
    
    def _validate_data_consistency(self, state: LangGraphTaskState) -> List[str]:
        """验证数据一致性"""
        errors = []
        
        try:
            # 验证工作流阶段与任务状态的一致性
            phase = state["workflow_context"]["current_phase"]
            task_status = state["task_state"]["status"]
            
            # 定义阶段与状态的映射关系
            phase_status_mapping = {
                WorkflowPhase.INITIALIZATION: [TaskStatus.PENDING],
                WorkflowPhase.ANALYSIS: [TaskStatus.ANALYZING, TaskStatus.PENDING],
                WorkflowPhase.DECOMPOSITION: [TaskStatus.DECOMPOSED, TaskStatus.ANALYZING],
                WorkflowPhase.COORDINATION: [TaskStatus.IN_PROGRESS, TaskStatus.DECOMPOSED],
                WorkflowPhase.EXECUTION: [TaskStatus.IN_PROGRESS],
                WorkflowPhase.REVIEW: [TaskStatus.REVIEWING, TaskStatus.IN_PROGRESS],
                WorkflowPhase.COMPLETION: [TaskStatus.COMPLETED, TaskStatus.CANCELLED],
                WorkflowPhase.ERROR_HANDLING: [TaskStatus.FAILED, TaskStatus.IN_PROGRESS, TaskStatus.ANALYZING]
            }
            
            expected_statuses = phase_status_mapping.get(phase, [])
            if expected_statuses and task_status not in expected_statuses:
                errors.append(f"工作流阶段 {phase.value} 与任务状态 {task_status.value} 不一致")
            
            # 验证智能体分配与活跃智能体的一致性
            active_agents = set(state["coordination_state"]["active_agents"])
            assigned_agents = set()
            for agent_list in state["coordination_state"]["agent_assignments"].values():
                assigned_agents.update(agent_list)
            
            # 检查是否有分配但不活跃的智能体
            inactive_assigned = assigned_agents - active_agents
            if inactive_assigned:
                errors.append(f"智能体 {list(inactive_assigned)} 已分配任务但不在活跃列表中")
            
            # 验证时间戳的逻辑性
            start_time = state["execution_start_time"]
            end_time = state["execution_end_time"]
            if start_time and end_time and end_time < start_time:
                errors.append("执行结束时间早于开始时间")
            
            # 验证阶段时间的逻辑性
            phase_times = state["workflow_context"]["phase_start_times"]
            sorted_phases = sorted(phase_times.items(), key=lambda x: x[1])
            for i in range(1, len(sorted_phases)):
                if sorted_phases[i][1] < sorted_phases[i-1][1]:
                    errors.append(f"阶段时间顺序错误: {sorted_phases[i][0]} 早于 {sorted_phases[i-1][0]}")
            
        except Exception as e:
            errors.append(f"数据一致性验证错误: {str(e)}")
        
        return errors


class StateTransitionManager:
    """状态转换管理器"""
    
    def __init__(self):
        self.validator = StateValidator()
        self.transition_hooks = {}
    
    def register_transition_hook(self, phase: WorkflowPhase, hook_func):
        """注册状态转换钩子"""
        if phase not in self.transition_hooks:
            self.transition_hooks[phase] = []
        self.transition_hooks[phase].append(hook_func)
    
    def safe_transition_to_phase(
        self, 
        state: LangGraphTaskState, 
        target_phase: WorkflowPhase,
        force: bool = False
    ) -> Tuple[LangGraphTaskState, bool, List[str]]:
        """安全地转换到目标阶段"""
        errors = []
        
        try:
            # 验证当前状态
            is_valid, validation_errors = self.validator.validate_state(state)
            if not is_valid and not force:
                errors.extend(validation_errors)
                return state, False, errors
            
            # 验证转换是否有效
            if not validate_state_transition(state, target_phase) and not force:
                current_phase = state["workflow_context"]["current_phase"]
                errors.append(f"无效的状态转换: {current_phase.value} -> {target_phase.value}")
                return state, False, errors
            
            # 执行转换前钩子
            if target_phase in self.transition_hooks:
                for hook in self.transition_hooks[target_phase]:
                    try:
                        state = hook(state, "before")
                    except Exception as e:
                        logger.warning(f"转换前钩子执行失败: {e}")
            
            # 执行状态转换
            old_phase = state["workflow_context"]["current_phase"]
            state = update_workflow_phase(state, target_phase)
            
            # 执行转换后钩子
            if target_phase in self.transition_hooks:
                for hook in self.transition_hooks[target_phase]:
                    try:
                        state = hook(state, "after")
                    except Exception as e:
                        logger.warning(f"转换后钩子执行失败: {e}")
            
            # 记录转换
            logger.info(f"状态转换成功: {old_phase.value} -> {target_phase.value}")
            
            return state, True, []
            
        except Exception as e:
            error_msg = f"状态转换异常: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
            return state, False, errors
    
    def safe_update_task_status(
        self,
        state: LangGraphTaskState,
        new_status: TaskStatus,
        force: bool = False
    ) -> Tuple[LangGraphTaskState, bool, List[str]]:
        """安全地更新任务状态"""
        errors = []
        
        try:
            # 验证当前状态
            is_valid, validation_errors = self.validator.validate_state(state)
            if not is_valid and not force:
                errors.extend(validation_errors)
                return state, False, errors
            
            # 记录旧状态
            old_status = state["task_state"]["status"]
            
            # 执行状态更新
            state = update_task_status(state, new_status)
            
            # 记录更新
            logger.info(f"任务状态更新成功: {old_status.value} -> {new_status.value}")
            
            return state, True, []
            
        except Exception as e:
            error_msg = f"任务状态更新异常: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
            return state, False, errors
    
    def validate_and_repair_state(
        self, 
        state: LangGraphTaskState
    ) -> Tuple[LangGraphTaskState, bool, List[str]]:
        """验证并修复状态"""
        errors = []
        repaired = False
        
        try:
            # 验证状态
            is_valid, validation_errors = self.validator.validate_state(state)
            
            if not is_valid:
                errors.extend(validation_errors)
                
                # 尝试修复常见问题
                state, repair_success = self._attempt_state_repair(state, validation_errors)
                if repair_success:
                    repaired = True
                    # 重新验证修复后的状态
                    is_valid, remaining_errors = self.validator.validate_state(state)
                    if remaining_errors:
                        errors.extend([f"修复后仍存在问题: {err}" for err in remaining_errors])
            
            return state, is_valid and repaired, errors
            
        except Exception as e:
            error_msg = f"状态修复异常: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
            return state, False, errors
    
    def _attempt_state_repair(
        self, 
        state: LangGraphTaskState, 
        errors: List[str]
    ) -> Tuple[LangGraphTaskState, bool]:
        """尝试修复状态"""
        repaired = False
        
        try:
            # 修复缺失的字段
            if "缺少必需字段" in str(errors):
                state = self._repair_missing_fields(state)
                repaired = True
            
            # 修复时间戳问题
            if "时间" in str(errors):
                state = self._repair_timestamp_issues(state)
                repaired = True
            
            # 修复智能体一致性问题
            if "智能体" in str(errors):
                state = self._repair_agent_consistency(state)
                repaired = True
            
            return state, repaired
            
        except Exception as e:
            logger.error(f"状态修复失败: {e}", exc_info=True)
            return state, False
    
    def _repair_missing_fields(self, state: LangGraphTaskState) -> LangGraphTaskState:
        """修复缺失字段"""
        # 确保所有必需字段存在
        if "agent_messages" not in state:
            state["agent_messages"] = []
        
        if "performance_metrics" not in state:
            state["performance_metrics"] = {}
        
        if "coordination_state" not in state:
            from .state import CoordinationState
            state["coordination_state"] = CoordinationState(
                active_agents=[],
                agent_assignments={},
                resource_allocation={},
                coordination_mode="centralized",
                sync_points=[],
                conflicts=[]
            )
        
        return state
    
    def _repair_timestamp_issues(self, state: LangGraphTaskState) -> LangGraphTaskState:
        """修复时间戳问题"""
        current_time = datetime.now()
        
        # 修复执行时间问题
        if state.get("execution_end_time") and state.get("execution_start_time"):
            if state["execution_end_time"] < state["execution_start_time"]:
                state["execution_end_time"] = None
        
        # 确保阶段开始时间存在
        current_phase = state["workflow_context"]["current_phase"]
        if current_phase.value not in state["workflow_context"]["phase_start_times"]:
            state["workflow_context"]["phase_start_times"][current_phase.value] = current_time
        
        return state
    
    def _repair_agent_consistency(self, state: LangGraphTaskState) -> LangGraphTaskState:
        """修复智能体一致性问题"""
        # 清理不活跃的智能体分配
        active_agents = set(state["coordination_state"]["active_agents"])
        assignments = state["coordination_state"]["agent_assignments"]
        
        # 移除不活跃智能体的分配
        inactive_agents = set(assignments.keys()) - active_agents
        for agent in inactive_agents:
            del assignments[agent]
        
        return state


# 全局实例
state_validator = StateValidator()
state_transition_manager = StateTransitionManager()


def validate_state(state: LangGraphTaskState) -> Tuple[bool, List[str]]:
    """验证状态（便捷函数）"""
    return state_validator.validate_state(state)


def safe_transition_to_phase(
    state: LangGraphTaskState, 
    target_phase: WorkflowPhase,
    force: bool = False
) -> Tuple[LangGraphTaskState, bool, List[str]]:
    """安全状态转换（便捷函数）"""
    return state_transition_manager.safe_transition_to_phase(state, target_phase, force)


def safe_update_task_status(
    state: LangGraphTaskState,
    new_status: TaskStatus,
    force: bool = False
) -> Tuple[LangGraphTaskState, bool, List[str]]:
    """安全任务状态更新（便捷函数）"""
    return state_transition_manager.safe_update_task_status(state, new_status, force)