"""多智能体工作流引擎 - 基于LangGraph的StateGraph实现"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Union, Literal
from datetime import datetime
from enum import Enum

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from ..core.state import (
    LangGraphTaskState,
    WorkflowPhase,
    create_initial_state,
    update_workflow_phase,
    update_task_status,
    add_agent_message,
    create_checkpoint,
    validate_state_transition
)
from ..legacy.task_state import TaskStatus
from ..agents.meta_agent_wrapper import MetaAgentWrapper
from ..agents.coordinator_wrapper import CoordinatorWrapper
from ..agents.task_decomposer_wrapper import TaskDecomposerWrapper
from ..agents.generic_wrapper import GenericAgentWrapper
from .routing import WorkflowRouter, RoutingStrategy, ExecutionMode

logger = logging.getLogger(__name__)


class WorkflowExecutionMode(str, Enum):
    """工作流执行模式"""
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"     # 并行执行
    ADAPTIVE = "adaptive"     # 自适应执行


class WorkflowStatus(str, Enum):
    """工作流状态"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MultiAgentWorkflow:
    """多智能体工作流引擎
    
    基于LangGraph的StateGraph实现，提供多智能体协作的工作流编排和执行能力。
    支持智能体节点的动态路由、条件执行、检查点恢复等功能。
    """
    
    def __init__(
        self,
        workflow_id: str,
        checkpointer: Optional[MemorySaver] = None,
        execution_mode: WorkflowExecutionMode = WorkflowExecutionMode.ADAPTIVE,
        routing_strategy: RoutingStrategy = RoutingStrategy.ADAPTIVE,
        max_iterations: int = 100,
        timeout_seconds: int = 3600
    ):
        self.workflow_id = workflow_id
        self.execution_mode = execution_mode
        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds
        
        # 检查点管理器
        self.checkpointer = checkpointer or MemorySaver()
        
        # 路由器
        self.router = WorkflowRouter(routing_strategy)
        
        # 工作流状态
        self.status = WorkflowStatus.CREATED
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # 智能体注册表
        self.agents: Dict[str, Any] = {}
        self.agent_wrappers: Dict[str, Any] = {}
        
        # 工作流图
        self.graph: Optional[StateGraph] = None
        self.compiled_graph: Optional[Any] = None
        
        # 执行统计
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "total_nodes_executed": 0
        }
        
        # 初始化工作流图
        self._initialize_workflow_graph()
    
    def _initialize_workflow_graph(self):
        """初始化工作流图结构"""
        try:
            # 创建StateGraph
            self.graph = StateGraph(LangGraphTaskState)
            
            # 添加智能体节点（稍后注册时添加）
            # 这里先定义基本的工作流结构
            
            # 添加条件路由节点
            self.graph.add_node("route_to_analysis", self._route_to_analysis)
            self.graph.add_node("route_to_decomposition", self._route_to_decomposition)
            self.graph.add_node("route_to_coordination", self._route_to_coordination)
            self.graph.add_node("route_to_execution", self._route_to_execution)
            self.graph.add_node("route_to_completion", self._route_to_completion)
            
            # 设置入口点
            self.graph.set_entry_point("route_to_analysis")
            
            logger.info(f"工作流图初始化完成: {self.workflow_id}")
            
        except Exception as e:
            logger.error(f"工作流图初始化失败: {e}")
            raise
    
    def register_agent(
        self,
        agent_id: str,
        agent_instance: Any,
        agent_type: str = "generic",
        **wrapper_kwargs
    ) -> None:
        """注册智能体到工作流
        
        Args:
            agent_id: 智能体唯一标识
            agent_instance: 智能体实例
            agent_type: 智能体类型 (meta_agent, coordinator, task_decomposer, generic)
            **wrapper_kwargs: 包装器额外参数
        """
        try:
            # 创建对应的包装器
            if agent_type == "meta_agent":
                wrapper = MetaAgentWrapper(agent_instance, **wrapper_kwargs)
            elif agent_type == "coordinator":
                wrapper = CoordinatorWrapper(agent_instance, **wrapper_kwargs)
            elif agent_type == "task_decomposer":
                wrapper = TaskDecomposerWrapper(agent_instance, **wrapper_kwargs)
            else:
                wrapper = GenericAgentWrapper(agent_instance, agent_type, **wrapper_kwargs)
            
            # 注册智能体和包装器
            self.agents[agent_id] = agent_instance
            self.agent_wrappers[agent_id] = wrapper
            
            # 添加到工作流图
            self.graph.add_node(agent_id, wrapper)
            
            logger.info(f"智能体注册成功: {agent_id} ({agent_type})")
            
        except Exception as e:
            logger.error(f"智能体注册失败 {agent_id}: {e}")
            raise
    
    def add_conditional_edge(
        self,
        source_node: str,
        condition_func: Callable[[LangGraphTaskState], str],
        condition_map: Dict[str, str]
    ) -> None:
        """添加条件边
        
        Args:
            source_node: 源节点
            condition_func: 条件判断函数
            condition_map: 条件映射 {condition_result: target_node}
        """
        try:
            self.graph.add_conditional_edges(
                source_node,
                condition_func,
                condition_map
            )
            logger.debug(f"条件边添加成功: {source_node} -> {condition_map}")
            
        except Exception as e:
            logger.error(f"条件边添加失败: {e}")
            raise
    
    def add_edge(self, source_node: str, target_node: str) -> None:
        """添加直接边
        
        Args:
            source_node: 源节点
            target_node: 目标节点
        """
        try:
            self.graph.add_edge(source_node, target_node)
            logger.debug(f"边添加成功: {source_node} -> {target_node}")
            
        except Exception as e:
            logger.error(f"边添加失败: {e}")
            raise
    
    def compile_workflow(self) -> None:
        """编译工作流图"""
        try:
            if not self.graph:
                raise ValueError("工作流图未初始化")
            
            # 设置默认的工作流路由
            self._setup_default_routing()
            
            # 编译图
            self.compiled_graph = self.graph.compile(
                checkpointer=self.checkpointer,
                interrupt_before=[],  # 可以设置中断点
                interrupt_after=[]
            )
            
            self.status = WorkflowStatus.CREATED
            logger.info(f"工作流编译完成: {self.workflow_id}")
            
        except Exception as e:
            logger.error(f"工作流编译失败: {e}")
            self.status = WorkflowStatus.FAILED
            raise
    
    def _setup_default_routing(self) -> None:
        """设置默认的工作流路由"""
        # 构建条件映射，只包含已注册的智能体
        analysis_map = {"skip": "route_to_decomposition"}
        if "meta_agent" in self.agent_wrappers:
            analysis_map["meta_agent"] = "meta_agent"
        
        decomposition_map = {"skip": "route_to_coordination"}
        if "task_decomposer" in self.agent_wrappers:
            decomposition_map["task_decomposer"] = "task_decomposer"
        
        coordination_map = {"skip": "route_to_execution"}
        if "coordinator" in self.agent_wrappers:
            coordination_map["coordinator"] = "coordinator"
        
        # 分析阶段路由
        self.add_conditional_edge(
            "route_to_analysis",
            self._should_analyze,
            analysis_map
        )
        
        # 分解阶段路由
        self.add_conditional_edge(
            "route_to_decomposition", 
            self._should_decompose,
            decomposition_map
        )
        
        # 协调阶段路由
        self.add_conditional_edge(
            "route_to_coordination",
            self._should_coordinate,
            coordination_map
        )
        
        # 执行阶段路由
        self.add_conditional_edge(
            "route_to_execution",
            self._should_execute,
            {
                "execute": "route_to_completion",
                "retry": "route_to_analysis"
            }
        )
        
        # 完成阶段路由
        self.add_conditional_edge(
            "route_to_completion",
            self._should_complete,
            {
                "complete": END,
                "continue": "route_to_coordination"
            }
        )
        
        # 智能体节点的后续路由
        if "meta_agent" in self.agent_wrappers:
            self.add_edge("meta_agent", "route_to_decomposition")
        
        if "task_decomposer" in self.agent_wrappers:
            self.add_edge("task_decomposer", "route_to_coordination")
        
        if "coordinator" in self.agent_wrappers:
            self.add_edge("coordinator", "route_to_execution")
    
    async def execute(
        self,
        initial_input: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> LangGraphTaskState:
        """执行工作流
        
        Args:
            initial_input: 初始输入数据
            config: 执行配置
            
        Returns:
            最终的工作流状态
        """
        if not self.compiled_graph:
            raise ValueError("工作流未编译，请先调用 compile_workflow()")
        
        try:
            self.status = WorkflowStatus.RUNNING
            self.started_at = datetime.now()
            
            # 创建初始状态
            initial_state = create_initial_state(
                title=initial_input.get("title", "Multi-Agent Task"),
                description=initial_input.get("description", ""),
                task_type=initial_input.get("task_type", "general"),
                priority=initial_input.get("priority", 1),
                input_data=initial_input.get("input_data", {}),
                requester_id=initial_input.get("requester_id")
            )
            
            # 设置执行配置
            execution_config = config or {}
            execution_config.update({
                "configurable": {
                    "thread_id": f"workflow_{self.workflow_id}_{datetime.now().timestamp()}"
                }
            })
            
            # 执行工作流
            logger.info(f"开始执行工作流: {self.workflow_id}")
            
            final_state = None
            async for state in self.compiled_graph.astream(
                initial_state,
                config=execution_config
            ):
                final_state = state
                
                # 记录执行进度
                current_node = state.get("current_node", "unknown")
                logger.debug(f"工作流节点执行: {current_node}")
                
                # 检查超时
                if self._is_execution_timeout():
                    logger.warning("工作流执行超时")
                    break
            
            # 更新执行统计
            self._update_execution_stats(True)
            
            self.status = WorkflowStatus.COMPLETED
            self.completed_at = datetime.now()
            
            logger.info(f"工作流执行完成: {self.workflow_id}")
            return final_state
            
        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            self._update_execution_stats(False)
            self.status = WorkflowStatus.FAILED
            raise
    
    async def pause_execution(self, thread_id: str) -> bool:
        """暂停工作流执行"""
        try:
            # LangGraph的暂停机制需要通过interrupt实现
            # 这里可以设置暂停标志
            self.status = WorkflowStatus.PAUSED
            logger.info(f"工作流暂停: {self.workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"工作流暂停失败: {e}")
            return False
    
    async def resume_execution(
        self,
        thread_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> LangGraphTaskState:
        """恢复工作流执行"""
        try:
            if not self.compiled_graph:
                raise ValueError("工作流未编译")
            
            # 从检查点恢复
            execution_config = config or {}
            execution_config.update({
                "configurable": {"thread_id": thread_id}
            })
            
            self.status = WorkflowStatus.RUNNING
            logger.info(f"工作流恢复执行: {self.workflow_id}")
            
            # 继续执行
            final_state = None
            async for state in self.compiled_graph.astream(
                None,  # 从检查点恢复时不需要初始状态
                config=execution_config
            ):
                final_state = state
            
            self.status = WorkflowStatus.COMPLETED
            return final_state
            
        except Exception as e:
            logger.error(f"工作流恢复失败: {e}")
            self.status = WorkflowStatus.FAILED
            raise
    
    def get_execution_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """获取执行历史"""
        try:
            if not self.compiled_graph:
                return []
            
            # 从检查点获取历史
            config = {"configurable": {"thread_id": thread_id}}
            history = []
            
            for checkpoint in self.compiled_graph.get_state_history(config):
                history.append({
                    "checkpoint_id": checkpoint.config.get("configurable", {}).get("checkpoint_id"),
                    "values": checkpoint.values,
                    "next": checkpoint.next,
                    "created_at": checkpoint.created_at
                })
            
            return history
            
        except Exception as e:
            logger.error(f"获取执行历史失败: {e}")
            return []
    
    # 条件判断函数
    def _should_analyze(self, state: LangGraphTaskState) -> str:
        """判断是否需要分析"""
        available_agents = list(self.agent_wrappers.keys())
        decision = self.router.should_analyze(state, available_agents)
        self.router.update_routing_stats("analyze", decision != "skip")
        return decision
    
    def _should_decompose(self, state: LangGraphTaskState) -> str:
        """判断是否需要分解"""
        available_agents = list(self.agent_wrappers.keys())
        decision = self.router.should_decompose(state, available_agents)
        self.router.update_routing_stats("decompose", decision != "skip")
        return decision
    
    def _should_coordinate(self, state: LangGraphTaskState) -> str:
        """判断是否需要协调"""
        available_agents = list(self.agent_wrappers.keys())
        decision = self.router.should_coordinate(state, available_agents)
        self.router.update_routing_stats("coordinate", decision != "skip")
        return decision
    
    def _should_execute(self, state: LangGraphTaskState) -> str:
        """判断是否应该执行"""
        # 检查当前工作流阶段
        current_phase = state["workflow_context"]["current_phase"]
        
        if current_phase == WorkflowPhase.EXECUTION:
            return "execute"
        elif current_phase == WorkflowPhase.ERROR_HANDLING:
            return "retry"
        
        return "execute"
    
    def _should_complete(self, state: LangGraphTaskState) -> str:
        """判断是否应该完成"""
        decision = self.router.should_continue_execution(state)
        self.router.update_routing_stats("complete", decision == "complete")
        return decision
    
    # 路由节点函数
    async def _route_to_analysis(self, state: LangGraphTaskState) -> LangGraphTaskState:
        """路由到分析阶段"""
        state["current_node"] = "route_to_analysis"
        state = update_workflow_phase(state, WorkflowPhase.ANALYSIS)
        return state
    
    async def _route_to_decomposition(self, state: LangGraphTaskState) -> LangGraphTaskState:
        """路由到分解阶段"""
        state["current_node"] = "route_to_decomposition"
        state = update_workflow_phase(state, WorkflowPhase.DECOMPOSITION)
        return state
    
    async def _route_to_coordination(self, state: LangGraphTaskState) -> LangGraphTaskState:
        """路由到协调阶段"""
        state["current_node"] = "route_to_coordination"
        state = update_workflow_phase(state, WorkflowPhase.COORDINATION)
        return state
    
    async def _route_to_execution(self, state: LangGraphTaskState) -> LangGraphTaskState:
        """路由到执行阶段"""
        state["current_node"] = "route_to_execution"
        state = update_workflow_phase(state, WorkflowPhase.EXECUTION)
        return state
    
    async def _route_to_completion(self, state: LangGraphTaskState) -> LangGraphTaskState:
        """路由到完成阶段"""
        state["current_node"] = "route_to_completion"
        state = update_workflow_phase(state, WorkflowPhase.COMPLETION)
        state = update_task_status(state, TaskStatus.COMPLETED)
        return state
    
    def _is_execution_timeout(self) -> bool:
        """检查是否执行超时"""
        if not self.started_at:
            return False
        
        elapsed = (datetime.now() - self.started_at).total_seconds()
        return elapsed > self.timeout_seconds
    
    def _update_execution_stats(self, success: bool) -> None:
        """更新执行统计"""
        self.execution_stats["total_executions"] += 1
        
        if success:
            self.execution_stats["successful_executions"] += 1
        else:
            self.execution_stats["failed_executions"] += 1
        
        # 更新平均执行时间
        if self.started_at and self.completed_at:
            execution_time = (self.completed_at - self.started_at).total_seconds()
            total_time = (self.execution_stats["average_execution_time"] * 
                         (self.execution_stats["total_executions"] - 1) + execution_time)
            self.execution_stats["average_execution_time"] = total_time / self.execution_stats["total_executions"]
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """获取工作流信息"""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "execution_mode": self.execution_mode.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "registered_agents": list(self.agents.keys()),
            "execution_stats": self.execution_stats,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds
        }
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取智能体信息"""
        if agent_id not in self.agent_wrappers:
            return None
        
        wrapper = self.agent_wrappers[agent_id]
        return wrapper.get_agent_info()
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有注册的智能体"""
        agents_info = []
        for agent_id, wrapper in self.agent_wrappers.items():
            info = wrapper.get_agent_info()
            info["agent_id"] = agent_id
            agents_info.append(info)
        
        return agents_info
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        return self.router.get_routing_statistics()
    
    def set_routing_strategy(self, strategy: RoutingStrategy) -> None:
        """设置路由策略"""
        self.router.routing_strategy = strategy
        logger.info(f"路由策略已更新为: {strategy.value}")
    
    def get_execution_mode_recommendation(self, state: LangGraphTaskState) -> ExecutionMode:
        """获取执行模式推荐"""
        available_agents = list(self.agent_wrappers.keys())
        return self.router.determine_execution_mode(state, available_agents)