"""工作流条件路由逻辑 - 智能决策和动态路由"""

import logging
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from enum import Enum
from abc import ABC, abstractmethod
import re
from datetime import datetime

from ..core.state import LangGraphTaskState, WorkflowPhase
from ..legacy.task_state import TaskStatus
from ..utils.helpers import calculate_complexity_score

logger = logging.getLogger(__name__)


class RoutingDecision(str, Enum):
    """路由决策类型"""
    CONTINUE = "continue"
    SKIP = "skip"
    RETRY = "retry"
    BRANCH = "branch"
    PARALLEL = "parallel"
    END = "end"
    ERROR = "error"


class ConditionOperator(str, Enum):
    """条件操作符"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "ge"
    LESS_EQUAL = "le"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    REGEX_MATCH = "regex_match"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class LogicalOperator(str, Enum):
    """逻辑操作符"""
    AND = "and"
    OR = "or"
    NOT = "not"


class RoutingStrategy(str, Enum):
    """路由策略枚举"""
    COMPLEXITY_BASED = "complexity_based"  # 基于复杂度的路由
    CAPABILITY_BASED = "capability_based"  # 基于能力的路由
    LOAD_BALANCED = "load_balanced"        # 负载均衡路由
    PRIORITY_BASED = "priority_based"      # 基于优先级的路由
    ADAPTIVE = "adaptive"                  # 自适应路由


class ExecutionMode(str, Enum):
    """执行模式枚举"""
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"     # 并行执行
    PIPELINE = "pipeline"     # 流水线执行
    CONDITIONAL = "conditional"  # 条件执行


class TaskComplexity(str, Enum):
    """任务复杂度枚举"""
    SIMPLE = "simple"      # 简单任务 (0.0-0.3)
    MODERATE = "moderate"  # 中等任务 (0.3-0.6)
    COMPLEX = "complex"    # 复杂任务 (0.6-0.8)
    VERY_COMPLEX = "very_complex"  # 非常复杂 (0.8-1.0)


class RouteCondition:
    """路由条件"""
    
    def __init__(
        self,
        field_path: str,
        operator: ConditionOperator,
        value: Any = None,
        description: str = ""
    ):
        self.field_path = field_path
        self.operator = operator
        self.value = value
        self.description = description
    
    def evaluate(self, state: LangGraphTaskState) -> bool:
        """评估条件"""
        try:
            # 获取字段值
            field_value = self._get_field_value(state, self.field_path)
            # 执行条件判断
            return self._apply_operator(field_value, self.operator, self.value)
        except Exception as e:
            logger.error(f"条件评估失败: {e}")
            return False
    
    def _get_field_value(self, state: LangGraphTaskState, field_path: str) -> Any:
        """获取字段值"""
        try:
            # 支持点号分隔的路径，如 "task_state.status"
            parts = field_path.split(".")
            value = state
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = getattr(value, part, None)
                if value is None:
                    break
            return value
        except Exception as e:
            logger.debug(f"获取字段值失败: {field_path}, {e}")
            return None
    
    def _apply_operator(self, field_value: Any, operator: ConditionOperator, expected_value: Any) -> bool:
        """应用操作符"""
        try:
            if operator == ConditionOperator.EQUALS:
                return field_value == expected_value
            elif operator == ConditionOperator.NOT_EQUALS:
                return field_value != expected_value
            elif operator == ConditionOperator.GREATER_THAN:
                return field_value > expected_value
            elif operator == ConditionOperator.LESS_THAN:
                return field_value < expected_value
            elif operator == ConditionOperator.GREATER_EQUAL:
                return field_value >= expected_value
            elif operator == ConditionOperator.LESS_EQUAL:
                return field_value <= expected_value
            elif operator == ConditionOperator.CONTAINS:
                return expected_value in field_value if field_value else False
            elif operator == ConditionOperator.NOT_CONTAINS:
                return expected_value not in field_value if field_value else True
            elif operator == ConditionOperator.IN:
                return field_value in expected_value if expected_value else False
            elif operator == ConditionOperator.NOT_IN:
                return field_value not in expected_value if expected_value else True
            elif operator == ConditionOperator.REGEX_MATCH:
                return bool(re.match(expected_value, str(field_value))) if field_value else False
            elif operator == ConditionOperator.EXISTS:
                return field_value is not None
            elif operator == ConditionOperator.NOT_EXISTS:
                return field_value is None
            else:
                logger.warning(f"未知操作符: {operator}")
                return False
        except Exception as e:
            logger.error(f"操作符应用失败: {operator}, {e}")
            return False


class CompositeCondition:
    """复合条件"""
    
    def __init__(
        self,
        conditions: List[Union[RouteCondition, 'CompositeCondition']],
        operator: LogicalOperator = LogicalOperator.AND,
        description: str = ""
    ):
        self.conditions = conditions
        self.operator = operator
        self.description = description
    
    def evaluate(self, state: LangGraphTaskState) -> bool:
        """评估复合条件"""
        try:
            if not self.conditions:
                return True
            
            results = [condition.evaluate(state) for condition in self.conditions]
            
            if self.operator == LogicalOperator.AND:
                return all(results)
            elif self.operator == LogicalOperator.OR:
                return any(results)
            elif self.operator == LogicalOperator.NOT:
                # NOT操作符只对第一个条件取反
                return not results[0] if results else True
            else:
                logger.warning(f"未知逻辑操作符: {self.operator}")
                return False
        except Exception as e:
            logger.error(f"复合条件评估失败: {e}")
            return False


class RouteRule:
    """路由规则"""
    
    def __init__(
        self,
        name: str,
        condition: Union[RouteCondition, CompositeCondition],
        target: str,
        decision: RoutingDecision = RoutingDecision.CONTINUE,
        priority: int = 0,
        description: str = ""
    ):
        self.name = name
        self.condition = condition
        self.target = target
        self.decision = decision
        self.priority = priority
        self.description = description
        self.execution_count = 0
        self.success_count = 0
    
    def evaluate(self, state: LangGraphTaskState) -> Tuple[bool, RoutingDecision, str]:
        """评估路由规则"""
        try:
            self.execution_count += 1
            
            if self.condition.evaluate(state):
                self.success_count += 1
                logger.debug(f"路由规则 '{self.name}' 匹配，目标: {self.target}")
                return True, self.decision, self.target
            
            return False, RoutingDecision.CONTINUE, ""
        except Exception as e:
            logger.error(f"路由规则评估失败: {self.name}, {e}")
            return False, RoutingDecision.ERROR, ""
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        return self.success_count / self.execution_count if self.execution_count > 0 else 0.0


class ConditionalRouter:
    """条件路由器"""
    
    def __init__(self):
        self.rules: List[RouteRule] = []
        self.default_target = "continue"
        self.default_decision = RoutingDecision.CONTINUE
    
    def add_rule(self, rule: RouteRule) -> None:
        """添加路由规则"""
        self.rules.append(rule)
        # 按优先级排序
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def remove_rule(self, rule_name: str) -> bool:
        """移除路由规则"""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                self.rules.pop(i)
                return True
        return False
    
    def evaluate(self, state: LangGraphTaskState) -> Tuple[RoutingDecision, str]:
        """评估所有规则并返回路由决策"""
        try:
            # 按优先级顺序评估规则
            for rule in self.rules:
                matched, decision, target = rule.evaluate(state)
                if matched:
                    logger.info(f"路由规则 '{rule.name}' 匹配，决策: {decision.value}, 目标: {target}")
                    return decision, target
            
            # 没有规则匹配，返回默认决策
            logger.debug(f"没有规则匹配，使用默认决策: {self.default_decision.value}")
            return self.default_decision, self.default_target
            
        except Exception as e:
            logger.error(f"条件路由评估失败: {e}")
            return RoutingDecision.ERROR, "error"
    
    def get_rule_statistics(self) -> List[Dict[str, Any]]:
        """获取规则统计信息"""
        return [
            {
                "name": rule.name,
                "priority": rule.priority,
                "execution_count": rule.execution_count,
                "success_count": rule.success_count,
                "success_rate": rule.get_success_rate(),
                "description": rule.description
            }
            for rule in self.rules
        ]


class AdvancedRoutingEngine:
    """高级路由引擎"""
    
    def __init__(self):
        self.routers: Dict[str, ConditionalRouter] = {}
        self.global_conditions: List[RouteCondition] = []
        self.routing_history: List[Dict[str, Any]] = []
        self.performance_metrics = {
            "total_evaluations": 0,
            "successful_routes": 0,
            "failed_routes": 0,
            "average_evaluation_time": 0.0
        }
    
    def create_router(self, router_name: str) -> ConditionalRouter:
        """创建新的条件路由器"""
        router = ConditionalRouter()
        self.routers[router_name] = router
        return router
    
    def get_router(self, router_name: str) -> Optional[ConditionalRouter]:
        """获取条件路由器"""
        return self.routers.get(router_name)
    
    def add_global_condition(self, condition: RouteCondition) -> None:
        """添加全局条件"""
        self.global_conditions.append(condition)
    
    def evaluate_router(
        self, 
        router_name: str, 
        state: LangGraphTaskState
    ) -> Tuple[RoutingDecision, str]:
        """评估指定路由器"""
        start_time = datetime.now()
        
        try:
            self.performance_metrics["total_evaluations"] += 1
            
            # 检查全局条件
            for condition in self.global_conditions:
                if not condition.evaluate(state):
                    logger.warning(f"全局条件 '{condition.description}' 不满足")
                    self.performance_metrics["failed_routes"] += 1
                    return RoutingDecision.ERROR, "global_condition_failed"
            
            # 获取路由器
            router = self.routers.get(router_name)
            if not router:
                logger.error(f"路由器 '{router_name}' 不存在")
                self.performance_metrics["failed_routes"] += 1
                return RoutingDecision.ERROR, "router_not_found"
            
            # 评估路由器
            decision, target = router.evaluate(state)
            
            # 记录路由历史
            evaluation_time = (datetime.now() - start_time).total_seconds()
            self.routing_history.append({
                "timestamp": datetime.now().isoformat(),
                "router_name": router_name,
                "decision": decision.value,
                "target": target,
                "evaluation_time": evaluation_time,
                "task_id": state.get("task_state", {}).get("task_id", "unknown")
            })
            
            # 更新性能指标
            if decision != RoutingDecision.ERROR:
                self.performance_metrics["successful_routes"] += 1
            else:
                self.performance_metrics["failed_routes"] += 1
            
            # 更新平均评估时间
            total_time = (
                self.performance_metrics["average_evaluation_time"] * 
                (self.performance_metrics["total_evaluations"] - 1) + 
                evaluation_time
            )
            self.performance_metrics["average_evaluation_time"] = (
                total_time / self.performance_metrics["total_evaluations"]
            )
            
            return decision, target
            
        except Exception as e:
            logger.error(f"路由器评估失败: {router_name}, {e}")
            self.performance_metrics["failed_routes"] += 1
            return RoutingDecision.ERROR, "evaluation_failed"
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            **self.performance_metrics,
            "success_rate": (
                self.performance_metrics["successful_routes"] / 
                self.performance_metrics["total_evaluations"]
                if self.performance_metrics["total_evaluations"] > 0 else 0
            ),
            "total_routers": len(self.routers),
            "total_global_conditions": len(self.global_conditions)
        }
    
    def get_routing_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取路由历史"""
        return self.routing_history[-limit:]
    
    def clear_history(self) -> None:
        """清空路由历史"""
        self.routing_history.clear()


class WorkflowRouter:
    """工作流路由器
    
    负责根据任务状态、复杂度、智能体能力等因素进行智能路由决策。
    集成了高级条件路由引擎，支持复杂的决策树和动态路由策略。
    """
    
    def __init__(
        self,
        routing_strategy: RoutingStrategy = RoutingStrategy.ADAPTIVE,
        complexity_thresholds: Optional[Dict[str, float]] = None
    ):
        self.routing_strategy = routing_strategy
        self.complexity_thresholds = complexity_thresholds or {
            "simple": 0.3,
            "moderate": 0.6,
            "complex": 0.8
        }
        
        # 高级路由引擎
        self.routing_engine = AdvancedRoutingEngine()
        self._setup_default_routers()
        
        # 路由统计
        self.routing_stats = {
            "total_routes": 0,
            "successful_routes": 0,
            "failed_routes": 0,
            "route_decisions": {},
            "complexity_distribution": {
                "simple": 0,
                "moderate": 0,
                "complex": 0,
                "very_complex": 0
            }
        }
    
    def should_analyze(
        self, 
        state: LangGraphTaskState, 
        available_agents: List[str]
    ) -> str:
        """判断是否需要分析阶段"""
        try:
            # 检查是否已经有分析结果
            if "meta_agent" in state["workflow_context"]["agent_results"]:
                logger.debug("分析已完成，跳过分析阶段")
                return "skip"
            
            # 检查是否有MetaAgent可用
            if "meta_agent" not in available_agents:
                logger.debug("MetaAgent不可用，跳过分析阶段")
                return "skip"
            
            # 根据任务复杂度决定是否需要分析
            complexity = self._calculate_task_complexity(state)
            
            if complexity in [TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX]:
                logger.info(f"任务复杂度为{complexity.value}，需要MetaAgent分析")
                return "meta_agent"
            
            # 检查是否有特殊要求需要分析
            if self._requires_analysis(state):
                logger.info("任务有特殊要求，需要MetaAgent分析")
                return "meta_agent"
            
            logger.debug("任务简单，跳过分析阶段")
            return "skip"
            
        except Exception as e:
            logger.error(f"分析路由判断失败: {e}")
            return "skip"
    
    def should_decompose(
        self, 
        state: LangGraphTaskState, 
        available_agents: List[str]
    ) -> str:
        """判断是否需要分解阶段"""
        try:
            # 检查是否有TaskDecomposer可用
            if "task_decomposer" not in available_agents:
                logger.debug("TaskDecomposer不可用，跳过分解阶段")
                return "skip"
            
            # 检查MetaAgent的分析结果
            meta_result = state["workflow_context"]["agent_results"].get("meta_agent", {}).get("result", {})
            
            if meta_result.get("requires_decomposition", False):
                logger.info("MetaAgent建议进行任务分解")
                return "task_decomposer"
            
            # 基于任务复杂度判断
            complexity = self._calculate_task_complexity(state)
            
            if complexity == TaskComplexity.VERY_COMPLEX:
                logger.info(f"任务复杂度为{complexity.value}，需要分解")
                return "task_decomposer"
            
            # 检查任务描述中的分解指示
            if self._indicates_decomposition_needed(state):
                logger.info("任务描述表明需要分解")
                return "task_decomposer"
            
            logger.debug("不需要任务分解")
            return "skip"
            
        except Exception as e:
            logger.error(f"分解路由判断失败: {e}")
            return "skip"
    
    def should_coordinate(
        self, 
        state: LangGraphTaskState, 
        available_agents: List[str]
    ) -> str:
        """判断是否需要协调阶段"""
        try:
            # 检查是否有Coordinator可用
            if "coordinator" not in available_agents:
                logger.debug("Coordinator不可用，跳过协调阶段")
                return "skip"
            
            # 检查是否有子任务需要协调
            subtasks = state["task_state"].get("subtasks", [])
            if subtasks:
                logger.info(f"发现{len(subtasks)}个子任务，需要协调")
                return "coordinator"
            
            # 检查是否有多个智能体参与
            active_agents = len(state["workflow_context"]["agent_results"])
            if active_agents > 1:
                logger.info(f"有{active_agents}个智能体参与，需要协调")
                return "coordinator"
            
            # 检查是否有协调状态需要处理
            coordination_state = state.get("coordination_state", {})
            if coordination_state.get("conflicts") or coordination_state.get("sync_required"):
                logger.info("发现协调状态问题，需要协调")
                return "coordinator"
            
            # 检查任务优先级和资源需求
            if self._requires_coordination(state):
                logger.info("任务特性要求协调")
                return "coordinator"
            
            logger.debug("不需要协调")
            return "skip"
            
        except Exception as e:
            logger.error(f"协调路由判断失败: {e}")
            return "skip"
    
    def determine_execution_mode(
        self, 
        state: LangGraphTaskState, 
        available_agents: List[str]
    ) -> ExecutionMode:
        """确定执行模式"""
        try:
            # 检查子任务的依赖关系
            subtasks = state["task_state"].get("subtasks", [])
            if subtasks:
                dependencies = state["workflow_context"]["execution_metadata"].get("task_dependencies", [])
                
                if not dependencies:
                    # 无依赖关系，可以并行执行
                    logger.info("子任务无依赖关系，选择并行执行")
                    return ExecutionMode.PARALLEL
                
                # 分析依赖关系复杂度
                if self._has_complex_dependencies(dependencies):
                    logger.info("子任务有复杂依赖关系，选择流水线执行")
                    return ExecutionMode.PIPELINE
                else:
                    logger.info("子任务有简单依赖关系，选择顺序执行")
                    return ExecutionMode.SEQUENTIAL
            
            # 检查任务复杂度
            complexity = self._calculate_task_complexity(state)
            
            if complexity == TaskComplexity.SIMPLE:
                return ExecutionMode.SEQUENTIAL
            elif complexity in [TaskComplexity.MODERATE, TaskComplexity.COMPLEX]:
                return ExecutionMode.CONDITIONAL
            else:
                return ExecutionMode.PIPELINE
                
        except Exception as e:
            logger.error(f"执行模式确定失败: {e}")
            return ExecutionMode.SEQUENTIAL
    
    def select_agents_for_execution(
        self, 
        state: LangGraphTaskState, 
        available_agents: List[str],
        agent_capabilities: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """为执行阶段选择智能体"""
        try:
            selected_agents = []
            
            # 获取任务需求
            task_requirements = self._extract_task_requirements(state)
            
            # 根据路由策略选择智能体
            if self.routing_strategy == RoutingStrategy.CAPABILITY_BASED:
                selected_agents = self._select_by_capability(
                    task_requirements, available_agents, agent_capabilities
                )
            elif self.routing_strategy == RoutingStrategy.LOAD_BALANCED:
                selected_agents = self._select_by_load_balance(
                    task_requirements, available_agents, agent_capabilities
                )
            elif self.routing_strategy == RoutingStrategy.PRIORITY_BASED:
                selected_agents = self._select_by_priority(
                    state, available_agents, agent_capabilities
                )
            else:  # ADAPTIVE or COMPLEXITY_BASED
                selected_agents = self._select_adaptively(
                    state, available_agents, agent_capabilities
                )
            
            logger.info(f"为执行阶段选择了{len(selected_agents)}个智能体: {selected_agents}")
            return selected_agents
            
        except Exception as e:
            logger.error(f"智能体选择失败: {e}")
            return available_agents[:1] if available_agents else []
    
    def should_continue_execution(
        self, 
        state: LangGraphTaskState
    ) -> str:
        """判断是否应该继续执行"""
        try:
            # 检查任务状态
            task_status = state["task_state"]["status"]
            
            if task_status == TaskStatus.COMPLETED:
                logger.info("任务已完成")
                return "complete"
            elif task_status == TaskStatus.FAILED:
                logger.info("任务失败")
                return "complete"
            elif task_status == TaskStatus.CANCELLED:
                logger.info("任务已取消")
                return "complete"
            
            # 检查子任务状态
            subtasks = state["task_state"].get("subtasks", [])
            if subtasks:
                pending_subtasks = [task for task in subtasks if task.get("status") == "pending"]
                if pending_subtasks:
                    logger.info(f"还有{len(pending_subtasks)}个子任务待处理")
                    return "continue"
            
            # 检查错误状态
            if state.get("error_state"):
                error_count = state.get("retry_count", 0)
                if error_count < 3:  # 最大重试次数
                    logger.info("发现错误，准备重试")
                    return "retry"
                else:
                    logger.warning("重试次数已达上限，任务失败")
                    return "complete"
            
            # 检查工作流阶段
            current_phase = state["workflow_context"]["current_phase"]
            if current_phase == WorkflowPhase.EXECUTION:
                logger.info("执行阶段完成")
                return "complete"
            
            logger.debug("继续执行")
            return "continue"
            
        except Exception as e:
            logger.error(f"执行继续判断失败: {e}")
            return "complete"
    
    def _calculate_task_complexity(self, state: LangGraphTaskState) -> TaskComplexity:
        """计算任务复杂度"""
        try:
            # 使用现有的复杂度计算函数
            complexity_score = calculate_complexity_score({
                "description": state["task_state"]["description"],
                "requirements": state["task_state"]["requirements"],
                "input_data": state["task_state"]["input_data"],
                "priority": state["task_state"]["priority"]
            })
            
            # 更新统计
            if complexity_score < self.complexity_thresholds["simple"]:
                complexity = TaskComplexity.SIMPLE
                self.routing_stats["complexity_distribution"]["simple"] += 1
            elif complexity_score < self.complexity_thresholds["moderate"]:
                complexity = TaskComplexity.MODERATE
                self.routing_stats["complexity_distribution"]["moderate"] += 1
            elif complexity_score < self.complexity_thresholds["complex"]:
                complexity = TaskComplexity.COMPLEX
                self.routing_stats["complexity_distribution"]["complex"] += 1
            else:
                complexity = TaskComplexity.VERY_COMPLEX
                self.routing_stats["complexity_distribution"]["very_complex"] += 1
            
            logger.debug(f"任务复杂度: {complexity.value} (分数: {complexity_score:.2f})")
            return complexity
            
        except Exception as e:
            logger.error(f"复杂度计算失败: {e}")
            return TaskComplexity.MODERATE
    
    def _requires_analysis(self, state: LangGraphTaskState) -> bool:
        """检查是否需要分析"""
        # 检查任务描述中的关键词
        description = state["task_state"]["description"].lower()
        analysis_keywords = ["分析", "研究", "调查", "评估", "analyze", "research", "investigate", "assess"]
        
        for keyword in analysis_keywords:
            if keyword in description:
                return True
        
        # 检查任务类型
        task_type = state["task_state"]["task_type"]
        if task_type in ["analysis", "research", "investigation", "assessment"]:
            return True
        
        # 检查需求复杂度
        requirements = state["task_state"]["requirements"]
        if len(requirements) > 5:  # 需求较多
            return True
        
        return False
    
    def _indicates_decomposition_needed(self, state: LangGraphTaskState) -> bool:
        """检查是否需要分解"""
        description = state["task_state"]["description"].lower()
        decomposition_keywords = [
            "分解", "拆分", "步骤", "阶段", "分阶段", 
            "decompose", "break down", "steps", "phases", "stages"
        ]
        
        for keyword in decomposition_keywords:
            if keyword in description:
                return True
        
        # 检查需求数量
        requirements = state["task_state"]["requirements"]
        if len(requirements) > 3:
            return True
        
        return False
    
    def _requires_coordination(self, state: LangGraphTaskState) -> bool:
        """检查是否需要协调"""
        # 检查任务优先级
        priority = state["task_state"]["priority"]
        if priority >= 3:  # 高优先级任务
            return True
        
        # 检查任务类型
        task_type = state["task_state"]["task_type"]
        if task_type in ["coordination", "collaboration", "multi_agent"]:
            return True
        
        # 检查输入数据复杂度
        input_data = state["task_state"]["input_data"]
        if len(input_data) > 10:  # 输入数据较多
            return True
        
        return False
    
    def _has_complex_dependencies(self, dependencies: List[Dict[str, Any]]) -> bool:
        """检查是否有复杂依赖关系"""
        if len(dependencies) > 5:  # 依赖关系较多
            return True
        
        # 检查是否有复杂的依赖模式
        from_tasks = {}
        to_tasks = {}
        
        for dep in dependencies:
            from_task = dep.get("from")
            to_task = dep.get("to")
            
            # 统计每个任务作为源和目标的次数
            from_tasks[from_task] = from_tasks.get(from_task, 0) + 1
            to_tasks[to_task] = to_tasks.get(to_task, 0) + 1
        
        # 检查是否有任务依赖多个其他任务（扇入）
        for task, count in to_tasks.items():
            if count > 2:
                return True
        
        # 检查是否有任务被多个其他任务依赖（扇出）
        for task, count in from_tasks.items():
            if count > 2:
                return True
        
        return False
    
    def _extract_task_requirements(self, state: LangGraphTaskState) -> List[str]:
        """提取任务需求"""
        requirements = state["task_state"]["requirements"].copy()
        
        # 从任务描述中提取额外需求
        description = state["task_state"]["description"].lower()
        
        # 添加基于描述的需求
        if "数据" in description or "data" in description:
            requirements.append("data_processing")
        if "分析" in description or "analysis" in description:
            requirements.append("analysis")
        if "报告" in description or "report" in description:
            requirements.append("reporting")
        if "协调" in description or "coordination" in description:
            requirements.append("coordination")
        
        return list(set(requirements))  # 去重
    
    def _select_by_capability(
        self, 
        requirements: List[str], 
        available_agents: List[str], 
        agent_capabilities: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """基于能力选择智能体"""
        selected = []
        
        for agent_id in available_agents:
            capabilities = agent_capabilities.get(agent_id, {}).get("capabilities", [])
            
            # 计算能力匹配度
            match_score = len(set(requirements) & set(capabilities)) / len(requirements) if requirements else 0
            
            if match_score > 0.5:  # 匹配度阈值
                selected.append(agent_id)
        
        return selected or available_agents[:1]  # 至少选择一个
    
    def _select_by_load_balance(
        self, 
        requirements: List[str], 
        available_agents: List[str], 
        agent_capabilities: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """基于负载均衡选择智能体"""
        # 简化的负载均衡：选择负载最低的智能体
        agent_loads = {}
        
        for agent_id in available_agents:
            # 假设从capabilities中获取当前负载
            load = agent_capabilities.get(agent_id, {}).get("current_load", 0)
            agent_loads[agent_id] = load
        
        # 按负载排序
        sorted_agents = sorted(agent_loads.items(), key=lambda x: x[1])
        
        # 选择负载最低的几个智能体
        selected = [agent_id for agent_id, _ in sorted_agents[:min(3, len(sorted_agents))]]
        
        return selected
    
    def _select_by_priority(
        self, 
        state: LangGraphTaskState, 
        available_agents: List[str], 
        agent_capabilities: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """基于优先级选择智能体"""
        task_priority = state["task_state"]["priority"]
        
        # 高优先级任务选择更多智能体
        if task_priority >= 3:
            return available_agents[:min(3, len(available_agents))]
        elif task_priority >= 2:
            return available_agents[:min(2, len(available_agents))]
        else:
            return available_agents[:1]
    
    def _select_adaptively(
        self, 
        state: LangGraphTaskState, 
        available_agents: List[str], 
        agent_capabilities: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """自适应选择智能体"""
        # 综合考虑复杂度、能力、负载等因素
        complexity = self._calculate_task_complexity(state)
        requirements = self._extract_task_requirements(state)
        
        # 基于复杂度确定智能体数量
        if complexity == TaskComplexity.SIMPLE:
            max_agents = 1
        elif complexity == TaskComplexity.MODERATE:
            max_agents = 2
        else:
            max_agents = 3
        
        # 基于能力选择
        capability_selected = self._select_by_capability(requirements, available_agents, agent_capabilities)
        
        # 基于负载均衡调整
        load_balanced = self._select_by_load_balance(requirements, capability_selected, agent_capabilities)
        
        # 取交集并限制数量
        final_selected = list(set(capability_selected) & set(load_balanced))
        
        if not final_selected:
            final_selected = capability_selected[:max_agents]
        
        return final_selected[:max_agents]
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        return {
            "routing_strategy": self.routing_strategy.value,
            "complexity_thresholds": self.complexity_thresholds,
            "routing_stats": self.routing_stats,
            "success_rate": (
                self.routing_stats["successful_routes"] / self.routing_stats["total_routes"]
                if self.routing_stats["total_routes"] > 0 else 0
            )
        }
    
    def update_routing_stats(self, decision: str, success: bool):
        """更新路由统计"""
        self.routing_stats["total_routes"] += 1
        
        if success:
            self.routing_stats["successful_routes"] += 1
        else:
            self.routing_stats["failed_routes"] += 1
        
        if decision not in self.routing_stats["route_decisions"]:
            self.routing_stats["route_decisions"][decision] = 0
        self.routing_stats["route_decisions"][decision] += 1
    
    def _setup_default_routers(self):
        """设置默认路由器"""
        try:
            # 分析阶段路由器
            analysis_router = self.routing_engine.create_router("analysis")
            
            # 规则1: 复杂任务需要分析
            complex_condition = CompositeCondition([
                RouteCondition("task_state.complexity_score", ConditionOperator.GREATER_THAN, 0.6),
                RouteCondition("workflow_context.agent_results.meta_agent", ConditionOperator.NOT_EXISTS)
            ], LogicalOperator.AND)
            
            analysis_router.add_rule(RouteRule(
                name="complex_task_analysis",
                condition=complex_condition,
                target="meta_agent",
                decision=RoutingDecision.CONTINUE,
                priority=10,
                description="复杂任务需要MetaAgent分析"
            ))
            
            # 规则2: 包含分析关键词
            analysis_keyword_condition = RouteCondition(
                "task_state.description", 
                ConditionOperator.REGEX_MATCH, 
                r".*(分析|研究|调查|评估|analyze|research|investigate|assess).*"
            )
            
            analysis_router.add_rule(RouteRule(
                name="analysis_keyword_match",
                condition=analysis_keyword_condition,
                target="meta_agent",
                decision=RoutingDecision.CONTINUE,
                priority=8,
                description="任务描述包含分析关键词"
            ))
            
            # 分解阶段路由器
            decomposition_router = self.routing_engine.create_router("decomposition")
            
            # 规则1: MetaAgent建议分解
            meta_suggests_decomposition = RouteCondition(
                "workflow_context.agent_results.meta_agent.result.requires_decomposition",
                ConditionOperator.EQUALS,
                True
            )
            
            decomposition_router.add_rule(RouteRule(
                name="meta_suggests_decomposition",
                condition=meta_suggests_decomposition,
                target="task_decomposer",
                decision=RoutingDecision.CONTINUE,
                priority=10,
                description="MetaAgent建议进行任务分解"
            ))
            
            # 规则2: 非常复杂的任务
            very_complex_condition = RouteCondition(
                "task_state.complexity_score", 
                ConditionOperator.GREATER_THAN, 
                0.8
            )
            
            decomposition_router.add_rule(RouteRule(
                name="very_complex_task",
                condition=very_complex_condition,
                target="task_decomposer",
                decision=RoutingDecision.CONTINUE,
                priority=9,
                description="非常复杂的任务需要分解"
            ))
            
            # 协调阶段路由器
            coordination_router = self.routing_engine.create_router("coordination")
            
            # 规则1: 有子任务需要协调
            has_subtasks_condition = RouteCondition(
                "task_state.subtasks",
                ConditionOperator.EXISTS
            )
            
            coordination_router.add_rule(RouteRule(
                name="has_subtasks",
                condition=has_subtasks_condition,
                target="coordinator",
                decision=RoutingDecision.CONTINUE,
                priority=10,
                description="有子任务需要协调"
            ))
            
            # 规则2: 多个智能体参与
            multiple_agents_condition = CompositeCondition([
                RouteCondition("workflow_context.agent_results", ConditionOperator.EXISTS),
                # 这里可以添加更复杂的条件来检查智能体数量
            ])
            
            coordination_router.add_rule(RouteRule(
                name="multiple_agents",
                condition=multiple_agents_condition,
                target="coordinator",
                decision=RoutingDecision.CONTINUE,
                priority=8,
                description="多个智能体参与需要协调"
            ))
            
            # 执行控制路由器
            execution_router = self.routing_engine.create_router("execution")
            
            # 规则1: 任务已完成
            task_completed_condition = RouteCondition(
                "task_state.status",
                ConditionOperator.EQUALS,
                TaskStatus.COMPLETED
            )
            
            execution_router.add_rule(RouteRule(
                name="task_completed",
                condition=task_completed_condition,
                target="complete",
                decision=RoutingDecision.END,
                priority=10,
                description="任务已完成"
            ))
            
            # 规则2: 任务失败
            task_failed_condition = RouteCondition(
                "task_state.status",
                ConditionOperator.EQUALS,
                TaskStatus.FAILED
            )
            
            execution_router.add_rule(RouteRule(
                name="task_failed",
                condition=task_failed_condition,
                target="complete",
                decision=RoutingDecision.END,
                priority=10,
                description="任务失败"
            ))
            
            # 规则3: 需要重试
            retry_condition = CompositeCondition([
                RouteCondition("error_state", ConditionOperator.EXISTS),
                RouteCondition("retry_count", ConditionOperator.LESS_THAN, 3)
            ], LogicalOperator.AND)
            
            execution_router.add_rule(RouteRule(
                name="retry_on_error",
                condition=retry_condition,
                target="retry",
                decision=RoutingDecision.RETRY,
                priority=9,
                description="错误状态下重试"
            ))
            
            # 添加全局条件
            self.routing_engine.add_global_condition(
                RouteCondition(
                    "task_state.status",
                    ConditionOperator.NOT_EQUALS,
                    TaskStatus.CANCELLED,
                    "任务未被取消"
                )
            )
            
            logger.info("默认路由器设置完成")
            
        except Exception as e:
            logger.error(f"设置默认路由器失败: {e}")
    
    def evaluate_conditional_route(
        self, 
        router_name: str, 
        state: LangGraphTaskState
    ) -> Tuple[RoutingDecision, str]:
        """使用条件路由引擎评估路由"""
        try:
            decision, target = self.routing_engine.evaluate_router(router_name, state)
            
            # 更新统计
            success = decision != RoutingDecision.ERROR
            self.update_routing_stats(f"{router_name}_{decision.value}", success)
            
            return decision, target
            
        except Exception as e:
            logger.error(f"条件路由评估失败: {router_name}, {e}")
            self.update_routing_stats(f"{router_name}_error", False)
            return RoutingDecision.ERROR, "error"
    
    def should_analyze_advanced(self, state: LangGraphTaskState, available_agents: List[str]) -> str:
        """使用高级条件路由判断是否需要分析"""
        try:
            if "meta_agent" not in available_agents:
                return "skip"
            
            decision, target = self.evaluate_conditional_route("analysis", state)
            
            if decision == RoutingDecision.CONTINUE and target == "meta_agent":
                return "meta_agent"
            else:
                return "skip"
                
        except Exception as e:
            logger.error(f"高级分析路由失败: {e}")
            return self.should_analyze(state, available_agents)  # 回退到原始方法
    
    def should_decompose_advanced(self, state: LangGraphTaskState, available_agents: List[str]) -> str:
        """使用高级条件路由判断是否需要分解"""
        try:
            if "task_decomposer" not in available_agents:
                return "skip"
            
            decision, target = self.evaluate_conditional_route("decomposition", state)
            
            if decision == RoutingDecision.CONTINUE and target == "task_decomposer":
                return "task_decomposer"
            else:
                return "skip"
                
        except Exception as e:
            logger.error(f"高级分解路由失败: {e}")
            return self.should_decompose(state, available_agents)  # 回退到原始方法
    
    def should_coordinate_advanced(self, state: LangGraphTaskState, available_agents: List[str]) -> str:
        """使用高级条件路由判断是否需要协调"""
        try:
            if "coordinator" not in available_agents:
                return "skip"
            
            decision, target = self.evaluate_conditional_route("coordination", state)
            
            if decision == RoutingDecision.CONTINUE and target == "coordinator":
                return "coordinator"
            else:
                return "skip"
                
        except Exception as e:
            logger.error(f"高级协调路由失败: {e}")
            return self.should_coordinate(state, available_agents)  # 回退到原始方法
    
    def should_continue_execution_advanced(self, state: LangGraphTaskState) -> str:
        """使用高级条件路由判断是否继续执行"""
        try:
            decision, target = self.evaluate_conditional_route("execution", state)
            
            if decision == RoutingDecision.END:
                return "complete"
            elif decision == RoutingDecision.RETRY:
                return "retry"
            else:
                return "continue"
                
        except Exception as e:
            logger.error(f"高级执行路由失败: {e}")
            return self.should_continue_execution(state)  # 回退到原始方法
    
    def add_custom_rule(
        self, 
        router_name: str, 
        rule: RouteRule
    ) -> bool:
        """添加自定义路由规则"""
        try:
            router = self.routing_engine.get_router(router_name)
            if not router:
                # 创建新路由器
                router = self.routing_engine.create_router(router_name)
            
            router.add_rule(rule)
            logger.info(f"添加自定义规则 '{rule.name}' 到路由器 '{router_name}'")
            return True
            
        except Exception as e:
            logger.error(f"添加自定义规则失败: {e}")
            return False
    
    def remove_custom_rule(self, router_name: str, rule_name: str) -> bool:
        """移除自定义路由规则"""
        try:
            router = self.routing_engine.get_router(router_name)
            if router:
                result = router.remove_rule(rule_name)
                if result:
                    logger.info(f"移除规则 '{rule_name}' 从路由器 '{router_name}'")
                return result
            return False
            
        except Exception as e:
            logger.error(f"移除自定义规则失败: {e}")
            return False
    
    def get_advanced_routing_statistics(self) -> Dict[str, Any]:
        """获取高级路由统计信息"""
        try:
            engine_metrics = self.routing_engine.get_performance_metrics()
            
            # 获取各路由器的规则统计
            router_stats = {}
            for router_name, router in self.routing_engine.routers.items():
                router_stats[router_name] = router.get_rule_statistics()
            
            return {
                "basic_routing_stats": self.routing_stats,
                "engine_performance": engine_metrics,
                "router_statistics": router_stats,
                "routing_history": self.routing_engine.get_routing_history(50)
            }
            
        except Exception as e:
            logger.error(f"获取高级路由统计失败: {e}")
            return self.get_routing_statistics()
    
    def create_condition_builder(self) -> 'ConditionBuilder':
        """创建条件构建器"""
        return ConditionBuilder()


class ConditionBuilder:
    """条件构建器 - 提供流畅的API来构建复杂条件"""
    
    def __init__(self):
        self.conditions: List[Union[RouteCondition, CompositeCondition]] = []
        self.current_operator = LogicalOperator.AND
    
    def field(self, field_path: str) -> 'FieldConditionBuilder':
        """开始构建字段条件"""
        return FieldConditionBuilder(self, field_path)
    
    def and_condition(self) -> 'ConditionBuilder':
        """设置AND逻辑"""
        self.current_operator = LogicalOperator.AND
        return self
    
    def or_condition(self) -> 'ConditionBuilder':
        """设置OR逻辑"""
        self.current_operator = LogicalOperator.OR
        return self
    
    def not_condition(self) -> 'ConditionBuilder':
        """设置NOT逻辑"""
        self.current_operator = LogicalOperator.NOT
        return self
    
    def build(self) -> Union[RouteCondition, CompositeCondition]:
        """构建最终条件"""
        if len(self.conditions) == 1:
            return self.conditions[0]
        elif len(self.conditions) > 1:
            return CompositeCondition(self.conditions, self.current_operator)
        else:
            raise ValueError("没有条件可以构建")


class FieldConditionBuilder:
    """字段条件构建器"""
    
    def __init__(self, parent: ConditionBuilder, field_path: str):
        self.parent = parent
        self.field_path = field_path
    
    def equals(self, value: Any) -> ConditionBuilder:
        """等于条件"""
        condition = RouteCondition(self.field_path, ConditionOperator.EQUALS, value)
        self.parent.conditions.append(condition)
        return self.parent
    
    def not_equals(self, value: Any) -> ConditionBuilder:
        """不等于条件"""
        condition = RouteCondition(self.field_path, ConditionOperator.NOT_EQUALS, value)
        self.parent.conditions.append(condition)
        return self.parent
    
    def greater_than(self, value: Any) -> ConditionBuilder:
        """大于条件"""
        condition = RouteCondition(self.field_path, ConditionOperator.GREATER_THAN, value)
        self.parent.conditions.append(condition)
        return self.parent
    
    def less_than(self, value: Any) -> ConditionBuilder:
        """小于条件"""
        condition = RouteCondition(self.field_path, ConditionOperator.LESS_THAN, value)
        self.parent.conditions.append(condition)
        return self.parent
    
    def contains(self, value: Any) -> ConditionBuilder:
        """包含条件"""
        condition = RouteCondition(self.field_path, ConditionOperator.CONTAINS, value)
        self.parent.conditions.append(condition)
        return self.parent
    
    def regex_match(self, pattern: str) -> ConditionBuilder:
        """正则匹配条件"""
        condition = RouteCondition(self.field_path, ConditionOperator.REGEX_MATCH, pattern)
        self.parent.conditions.append(condition)
        return self.parent
    
    def exists(self) -> ConditionBuilder:
        """存在条件"""
        condition = RouteCondition(self.field_path, ConditionOperator.EXISTS)
        self.parent.conditions.append(condition)
        return self.parent
    
    def not_exists(self) -> ConditionBuilder:
        """不存在条件"""
        condition = RouteCondition(self.field_path, ConditionOperator.NOT_EXISTS)
        self.parent.conditions.append(condition)
        return self.parent