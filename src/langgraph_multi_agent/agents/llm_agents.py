   """基于LLM的智能体实现"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..llm import chat
from ..utils.helpers import calculate_complexity_score

logger = logging.getLogger(__name__)


class LLMMetaAgent:
    """基于LLM的MetaAgent实现"""
    
    def __init__(self):
        self.agent_id = "llm_meta_agent"
        self.agent_type = "meta_agent"
        
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务分析"""
        try:
            # 提取任务信息
            task_title = task_data.get("title", "")
            task_description = task_data.get("description", "")
            task_requirements = task_data.get("requirements", [])
            task_type = task_data.get("task_type", "general")
            priority = task_data.get("priority", 2)
            
            # 构建系统提示
            system_message = """你是一个专业的任务分析专家，负责分析用户提交的任务并提供详细的分析结果。

你的职责包括：
1. 评估任务复杂度 (simple/medium/complex)
2. 估算执行时间 (秒)
3. 推荐合适的智能体类型
4. 判断是否需要任务分解
5. 识别是否需要需求澄清
6. 提供分析置信度

请以JSON格式返回分析结果，包含以下字段：
- task_complexity: 任务复杂度
- estimated_time: 预估执行时间(秒)
- complexity_score: 复杂度分数(0-1)
- requires_decomposition: 是否需要分解
- clarification_needed: 是否需要澄清
- recommended_agents: 推荐的智能体列表
- analysis_summary: 分析摘要
- confidence: 分析置信度(0-1)
- next_steps: 建议的下一步操作"""

            # 构建分析提示
            prompt = f"""
请分析以下任务：

任务标题: {task_title}
任务描述: {task_description}
任务类型: {task_type}
优先级: {priority}
具体要求: {json.dumps(task_requirements, ensure_ascii=False)}

请根据以上信息进行全面分析，并以JSON格式返回结果。
"""
            
            # 调用LLM进行分析
            llm_response = await chat(prompt, system_message, temperature=0.3)
            
            # 解析LLM响应
            try:
                analysis_result = json.loads(llm_response)
                
                # 验证和补充必要字段
                analysis_result = self._validate_analysis_result(analysis_result, task_data)
                
            except json.JSONDecodeError as e:
                logger.warning(f"LLM响应JSON解析失败: {e}, 响应内容: {llm_response}")
                # 使用默认分析结果
                analysis_result = self._get_default_analysis(task_data)
                analysis_result["llm_response"] = llm_response
            
            # 添加执行元数据
            analysis_result["analysis_timestamp"] = datetime.now().isoformat()
            analysis_result["agent_id"] = self.agent_id
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"MetaAgent任务分析失败: {e}")
            # 返回默认分析结果
            return self._get_default_analysis(task_data, error=str(e))
    
    def _validate_analysis_result(self, result: Dict[str, Any], task_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证和补充分析结果"""
        
        # 确保必要字段存在
        defaults = {
            "task_complexity": "medium",
            "estimated_time": 300,
            "complexity_score": 0.5,
            "requires_decomposition": False,
            "clarification_needed": False,
            "recommended_agents": ["generic_agent"],
            "analysis_summary": "任务分析完成",
            "confidence": 0.8,
            "next_steps": ["执行任务"]
        }
        
        for key, default_value in defaults.items():
            if key not in result:
                result[key] = default_value
        
        # 验证数据类型和范围
        if not isinstance(result["complexity_score"], (int, float)) or not 0 <= result["complexity_score"] <= 1:
            result["complexity_score"] = 0.5
        
        if not isinstance(result["confidence"], (int, float)) or not 0 <= result["confidence"] <= 1:
            result["confidence"] = 0.8
        
        if not isinstance(result["estimated_time"], (int, float)) or result["estimated_time"] <= 0:
            result["estimated_time"] = 300
        
        if result["task_complexity"] not in ["simple", "medium", "complex"]:
            result["task_complexity"] = "medium"
        
        # 根据复杂度调整其他参数
        if result["complexity_score"] > 0.7:
            result["requires_decomposition"] = True
            result["task_complexity"] = "complex"
        elif result["complexity_score"] < 0.3:
            result["task_complexity"] = "simple"
        
        return result
    
    def _get_default_analysis(self, task_data: Dict[str, Any], error: Optional[str] = None) -> Dict[str, Any]:
        """获取默认分析结果"""
        
        # 基于任务数据计算基础复杂度
        complexity_score = calculate_complexity_score(task_data)
        
        # 根据复杂度确定其他参数
        if complexity_score > 0.7:
            task_complexity = "complex"
            estimated_time = 1800
            requires_decomposition = True
            recommended_agents = ["task_decomposer", "coordinator"]
        elif complexity_score < 0.3:
            task_complexity = "simple"
            estimated_time = 180
            requires_decomposition = False
            recommended_agents = ["generic_agent"]
        else:
            task_complexity = "medium"
            estimated_time = 600
            requires_decomposition = False
            recommended_agents = ["analysis_agent"]
        
        result = {
            "task_complexity": task_complexity,
            "estimated_time": estimated_time,
            "complexity_score": complexity_score,
            "requires_decomposition": requires_decomposition,
            "clarification_needed": False,
            "recommended_agents": recommended_agents,
            "analysis_summary": f"基于规则的默认分析 (复杂度: {complexity_score:.2f})",
            "confidence": 0.6,
            "next_steps": ["根据复杂度执行相应流程"],
            "analysis_timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "fallback_analysis": True
        }
        
        if error:
            result["error"] = error
            result["confidence"] = 0.4
        
        return result


class LLMTaskDecomposer:
    """基于LLM的任务分解器"""
    
    def __init__(self):
        self.agent_id = "llm_task_decomposer"
        self.agent_type = "task_decomposer"
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务分解"""
        try:
            # 提取任务信息
            task_title = task_data.get("title", "")
            task_description = task_data.get("description", "")
            task_requirements = task_data.get("requirements", [])
            
            # 构建系统提示
            system_message = """你是一个专业的任务分解专家，负责将复杂任务分解为可执行的子任务。

你的职责包括：
1. 分析任务的逻辑结构
2. 识别任务依赖关系
3. 将任务分解为合理的子任务
4. 为每个子任务分配合适的智能体
5. 制定执行计划

请以JSON格式返回分解结果，包含以下字段：
- subtasks: 子任务列表，每个子任务包含id、title、description、assigned_agent、dependencies
- execution_plan: 执行计划，包含execution_mode、estimated_total_time
- dependencies_graph: 依赖关系图
- decomposition_strategy: 分解策略
- confidence: 分解置信度"""

            # 构建分解提示
            prompt = f"""
请分解以下复杂任务：

任务标题: {task_title}
任务描述: {task_description}
具体要求: {json.dumps(task_requirements, ensure_ascii=False)}

请将此任务分解为3-8个可执行的子任务，并制定合理的执行计划。
"""
            
            # 调用LLM进行分解
            llm_response = await chat(prompt, system_message, temperature=0.4)
            
            # 解析LLM响应
            try:
                decomposition_result = json.loads(llm_response)
                decomposition_result = self._validate_decomposition_result(decomposition_result, task_data)
                
            except json.JSONDecodeError as e:
                logger.warning(f"任务分解LLM响应解析失败: {e}")
                decomposition_result = self._get_default_decomposition(task_data)
                decomposition_result["llm_response"] = llm_response
            
            # 添加执行元数据
            decomposition_result["decomposition_timestamp"] = datetime.now().isoformat()
            decomposition_result["agent_id"] = self.agent_id
            
            return decomposition_result
            
        except Exception as e:
            logger.error(f"任务分解失败: {e}")
            return self._get_default_decomposition(task_data, error=str(e))
    
    def _validate_decomposition_result(self, result: Dict[str, Any], task_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证分解结果"""
        
        # 确保必要字段存在
        if "subtasks" not in result or not isinstance(result["subtasks"], list):
            result["subtasks"] = self._generate_default_subtasks(task_data)
        
        if "execution_plan" not in result:
            result["execution_plan"] = {
                "execution_mode": "sequential",
                "estimated_total_time": len(result["subtasks"]) * 300
            }
        
        if "confidence" not in result:
            result["confidence"] = 0.7
        
        # 验证子任务格式
        validated_subtasks = []
        for i, subtask in enumerate(result["subtasks"]):
            if not isinstance(subtask, dict):
                continue
            
            validated_subtask = {
                "id": subtask.get("id", f"subtask_{i+1}"),
                "title": subtask.get("title", f"子任务 {i+1}"),
                "description": subtask.get("description", ""),
                "assigned_agent": subtask.get("assigned_agent", "generic_agent"),
                "dependencies": subtask.get("dependencies", []),
                "estimated_time": subtask.get("estimated_time", 300)
            }
            validated_subtasks.append(validated_subtask)
        
        result["subtasks"] = validated_subtasks
        
        return result
    
    def _generate_default_subtasks(self, task_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成默认子任务"""
        requirements = task_data.get("requirements", [])
        
        subtasks = []
        for i, req in enumerate(requirements[:5]):  # 最多5个子任务
            subtasks.append({
                "id": f"subtask_{i+1}",
                "title": f"处理需求: {req}",
                "description": f"执行任务需求: {req}",
                "assigned_agent": "generic_agent",
                "dependencies": [f"subtask_{i}"] if i > 0 else [],
                "estimated_time": 300
            })
        
        if not subtasks:
            # 如果没有具体需求，创建通用子任务
            subtasks = [
                {
                    "id": "subtask_1",
                    "title": "任务准备",
                    "description": "准备任务执行所需的资源和环境",
                    "assigned_agent": "generic_agent",
                    "dependencies": [],
                    "estimated_time": 180
                },
                {
                    "id": "subtask_2", 
                    "title": "任务执行",
                    "description": "执行主要任务逻辑",
                    "assigned_agent": "generic_agent",
                    "dependencies": ["subtask_1"],
                    "estimated_time": 600
                },
                {
                    "id": "subtask_3",
                    "title": "结果整理",
                    "description": "整理和验证任务执行结果",
                    "assigned_agent": "generic_agent", 
                    "dependencies": ["subtask_2"],
                    "estimated_time": 180
                }
            ]
        
        return subtasks
    
    def _get_default_decomposition(self, task_data: Dict[str, Any], error: Optional[str] = None) -> Dict[str, Any]:
        """获取默认分解结果"""
        
        subtasks = self._generate_default_subtasks(task_data)
        
        result = {
            "subtasks": subtasks,
            "execution_plan": {
                "execution_mode": "sequential",
                "estimated_total_time": sum(st["estimated_time"] for st in subtasks)
            },
            "dependencies_graph": {st["id"]: st["dependencies"] for st in subtasks},
            "decomposition_strategy": "requirement_based",
            "confidence": 0.5,
            "decomposition_timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "fallback_decomposition": True
        }
        
        if error:
            result["error"] = error
            result["confidence"] = 0.3
        
        return result


class LLMCoordinator:
    """基于LLM的协调器"""
    
    def __init__(self):
        self.agent_id = "llm_coordinator"
        self.agent_type = "coordinator"
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理智能体协调"""
        try:
            # 提取协调信息
            subtasks = task_data.get("subtasks", [])
            available_agents = task_data.get("available_agents", [])
            coordination_context = task_data.get("coordination_context", {})
            
            # 构建系统提示
            system_message = """你是一个智能体协调专家，负责协调多个智能体的工作。

你的职责包括：
1. 分析智能体能力和任务需求的匹配度
2. 解决智能体之间的冲突
3. 优化资源分配
4. 监控执行进度
5. 调整协调策略

请以JSON格式返回协调结果，包含以下字段：
- agent_assignments: 智能体分配方案
- coordination_strategy: 协调策略
- conflict_resolutions: 冲突解决方案
- resource_allocation: 资源分配计划
- monitoring_plan: 监控计划
- confidence: 协调置信度"""

            # 构建协调提示
            prompt = f"""
请协调以下智能体工作：

子任务列表: {json.dumps(subtasks, ensure_ascii=False)}
可用智能体: {json.dumps(available_agents, ensure_ascii=False)}
协调上下文: {json.dumps(coordination_context, ensure_ascii=False)}

请制定合理的协调方案，确保任务高效执行。
"""
            
            # 调用LLM进行协调
            llm_response = await chat(prompt, system_message, temperature=0.3)
            
            # 解析LLM响应
            try:
                coordination_result = json.loads(llm_response)
                coordination_result = self._validate_coordination_result(coordination_result, task_data)
                
            except json.JSONDecodeError as e:
                logger.warning(f"协调LLM响应解析失败: {e}")
                coordination_result = self._get_default_coordination(task_data)
                coordination_result["llm_response"] = llm_response
            
            # 添加执行元数据
            coordination_result["coordination_timestamp"] = datetime.now().isoformat()
            coordination_result["agent_id"] = self.agent_id
            
            return coordination_result
            
        except Exception as e:
            logger.error(f"智能体协调失败: {e}")
            return self._get_default_coordination(task_data, error=str(e))
    
    def _validate_coordination_result(self, result: Dict[str, Any], task_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证协调结果"""
        
        defaults = {
            "agent_assignments": {},
            "coordination_strategy": "sequential",
            "conflict_resolutions": [],
            "resource_allocation": {},
            "monitoring_plan": {"check_interval": 60},
            "confidence": 0.7
        }
        
        for key, default_value in defaults.items():
            if key not in result:
                result[key] = default_value
        
        return result
    
    def _get_default_coordination(self, task_data: Dict[str, Any], error: Optional[str] = None) -> Dict[str, Any]:
        """获取默认协调结果"""
        
        subtasks = task_data.get("subtasks", [])
        
        # 简单的顺序分配
        agent_assignments = {}
        for i, subtask in enumerate(subtasks):
            agent_assignments[subtask.get("id", f"subtask_{i}")] = subtask.get("assigned_agent", "generic_agent")
        
        result = {
            "agent_assignments": agent_assignments,
            "coordination_strategy": "sequential",
            "conflict_resolutions": [],
            "resource_allocation": {"cpu": "shared", "memory": "shared"},
            "monitoring_plan": {"check_interval": 60, "timeout": 3600},
            "confidence": 0.5,
            "coordination_timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "fallback_coordination": True
        }
        
        if error:
            result["error"] = error
            result["confidence"] = 0.3
        
        return result


class LLMGenericAgent:
    """基于LLM的通用智能体"""
    
    def __init__(self, agent_type: str = "generic", capabilities: List[str] = None):
        self.agent_id = f"llm_{agent_type}_agent"
        self.agent_type = agent_type
        self.capabilities = capabilities or ["general_processing"]
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理通用任务"""
        try:
            # 提取任务信息
            task_title = task_data.get("title", "")
            task_description = task_data.get("description", "")
            task_requirements = task_data.get("requirements", [])
            
            # 构建系统提示
            system_message = f"""你是一个{self.agent_type}智能体，具备以下能力: {', '.join(self.capabilities)}。

你的职责是根据任务要求，提供专业的处理结果。

请以JSON格式返回处理结果，包含以下字段：
- processing_result: 处理结果
- output_data: 输出数据
- processing_summary: 处理摘要
- quality_score: 质量分数(0-1)
- recommendations: 建议
- confidence: 处理置信度(0-1)"""

            # 构建处理提示
            prompt = f"""
请处理以下任务：

任务标题: {task_title}
任务描述: {task_description}
具体要求: {json.dumps(task_requirements, ensure_ascii=False)}

请根据你的专业能力提供高质量的处理结果。
"""
            
            # 调用LLM进行处理
            llm_response = await chat(prompt, system_message, temperature=0.5)
            
            # 解析LLM响应
            try:
                processing_result = json.loads(llm_response)
                processing_result = self._validate_processing_result(processing_result, task_data)
                
            except json.JSONDecodeError as e:
                logger.warning(f"通用智能体LLM响应解析失败: {e}")
                processing_result = self._get_default_processing_result(task_data)
                processing_result["llm_response"] = llm_response
            
            # 添加执行元数据
            processing_result["processing_timestamp"] = datetime.now().isoformat()
            processing_result["agent_id"] = self.agent_id
            processing_result["agent_type"] = self.agent_type
            
            return processing_result
            
        except Exception as e:
            logger.error(f"通用智能体处理失败: {e}")
            return self._get_default_processing_result(task_data, error=str(e))
    
    def _validate_processing_result(self, result: Dict[str, Any], task_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证处理结果"""
        
        defaults = {
            "processing_result": "任务处理完成",
            "output_data": {},
            "processing_summary": f"{self.agent_type}智能体已完成任务处理",
            "quality_score": 0.8,
            "recommendations": [],
            "confidence": 0.8
        }
        
        for key, default_value in defaults.items():
            if key not in result:
                result[key] = default_value
        
        # 验证数值范围
        if not isinstance(result["quality_score"], (int, float)) or not 0 <= result["quality_score"] <= 1:
            result["quality_score"] = 0.8
        
        if not isinstance(result["confidence"], (int, float)) or not 0 <= result["confidence"] <= 1:
            result["confidence"] = 0.8
        
        return result
    
    def _get_default_processing_result(self, task_data: Dict[str, Any], error: Optional[str] = None) -> Dict[str, Any]:
        """获取默认处理结果"""
        
        task_title = task_data.get("title", "未知任务")
        
        result = {
            "processing_result": f"已处理任务: {task_title}",
            "output_data": {
                "processed": True,
                "task_id": task_data.get("task_id"),
                "processing_method": "default"
            },
            "processing_summary": f"{self.agent_type}智能体使用默认方法处理了任务",
            "quality_score": 0.6,
            "recommendations": ["建议进一步优化处理逻辑"],
            "confidence": 0.5,
            "processing_timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "fallback_processing": True
        }
        
        if error:
            result["error"] = error
            result["confidence"] = 0.3
            result["quality_score"] = 0.3
        
        return result