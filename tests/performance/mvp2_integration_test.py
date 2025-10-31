#!/usr/bin/env python3
"""
MVP2前端集成稳定性测试

这个脚本专门测试与MVP2前端的集成稳定性，包括：
- API接口稳定性测试
- WebSocket连接稳定性测试
- 前端数据格式兼容性测试
- 高并发前端请求测试
- 长时间连接稳定性测试
"""

import asyncio
import logging
import time
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import aiohttp
import websockets
from concurrent.futures import ThreadPoolExecutor
import threading
import random

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入系统组件
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langgraph_multi_agent.api.app import create_app
from langgraph_multi_agent.api.models import TaskCreateRequest, TaskType, Priority, ExecutionMode
from langgraph_multi_agent.system.integration import SystemIntegrator


class MVP2IntegrationTestMetrics:
    """MVP2集成测试指标收集器"""
    
    def __init__(self):
        self.api_response_times = []
        self.websocket_message_times = []
        self.connection_durations = []
        self.error_count = 0
        self.success_count = 0
        self.websocket_errors = 0
        self.websocket_messages = 0
        self.data_format_errors = 0
        self.concurrent_request_results = []
        
    def add_api_response(self, response_time: float, success: bool):
        """添加API响应结果"""
        self.api_response_times.append(response_time)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def add_websocket_message(self, message_time: float, success: bool):
        """添加WebSocket消息结果"""
        self.websocket_message_times.append(message_time)
        if success:
            self.websocket_messages += 1
        else:
            self.websocket_errors += 1
    
    def add_connection_duration(self, duration: float):
        """添加连接持续时间"""
        self.connection_durations.append(duration)
    
    def add_data_format_error(self):
        """添加数据格式错误"""
        self.data_format_errors += 1
    
    def add_concurrent_result(self, result: Dict[str, Any]):
        """添加并发测试结果"""
        self.concurrent_request_results.append(result)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取测试摘要"""
        total_requests = len(self.api_response_times)
        total_ws_messages = len(self.websocket_message_times)
        
        return {
            "api_performance": {
                "total_requests": total_requests,
                "successful_requests": self.success_count,
                "failed_requests": self.error_count,
                "success_rate": self.success_count / total_requests if total_requests > 0 else 0,
                "avg_response_time": statistics.mean(self.api_response_times) if self.api_response_times else 0,
                "min_response_time": min(self.api_response_times) if self.api_response_times else 0,
                "max_response_time": max(self.api_response_times) if self.api_response_times else 0,
                "p95_response_time": statistics.quantiles(self.api_response_times, n=20)[18] if len(self.api_response_times) >= 20 else 0,
                "p99_response_time": statistics.quantiles(self.api_response_times, n=100)[98] if len(self.api_response_times) >= 100 else 0
            },
            "websocket_performance": {
                "total_messages": total_ws_messages,
                "successful_messages": self.websocket_messages,
                "failed_messages": self.websocket_errors,
                "message_success_rate": self.websocket_messages / total_ws_messages if total_ws_messages > 0 else 0,
                "avg_message_time": statistics.mean(self.websocket_message_times) if self.websocket_message_times else 0
            },
            "connection_stability": {
                "total_connections": len(self.connection_durations),
                "avg_connection_duration": statistics.mean(self.connection_durations) if self.connection_durations else 0,
                "min_connection_duration": min(self.connection_durations) if self.connection_durations else 0,
                "max_connection_duration": max(self.connection_durations) if self.connection_durations else 0
            },
            "data_integrity": {
                "format_errors": self.data_format_errors,
                "format_error_rate": self.data_format_errors / total_requests if total_requests > 0 else 0
            },
            "concurrent_performance": {
                "concurrent_tests": len(self.concurrent_request_results),
                "concurrent_results": self.concurrent_request_results
            }
        }


class MVP2IntegrationTester:
    """MVP2集成测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8000", ws_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.ws_url = ws_url
        self.metrics = MVP2IntegrationTestMetrics()
        self.session = None
        
    async def initialize(self):
        """初始化测试器"""
        self.session = aiohttp.ClientSession()
        logger.info("MVP2集成测试器初始化完成")
    
    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()
        logger.info("MVP2集成测试器清理完成")
    
    async def test_api_stability(self, num_requests: int = 100) -> Dict[str, Any]:
        """测试API接口稳定性"""
        logger.info(f"开始API稳定性测试 - {num_requests} 个请求")
        
        # 测试不同的API端点
        endpoints = [
            {"method": "GET", "path": "/health"},
            {"method": "GET", "path": "/version"},
            {"method": "GET", "path": "/api/v1/tasks"},
            {"method": "GET", "path": "/api/v1/system/status"},
            {"method": "POST", "path": "/api/v1/tasks", "data": self._create_sample_task_data()}
        ]
        
        for i in range(num_requests):
            endpoint = random.choice(endpoints)
            
            start_time = time.time()
            success = False
            
            try:
                if endpoint["method"] == "GET":
                    async with self.session.get(f"{self.base_url}{endpoint['path']}") as response:
                        success = response.status < 400
                        data = await response.json()
                        
                        # 验证数据格式
                        if not self._validate_response_format(data):
                            self.metrics.add_data_format_error()
                
                elif endpoint["method"] == "POST":
                    async with self.session.post(
                        f"{self.base_url}{endpoint['path']}", 
                        json=endpoint.get("data", {})
                    ) as response:
                        success = response.status < 400
                        data = await response.json()
                        
                        # 验证数据格式
                        if not self._validate_response_format(data):
                            self.metrics.add_data_format_error()
                
                response_time = time.time() - start_time
                self.metrics.add_api_response(response_time, success)
                
            except Exception as e:
                response_time = time.time() - start_time
                self.metrics.add_api_response(response_time, False)
                logger.error(f"API请求失败: {e}")
            
            # 显示进度
            if (i + 1) % 20 == 0:
                logger.info(f"API测试进度: {i + 1}/{num_requests}")
            
            # 短暂休息
            await asyncio.sleep(0.1)
        
        logger.info("API稳定性测试完成")
        return self.metrics.get_summary()["api_performance"]
    
    def _create_sample_task_data(self) -> Dict[str, Any]:
        """创建示例任务数据"""
        return {
            "title": f"测试任务 {random.randint(1000, 9999)}",
            "description": "MVP2集成测试任务",
            "task_type": random.choice(["analysis", "processing", "reporting"]),
            "priority": random.randint(1, 4),
            "requirements": ["处理数据", "生成报告"],
            "execution_mode": random.choice(["sequential", "parallel", "adaptive"]),
            "timeout_seconds": 300
        }
    
    def _validate_response_format(self, data: Dict[str, Any]) -> bool:
        """验证响应数据格式"""
        try:
            # 检查基本字段
            if not isinstance(data, dict):
                return False
            
            # 检查API响应格式
            if "success" in data:
                # 标准API响应格式
                required_fields = ["success", "message"]
                return all(field in data for field in required_fields)
            
            # 检查其他格式
            return True
            
        except Exception:
            return False
    
    async def test_websocket_stability(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """测试WebSocket连接稳定性"""
        logger.info(f"开始WebSocket稳定性测试 - 持续 {duration_minutes} 分钟")
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        connections = []
        
        try:
            # 创建多个WebSocket连接
            for i in range(5):
                client_id = f"test_client_{i}"
                connection_task = asyncio.create_task(
                    self._websocket_connection_test(client_id, end_time)
                )
                connections.append(connection_task)
            
            # 等待所有连接测试完成
            await asyncio.gather(*connections, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"WebSocket测试失败: {e}")
        
        logger.info("WebSocket稳定性测试完成")
        return self.metrics.get_summary()["websocket_performance"]
    
    async def _websocket_connection_test(self, client_id: str, end_time: datetime):
        """单个WebSocket连接测试"""
        connection_start = time.time()
        
        try:
            uri = f"{self.ws_url}/api/v1/ws/connect?client_id={client_id}"
            
            async with websockets.connect(uri) as websocket:
                logger.info(f"WebSocket连接建立: {client_id}")
                
                # 发送订阅消息
                subscribe_message = {
                    "type": "subscribe",
                    "data": {
                        "subscription_type": "system"
                    }
                }
                
                await websocket.send(json.dumps(subscribe_message))
                
                message_count = 0
                
                while datetime.now() < end_time:
                    try:
                        # 发送ping消息
                        ping_start = time.time()
                        ping_message = {
                            "type": "ping",
                            "data": {"timestamp": datetime.now().isoformat()}
                        }
                        
                        await websocket.send(json.dumps(ping_message))
                        
                        # 等待响应
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        ping_time = time.time() - ping_start
                        
                        # 验证响应
                        try:
                            response_data = json.loads(response)
                            success = response_data.get("type") == "pong"
                        except json.JSONDecodeError:
                            success = False
                        
                        self.metrics.add_websocket_message(ping_time, success)
                        message_count += 1
                        
                        # 随机发送其他消息
                        if random.random() < 0.3:
                            status_message = {
                                "type": "get_status",
                                "data": {}
                            }
                            await websocket.send(json.dumps(status_message))
                        
                        await asyncio.sleep(2)  # 每2秒发送一次
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"WebSocket响应超时: {client_id}")
                        self.metrics.add_websocket_message(5.0, False)
                    except Exception as e:
                        logger.error(f"WebSocket消息处理失败 {client_id}: {e}")
                        self.metrics.add_websocket_message(0, False)
                
                connection_duration = time.time() - connection_start
                self.metrics.add_connection_duration(connection_duration)
                
                logger.info(f"WebSocket连接测试完成: {client_id}, 消息数: {message_count}")
        
        except Exception as e:
            logger.error(f"WebSocket连接失败 {client_id}: {e}")
            connection_duration = time.time() - connection_start
            self.metrics.add_connection_duration(connection_duration)
    
    async def test_concurrent_requests(self, concurrent_users: int = 20, requests_per_user: int = 10) -> Dict[str, Any]:
        """测试并发请求处理"""
        logger.info(f"开始并发请求测试 - {concurrent_users} 个并发用户，每用户 {requests_per_user} 个请求")
        
        async def user_simulation(user_id: int):
            """模拟单个用户的请求"""
            user_results = {
                "user_id": user_id,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_time": 0,
                "response_times": []
            }
            
            start_time = time.time()
            
            for i in range(requests_per_user):
                request_start = time.time()
                
                try:
                    # 模拟不同类型的请求
                    if i % 3 == 0:
                        # 创建任务
                        task_data = self._create_sample_task_data()
                        async with self.session.post(f"{self.base_url}/api/v1/tasks", json=task_data) as response:
                            success = response.status < 400
                    elif i % 3 == 1:
                        # 获取任务列表
                        async with self.session.get(f"{self.base_url}/api/v1/tasks") as response:
                            success = response.status < 400
                    else:
                        # 获取系统状态
                        async with self.session.get(f"{self.base_url}/api/v1/system/status") as response:
                            success = response.status < 400
                    
                    request_time = time.time() - request_start
                    user_results["response_times"].append(request_time)
                    
                    if success:
                        user_results["successful_requests"] += 1
                    else:
                        user_results["failed_requests"] += 1
                
                except Exception as e:
                    request_time = time.time() - request_start
                    user_results["response_times"].append(request_time)
                    user_results["failed_requests"] += 1
                    logger.error(f"用户 {user_id} 请求失败: {e}")
                
                # 随机间隔
                await asyncio.sleep(random.uniform(0.1, 0.5))
            
            user_results["total_time"] = time.time() - start_time
            return user_results
        
        # 并发执行所有用户模拟
        tasks = [user_simulation(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        valid_results = [r for r in results if isinstance(r, dict)]
        
        for result in valid_results:
            self.metrics.add_concurrent_result(result)
        
        # 计算汇总统计
        total_requests = sum(r["successful_requests"] + r["failed_requests"] for r in valid_results)
        total_successful = sum(r["successful_requests"] for r in valid_results)
        all_response_times = []
        for r in valid_results:
            all_response_times.extend(r["response_times"])
        
        concurrent_summary = {
            "concurrent_users": concurrent_users,
            "requests_per_user": requests_per_user,
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "failed_requests": total_requests - total_successful,
            "success_rate": total_successful / total_requests if total_requests > 0 else 0,
            "avg_response_time": statistics.mean(all_response_times) if all_response_times else 0,
            "max_response_time": max(all_response_times) if all_response_times else 0,
            "throughput": total_requests / max(r["total_time"] for r in valid_results) if valid_results else 0
        }
        
        logger.info("并发请求测试完成")
        return concurrent_summary
    
    async def test_data_format_compatibility(self) -> Dict[str, Any]:
        """测试数据格式兼容性"""
        logger.info("开始数据格式兼容性测试")
        
        compatibility_results = {
            "task_creation_format": False,
            "task_list_format": False,
            "task_detail_format": False,
            "system_status_format": False,
            "websocket_message_format": False,
            "error_response_format": False
        }
        
        try:
            # 测试任务创建响应格式
            task_data = self._create_sample_task_data()
            async with self.session.post(f"{self.base_url}/api/v1/tasks", json=task_data) as response:
                if response.status < 400:
                    data = await response.json()
                    compatibility_results["task_creation_format"] = self._validate_task_creation_response(data)
            
            # 测试任务列表响应格式
            async with self.session.get(f"{self.base_url}/api/v1/tasks") as response:
                if response.status < 400:
                    data = await response.json()
                    compatibility_results["task_list_format"] = self._validate_task_list_response(data)
            
            # 测试系统状态响应格式
            async with self.session.get(f"{self.base_url}/api/v1/system/status") as response:
                if response.status < 400:
                    data = await response.json()
                    compatibility_results["system_status_format"] = self._validate_system_status_response(data)
            
            # 测试错误响应格式
            async with self.session.get(f"{self.base_url}/api/v1/tasks/nonexistent") as response:
                if response.status >= 400:
                    data = await response.json()
                    compatibility_results["error_response_format"] = self._validate_error_response(data)
            
        except Exception as e:
            logger.error(f"数据格式兼容性测试失败: {e}")
        
        logger.info("数据格式兼容性测试完成")
        return compatibility_results
    
    def _validate_task_creation_response(self, data: Dict[str, Any]) -> bool:
        """验证任务创建响应格式"""
        required_fields = ["success", "message", "data"]
        if not all(field in data for field in required_fields):
            return False
        
        if data["success"] and "task_id" in data["data"]:
            return True
        
        return False
    
    def _validate_task_list_response(self, data: Dict[str, Any]) -> bool:
        """验证任务列表响应格式"""
        if isinstance(data, dict) and "tasks" in data:
            return isinstance(data["tasks"], list)
        return False
    
    def _validate_system_status_response(self, data: Dict[str, Any]) -> bool:
        """验证系统状态响应格式"""
        if isinstance(data, dict):
            return "success" in data or "initialized" in data
        return False
    
    def _validate_error_response(self, data: Dict[str, Any]) -> bool:
        """验证错误响应格式"""
        return isinstance(data, dict) and ("error_code" in data or "detail" in data)
    
    async def test_long_running_stability(self, duration_hours: float = 0.5) -> Dict[str, Any]:
        """测试长时间运行稳定性"""
        logger.info(f"开始长时间运行稳定性测试 - 持续 {duration_hours} 小时")
        
        end_time = datetime.now() + timedelta(hours=duration_hours)
        stability_metrics = {
            "start_time": datetime.now().isoformat(),
            "planned_duration_hours": duration_hours,
            "requests_sent": 0,
            "errors_encountered": 0,
            "connection_drops": 0,
            "performance_degradation": False
        }
        
        initial_response_times = []
        
        # 收集初始性能基线
        for _ in range(10):
            start_time = time.time()
            try:
                async with self.session.get(f"{self.base_url}/health") as response:
                    if response.status < 400:
                        response_time = time.time() - start_time
                        initial_response_times.append(response_time)
            except Exception:
                pass
            await asyncio.sleep(1)
        
        baseline_response_time = statistics.mean(initial_response_times) if initial_response_times else 1.0
        
        # 长时间运行测试
        while datetime.now() < end_time:
            try:
                # 发送测试请求
                start_time = time.time()
                async with self.session.get(f"{self.base_url}/health") as response:
                    response_time = time.time() - start_time
                    
                    if response.status < 400:
                        stability_metrics["requests_sent"] += 1
                        
                        # 检查性能退化
                        if response_time > baseline_response_time * 3:
                            stability_metrics["performance_degradation"] = True
                    else:
                        stability_metrics["errors_encountered"] += 1
                
                # 随机间隔
                await asyncio.sleep(random.uniform(5, 15))
                
            except Exception as e:
                stability_metrics["errors_encountered"] += 1
                logger.error(f"长时间测试请求失败: {e}")
                await asyncio.sleep(10)
        
        stability_metrics["end_time"] = datetime.now().isoformat()
        stability_metrics["actual_duration_hours"] = (datetime.now() - datetime.fromisoformat(stability_metrics["start_time"])).total_seconds() / 3600
        stability_metrics["error_rate"] = stability_metrics["errors_encountered"] / max(stability_metrics["requests_sent"], 1)
        
        logger.info("长时间运行稳定性测试完成")
        return stability_metrics


async def run_comprehensive_mvp2_integration_test():
    """运行综合MVP2集成测试"""
    
    print("=" * 80)
    print("MVP2前端集成稳定性测试")
    print("=" * 80)
    
    # 初始化系统
    print("\n🚀 初始化测试系统...")
    
    config = {
        "checkpoint_storage": "memory",
        "enable_metrics": True,
        "enable_tracing": False,
        "cors_origins": ["*"],
        "enable_auth": False,
        "enable_rate_limit": False
    }
    
    integrator = SystemIntegrator(config)
    
    try:
        # 启动系统
        success = await integrator.initialize_system()
        if not success:
            print("❌ 系统初始化失败")
            return
        
        print("✅ 测试系统初始化成功")
        
        # 创建测试器
        tester = MVP2IntegrationTester()
        await tester.initialize()
        
        # 收集所有测试结果
        all_results = {}
        
        # 1. API稳定性测试
        print("\n" + "="*60)
        print("测试 1/5: API接口稳定性")
        print("="*60)
        
        api_result = await tester.test_api_stability(num_requests=200)
        all_results["api_stability"] = api_result
        
        print(f"   API成功率: {api_result['success_rate']:.2%}")
        print(f"   平均响应时间: {api_result['avg_response_time']:.3f} 秒")
        print(f"   P95响应时间: {api_result['p95_response_time']:.3f} 秒")
        
        # 2. WebSocket稳定性测试
        print("\n" + "="*60)
        print("测试 2/5: WebSocket连接稳定性")
        print("="*60)
        
        ws_result = await tester.test_websocket_stability(duration_minutes=3)
        all_results["websocket_stability"] = ws_result
        
        print(f"   WebSocket消息成功率: {ws_result['message_success_rate']:.2%}")
        print(f"   平均消息时间: {ws_result['avg_message_time']:.3f} 秒")
        
        # 3. 并发请求测试
        print("\n" + "="*60)
        print("测试 3/5: 并发请求处理")
        print("="*60)
        
        concurrent_result = await tester.test_concurrent_requests(concurrent_users=30, requests_per_user=15)
        all_results["concurrent_requests"] = concurrent_result
        
        print(f"   并发成功率: {concurrent_result['success_rate']:.2%}")
        print(f"   吞吐量: {concurrent_result['throughput']:.2f} 请求/秒")
        print(f"   最大响应时间: {concurrent_result['max_response_time']:.3f} 秒")
        
        # 4. 数据格式兼容性测试
        print("\n" + "="*60)
        print("测试 4/5: 数据格式兼容性")
        print("="*60)
        
        format_result = await tester.test_data_format_compatibility()
        all_results["data_format_compatibility"] = format_result
        
        compatible_formats = sum(1 for v in format_result.values() if v)
        total_formats = len(format_result)
        print(f"   格式兼容性: {compatible_formats}/{total_formats} ({compatible_formats/total_formats:.2%})")
        
        # 5. 长时间运行稳定性测试
        print("\n" + "="*60)
        print("测试 5/5: 长时间运行稳定性")
        print("="*60)
        
        stability_result = await tester.test_long_running_stability(duration_hours=0.25)  # 15分钟
        all_results["long_running_stability"] = stability_result
        
        print(f"   运行时长: {stability_result['actual_duration_hours']:.2f} 小时")
        print(f"   错误率: {stability_result['error_rate']:.2%}")
        print(f"   性能退化: {'是' if stability_result['performance_degradation'] else '否'}")
        
        # 生成综合报告
        print("\n" + "="*80)
        print("MVP2集成测试报告")
        print("="*80)
        
        generate_mvp2_integration_report(all_results)
        
        # 清理测试器
        await tester.cleanup()
        
    except Exception as e:
        print(f"❌ MVP2集成测试失败: {e}")
        logger.error(f"MVP2集成测试错误: {e}")
    
    finally:
        # 清理系统
        print("\n🧹 清理测试资源...")
        try:
            await integrator.shutdown_system()
            print("✅ 系统关闭完成")
        except Exception as e:
            print(f"⚠️  系统关闭时出现警告: {e}")
    
    print("\n" + "="*80)
    print("MVP2前端集成测试完成")
    print("="*80)


def generate_mvp2_integration_report(results: Dict[str, Any]):
    """生成MVP2集成测试报告"""
    
    print("\n📊 MVP2集成测试结果摘要:")
    print("-" * 70)
    
    # API稳定性结果
    if "api_stability" in results:
        api = results["api_stability"]
        print(f"API接口稳定性:")
        print(f"  • 总请求数: {api['total_requests']}")
        print(f"  • 成功率: {api['success_rate']:.2%}")
        print(f"  • 平均响应时间: {api['avg_response_time']:.3f} 秒")
        print(f"  • P95响应时间: {api['p95_response_time']:.3f} 秒")
        print(f"  • P99响应时间: {api['p99_response_time']:.3f} 秒")
    
    # WebSocket稳定性结果
    if "websocket_stability" in results:
        ws = results["websocket_stability"]
        print(f"\nWebSocket连接稳定性:")
        print(f"  • 总消息数: {ws['total_messages']}")
        print(f"  • 消息成功率: {ws['message_success_rate']:.2%}")
        print(f"  • 平均消息时间: {ws['avg_message_time']:.3f} 秒")
    
    # 并发请求结果
    if "concurrent_requests" in results:
        concurrent = results["concurrent_requests"]
        print(f"\n并发请求处理:")
        print(f"  • 并发用户数: {concurrent['concurrent_users']}")
        print(f"  • 总请求数: {concurrent['total_requests']}")
        print(f"  • 成功率: {concurrent['success_rate']:.2%}")
        print(f"  • 吞吐量: {concurrent['throughput']:.2f} 请求/秒")
        print(f"  • 最大响应时间: {concurrent['max_response_time']:.3f} 秒")
    
    # 数据格式兼容性结果
    if "data_format_compatibility" in results:
        format_compat = results["data_format_compatibility"]
        print(f"\n数据格式兼容性:")
        compatible_count = sum(1 for v in format_compat.values() if v)
        total_count = len(format_compat)
        print(f"  • 兼容格式: {compatible_count}/{total_count} ({compatible_count/total_count:.2%})")
        
        for format_name, is_compatible in format_compat.items():
            status = "✅" if is_compatible else "❌"
            print(f"    {status} {format_name}")
    
    # 长时间运行稳定性结果
    if "long_running_stability" in results:
        stability = results["long_running_stability"]
        print(f"\n长时间运行稳定性:")
        print(f"  • 运行时长: {stability['actual_duration_hours']:.2f} 小时")
        print(f"  • 发送请求: {stability['requests_sent']} 个")
        print(f"  • 错误率: {stability['error_rate']:.2%}")
        print(f"  • 性能退化: {'是' if stability['performance_degradation'] else '否'}")
    
    # 整体评估
    print(f"\n🎯 MVP2集成稳定性评估:")
    print("-" * 40)
    
    # 计算综合得分
    score = 0
    max_score = 0
    
    if "api_stability" in results:
        api_score = results["api_stability"]["success_rate"] * 30
        score += api_score
        max_score += 30
    
    if "websocket_stability" in results:
        ws_score = results["websocket_stability"]["message_success_rate"] * 20
        score += ws_score
        max_score += 20
    
    if "concurrent_requests" in results:
        concurrent_score = results["concurrent_requests"]["success_rate"] * 25
        score += concurrent_score
        max_score += 25
    
    if "data_format_compatibility" in results:
        format_compat = results["data_format_compatibility"]
        compat_rate = sum(1 for v in format_compat.values() if v) / len(format_compat)
        format_score = compat_rate * 15
        score += format_score
        max_score += 15
    
    if "long_running_stability" in results:
        stability = results["long_running_stability"]
        stability_score = (1 - stability["error_rate"]) * 10
        if not stability["performance_degradation"]:
            stability_score += 5
        score += stability_score
        max_score += 15
    
    if max_score > 0:
        final_score = (score / max_score) * 100
        
        if final_score >= 95:
            grade = "优秀 🏆"
            recommendation = "MVP2集成非常稳定，可以投入生产使用"
        elif final_score >= 85:
            grade = "良好 👍"
            recommendation = "MVP2集成基本稳定，建议进行小规模部署测试"
        elif final_score >= 70:
            grade = "一般 👌"
            recommendation = "MVP2集成存在一些问题，需要优化后再部署"
        else:
            grade = "需要改进 ⚠️"
            recommendation = "MVP2集成不够稳定，需要重大改进"
        
        print(f"综合得分: {final_score:.1f}/100 - {grade}")
        print(f"建议: {recommendation}")
    
    # 保存详细报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"mvp2_integration_report_{timestamp}.json"
    
    try:
        import json
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)
        print(f"\n📄 详细报告已保存到: {report_file}")
    except Exception as e:
        print(f"⚠️  保存报告失败: {e}")


def main():
    """主函数"""
    try:
        asyncio.run(run_comprehensive_mvp2_integration_test())
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"MVP2集成测试程序执行失败: {e}")
        logger.error(f"主程序错误: {e}")


if __name__ == "__main__":
    main()