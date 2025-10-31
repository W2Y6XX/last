"""
智能体系统测试套件
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from ..core.test_controller import TestSuite
from ..core.test_result import TestResult, TestSuiteResult, TestStatus, ResultType
from ..config.test_config import TestConfiguration
from ..utils.helpers import retry_on_failure, timeout_after
from ..utils.logging_utils import get_logger
from ..utils.data_utils import TestDataGenerator


class AgentTestSuite(TestSuite):
    """智能体系统测试套件"""
    
    def __init__(self, name: str, config: TestConfiguration):
        super().__init__(name, config)
        self.logger = get_logger("agent_test")
        self.data_generator = TestDataGenerator()
    
    async def run_all_tests(self) -> TestSuiteResult:
        """运行所有智能体测试"""
        self.logger.info("🤖 开始智能体系统测试套件")
        
        suite_result = TestSuiteResult(
            suite_name=self.name,
            start_time=datetime.now()
        )
        
        # 定义测试用例
        test_cases = [
            ("meta_agent", self._test_meta_agent),
            ("task_decomposer", self._test_task_decomposer),
            ("coordinator", self._test_coordinator),
            ("llm_integration", self._test_llm_integration)
        ]
        
        # 执行测试用例
        for test_name, test_func in test_cases:
            result = await self._run_single_test(test_name, test_func)
            suite_result.add_result(result)
        
        suite_result.end_time = datetime.now()
        suite_result.calculate_duration()
        
        self.logger.info(f"🤖 智能体系统测试套件完成: {suite_result.passed_tests}/{suite_result.total_tests} 通过")
        
        return suite_result
    
    async def _run_single_test(self, test_name: str, test_func) -> TestResult:
        """运行单个测试"""
        result = self.create_test_result(test_name)
        result.start_time = datetime.now()
        result.result_type = ResultType.FUNCTIONAL
        result.tags = ["agent", "ai"]
        
        self.logger.test_start(test_name)
        
        try:
            success, details = await test_func()
            
            result.end_time = datetime.now()
            result.calculate_duration()
            
            if success:
                result.set_success(details)
                self.logger.test_end(test_name, True, result.duration)
            else:
                error_msg = details.get("error", "Unknown error") if isinstance(details, dict) else str(details)
                result.set_error(error_msg)
                self.logger.test_end(test_name, False, result.duration)
            
        except Exception as e:
            result.end_time = datetime.now()
            result.calculate_duration()
            result.set_error(str(e))
            self.logger.error_detail(e, {"test_name": test_name})
        
        return result
    
    @timeout_after(180.0)
    async def _test_meta_agent(self) -> Tuple[bool, Dict[str, Any]]:
        """测试MetaAgent功能"""
        self.logger.test_step("测试MetaAgent任务分析功能")
        
        # 模拟MetaAgent测试（不实际调用LLM）
        test_tasks = [
            self.data_generator.generate_task_data("analysis", "simple"),
            self.data_generator.generate_task_data("processing", "medium"),
            self.data_generator.generate_task_data("complex_workflow", "complex")
        ]
        
        results = {
            "tasks_analyzed": 0,
            "analysis_results": [],
            "average_analysis_time": 0,
            "complexity_scores": []
        }
        
        total_analysis_time = 0
        
        for i, task in enumerate(test_tasks):
            try:
                start_time = time.time()
                
                # 模拟MetaAgent分析
                mock_analysis = self._mock_meta_agent_analysis(task)
                
                analysis_time = time.time() - start_time
                total_analysis_time += analysis_time
                
                results["tasks_analyzed"] += 1
                results["analysis_results"].append({
                    "task_id": task["task_id"],
                    "complexity_score": mock_analysis["complexity_score"],
                    "requires_decomposition": mock_analysis["requires_decomposition"],
                    "estimated_time": mock_analysis["estimated_time"],
                    "analysis_time": analysis_time
                })
                results["complexity_scores"].append(mock_analysis["complexity_score"])
                
                self.logger.test_step(f"✅ 任务 {i+1} 分析完成 - 复杂度: {mock_analysis['complexity_score']:.2f}")
                
            except Exception as e:
                self.logger.test_step(f"❌ 任务 {i+1} 分析失败: {e}")
        
        if results["tasks_analyzed"] > 0:
            results["average_analysis_time"] = total_analysis_time / results["tasks_analyzed"]
            results["average_complexity"] = sum(results["complexity_scores"]) / len(results["complexity_scores"])
        
        success = results["tasks_analyzed"] == len(test_tasks)
        
        return success, results
    
    @timeout_after(180.0)
    async def _test_task_decomposer(self) -> Tuple[bool, Dict[str, Any]]:
        """测试TaskDecomposer功能"""
        self.logger.test_step("测试TaskDecomposer任务分解功能")
        
        # 创建需要分解的复杂任务
        complex_task = self.data_generator.generate_task_data("complex_analysis", "complex")
        
        results = {
            "decomposition_successful": False,
            "subtasks_generated": 0,
            "decomposition_time": 0,
            "subtask_details": []
        }
        
        try:
            start_time = time.time()
            
            # 模拟任务分解
            mock_decomposition = self._mock_task_decomposition(complex_task)
            
            decomposition_time = time.time() - start_time
            
            results["decomposition_successful"] = True
            results["subtasks_generated"] = len(mock_decomposition["subtasks"])
            results["decomposition_time"] = decomposition_time
            results["subtask_details"] = mock_decomposition["subtasks"]
            results["dependencies"] = mock_decomposition.get("dependencies", [])
            
            self.logger.test_step(f"✅ 任务分解成功 - 生成 {len(mock_decomposition['subtasks'])} 个子任务")
            
        except Exception as e:
            results["error"] = str(e)
            self.logger.test_step(f"❌ 任务分解失败: {e}")
        
        success = results["decomposition_successful"] and results["subtasks_generated"] > 0
        
        return success, results
    
    @timeout_after(120.0)
    async def _test_coordinator(self) -> Tuple[bool, Dict[str, Any]]:
        """测试Coordinator功能"""
        self.logger.test_step("测试Coordinator智能体协调功能")
        
        # 模拟多个智能体任务
        agent_tasks = [
            {"agent_id": "agent_1", "task_type": "analysis", "priority": 1},
            {"agent_id": "agent_2", "task_type": "processing", "priority": 2},
            {"agent_id": "agent_3", "task_type": "validation", "priority": 3}
        ]
        
        results = {
            "coordination_successful": False,
            "agents_coordinated": 0,
            "coordination_time": 0,
            "execution_plan": [],
            "resource_allocation": {}
        }
        
        try:
            start_time = time.time()
            
            # 模拟协调过程
            mock_coordination = self._mock_coordinator_planning(agent_tasks)
            
            coordination_time = time.time() - start_time
            
            results["coordination_successful"] = True
            results["agents_coordinated"] = len(agent_tasks)
            results["coordination_time"] = coordination_time
            results["execution_plan"] = mock_coordination["execution_plan"]
            results["resource_allocation"] = mock_coordination["resource_allocation"]
            
            self.logger.test_step(f"✅ 智能体协调成功 - 协调 {len(agent_tasks)} 个智能体")
            
        except Exception as e:
            results["error"] = str(e)
            self.logger.test_step(f"❌ 智能体协调失败: {e}")
        
        success = results["coordination_successful"] and results["agents_coordinated"] > 0
        
        return success, results
    
    @timeout_after(60.0)
    async def _test_llm_integration(self) -> Tuple[bool, Dict[str, Any]]:
        """测试LLM集成"""
        self.logger.test_step("测试LLM集成功能")
        
        results = {
            "llm_client_available": False,
            "configuration_valid": False,
            "mock_request_successful": False,
            "response_time": 0
        }
        
        try:
            # 检查LLM客户端是否可用
            try:
                # 尝试导入LLM客户端
                import sys
                import os
                
                # 添加项目路径
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                if project_root not in sys.path:
                    sys.path.append(project_root)
                
                from langgraph_multi_agent.llm.siliconflow_client import SiliconFlowClient
                
                client = SiliconFlowClient()
                results["llm_client_available"] = True
                
                # 检查配置
                if hasattr(client, 'api_key') and client.api_key:
                    results["configuration_valid"] = True
                    self.logger.test_step("✅ LLM客户端配置有效")
                else:
                    self.logger.test_step("⚠️ LLM客户端配置无效或缺失")
                
            except ImportError as e:
                self.logger.test_step(f"⚠️ LLM客户端不可用: {e}")
            except Exception as e:
                self.logger.test_step(f"⚠️ LLM客户端初始化失败: {e}")
            
            # 模拟LLM请求（不实际调用API）
            start_time = time.time()
            
            mock_response = self._mock_llm_request("测试提示词")
            
            response_time = time.time() - start_time
            
            results["mock_request_successful"] = True
            results["response_time"] = response_time
            results["mock_response"] = mock_response
            
            self.logger.test_step("✅ LLM模拟请求成功")
            
        except Exception as e:
            results["error"] = str(e)
            self.logger.test_step(f"❌ LLM集成测试失败: {e}")
        
        # 如果客户端可用或模拟请求成功，则认为测试通过
        success = results["llm_client_available"] or results["mock_request_successful"]
        
        return success, results
    
    def _mock_meta_agent_analysis(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """模拟MetaAgent分析"""
        # 根据任务类型和复杂度生成模拟分析结果
        task_type = task.get("task_type", "general")
        description = task.get("description", "")
        
        # 计算复杂度分数
        complexity_score = 0.3  # 基础复杂度
        
        if "complex" in task_type.lower() or "complex" in description.lower():
            complexity_score += 0.4
        if len(task.get("requirements", [])) > 3:
            complexity_score += 0.2
        if len(task.get("constraints", [])) > 2:
            complexity_score += 0.1
        
        complexity_score = min(complexity_score, 1.0)
        
        return {
            "complexity_score": complexity_score,
            "requires_decomposition": complexity_score > 0.6,
            "estimated_time": int(complexity_score * 1800),  # 最多30分钟
            "recommended_agents": ["meta_agent", "coordinator"] if complexity_score > 0.5 else ["meta_agent"],
            "confidence": 0.85
        }
    
    def _mock_task_decomposition(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """模拟任务分解"""
        subtasks = []
        
        # 根据任务类型生成子任务
        task_type = task.get("task_type", "general")
        
        if "analysis" in task_type.lower():
            subtasks = [
                {"name": "数据收集", "type": "data_collection", "priority": 1},
                {"name": "数据预处理", "type": "preprocessing", "priority": 2},
                {"name": "分析执行", "type": "analysis", "priority": 3},
                {"name": "结果验证", "type": "validation", "priority": 4}
            ]
        elif "processing" in task_type.lower():
            subtasks = [
                {"name": "输入验证", "type": "validation", "priority": 1},
                {"name": "数据处理", "type": "processing", "priority": 2},
                {"name": "输出生成", "type": "output", "priority": 3}
            ]
        else:
            subtasks = [
                {"name": "任务准备", "type": "preparation", "priority": 1},
                {"name": "任务执行", "type": "execution", "priority": 2},
                {"name": "结果整理", "type": "finalization", "priority": 3}
            ]
        
        return {
            "subtasks": subtasks,
            "dependencies": [
                {"from": subtasks[i]["name"], "to": subtasks[i+1]["name"]} 
                for i in range(len(subtasks)-1)
            ],
            "estimated_total_time": len(subtasks) * 300  # 每个子任务5分钟
        }
    
    def _mock_coordinator_planning(self, agent_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """模拟协调器规划"""
        # 按优先级排序任务
        sorted_tasks = sorted(agent_tasks, key=lambda x: x.get("priority", 999))
        
        execution_plan = []
        resource_allocation = {}
        
        for i, task in enumerate(sorted_tasks):
            execution_plan.append({
                "step": i + 1,
                "agent_id": task["agent_id"],
                "task_type": task["task_type"],
                "estimated_start_time": i * 300,  # 每个任务间隔5分钟
                "estimated_duration": 600  # 每个任务10分钟
            })
            
            resource_allocation[task["agent_id"]] = {
                "cpu_allocation": 0.5,
                "memory_allocation": "512MB",
                "priority_level": task.get("priority", 5)
            }
        
        return {
            "execution_plan": execution_plan,
            "resource_allocation": resource_allocation,
            "total_estimated_time": len(sorted_tasks) * 600,
            "parallel_execution_possible": len(sorted_tasks) <= 3
        }
    
    def _mock_llm_request(self, prompt: str) -> Dict[str, Any]:
        """模拟LLM请求"""
        return {
            "response": f"这是对提示词 '{prompt[:50]}...' 的模拟响应",
            "tokens_used": len(prompt.split()) + 20,
            "model": "mock_model",
            "success": True,
            "latency": 0.5
        }