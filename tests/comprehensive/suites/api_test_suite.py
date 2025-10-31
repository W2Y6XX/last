"""
API测试套件
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from ..core.test_controller import TestSuite
from ..core.test_result import TestResult, TestSuiteResult, TestStatus, ResultType
from ..config.test_config import TestConfiguration
from ..utils.helpers import retry_on_failure, timeout_after
from ..utils.logging_utils import get_logger
from ..utils.data_utils import TestDataGenerator


class APITestSuite(TestSuite):
    """API测试套件"""
    
    def __init__(self, name: str, config: TestConfiguration):
        super().__init__(name, config)
        self.logger = get_logger("api_test")
        self.data_generator = TestDataGenerator()
        self.session = None
    
    async def run_all_tests(self) -> TestSuiteResult:
        """运行所有API测试"""
        self.logger.info("🔌 开始API测试套件")
        
        suite_result = TestSuiteResult(
            suite_name=self.name,
            start_time=datetime.now()
        )
        
        try:
            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # 定义测试用例
            test_cases = [
                ("system_endpoints", self._test_system_endpoints),
                ("agent_endpoints", self._test_agent_endpoints),
                ("task_endpoints", self._test_task_endpoints),
                ("websocket_endpoints", self._test_websocket_endpoints),
                ("error_handling", self._test_error_handling)
            ]
            
            # 执行测试用例
            for test_name, test_func in test_cases:
                result = await self._run_single_test(test_name, test_func)
                suite_result.add_result(result)
        
        finally:
            # 清理HTTP会话
            if self.session:
                await self.session.close()
        
        suite_result.end_time = datetime.now()
        suite_result.calculate_duration()
        
        self.logger.info(f"🔌 API测试套件完成: {suite_result.passed_tests}/{suite_result.total_tests} 通过")
        
        return suite_result
    
    async def _run_single_test(self, test_name: str, test_func) -> TestResult:
        """运行单个测试"""
        result = self.create_test_result(test_name)
        result.start_time = datetime.now()
        result.result_type = ResultType.FUNCTIONAL
        result.tags = ["api", "backend"]
        
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
            
            # 添加性能指标
            if "average_response_time" in details:
                result.add_metric("avg_response_time", details["average_response_time"], "s", 
                                self.config.performance_thresholds.get("max_response_time", 5.0))
            
        except Exception as e:
            result.end_time = datetime.now()
            result.calculate_duration()
            result.set_error(str(e))
            self.logger.error_detail(e, {"test_name": test_name})
        
        return result
    
    @timeout_after(60.0)
    async def _test_system_endpoints(self) -> Tuple[bool, Dict[str, Any]]:
        """测试系统管理端点"""
        self.logger.test_step("测试系统管理API端点")
        
        endpoints = [
            ("/", "GET", "根路径"),
            ("/health", "GET", "健康检查"),
            ("/docs", "GET", "API文档"),
            ("/api/v1/system/status", "GET", "系统状态"),
            ("/api/v1/system/health", "GET", "系统健康"),
            ("/api/v1/system/metrics", "GET", "系统指标")
        ]
        
        results = {}
        all_success = True
        total_response_time = 0
        successful_requests = 0
        
        for endpoint, method, description in endpoints:
            try:
                start_time = time.time()
                
                url = f"{self.config.base_url}{endpoint}"
                
                async with self.session.request(method, url) as response:
                    response_time = time.time() - start_time
                    total_response_time += response_time
                    
                    success = response.status < 400
                    
                    # 读取响应内容
                    try:
                        if response.content_type == 'application/json':
                            content = await response.json()
                            content_type = "json"
                        else:
                            content = await response.text()
                            content_type = "text"
                    except:
                        content = None
                        content_type = "unknown"
                    
                    results[endpoint] = {
                        "success": success,
                        "status": response.status,
                        "method": method,
                        "response_time": response_time,
                        "description": description,
                        "content_type": content_type,
                        "content_length": len(str(content)) if content else 0,
                        "headers": dict(response.headers)
                    }
                    
                    if success:
                        successful_requests += 1
                        self.logger.test_step(f"✅ {description} ({endpoint}): {response.status} - {response_time:.3f}s")
                    else:
                        self.logger.test_step(f"❌ {description} ({endpoint}): {response.status} - {response_time:.3f}s")
                        all_success = False
                
            except Exception as e:
                results[endpoint] = {
                    "success": False,
                    "error": str(e),
                    "method": method,
                    "description": description,
                    "error_type": type(e).__name__
                }
                all_success = False
                self.logger.test_step(f"❌ {description} ({endpoint}): 异常 - {e}")
        
        # 计算统计信息
        avg_response_time = total_response_time / len(endpoints) if endpoints else 0
        success_rate = (successful_requests / len(endpoints) * 100) if endpoints else 0
        
        summary = {
            "endpoints_tested": len(endpoints),
            "successful_requests": successful_requests,
            "failed_requests": len(endpoints) - successful_requests,
            "success_rate": success_rate,
            "average_response_time": avg_response_time,
            "total_response_time": total_response_time,
            "results": results
        }
        
        return all_success, summary
    
    @timeout_after(60.0)
    async def _test_agent_endpoints(self) -> Tuple[bool, Dict[str, Any]]:
        """测试智能体管理端点"""
        self.logger.test_step("测试智能体管理API端点")
        
        endpoints = [
            ("/api/v1/agents", "GET", "智能体列表"),
            ("/api/v1/agents/status", "GET", "智能体状态"),
            ("/api/v1/agents/meta", "GET", "元智能体信息"),
            ("/api/v1/agents/coordinator", "GET", "协调器信息"),
            ("/api/v1/agents/decomposer", "GET", "任务分解器信息")
        ]
        
        results = {}
        all_success = True
        
        for endpoint, method, description in endpoints:
            try:
                start_time = time.time()
                
                url = f"{self.config.base_url}{endpoint}"
                
                async with self.session.request(method, url) as response:
                    response_time = time.time() - start_time
                    
                    success = response.status < 400
                    
                    # 读取响应内容
                    try:
                        content = await response.json()
                        
                        # 验证智能体数据结构
                        if success and endpoint == "/api/v1/agents":
                            if isinstance(content, list):
                                agent_validation = self._validate_agent_list(content)
                                results[f"{endpoint}_validation"] = agent_validation
                            elif isinstance(content, dict) and "agents" in content:
                                agent_validation = self._validate_agent_list(content["agents"])
                                results[f"{endpoint}_validation"] = agent_validation
                        
                    except:
                        content = await response.text()
                    
                    results[endpoint] = {
                        "success": success,
                        "status": response.status,
                        "method": method,
                        "response_time": response_time,
                        "description": description,
                        "content_type": response.content_type,
                        "content_length": len(str(content)) if content else 0
                    }
                    
                    if success:
                        self.logger.test_step(f"✅ {description}: {response.status} - {response_time:.3f}s")
                    else:
                        self.logger.test_step(f"❌ {description}: {response.status} - {response_time:.3f}s")
                        all_success = False
                
            except Exception as e:
                results[endpoint] = {
                    "success": False,
                    "error": str(e),
                    "method": method,
                    "description": description,
                    "error_type": type(e).__name__
                }
                all_success = False
                self.logger.test_step(f"❌ {description}: 异常 - {e}")
        
        return all_success, results
    
    @timeout_after(120.0)
    async def _test_task_endpoints(self) -> Tuple[bool, Dict[str, Any]]:
        """测试任务管理端点"""
        self.logger.test_step("测试任务管理API端点")
        
        results = {}
        created_task_id = None
        
        # 1. 测试获取任务列表
        try:
            async with self.session.get(f"{self.config.base_url}/api/v1/tasks") as response:
                list_success = response.status < 400
                
                results["list_tasks"] = {
                    "success": list_success,
                    "status": response.status,
                    "description": "获取任务列表"
                }
                
                if list_success:
                    self.logger.test_step("✅ 获取任务列表成功")
                else:
                    self.logger.test_step(f"❌ 获取任务列表失败: {response.status}")
        
        except Exception as e:
            results["list_tasks"] = {
                "success": False,
                "error": str(e),
                "description": "获取任务列表"
            }
            self.logger.test_step(f"❌ 获取任务列表异常: {e}")
        
        # 2. 测试创建任务
        try:
            task_data = self.data_generator.generate_task_data("test", "simple")
            
            async with self.session.post(
                f"{self.config.base_url}/api/v1/tasks",
                json=task_data
            ) as response:
                create_success = response.status in [200, 201]
                
                results["create_task"] = {
                    "success": create_success,
                    "status": response.status,
                    "description": "创建任务"
                }
                
                if create_success:
                    try:
                        response_data = await response.json()
                        created_task_id = response_data.get("task_id") or response_data.get("id")
                        results["create_task"]["task_id"] = created_task_id
                        self.logger.test_step(f"✅ 创建任务成功: {created_task_id}")
                    except:
                        self.logger.test_step("✅ 创建任务成功但无法解析响应")
                else:
                    self.logger.test_step(f"❌ 创建任务失败: {response.status}")
        
        except Exception as e:
            results["create_task"] = {
                "success": False,
                "error": str(e),
                "description": "创建任务"
            }
            self.logger.test_step(f"❌ 创建任务异常: {e}")
        
        # 3. 测试获取特定任务（如果创建成功）
        if created_task_id:
            try:
                async with self.session.get(
                    f"{self.config.base_url}/api/v1/tasks/{created_task_id}"
                ) as response:
                    get_success = response.status < 400
                    
                    results["get_task"] = {
                        "success": get_success,
                        "status": response.status,
                        "description": "获取特定任务",
                        "task_id": created_task_id
                    }
                    
                    if get_success:
                        self.logger.test_step(f"✅ 获取任务成功: {created_task_id}")
                    else:
                        self.logger.test_step(f"❌ 获取任务失败: {response.status}")
            
            except Exception as e:
                results["get_task"] = {
                    "success": False,
                    "error": str(e),
                    "description": "获取特定任务",
                    "task_id": created_task_id
                }
                self.logger.test_step(f"❌ 获取任务异常: {e}")
        
        # 4. 测试任务统计
        try:
            async with self.session.get(
                f"{self.config.base_url}/api/v1/tasks/statistics"
            ) as response:
                stats_success = response.status < 400
                
                results["task_statistics"] = {
                    "success": stats_success,
                    "status": response.status,
                    "description": "任务统计"
                }
                
                if stats_success:
                    self.logger.test_step("✅ 获取任务统计成功")
                else:
                    self.logger.test_step(f"❌ 获取任务统计失败: {response.status}")
        
        except Exception as e:
            results["task_statistics"] = {
                "success": False,
                "error": str(e),
                "description": "任务统计"
            }
            self.logger.test_step(f"❌ 获取任务统计异常: {e}")
        
        # 计算总体成功率
        successful_operations = sum(1 for r in results.values() if r.get("success", False))
        total_operations = len(results)
        overall_success = (successful_operations / total_operations) >= 0.7 if total_operations > 0 else False
        
        summary = {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "success_rate": (successful_operations / total_operations * 100) if total_operations > 0 else 0,
            "created_task_id": created_task_id,
            "operations": results
        }
        
        return overall_success, summary
    
    @timeout_after(45.0)
    async def _test_websocket_endpoints(self) -> Tuple[bool, Dict[str, Any]]:
        """测试WebSocket端点"""
        self.logger.test_step("测试WebSocket API端点")
        
        # 由于WebSocket测试比较复杂，这里实现基本的连接测试
        try:
            # 检查WebSocket相关的HTTP端点
            ws_endpoints = [
                ("/ws", "GET", "WebSocket端点"),
                ("/api/v1/ws/status", "GET", "WebSocket状态")
            ]
            
            results = {}
            
            for endpoint, method, description in ws_endpoints:
                try:
                    url = f"{self.config.base_url}{endpoint}"
                    
                    async with self.session.request(method, url) as response:
                        # WebSocket端点可能返回426 Upgrade Required，这是正常的
                        success = response.status in [200, 426, 101]
                        
                        results[endpoint] = {
                            "success": success,
                            "status": response.status,
                            "method": method,
                            "description": description
                        }
                        
                        if success:
                            self.logger.test_step(f"✅ {description}: {response.status}")
                        else:
                            self.logger.test_step(f"❌ {description}: {response.status}")
                
                except Exception as e:
                    results[endpoint] = {
                        "success": False,
                        "error": str(e),
                        "method": method,
                        "description": description
                    }
                    self.logger.test_step(f"❌ {description}: 异常 - {e}")
            
            # 尝试WebSocket连接（如果有websockets库）
            try:
                import websockets
                
                ws_url = self.config.base_url.replace("http://", "ws://").replace("https://", "wss://")
                ws_url += "/ws"
                
                try:
                    async with websockets.connect(ws_url, timeout=10) as websocket:
                        await websocket.send('{"type": "ping"}')
                        
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            results["websocket_connection"] = {
                                "success": True,
                                "description": "WebSocket连接测试",
                                "response_received": True
                            }
                            self.logger.test_step("✅ WebSocket连接测试成功")
                        except asyncio.TimeoutError:
                            results["websocket_connection"] = {
                                "success": True,  # 连接成功即可
                                "description": "WebSocket连接测试",
                                "response_received": False,
                                "note": "连接成功但未收到响应"
                            }
                            self.logger.test_step("✅ WebSocket连接成功（无响应）")
                
                except Exception as e:
                    results["websocket_connection"] = {
                        "success": False,
                        "error": str(e),
                        "description": "WebSocket连接测试"
                    }
                    self.logger.test_step(f"❌ WebSocket连接失败: {e}")
            
            except ImportError:
                results["websocket_connection"] = {
                    "success": None,
                    "skipped": True,
                    "reason": "websockets library not available",
                    "description": "WebSocket连接测试"
                }
                self.logger.test_step("⏭️ 跳过WebSocket连接测试 - 缺少websockets库")
            
            # 计算成功率
            testable_results = [r for r in results.values() if not r.get("skipped", False)]
            successful_tests = sum(1 for r in testable_results if r.get("success", False))
            total_tests = len(testable_results)
            
            overall_success = (successful_tests / total_tests) >= 0.5 if total_tests > 0 else True
            
            summary = {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "skipped_tests": len(results) - total_tests,
                "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
                "results": results
            }
            
            return overall_success, summary
        
        except Exception as e:
            return False, {"error": str(e), "error_type": type(e).__name__}
    
    @timeout_after(60.0)
    async def _test_error_handling(self) -> Tuple[bool, Dict[str, Any]]:
        """测试API错误处理"""
        self.logger.test_step("测试API错误处理")
        
        error_tests = [
            # 测试404错误
            {
                "name": "not_found",
                "url": f"{self.config.base_url}/api/v1/nonexistent",
                "method": "GET",
                "expected_status": 404,
                "description": "不存在的端点"
            },
            # 测试405错误
            {
                "name": "method_not_allowed",
                "url": f"{self.config.base_url}/api/v1/tasks",
                "method": "DELETE",  # 假设不支持DELETE
                "expected_status": 405,
                "description": "不支持的HTTP方法"
            },
            # 测试400错误
            {
                "name": "bad_request",
                "url": f"{self.config.base_url}/api/v1/tasks",
                "method": "POST",
                "data": {"invalid": "data"},  # 无效数据
                "expected_status": 400,
                "description": "无效请求数据"
            },
            # 测试超大请求
            {
                "name": "large_request",
                "url": f"{self.config.base_url}/api/v1/tasks",
                "method": "POST",
                "data": {"description": "x" * 10000},  # 超大数据
                "expected_status": [400, 413],  # Bad Request 或 Payload Too Large
                "description": "超大请求负载"
            }
        ]
        
        results = {}
        successful_error_tests = 0
        
        for test in error_tests:
            try:
                start_time = time.time()
                
                kwargs = {}
                if test.get("data"):
                    kwargs["json"] = test["data"]
                
                async with self.session.request(
                    test["method"], 
                    test["url"], 
                    **kwargs
                ) as response:
                    
                    response_time = time.time() - start_time
                    
                    expected_statuses = test["expected_status"]
                    if not isinstance(expected_statuses, list):
                        expected_statuses = [expected_statuses]
                    
                    success = response.status in expected_statuses
                    
                    # 检查错误响应格式
                    error_format_valid = False
                    try:
                        if response.content_type == 'application/json':
                            error_data = await response.json()
                            # 检查是否有错误信息字段
                            error_format_valid = any(
                                key in error_data 
                                for key in ["error", "message", "detail", "errors"]
                            )
                    except:
                        pass
                    
                    results[test["name"]] = {
                        "success": success,
                        "actual_status": response.status,
                        "expected_status": test["expected_status"],
                        "response_time": response_time,
                        "description": test["description"],
                        "error_format_valid": error_format_valid
                    }
                    
                    if success:
                        successful_error_tests += 1
                        self.logger.test_step(f"✅ {test['description']}: {response.status} (预期)")
                    else:
                        self.logger.test_step(f"❌ {test['description']}: {response.status} (预期 {test['expected_status']})")
            
            except Exception as e:
                results[test["name"]] = {
                    "success": False,
                    "error": str(e),
                    "description": test["description"],
                    "error_type": type(e).__name__
                }
                self.logger.test_step(f"❌ {test['description']}: 异常 - {e}")
        
        # 计算成功率
        total_error_tests = len(error_tests)
        error_handling_success_rate = (successful_error_tests / total_error_tests * 100) if total_error_tests > 0 else 0
        overall_success = error_handling_success_rate >= 70  # 70%以上的错误处理测试通过
        
        summary = {
            "total_error_tests": total_error_tests,
            "successful_error_tests": successful_error_tests,
            "error_handling_success_rate": error_handling_success_rate,
            "results": results
        }
        
        return overall_success, summary
    
    def _validate_agent_list(self, agents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证智能体列表数据结构"""
        validation_result = {
            "total_agents": len(agents),
            "valid_agents": 0,
            "validation_errors": []
        }
        
        required_fields = ["id", "name", "type", "status"]
        
        for i, agent in enumerate(agents):
            agent_valid = True
            
            for field in required_fields:
                if field not in agent:
                    validation_result["validation_errors"].append(
                        f"Agent {i}: Missing required field '{field}'"
                    )
                    agent_valid = False
            
            if agent_valid:
                validation_result["valid_agents"] += 1
        
        validation_result["validation_success"] = (
            validation_result["valid_agents"] == validation_result["total_agents"]
        )
        
        return validation_result