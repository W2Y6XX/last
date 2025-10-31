"""
多智能体任务管理系统 - TaskDecomposer-Agent（任务分解智能体）
创建时间: 2025-10-20
职责：任务分解、依赖分析、工作流规划

重构说明：从 agent-implementations/task_decomposer_agent.py 迁移到新的结构化目录
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

from ..base.base_agent import BaseAgent, MessageType, Message, Config, AgentError, MessageBus

logger = logging.getLogger(__name__)

class TaskDecomposerAgent(BaseAgent):
    """任务分解智能体

    负责将复杂任务分解为可执行的子任务，分析依赖关系。
    """

    def __init__(self, agent_id: str = "task_decomposer", config: Config = None, message_bus: MessageBus = None):
        super().__init__(agent_id, "task_decomposer", config, message_bus)

        # 任务分解器特有状态
        self.decomposition_history: List[Dict[str, Any]] = []
        self.task_patterns: Dict[str, Dict[str, Any]] = {}
        self.dependency_graphs: Dict[str, Dict[str, List[str]]] = {}

        # 分解指标
        self.decomposition_metrics = {
            "tasks_decomposed": 0,
            "subtasks_created": 0,
            "dependencies_analyzed": 0,
            "average_decomposition_time": 0.0
        }

    async def initialize(self) -> bool:
        """初始化任务分解智能体"""
        try:
            # 注册消息处理器
            await self.register_message_handler(MessageType.TASK_REQUEST, self.handle_decomposition_request)

            # 注册分解能力
            await self.register_capability("task_decomposition")
            await self.register_capability("dependency_analysis")
            await self.register_capability("workflow_planning")
            await self.register_capability("complexity_assessment")

            # 初始化任务模式
            await self._initialize_task_patterns()

            self.is_initialized = True
            logger.info(f"任务分解智能体 {self.agent_id} 初始化完成")
            return True

        except Exception as e:
            logger.error(f"任务分解智能体初始化失败: {e}")
            return False

    async def _initialize_task_patterns(self):
        """初始化任务模式"""
        self.task_patterns = {
            "data_analysis": {
                "typical_subtasks": ["data_collection", "data_cleaning", "analysis", "reporting"],
                "dependencies": {
                    "analysis": ["data_cleaning"],
                    "reporting": ["analysis"]
                }
            },
            "content_creation": {
                "typical_subtasks": ["research", "outline", "drafting", "review", "finalization"],
                "dependencies": {
                    "outline": ["research"],
                    "drafting": ["outline"],
                    "review": ["drafting"],
                    "finalization": ["review"]
                }
            },
            "problem_solving": {
                "typical_subtasks": ["problem_identification", "research", "solution_design", "implementation", "testing"],
                "dependencies": {
                    "research": ["problem_identification"],
                    "solution_design": ["research"],
                    "implementation": ["solution_design"],
                    "testing": ["implementation"]
                }
            }
        }

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务分解"""
        try:
            task_id = task_data.get("task_id", str(uuid.uuid4()))
            decomposition_id = str(uuid.uuid4())
            start_time = datetime.now(timezone.utc)

            # 分析任务复杂度
            complexity = await self._assess_task_complexity(task_data)

            # 确定分解策略
            strategy = await self._determine_decomposition_strategy(task_data, complexity)

            # 执行任务分解
            decomposition_result = await self._decompose_task(task_data, strategy)

            # 分析依赖关系
            dependency_analysis = await self._analyze_dependencies(decomposition_result["subtasks"])

            # 创建工作流计划
            workflow_plan = await self._create_workflow_plan(decomposition_result["subtasks"], dependency_analysis)

            # 记录分解历史
            decomposition_record = {
                "decomposition_id": decomposition_id,
                "task_id": task_id,
                "original_task": task_data,
                "complexity": complexity,
                "strategy": strategy,
                "subtasks": decomposition_result["subtasks"],
                "dependencies": dependency_analysis,
                "workflow_plan": workflow_plan,
                "start_time": start_time,
                "end_time": datetime.now(timezone.utc),
                "duration": (datetime.now(timezone.utc) - start_time).total_seconds()
            }

            self.decomposition_history.append(decomposition_record)
            self._update_decomposition_metrics(decomposition_record)

            return {
                "success": True,
                "decomposition_id": decomposition_id,
                "complexity": complexity,
                "subtasks_count": len(decomposition_result["subtasks"]),
                "subtasks": decomposition_result["subtasks"],
                "dependencies": dependency_analysis,
                "workflow_plan": workflow_plan,
                "duration": decomposition_record["duration"]
            }

        except Exception as e:
            logger.error(f"处理任务分解失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _assess_task_complexity(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估任务复杂度"""
        try:
            task_type = task_data.get("task_type", "general")
            input_data = task_data.get("input_data", {})
            requirements = task_data.get("requirements", [])

            # 基础复杂度因素
            complexity_factors = {
                "input_size": len(str(input_data)),
                "requirements_count": len(requirements),
                "task_type_complexity": self._get_task_type_complexity(task_type),
                "has_dependencies": bool(task_data.get("dependencies")),
                "deadline_pressure": self._assess_deadline_pressure(task_data.get("deadline"))
            }

            # 计算综合复杂度分数
            complexity_score = (
                min(complexity_factors["input_size"] / 1000, 10) +  # 输入大小权重
                complexity_factors["requirements_count"] * 2 +        # 需求数量权重
                complexity_factors["task_type_complexity"] +           # 任务类型权重
                (5 if complexity_factors["has_dependencies"] else 0) +  # 依赖关系权重
                complexity_factors["deadline_pressure"]                # 截止时间压力权重
            )

            # 确定复杂度级别
            if complexity_score < 15:
                complexity_level = "low"
            elif complexity_score < 30:
                complexity_level = "medium"
            else:
                complexity_level = "high"

            return {
                "level": complexity_level,
                "score": complexity_score,
                "factors": complexity_factors,
                "needs_decomposition": complexity_level in ["medium", "high"]
            }

        except Exception as e:
            logger.error(f"评估任务复杂度失败: {e}")
            return {
                "level": "unknown",
                "score": 0,
                "error": str(e)
            }

    def _get_task_type_complexity(self, task_type: str) -> int:
        """获取任务类型复杂度"""
        complexity_map = {
            "simple_query": 1,
            "data_retrieval": 2,
            "basic_analysis": 4,
            "content_creation": 6,
            "data_analysis": 8,
            "problem_solving": 10,
            "complex_integration": 12,
            "multi_step_process": 10
        }
        return complexity_map.get(task_type, 5)

    def _assess_deadline_pressure(self, deadline: Optional[str]) -> int:
        """评估截止时间压力"""
        if not deadline:
            return 0

        try:
            deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
            time_remaining = (deadline_dt - datetime.now(timezone.utc)).total_seconds()

            if time_remaining < 3600:  # 1小时内
                return 5
            elif time_remaining < 86400:  # 24小时内
                return 3
            else:
                return 0
        except:
            return 0

    async def _determine_decomposition_strategy(self, task_data: Dict[str, Any], complexity: Dict[str, Any]) -> Dict[str, Any]:
        """确定分解策略"""
        try:
            task_type = task_data.get("task_type", "general")
            complexity_level = complexity.get("level", "low")

            strategy = {
                "approach": "sequential",
                "granularity": "coarse",
                "automation_level": "manual"
            }

            # 根据复杂度调整策略
            if complexity_level == "high":
                strategy.update({
                    "approach": "hierarchical",
                    "granularity": "fine",
                    "automation_level": "semi_automatic"
                })
            elif complexity_level == "medium":
                strategy.update({
                    "approach": "parallel",
                    "granularity": "medium",
                    "automation_level": "automatic"
                })

            # 根据任务类型调整
            if task_type in self.task_patterns:
                strategy["pattern_based"] = True
                strategy["pattern"] = task_type

            return strategy

        except Exception as e:
            logger.error(f"确定分解策略失败: {e}")
            return {
                "approach": "sequential",
                "granularity": "coarse",
                "error": str(e)
            }

    async def _decompose_task(self, task_data: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
        """分解任务"""
        try:
            task_type = task_data.get("task_type", "general")
            input_data = task_data.get("input_data", {})

            subtasks = []

            # 基于模式的分解
            if strategy.get("pattern_based") and task_type in self.task_patterns:
                pattern = self.task_patterns[task_type]
                subtasks = await self._decompose_by_pattern(task_data, pattern)
            else:
                # 通用分解逻辑
                subtasks = await self._decompose_generic(task_data, strategy)

            return {
                "subtasks": subtasks,
                "decomposition_method": "pattern_based" if strategy.get("pattern_based") else "generic"
            }

        except Exception as e:
            logger.error(f"任务分解失败: {e}")
            return {
                "subtasks": [],
                "error": str(e)
            }

    async def _decompose_by_pattern(self, task_data: Dict[str, Any], pattern: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于模式分解任务"""
        try:
            subtasks = []
            typical_subtasks = pattern["typical_subtasks"]
            dependencies = pattern["dependencies"]

            for i, subtask_name in enumerate(typical_subtasks):
                subtask = {
                    "subtask_id": str(uuid.uuid4()),
                    "name": subtask_name,
                    "description": f"执行 {subtask_name}",
                    "priority": task_data.get("priority", 2),
                    "estimated_duration": self._estimate_subtask_duration(subtask_name),
                    "required_capabilities": [subtask_name],
                    "dependencies": dependencies.get(subtask_name, []),
                    "input_data": self._prepare_subtask_input(subtask_name, task_data.get("input_data", {}))
                }
                subtasks.append(subtask)

            return subtasks

        except Exception as e:
            logger.error(f"基于模式分解失败: {e}")
            return []

    async def _decompose_generic(self, task_data: Dict[str, Any], strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """通用任务分解"""
        try:
            subtasks = []
            granularity = strategy.get("granularity", "coarse")

            if granularity == "fine":
                # 细粒度分解
                analysis_subtask = {
                    "subtask_id": str(uuid.uuid4()),
                    "name": "initial_analysis",
                    "description": "分析任务需求和输入",
                    "priority": task_data.get("priority", 2),
                    "estimated_duration": 300,
                    "required_capabilities": ["analysis"],
                    "dependencies": [],
                    "input_data": task_data.get("input_data", {})
                }
                subtasks.append(analysis_subtask)

                planning_subtask = {
                    "subtask_id": str(uuid.uuid4()),
                    "name": "execution_planning",
                    "description": "规划执行步骤",
                    "priority": task_data.get("priority", 2),
                    "estimated_duration": 600,
                    "required_capabilities": ["planning"],
                    "dependencies": [analysis_subtask["subtask_id"]],
                    "input_data": {}
                }
                subtasks.append(planning_subtask)

                execution_subtask = {
                    "subtask_id": str(uuid.uuid4()),
                    "name": "main_execution",
                    "description": "执行主要任务",
                    "priority": task_data.get("priority", 2),
                    "estimated_duration": 1800,
                    "required_capabilities": ["execution"],
                    "dependencies": [planning_subtask["subtask_id"]],
                    "input_data": task_data.get("input_data", {})
                }
                subtasks.append(execution_subtask)

            else:
                # 粗粒度分解 - 单个子任务
                subtask = {
                    "subtask_id": str(uuid.uuid4()),
                    "name": task_data.get("description", "main_task"),
                    "description": task_data.get("description", "执行主要任务"),
                    "priority": task_data.get("priority", 2),
                    "estimated_duration": 3600,
                    "required_capabilities": task_data.get("requirements", []),
                    "dependencies": [],
                    "input_data": task_data.get("input_data", {})
                }
                subtasks.append(subtask)

            return subtasks

        except Exception as e:
            logger.error(f"通用分解失败: {e}")
            return []

    def _estimate_subtask_duration(self, subtask_name: str) -> int:
        """估算子任务持续时间（秒）"""
        duration_map = {
            "data_collection": 600,
            "data_cleaning": 900,
            "analysis": 1800,
            "reporting": 1200,
            "research": 2400,
            "outline": 600,
            "drafting": 1800,
            "review": 900,
            "finalization": 600,
            "problem_identification": 300,
            "solution_design": 1200,
            "implementation": 3600,
            "testing": 1800
        }
        return duration_map.get(subtask_name, 1800)

    def _prepare_subtask_input(self, subtask_name: str, original_input: Dict[str, Any]) -> Dict[str, Any]:
        """准备子任务输入数据"""
        # 简化的输入数据准备逻辑
        return {
            "original_data": original_input,
            "subtask_context": {
                "subtask_name": subtask_name,
                "preparation_time": datetime.now(timezone.utc).isoformat()
            }
        }

    async def _analyze_dependencies(self, subtasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析依赖关系"""
        try:
            dependency_graph = {}
            dependency_matrix = {}

            # 构建依赖图
            for subtask in subtasks:
                subtask_id = subtask["subtask_id"]
                dependencies = subtask.get("dependencies", [])
                dependency_graph[subtask_id] = dependencies

            # 创建依赖矩阵
            for i, subtask1 in enumerate(subtasks):
                for j, subtask2 in enumerate(subtasks):
                    subtask1_id = subtask1["subtask_id"]
                    subtask2_id = subtask2["subtask_id"]

                    dependency_matrix[f"{subtask1_id}->{subtask2_id}"] = (
                        subtask2_id in subtask1.get("dependencies", [])
                    )

            # 检测循环依赖
            circular_deps = await self._detect_circular_dependencies(dependency_graph)

            return {
                "dependency_graph": dependency_graph,
                "dependency_matrix": dependency_matrix,
                "circular_dependencies": circular_deps,
                "dependency_count": sum(len(deps) for deps in dependency_graph.values())
            }

        except Exception as e:
            logger.error(f"依赖关系分析失败: {e}")
            return {
                "dependency_graph": {},
                "error": str(e)
            }

    async def _detect_circular_dependencies(self, dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
        """检测循环依赖"""
        try:
            # 简化的循环依赖检测
            visited = set()
            circular_deps = []

            def dfs(node: str, path: List[str]) -> bool:
                if node in path:
                    cycle_start = path.index(node)
                    circular_deps.append(path[cycle_start:] + [node])
                    return True

                if node in visited:
                    return False

                visited.add(node)
                for neighbor in dependency_graph.get(node, []):
                    if dfs(neighbor, path + [node]):
                        return True

                return False

            for node in dependency_graph:
                if node not in visited:
                    dfs(node, [])

            return circular_deps

        except Exception as e:
            logger.error(f"检测循环依赖失败: {e}")
            return []

    async def _create_workflow_plan(self, subtasks: List[Dict[str, Any]], dependency_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """创建工作流计划"""
        try:
            dependency_graph = dependency_analysis.get("dependency_graph", {})
            circular_deps = dependency_analysis.get("circular_dependencies", [])

            # 如果有循环依赖，打破循环
            if circular_deps:
                dependency_graph = await self._resolve_circular_dependencies(dependency_graph, circular_deps)

            # 创建执行序列
            execution_sequence = await self._create_execution_sequence(dependency_graph)

            # 识别并行执行组
            parallel_groups = await self._identify_parallel_groups(execution_sequence, dependency_graph)

            # 估算总执行时间
            total_duration = await self._estimate_total_execution_time(subtasks, parallel_groups)

            return {
                "execution_sequence": execution_sequence,
                "parallel_groups": parallel_groups,
                "estimated_total_duration": total_duration,
                "critical_path": await self._identify_critical_path(execution_sequence, dependency_graph),
                "has_circular_dependencies": len(circular_deps) > 0
            }

        except Exception as e:
            logger.error(f"创建工作流计划失败: {e}")
            return {
                "execution_sequence": [],
                "error": str(e)
            }

    async def _resolve_circular_dependencies(self, dependency_graph: Dict[str, List[str]], circular_deps: List[List[str]]) -> Dict[str, List[str]]:
        """解决循环依赖"""
        try:
            # 简化的循环依赖解决策略：移除最后一条依赖
            resolved_graph = dependency_graph.copy()

            for cycle in circular_deps:
                if len(cycle) >= 2:
                    # 移除循环中最后一个到第一个的依赖
                    source = cycle[-1]
                    target = cycle[0]

                    if source in resolved_graph and target in resolved_graph[source]:
                        resolved_graph[source].remove(target)
                        logger.warning(f"打破循环依赖: {source} -> {target}")

            return resolved_graph

        except Exception as e:
            logger.error(f"解决循环依赖失败: {e}")
            return dependency_graph

    async def _create_execution_sequence(self, dependency_graph: Dict[str, List[str]]) -> List[str]:
        """创建执行序列（拓扑排序）"""
        try:
            # 简化的拓扑排序实现
            in_degree = {}
            for node in dependency_graph:
                in_degree[node] = 0

            for node in dependency_graph:
                for neighbor in dependency_graph[node]:
                    in_degree[neighbor] = in_degree.get(neighbor, 0) + 1

            queue = [node for node in in_degree if in_degree[node] == 0]
            sequence = []

            while queue:
                current = queue.pop(0)
                sequence.append(current)

                for neighbor in dependency_graph.get(current, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            return sequence

        except Exception as e:
            logger.error(f"创建执行序列失败: {e}")
            return []

    async def _identify_parallel_groups(self, execution_sequence: List[str], dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
        """识别并行执行组"""
        try:
            parallel_groups = []
            processed = set()

            for node in execution_sequence:
                if node in processed:
                    continue

                # 找可以并行执行的任务
                current_group = [node]
                processed.add(node)

                # 检查后续节点是否可以并行执行
                for future_node in execution_sequence[execution_sequence.index(node) + 1:]:
                    if future_node not in processed:
                        # 检查是否与当前组中的任务有依赖关系
                        has_dependency = False
                        for group_node in current_group:
                            if (group_node in dependency_graph.get(future_node, []) or
                                future_node in dependency_graph.get(group_node, [])):
                                has_dependency = True
                                break

                        if not has_dependency:
                            current_group.append(future_node)
                            processed.add(future_node)

                parallel_groups.append(current_group)

            return parallel_groups

        except Exception as e:
            logger.error(f"识别并行组失败: {e}")
            return []

    async def _estimate_total_execution_time(self, subtasks: List[Dict[str, Any]], parallel_groups: List[List[str]]) -> int:
        """估算总执行时间"""
        try:
            # 创建子任务ID到持续时间的映射
            duration_map = {}
            for subtask in subtasks:
                duration_map[subtask["subtask_id"]] = subtask.get("estimated_duration", 1800)

            # 计算每组的时间（组内任务并行执行，取最大时间）
            total_time = 0
            for group in parallel_groups:
                group_time = max(duration_map.get(task_id, 1800) for task_id in group)
                total_time += group_time

            return total_time

        except Exception as e:
            logger.error(f"估算总执行时间失败: {e}")
            return 3600

    async def _identify_critical_path(self, execution_sequence: List[str], dependency_graph: Dict[str, List[str]]) -> List[str]:
        """识别关键路径"""
        try:
            # 简化的关键路径识别
            # 这里返回最长的依赖链
            longest_path = []
            max_duration = 0

            for start_node in execution_sequence:
                path = await self._find_longest_path(start_node, dependency_graph)
                if len(path) > len(longest_path):
                    longest_path = path

            return longest_path

        except Exception as e:
            logger.error(f"识别关键路径失败: {e}")
            return []

    async def _find_longest_path(self, start_node: str, dependency_graph: Dict[str, List[str]]) -> List[str]:
        """查找最长路径"""
        try:
            # 简化的最长路径查找
            visited = set()

            def dfs(node: str, path: List[str]) -> List[str]:
                if node in visited:
                    return path

                visited.add(node)
                longest_path = path

                for neighbor in dependency_graph.get(node, []):
                    neighbor_path = dfs(neighbor, path + [neighbor])
                    if len(neighbor_path) > len(longest_path):
                        longest_path = neighbor_path

                return longest_path

            return dfs(start_node, [start_node])

        except Exception as e:
            logger.error(f"查找最长路径失败: {e}")
            return [start_node]

    def _update_decomposition_metrics(self, decomposition_record: Dict[str, Any]):
        """更新分解指标"""
        self.decomposition_metrics["tasks_decomposed"] += 1
        self.decomposition_metrics["subtasks_created"] += len(decomposition_record.get("subtasks", []))

        total_time = self.decomposition_metrics.get("total_decomposition_time", 0)
        total_time += decomposition_record.get("duration", 0)
        self.decomposition_metrics["total_decomposition_time"] = total_time
        self.decomposition_metrics["average_decomposition_time"] = (
            total_time / self.decomposition_metrics["tasks_decomposed"]
        )

    async def handle_decomposition_request(self, message: Message) -> Optional[Message]:
        """处理分解请求"""
        try:
            task_data = message.content
            result = await self.process_task(task_data)

            return Message(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type=MessageType.TASK_RESPONSE,
                content=result,
                timestamp=datetime.now(timezone.utc),
                reply_to=message.message_id
            )

        except Exception as e:
            logger.error(f"处理分解请求失败: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """获取任务分解智能体状态"""
        base_status = super().get_status()

        # 添加分解器特有状态
        decomposition_status = {
            "decomposition_history_size": len(self.decomposition_history),
            "available_patterns": list(self.task_patterns.keys()),
            "decomposition_metrics": self.decomposition_metrics
        }

        base_status.update(decomposition_status)
        return base_status

    def __str__(self) -> str:
        return f"TaskDecomposerAgent(id={self.agent_id}, patterns={len(self.task_patterns)})"