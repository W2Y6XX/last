"""工作流执行控制模块"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
from enum import Enum

from ..core.state import LangGraphTaskState, WorkflowPhase
from ..legacy.task_state import TaskStatus

logger = logging.getLogger(__name__)


class ExecutionStrategy(str, Enum):
    """执行策略枚举"""
    FAIL_FAST = "fail_fast"          # 快速失败
    CONTINUE_ON_ERROR = "continue_on_error"  # 错误时继续
    RETRY_ON_ERROR = "retry_on_error"        # 错误时重试
    GRACEFUL_DEGRADATION = "graceful_degradation"  # 优雅降级


class ExecutionController:
    """执行控制器
    
    负责控制多智能体的并行和顺序执行，管理执行策略和错误处理。
    """
    
    def __init__(
        self,
        execution_strategy: ExecutionStrategy = ExecutionStrategy.RETRY_ON_ERROR,
        max_parallel_agents: int = 5,
        agent_timeout: int = 300,
        max_retries: int = 3
    ):
        self.execution_strategy = execution_strategy
        self.max_parallel_agents = max_parallel_agents
        self.agent_timeout = agent_timeout
        self.max_retries = max_retries
        
        # 执行统计
        self.execution_stats = {
            "parallel_executions": 0,
            "sequential_executions": 0,
            "pipeline_executions": 0,
            "failed_executions": 0,
            "total_agent_calls": 0,
            "average_parallel_time": 0.0,
            "average_sequential_time": 0.0
        }
    
    async def execute_parallel(
        self,
        agents: List[Callable[[LangGraphTaskState], Awaitable[LangGraphTaskState]]],
        state: LangGraphTaskState,
        agent_names: List[str]
    ) -> LangGraphTaskState:
        """并行执行多个智能体
        
        Args:
            agents: 智能体包装器列表
            state: 当前状态
            agent_names: 智能体名称列表
            
        Returns:
            更新后的状态
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始并行执行{len(agents)}个智能体: {agent_names}")
            
            # 限制并行数量
            if len(agents) > self.max_parallel_agents:
                logger.warning(f"智能体数量({len(agents)})超过最大并行数({self.max_parallel_agents})，将分批执行")
                return await self._execute_in_batches(agents, state, agent_names)
            
            # 为每个智能体创建状态副本
            agent_states = [state.copy() for _ in agents]
            
            # 并行执行所有智能体
            tasks = []
            for i, (agent, agent_state) in enumerate(zip(agents, agent_states)):
                task = asyncio.create_task(
                    self._execute_agent_with_timeout(agent, agent_state, agent_names[i])
                )
                tasks.append(task)
            
            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 合并结果
            final_state = await self._merge_parallel_results(state, results, agent_names)
            
            # 更新统计
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_parallel_stats(execution_time, len(agents), True)
            
            logger.info(f"并行执行完成，耗时{execution_time:.2f}秒")
            return final_state
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_parallel_stats(execution_time, len(agents), False)
            logger.error(f"并行执行失败: {e}")
            raise
    
    async def execute_sequential(
        self,
        agents: List[Callable[[LangGraphTaskState], Awaitable[LangGraphTaskState]]],
        state: LangGraphTaskState,
        agent_names: List[str]
    ) -> LangGraphTaskState:
        """顺序执行多个智能体
        
        Args:
            agents: 智能体包装器列表
            state: 当前状态
            agent_names: 智能体名称列表
            
        Returns:
            更新后的状态
        """
        start_time = datetime.now()
        current_state = state
        
        try:
            logger.info(f"开始顺序执行{len(agents)}个智能体: {agent_names}")
            
            for i, (agent, agent_name) in enumerate(zip(agents, agent_names)):
                logger.debug(f"执行智能体 {i+1}/{len(agents)}: {agent_name}")
                
                try:
                    # 执行单个智能体
                    current_state = await self._execute_agent_with_timeout(
                        agent, current_state, agent_name
                    )
                    
                    # 检查是否应该继续
                    if not self._should_continue_after_agent(current_state, agent_name):
                        logger.info(f"智能体{agent_name}执行后决定停止顺序执行")
                        break
                        
                except Exception as e:
                    # 根据执行策略处理错误
                    if not await self._handle_agent_error(e, agent_name, current_state):
                        logger.error(f"智能体{agent_name}执行失败，停止顺序执行")
                        break
            
            # 更新统计
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_sequential_stats(execution_time, len(agents), True)
            
            logger.info(f"顺序执行完成，耗时{execution_time:.2f}秒")
            return current_state
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_sequential_stats(execution_time, len(agents), False)
            logger.error(f"顺序执行失败: {e}")
            raise
    
    async def execute_pipeline(
        self,
        agents: List[Callable[[LangGraphTaskState], Awaitable[LangGraphTaskState]]],
        state: LangGraphTaskState,
        agent_names: List[str],
        dependencies: List[Dict[str, Any]]
    ) -> LangGraphTaskState:
        """流水线执行多个智能体
        
        Args:
            agents: 智能体包装器列表
            state: 当前状态
            agent_names: 智能体名称列表
            dependencies: 依赖关系列表
            
        Returns:
            更新后的状态
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始流水线执行{len(agents)}个智能体")
            
            # 构建依赖图
            dependency_graph = self._build_dependency_graph(agent_names, dependencies)
            
            # 计算执行顺序
            execution_order = self._topological_sort(dependency_graph)
            
            # 按依赖顺序执行
            current_state = state
            completed_agents = set()
            
            for agent_name in execution_order:
                if agent_name in agent_names:
                    agent_index = agent_names.index(agent_name)
                    agent = agents[agent_index]
                    
                    # 等待依赖完成
                    await self._wait_for_dependencies(agent_name, dependency_graph, completed_agents)
                    
                    # 执行智能体
                    logger.debug(f"流水线执行智能体: {agent_name}")
                    current_state = await self._execute_agent_with_timeout(
                        agent, current_state, agent_name
                    )
                    
                    completed_agents.add(agent_name)
            
            # 更新统计
            execution_time = (datetime.now() - start_time).total_seconds()
            self.execution_stats["pipeline_executions"] += 1
            
            logger.info(f"流水线执行完成，耗时{execution_time:.2f}秒")
            return current_state
            
        except Exception as e:
            self.execution_stats["failed_executions"] += 1
            logger.error(f"流水线执行失败: {e}")
            raise
    
    async def _execute_agent_with_timeout(
        self,
        agent: Callable[[LangGraphTaskState], Awaitable[LangGraphTaskState]],
        state: LangGraphTaskState,
        agent_name: str
    ) -> LangGraphTaskState:
        """带超时的智能体执行"""
        try:
            result = await asyncio.wait_for(
                agent(state),
                timeout=self.agent_timeout
            )
            self.execution_stats["total_agent_calls"] += 1
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"智能体{agent_name}执行超时({self.agent_timeout}秒)")
            raise
        except Exception as e:
            logger.error(f"智能体{agent_name}执行失败: {e}")
            raise
    
    async def _execute_in_batches(
        self,
        agents: List[Callable[[LangGraphTaskState], Awaitable[LangGraphTaskState]]],
        state: LangGraphTaskState,
        agent_names: List[str]
    ) -> LangGraphTaskState:
        """分批执行智能体"""
        current_state = state
        batch_size = self.max_parallel_agents
        
        for i in range(0, len(agents), batch_size):
            batch_agents = agents[i:i + batch_size]
            batch_names = agent_names[i:i + batch_size]
            
            logger.info(f"执行第{i//batch_size + 1}批智能体: {batch_names}")
            
            # 并行执行当前批次
            batch_states = [current_state.copy() for _ in batch_agents]
            tasks = [
                self._execute_agent_with_timeout(agent, batch_state, name)
                for agent, batch_state, name in zip(batch_agents, batch_states, batch_names)
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 合并批次结果
            current_state = await self._merge_parallel_results(current_state, batch_results, batch_names)
        
        return current_state
    
    async def _merge_parallel_results(
        self,
        original_state: LangGraphTaskState,
        results: List[Any],
        agent_names: List[str]
    ) -> LangGraphTaskState:
        """合并并行执行结果"""
        merged_state = original_state.copy()
        
        for i, (result, agent_name) in enumerate(zip(results, agent_names)):
            if isinstance(result, Exception):
                logger.error(f"智能体{agent_name}执行异常: {result}")
                
                # 根据执行策略处理异常
                if self.execution_strategy == ExecutionStrategy.FAIL_FAST:
                    raise result
                elif self.execution_strategy == ExecutionStrategy.CONTINUE_ON_ERROR:
                    continue
                # 其他策略的处理逻辑
                
            elif isinstance(result, dict):
                # 合并状态
                merged_state = self._merge_state_data(merged_state, result)
        
        return merged_state
    
    def _merge_state_data(
        self, 
        target_state: LangGraphTaskState, 
        source_state: LangGraphTaskState
    ) -> LangGraphTaskState:
        """合并状态数据"""
        # 合并智能体结果
        if "workflow_context" in source_state and "agent_results" in source_state["workflow_context"]:
            for agent_id, result in source_state["workflow_context"]["agent_results"].items():
                target_state["workflow_context"]["agent_results"][agent_id] = result
        
        # 合并智能体消息
        if "agent_messages" in source_state:
            target_state["agent_messages"].extend(source_state["agent_messages"])
        
        # 合并性能指标
        if "performance_metrics" in source_state:
            for metric_name, metric_data in source_state["performance_metrics"].items():
                if metric_name not in target_state["performance_metrics"]:
                    target_state["performance_metrics"][metric_name] = []
                target_state["performance_metrics"][metric_name].extend(metric_data)
        
        # 更新任务状态（取最新的）
        if "task_state" in source_state:
            target_state["task_state"]["updated_at"] = source_state["task_state"]["updated_at"]
            
            # 合并输出数据
            if source_state["task_state"].get("output_data"):
                if target_state["task_state"]["output_data"] is None:
                    target_state["task_state"]["output_data"] = {}
                target_state["task_state"]["output_data"].update(source_state["task_state"]["output_data"])
        
        return target_state
    
    def _build_dependency_graph(
        self, 
        agent_names: List[str], 
        dependencies: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """构建依赖图"""
        graph = {name: [] for name in agent_names}
        
        for dep in dependencies:
            from_agent = dep.get("from")
            to_agent = dep.get("to")
            
            if from_agent in graph and to_agent in agent_names:
                graph[from_agent].append(to_agent)
        
        return graph
    
    def _topological_sort(self, dependency_graph: Dict[str, List[str]]) -> List[str]:
        """拓扑排序"""
        # 简化的拓扑排序实现
        in_degree = {node: 0 for node in dependency_graph}
        
        # 计算入度
        for node in dependency_graph:
            for neighbor in dependency_graph[node]:
                in_degree[neighbor] += 1
        
        # 找到入度为0的节点
        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            # 更新邻居节点的入度
            for neighbor in dependency_graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    async def _wait_for_dependencies(
        self,
        agent_name: str,
        dependency_graph: Dict[str, List[str]],
        completed_agents: set
    ):
        """等待依赖完成"""
        # 找到依赖此智能体的其他智能体
        dependencies = []
        for node, neighbors in dependency_graph.items():
            if agent_name in neighbors:
                dependencies.append(node)
        
        # 等待所有依赖完成
        while not all(dep in completed_agents for dep in dependencies):
            await asyncio.sleep(0.1)  # 短暂等待
    
    def _should_continue_after_agent(
        self, 
        state: LangGraphTaskState, 
        agent_name: str
    ) -> bool:
        """判断智能体执行后是否应该继续"""
        # 检查任务状态
        task_status = state["task_state"]["status"]
        if task_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        
        # 检查错误状态
        if state.get("error_state") and self.execution_strategy == ExecutionStrategy.FAIL_FAST:
            return False
        
        # 检查工作流阶段
        current_phase = state["workflow_context"]["current_phase"]
        if current_phase == WorkflowPhase.ERROR_HANDLING:
            return False
        
        return True
    
    async def _handle_agent_error(
        self, 
        error: Exception, 
        agent_name: str, 
        state: LangGraphTaskState
    ) -> bool:
        """处理智能体错误
        
        Returns:
            True if should continue, False if should stop
        """
        logger.error(f"智能体{agent_name}执行错误: {error}")
        
        if self.execution_strategy == ExecutionStrategy.FAIL_FAST:
            return False
        elif self.execution_strategy == ExecutionStrategy.CONTINUE_ON_ERROR:
            return True
        elif self.execution_strategy == ExecutionStrategy.RETRY_ON_ERROR:
            # 检查重试次数
            retry_count = state.get("retry_count", 0)
            if retry_count < self.max_retries:
                logger.info(f"智能体{agent_name}准备重试，当前重试次数: {retry_count}")
                return True
            else:
                logger.warning(f"智能体{agent_name}重试次数已达上限")
                return False
        elif self.execution_strategy == ExecutionStrategy.GRACEFUL_DEGRADATION:
            # 实现优雅降级逻辑
            return await self._graceful_degradation(error, agent_name, state)
        
        return False
    
    async def _graceful_degradation(
        self, 
        error: Exception, 
        agent_name: str, 
        state: LangGraphTaskState
    ) -> bool:
        """优雅降级处理"""
        # 简化的优雅降级：尝试用其他智能体替代
        logger.info(f"尝试为失败的智能体{agent_name}进行优雅降级")
        
        # 这里可以实现更复杂的降级逻辑
        # 例如：选择备用智能体、降低任务要求等
        
        return True  # 继续执行
    
    def _update_parallel_stats(self, execution_time: float, agent_count: int, success: bool):
        """更新并行执行统计"""
        self.execution_stats["parallel_executions"] += 1
        self.execution_stats["total_agent_calls"] += agent_count
        
        if not success:
            self.execution_stats["failed_executions"] += 1
        
        # 更新平均时间
        total_parallel = self.execution_stats["parallel_executions"]
        current_avg = self.execution_stats["average_parallel_time"]
        self.execution_stats["average_parallel_time"] = (
            (current_avg * (total_parallel - 1) + execution_time) / total_parallel
        )
    
    def _update_sequential_stats(self, execution_time: float, agent_count: int, success: bool):
        """更新顺序执行统计"""
        self.execution_stats["sequential_executions"] += 1
        self.execution_stats["total_agent_calls"] += agent_count
        
        if not success:
            self.execution_stats["failed_executions"] += 1
        
        # 更新平均时间
        total_sequential = self.execution_stats["sequential_executions"]
        current_avg = self.execution_stats["average_sequential_time"]
        self.execution_stats["average_sequential_time"] = (
            (current_avg * (total_sequential - 1) + execution_time) / total_sequential
        )
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return {
            "execution_strategy": self.execution_strategy.value,
            "max_parallel_agents": self.max_parallel_agents,
            "agent_timeout": self.agent_timeout,
            "max_retries": self.max_retries,
            "execution_stats": self.execution_stats,
            "success_rate": (
                (self.execution_stats["parallel_executions"] + 
                 self.execution_stats["sequential_executions"] + 
                 self.execution_stats["pipeline_executions"] - 
                 self.execution_stats["failed_executions"]) /
                max(1, self.execution_stats["parallel_executions"] + 
                    self.execution_stats["sequential_executions"] + 
                    self.execution_stats["pipeline_executions"])
            )
        }
    
    def set_execution_strategy(self, strategy: ExecutionStrategy):
        """设置执行策略"""
        self.execution_strategy = strategy
        logger.info(f"执行策略已更新为: {strategy.value}")
    
    def reset_statistics(self):
        """重置统计信息"""
        self.execution_stats = {
            "parallel_executions": 0,
            "sequential_executions": 0,
            "pipeline_executions": 0,
            "failed_executions": 0,
            "total_agent_calls": 0,
            "average_parallel_time": 0.0,
            "average_sequential_time": 0.0
        }
        logger.info("执行统计已重置")