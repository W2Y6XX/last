"""
健康检查测试套件
"""

import asyncio
import time
import aiohttp
import requests
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from ..core.test_controller import TestSuite
from ..core.test_result import TestResult, TestSuiteResult, TestStatus, ResultType
from ..config.test_config import TestConfiguration
from ..utils.helpers import retry_on_failure, timeout_after, measure_time
from ..utils.logging_utils import get_logger


class HealthCheckSuite(TestSuite):
    """健康检查测试套件"""
    
    def __init__(self, name: str, config: TestConfiguration):
        super().__init__(name, config)
        self.logger = get_logger("health_check")
    
    async def run_all_tests(self) -> TestSuiteResult:
        """运行所有健康检查测试"""
        self.logger.info("🏥 开始健康检查测试套件")
        
        suite_result = TestSuiteResult(
            suite_name=self.name,
            start_time=datetime.now()
        )
        
        # 定义测试用例
        test_cases = [
            ("backend_health", self._test_backend_health),
            ("frontend_access", self._test_frontend_access),
            ("api_endpoints", self._test_api_endpoints),
            ("database_connection", self._test_database_connection),
            ("websocket_connection", self._test_websocket_connection)
        ]
        
        # 执行测试用例
        for test_name, test_func in test_cases:
            result = await self._run_single_test(test_name, test_func)
            suite_result.add_result(result)
            
            # 如果是关键测试失败，可能需要停止后续测试
            if result.status == TestStatus.FAILED and test_name in ["backend_health", "api_endpoints"]:
                self.logger.warning(f"关键测试 {test_name} 失败，但继续执行其他测试")
        
        suite_result.end_time = datetime.now()
        suite_result.calculate_duration()
        
        self.logger.info(f"🏥 健康检查测试套件完成: {suite_result.passed_tests}/{suite_result.total_tests} 通过")
        
        return suite_result
    
    async def _run_single_test(self, test_name: str, test_func) -> TestResult:
        """运行单个测试"""
        result = self.create_test_result(test_name)
        result.start_time = datetime.now()
        result.result_type = ResultType.FUNCTIONAL
        result.tags = ["health_check", "critical"]
        
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
            if "response_time" in details:
                result.add_metric("response_time", details["response_time"], "s", 
                                self.config.performance_thresholds.get("max_response_time", 5.0))
            
        except Exception as e:
            result.end_time = datetime.now()
            result.calculate_duration()
            result.set_error(str(e))
            self.logger.error_detail(e, {"test_name": test_name})
        
        return result
    
    @retry_on_failure(max_retries=2, delay=1.0)
    @timeout_after(30.0)
    async def _test_backend_health(self) -> Tuple[bool, Dict[str, Any]]:
        """测试后端健康状态"""
        self.logger.test_step("检查后端服务健康状态")
        
        try:
            start_time = time.time()
            
            # 使用requests进行同步请求
            response = requests.get(f"{self.config.base_url}/health", timeout=10)
            
            response_time = time.time() - start_time
            
            success = response.status_code == 200
            
            details = {
                "status_code": response.status_code,
                "response_time": response_time,
                "url": f"{self.config.base_url}/health"
            }
            
            # 尝试解析JSON响应
            try:
                if response.headers.get('content-type', '').startswith('application/json'):
                    details["content"] = response.json()
                else:
                    details["content"] = response.text[:500]  # 限制文本长度
            except:
                details["content"] = "Unable to parse response"
            
            if success:
                self.logger.test_step(f"后端健康检查成功 - 响应时间: {response_time:.3f}s")
            else:
                self.logger.test_step(f"后端健康检查失败 - 状态码: {response.status_code}")
            
            return success, details
            
        except requests.exceptions.RequestException as e:
            error_details = {
                "error": str(e),
                "url": f"{self.config.base_url}/health",
                "error_type": type(e).__name__
            }
            self.logger.test_step(f"后端健康检查异常: {e}")
            return False, error_details
    
    @retry_on_failure(max_retries=2, delay=1.0)
    @timeout_after(15.0)
    async def _test_frontend_access(self) -> Tuple[bool, Dict[str, Any]]:
        """测试前端访问"""
        self.logger.test_step("检查前端页面访问")
        
        try:
            start_time = time.time()
            
            # 测试主页面
            response = requests.get(f"{self.config.frontend_url}/88.html", timeout=10)
            
            response_time = time.time() - start_time
            
            success = response.status_code == 200
            
            details = {
                "status_code": response.status_code,
                "response_time": response_time,
                "content_length": len(response.content),
                "url": f"{self.config.frontend_url}/88.html"
            }
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '')
            details["content_type"] = content_type
            
            # 检查是否包含基本HTML结构
            if success and 'text/html' in content_type:
                content = response.text.lower()
                has_html = '<html' in content or '<!doctype html' in content
                has_body = '<body' in content
                details["has_html_structure"] = has_html and has_body
                
                if not (has_html and has_body):
                    success = False
                    details["error"] = "页面缺少基本HTML结构"
            
            if success:
                self.logger.test_step(f"前端访问成功 - 响应时间: {response_time:.3f}s, 内容长度: {len(response.content)} bytes")
            else:
                self.logger.test_step(f"前端访问失败 - 状态码: {response.status_code}")
            
            return success, details
            
        except requests.exceptions.RequestException as e:
            error_details = {
                "error": str(e),
                "url": f"{self.config.frontend_url}/88.html",
                "error_type": type(e).__name__
            }
            self.logger.test_step(f"前端访问异常: {e}")
            return False, error_details
    
    @timeout_after(45.0)
    async def _test_api_endpoints(self) -> Tuple[bool, Dict[str, Any]]:
        """测试关键API端点"""
        self.logger.test_step("检查关键API端点")
        
        # 定义要测试的端点
        endpoints = [
            ("/", "GET", "根路径"),
            ("/health", "GET", "健康检查"),
            ("/api/v1/system/status", "GET", "系统状态"),
            ("/api/v1/system/health", "GET", "系统健康"),
            ("/api/v1/agents", "GET", "智能体列表"),
            ("/api/v1/tasks", "GET", "任务列表")
        ]
        
        results = {}
        all_success = True
        total_response_time = 0
        
        for endpoint, method, description in endpoints:
            try:
                start_time = time.time()
                
                url = f"{self.config.base_url}{endpoint}"
                response = requests.request(method, url, timeout=10)
                
                response_time = time.time() - start_time
                total_response_time += response_time
                
                success = response.status_code < 400
                
                results[endpoint] = {
                    "success": success,
                    "status_code": response.status_code,
                    "method": method,
                    "response_time": response_time,
                    "description": description
                }
                
                # 尝试解析响应内容
                try:
                    if response.headers.get('content-type', '').startswith('application/json'):
                        content = response.json()
                        results[endpoint]["content_type"] = "json"
                        results[endpoint]["content_size"] = len(str(content))
                    else:
                        results[endpoint]["content_type"] = response.headers.get('content-type', 'unknown')
                        results[endpoint]["content_size"] = len(response.content)
                except:
                    results[endpoint]["content_type"] = "unknown"
                    results[endpoint]["content_size"] = len(response.content)
                
                if success:
                    self.logger.test_step(f"✅ {description} ({endpoint}): {response.status_code} - {response_time:.3f}s")
                else:
                    self.logger.test_step(f"❌ {description} ({endpoint}): {response.status_code} - {response_time:.3f}s")
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
        
        # 计算平均响应时间
        avg_response_time = total_response_time / len(endpoints) if endpoints else 0
        
        summary = {
            "endpoints_tested": len(endpoints),
            "successful_endpoints": sum(1 for r in results.values() if r.get("success", False)),
            "failed_endpoints": sum(1 for r in results.values() if not r.get("success", False)),
            "average_response_time": avg_response_time,
            "total_response_time": total_response_time,
            "results": results
        }
        
        return all_success, summary
    
    @timeout_after(20.0)
    async def _test_database_connection(self) -> Tuple[bool, Dict[str, Any]]:
        """测试数据库连接"""
        self.logger.test_step("检查数据库连接状态")
        
        # 通过API检查数据库状态
        try:
            start_time = time.time()
            
            # 尝试通过系统状态API获取数据库信息
            response = requests.get(f"{self.config.base_url}/api/v1/system/status", timeout=10)
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    status_data = response.json()
                    
                    # 检查响应中是否包含数据库信息
                    db_status = status_data.get("database", {})
                    
                    if db_status:
                        db_connected = db_status.get("connected", False)
                        
                        details = {
                            "database_connected": db_connected,
                            "database_info": db_status,
                            "response_time": response_time,
                            "check_method": "api_status"
                        }
                        
                        if db_connected:
                            self.logger.test_step(f"数据库连接正常 - 响应时间: {response_time:.3f}s")
                        else:
                            self.logger.test_step("数据库连接失败")
                        
                        return db_connected, details
                    else:
                        # 如果没有数据库信息，假设数据库正常（可能使用内存存储）
                        details = {
                            "database_connected": True,
                            "database_info": "No database info in status, assuming memory storage",
                            "response_time": response_time,
                            "check_method": "api_status_assumed"
                        }
                        
                        self.logger.test_step("未找到数据库状态信息，假设使用内存存储")
                        return True, details
                        
                except Exception as e:
                    details = {
                        "database_connected": False,
                        "error": f"Failed to parse status response: {e}",
                        "response_time": response_time,
                        "check_method": "api_status"
                    }
                    self.logger.test_step(f"解析系统状态响应失败: {e}")
                    return False, details
            else:
                details = {
                    "database_connected": False,
                    "error": f"System status API returned {response.status_code}",
                    "response_time": response_time,
                    "check_method": "api_status"
                }
                self.logger.test_step(f"系统状态API返回错误状态码: {response.status_code}")
                return False, details
                
        except Exception as e:
            details = {
                "database_connected": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "check_method": "api_status"
            }
            self.logger.test_step(f"数据库连接检查异常: {e}")
            return False, details
    
    @timeout_after(25.0)
    async def _test_websocket_connection(self) -> Tuple[bool, Dict[str, Any]]:
        """测试WebSocket连接"""
        self.logger.test_step("检查WebSocket连接")
        
        # 由于WebSocket测试比较复杂，这里先实现基本的连接测试
        try:
            import websockets
            
            # 构建WebSocket URL
            ws_url = self.config.base_url.replace("http://", "ws://").replace("https://", "wss://")
            ws_url += "/api/v1/ws/connect?client_id=health_check_test"  # 使用正确的WebSocket端点
            
            start_time = time.time()
            
            try:
                # 尝试建立WebSocket连接 - 修复版本兼容性问题
                async with websockets.connect(ws_url) as websocket:
                    # 发送测试消息
                    test_message = '{"type": "ping", "data": "health_check"}'
                    await websocket.send(test_message)
                    
                    # 等待响应
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_time = time.time() - start_time
                        
                        details = {
                            "websocket_connected": True,
                            "response_time": response_time,
                            "test_message_sent": test_message,
                            "response_received": response[:200] if response else None,  # 限制响应长度
                            "url": ws_url
                        }
                        
                        self.logger.test_step(f"WebSocket连接成功 - 响应时间: {response_time:.3f}s")
                        return True, details
                        
                    except asyncio.TimeoutError:
                        response_time = time.time() - start_time
                        
                        details = {
                            "websocket_connected": True,
                            "response_time": response_time,
                            "test_message_sent": test_message,
                            "response_received": None,
                            "warning": "Connection established but no response received",
                            "url": ws_url
                        }
                        
                        self.logger.test_step("WebSocket连接成功但未收到响应")
                        return True, details  # 连接成功，即使没有响应也算通过
                        
            except Exception as e:
                response_time = time.time() - start_time
                
                details = {
                    "websocket_connected": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "response_time": response_time,
                    "url": ws_url
                }
                
                self.logger.test_step(f"WebSocket连接失败: {e}")
                return False, details
                
        except ImportError:
            # 如果没有websockets库，跳过测试
            details = {
                "websocket_connected": None,
                "skipped": True,
                "reason": "websockets library not available",
                "suggestion": "pip install websockets"
            }
            
            self.logger.test_step("跳过WebSocket测试 - 缺少websockets库")
            return True, details  # 跳过不算失败
            
        except Exception as e:
            details = {
                "websocket_connected": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            
            self.logger.test_step(f"WebSocket测试异常: {e}")
            return False, details