#!/usr/bin/env python3
"""
综合性能和压力测试执行器

这个脚本执行任务7.4的所有测试要求：
- 进行并发任务处理的性能测试
- 执行大规模工作流的压力测试  
- 测试MVP2前端集成的稳定性

集成所有现有的测试模块并生成综合报告。
"""

import asyncio
import logging
import time
import json
import subprocess
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入系统组件
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langgraph_multi_agent.system.integration import SystemIntegrator
from langgraph_multi_agent.api.app import create_app
import uvicorn
import threading
import multiprocessing


class ComprehensivePerformanceTestRunner:
    """综合性能测试运行器"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.api_server_process = None
        self.api_server_thread = None
        
        # 测试配置
        self.test_config = {
            "api_host": "localhost",
            "api_port": 8001,  # 使用不同端口避免冲突
            "test_duration_minutes": 10,
            "concurrent_users": 50,
            "stress_test_tasks": 200,
            "mvp2_test_requests": 300
        }
        
        logger.info("综合性能测试运行器初始化完成")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有性能和压力测试"""
        
        print("=" * 100)
        print("LangGraph多智能体系统 - 综合性能和压力测试 (任务7.4)")
        print("=" * 100)
        
        self.start_time = datetime.now()
        
        try:
            # 1. 启动测试环境
            await self._setup_test_environment()
            
            # 2. 执行基准性能测试
            await self._run_benchmark_tests()
            
            # 3. 执行压力测试
            await self._run_stress_tests()
            
            # 4. 执行MVP2集成测试
            await self._run_mvp2_integration_tests()
            
            # 5. 执行大规模工作流测试
            await self._run_large_scale_workflow_tests()
            
            # 6. 执行并发任务处理测试
            await self._run_concurrent_task_tests()
            
            # 7. 生成综合报告
            self._generate_comprehensive_report()
            
        except Exception as e:
            logger.error(f"综合测试执行失败: {e}")
            self.test_results["error"] = str(e)
        
        finally:
            # 8. 清理测试环境
            await self._cleanup_test_environment()
        
        self.end_time = datetime.now()
        
        print("\n" + "=" * 100)
        print("综合性能和压力测试完成")
        print("=" * 100)
        
        return self.test_results
    
    async def _setup_test_environment(self):
        """设置测试环境"""
        print("\n🚀 设置测试环境...")
        
        try:
            # 初始化系统集成器
            config = {
                "checkpoint_storage": "memory",
                "enable_metrics": True,
                "enable_tracing": False,
                "optimization_level": "aggressive",
                "performance": {
                    "max_cache_size": 20000,
                    "enable_auto_optimization": True,
                    "max_workers": 8,
                    "execution_mode": "adaptive",
                    "enable_auto_scaling": True
                }
            }
            
            self.integrator = SystemIntegrator(config)
            success = await self.integrator.initialize_system()
            
            if not success:
                raise Exception("系统集成器初始化失败")
            
            # 启动API服务器
            await self._start_api_server()
            
            # 等待服务器启动
            await asyncio.sleep(3)
            
            print("✅ 测试环境设置完成")
            
        except Exception as e:
            logger.error(f"测试环境设置失败: {e}")
            raise
    
    async def _start_api_server(self):
        """启动API服务器"""
        try:
            def run_server():
                app = create_app()
                uvicorn.run(
                    app,
                    host=self.test_config["api_host"],
                    port=self.test_config["api_port"],
                    log_level="warning",  # 减少日志输出
                    access_log=False
                )
            
            # 在单独线程中启动服务器
            self.api_server_thread = threading.Thread(target=run_server, daemon=True)
            self.api_server_thread.start()
            
            logger.info(f"API服务器启动在 {self.test_config['api_host']}:{self.test_config['api_port']}")
            
        except Exception as e:
            logger.error(f"API服务器启动失败: {e}")
            raise
    
    async def _run_benchmark_tests(self):
        """运行基准性能测试"""
        print("\n" + "="*80)
        print("测试阶段 1/5: 基准性能测试")
        print("="*80)
        
        try:
            # 运行现有的基准测试
            result = await self._execute_test_script("benchmark.py")
            self.test_results["benchmark_tests"] = result
            
            if result.get("success"):
                print("✅ 基准性能测试完成")
                self._print_benchmark_summary(result)
            else:
                print("❌ 基准性能测试失败")
                
        except Exception as e:
            logger.error(f"基准测试失败: {e}")
            self.test_results["benchmark_tests"] = {"error": str(e)}
    
    async def _run_stress_tests(self):
        """运行压力测试"""
        print("\n" + "="*80)
        print("测试阶段 2/5: 系统压力测试")
        print("="*80)
        
        try:
            # 运行现有的压力测试
            result = await self._execute_test_script("stress_test.py")
            self.test_results["stress_tests"] = result
            
            if result.get("success"):
                print("✅ 系统压力测试完成")
                self._print_stress_summary(result)
            else:
                print("❌ 系统压力测试失败")
                
        except Exception as e:
            logger.error(f"压力测试失败: {e}")
            self.test_results["stress_tests"] = {"error": str(e)}
    
    async def _run_mvp2_integration_tests(self):
        """运行MVP2集成测试"""
        print("\n" + "="*80)
        print("测试阶段 3/5: MVP2前端集成稳定性测试")
        print("="*80)
        
        try:
            # 运行MVP2集成测试
            result = await self._execute_test_script("mvp2_integration_test.py")
            self.test_results["mvp2_integration_tests"] = result
            
            if result.get("success"):
                print("✅ MVP2集成测试完成")
                self._print_mvp2_summary(result)
            else:
                print("❌ MVP2集成测试失败")
                
        except Exception as e:
            logger.error(f"MVP2集成测试失败: {e}")
            self.test_results["mvp2_integration_tests"] = {"error": str(e)}
    
    async def _run_large_scale_workflow_tests(self):
        """运行大规模工作流测试"""
        print("\n" + "="*80)
        print("测试阶段 4/5: 大规模工作流压力测试")
        print("="*80)
        
        try:
            # 创建大规模工作流测试
            result = await self._execute_large_scale_workflow_test()
            self.test_results["large_scale_workflow_tests"] = result
            
            print("✅ 大规模工作流测试完成")
            self._print_workflow_summary(result)
                
        except Exception as e:
            logger.error(f"大规模工作流测试失败: {e}")
            self.test_results["large_scale_workflow_tests"] = {"error": str(e)}
    
    async def _run_concurrent_task_tests(self):
        """运行并发任务处理测试"""
        print("\n" + "="*80)
        print("测试阶段 5/5: 并发任务处理性能测试")
        print("="*80)
        
        try:
            # 创建并发任务测试
            result = await self._execute_concurrent_task_test()
            self.test_results["concurrent_task_tests"] = result
            
            print("✅ 并发任务处理测试完成")
            self._print_concurrent_summary(result)
                
        except Exception as e:
            logger.error(f"并发任务测试失败: {e}")
            self.test_results["concurrent_task_tests"] = {"error": str(e)}
    
    async def _execute_test_script(self, script_name: str) -> Dict[str, Any]:
        """执行测试脚本"""
        try:
            script_path = Path(__file__).parent / script_name
            
            if not script_path.exists():
                return {"success": False, "error": f"测试脚本不存在: {script_name}"}
            
            # 使用subprocess运行测试脚本
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            result = {
                "success": process.returncode == 0,
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "return_code": process.returncode
            }
            
            # 尝试解析JSON输出
            try:
                if "JSON_RESULT:" in result["stdout"]:
                    json_start = result["stdout"].find("JSON_RESULT:") + 12
                    json_data = result["stdout"][json_start:].strip()
                    result["data"] = json.loads(json_data)
            except json.JSONDecodeError:
                pass
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_large_scale_workflow_test(self) -> Dict[str, Any]:
        """执行大规模工作流测试"""
        try:
            print("   创建大规模工作流测试...")
            
            # 测试参数
            num_workflows = 100
            tasks_per_workflow = 5
            concurrent_workflows = 20
            
            start_time = time.time()
            successful_workflows = 0
            failed_workflows = 0
            workflow_times = []
            
            # 创建信号量控制并发
            semaphore = asyncio.Semaphore(concurrent_workflows)
            
            async def execute_workflow(workflow_id: int):
                async with semaphore:
                    workflow_start = time.time()
                    try:
                        # 创建工作流
                        workflow_name = f"large_scale_workflow_{workflow_id}"
                        await self.integrator.create_workflow(workflow_name, "complex")
                        
                        # 创建任务数据
                        task_data = {
                            "task_id": f"large_task_{workflow_id}",
                            "title": f"大规模测试任务 {workflow_id}",
                            "description": f"大规模工作流测试 - 工作流 {workflow_id}",
                            "requirements": [f"处理步骤 {i}" for i in range(tasks_per_workflow)]
                        }
                        
                        # 执行工作流
                        result = await self.integrator.execute_workflow(workflow_name, task_data)
                        
                        workflow_time = time.time() - workflow_start
                        workflow_times.append(workflow_time)
                        
                        return {"success": True, "time": workflow_time}
                        
                    except Exception as e:
                        workflow_time = time.time() - workflow_start
                        workflow_times.append(workflow_time)
                        logger.error(f"工作流 {workflow_id} 执行失败: {e}")
                        return {"success": False, "time": workflow_time, "error": str(e)}
            
            # 并发执行所有工作流
            print(f"   执行 {num_workflows} 个工作流，并发度 {concurrent_workflows}...")
            
            tasks = [execute_workflow(i) for i in range(num_workflows)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计结果
            for result in results:
                if isinstance(result, dict) and result.get("success"):
                    successful_workflows += 1
                else:
                    failed_workflows += 1
            
            total_time = time.time() - start_time
            
            return {
                "success": True,
                "total_workflows": num_workflows,
                "successful_workflows": successful_workflows,
                "failed_workflows": failed_workflows,
                "success_rate": successful_workflows / num_workflows,
                "total_time": total_time,
                "throughput": num_workflows / total_time,
                "avg_workflow_time": sum(workflow_times) / len(workflow_times) if workflow_times else 0,
                "min_workflow_time": min(workflow_times) if workflow_times else 0,
                "max_workflow_time": max(workflow_times) if workflow_times else 0,
                "concurrent_workflows": concurrent_workflows,
                "tasks_per_workflow": tasks_per_workflow
            }
            
        except Exception as e:
            logger.error(f"大规模工作流测试失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_concurrent_task_test(self) -> Dict[str, Any]:
        """执行并发任务处理测试"""
        try:
            print("   创建并发任务处理测试...")
            
            # 测试参数
            num_tasks = 200
            concurrent_tasks = 50
            task_types = ["simple", "analysis", "complex"]
            
            start_time = time.time()
            successful_tasks = 0
            failed_tasks = 0
            task_times = []
            
            # 创建信号量控制并发
            semaphore = asyncio.Semaphore(concurrent_tasks)
            
            async def execute_task(task_id: int):
                async with semaphore:
                    task_start = time.time()
                    try:
                        # 随机选择任务类型
                        task_type = task_types[task_id % len(task_types)]
                        
                        # 创建工作流
                        workflow_name = f"concurrent_workflow_{task_id}"
                        await self.integrator.create_workflow(workflow_name, task_type)
                        
                        # 创建任务数据
                        task_data = {
                            "task_id": f"concurrent_task_{task_id}",
                            "title": f"并发测试任务 {task_id}",
                            "description": f"并发任务处理测试 - 任务 {task_id}",
                            "task_type": task_type,
                            "priority": (task_id % 4) + 1,
                            "requirements": ["并发处理", "性能测试"]
                        }
                        
                        # 执行任务
                        result = await self.integrator.execute_workflow(workflow_name, task_data)
                        
                        task_time = time.time() - task_start
                        task_times.append(task_time)
                        
                        return {"success": True, "time": task_time, "task_type": task_type}
                        
                    except Exception as e:
                        task_time = time.time() - task_start
                        task_times.append(task_time)
                        logger.error(f"任务 {task_id} 执行失败: {e}")
                        return {"success": False, "time": task_time, "error": str(e)}
            
            # 并发执行所有任务
            print(f"   执行 {num_tasks} 个任务，并发度 {concurrent_tasks}...")
            
            tasks = [execute_task(i) for i in range(num_tasks)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计结果
            task_type_stats = {task_type: {"success": 0, "failed": 0} for task_type in task_types}
            
            for result in results:
                if isinstance(result, dict):
                    if result.get("success"):
                        successful_tasks += 1
                        task_type = result.get("task_type", "unknown")
                        if task_type in task_type_stats:
                            task_type_stats[task_type]["success"] += 1
                    else:
                        failed_tasks += 1
                        task_type = result.get("task_type", "unknown")
                        if task_type in task_type_stats:
                            task_type_stats[task_type]["failed"] += 1
                else:
                    failed_tasks += 1
            
            total_time = time.time() - start_time
            
            return {
                "success": True,
                "total_tasks": num_tasks,
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "success_rate": successful_tasks / num_tasks,
                "total_time": total_time,
                "throughput": num_tasks / total_time,
                "avg_task_time": sum(task_times) / len(task_times) if task_times else 0,
                "min_task_time": min(task_times) if task_times else 0,
                "max_task_time": max(task_times) if task_times else 0,
                "concurrent_tasks": concurrent_tasks,
                "task_type_stats": task_type_stats
            }
            
        except Exception as e:
            logger.error(f"并发任务测试失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _print_benchmark_summary(self, result: Dict[str, Any]):
        """打印基准测试摘要"""
        if "data" in result:
            data = result["data"]
            print(f"   单任务平均响应时间: {data.get('single_task', {}).get('response_time', {}).get('avg', 0):.3f} 秒")
            print(f"   批量处理最大吞吐量: {max(data.get('batch_processing', {}).values(), key=lambda x: x.get('throughput', 0) if isinstance(x, dict) else 0, default={}).get('throughput', 0):.2f} 任务/秒")
    
    def _print_stress_summary(self, result: Dict[str, Any]):
        """打印压力测试摘要"""
        if "data" in result:
            data = result["data"]
            concurrent = data.get("concurrent_tasks", {})
            print(f"   并发测试成功率: {concurrent.get('success_rate', 0):.2%}")
            print(f"   系统吞吐量: {concurrent.get('throughput', 0):.2f} 任务/秒")
    
    def _print_mvp2_summary(self, result: Dict[str, Any]):
        """打印MVP2测试摘要"""
        if "data" in result:
            data = result["data"]
            api = data.get("api_stability", {})
            print(f"   API稳定性: {api.get('success_rate', 0):.2%}")
            print(f"   WebSocket稳定性: {data.get('websocket_stability', {}).get('message_success_rate', 0):.2%}")
    
    def _print_workflow_summary(self, result: Dict[str, Any]):
        """打印工作流测试摘要"""
        print(f"   工作流成功率: {result.get('success_rate', 0):.2%}")
        print(f"   工作流吞吐量: {result.get('throughput', 0):.2f} 工作流/秒")
        print(f"   平均执行时间: {result.get('avg_workflow_time', 0):.3f} 秒")
    
    def _print_concurrent_summary(self, result: Dict[str, Any]):
        """打印并发测试摘要"""
        print(f"   任务成功率: {result.get('success_rate', 0):.2%}")
        print(f"   任务吞吐量: {result.get('throughput', 0):.2f} 任务/秒")
        print(f"   平均处理时间: {result.get('avg_task_time', 0):.3f} 秒")
    
    def _generate_comprehensive_report(self):
        """生成综合报告"""
        print("\n" + "="*100)
        print("综合性能和压力测试报告 (任务7.4)")
        print("="*100)
        
        # 测试概览
        total_duration = (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0
        
        print(f"\n📊 测试概览:")
        print(f"  • 测试开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else 'N/A'}")
        print(f"  • 测试结束时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else 'N/A'}")
        print(f"  • 总测试时长: {total_duration:.1f} 秒")
        print(f"  • 完成测试模块: {len([k for k, v in self.test_results.items() if isinstance(v, dict) and v.get('success')])}/5")
        
        # 详细结果
        print(f"\n📈 详细测试结果:")
        print("-" * 80)
        
        # 1. 基准性能测试结果
        benchmark = self.test_results.get("benchmark_tests", {})
        if benchmark.get("success"):
            print("✅ 基准性能测试: 通过")
        else:
            print("❌ 基准性能测试: 失败")
            if "error" in benchmark:
                print(f"    错误: {benchmark['error']}")
        
        # 2. 压力测试结果
        stress = self.test_results.get("stress_tests", {})
        if stress.get("success"):
            print("✅ 系统压力测试: 通过")
        else:
            print("❌ 系统压力测试: 失败")
            if "error" in stress:
                print(f"    错误: {stress['error']}")
        
        # 3. MVP2集成测试结果
        mvp2 = self.test_results.get("mvp2_integration_tests", {})
        if mvp2.get("success"):
            print("✅ MVP2前端集成测试: 通过")
        else:
            print("❌ MVP2前端集成测试: 失败")
            if "error" in mvp2:
                print(f"    错误: {mvp2['error']}")
        
        # 4. 大规模工作流测试结果
        workflow = self.test_results.get("large_scale_workflow_tests", {})
        if workflow.get("success"):
            print("✅ 大规模工作流测试: 通过")
            print(f"    成功率: {workflow.get('success_rate', 0):.2%}")
            print(f"    吞吐量: {workflow.get('throughput', 0):.2f} 工作流/秒")
        else:
            print("❌ 大规模工作流测试: 失败")
            if "error" in workflow:
                print(f"    错误: {workflow['error']}")
        
        # 5. 并发任务处理测试结果
        concurrent = self.test_results.get("concurrent_task_tests", {})
        if concurrent.get("success"):
            print("✅ 并发任务处理测试: 通过")
            print(f"    成功率: {concurrent.get('success_rate', 0):.2%}")
            print(f"    吞吐量: {concurrent.get('throughput', 0):.2f} 任务/秒")
        else:
            print("❌ 并发任务处理测试: 失败")
            if "error" in concurrent:
                print(f"    错误: {concurrent['error']}")
        
        # 综合评估
        print(f"\n🎯 任务7.4完成情况评估:")
        print("-" * 50)
        
        completed_requirements = []
        
        # 检查并发任务处理性能测试
        if concurrent.get("success"):
            completed_requirements.append("✅ 进行并发任务处理的性能测试")
        else:
            completed_requirements.append("❌ 进行并发任务处理的性能测试")
        
        # 检查大规模工作流压力测试
        if workflow.get("success") and stress.get("success"):
            completed_requirements.append("✅ 执行大规模工作流的压力测试")
        else:
            completed_requirements.append("❌ 执行大规模工作流的压力测试")
        
        # 检查MVP2前端集成稳定性测试
        if mvp2.get("success"):
            completed_requirements.append("✅ 测试MVP2前端集成的稳定性")
        else:
            completed_requirements.append("❌ 测试MVP2前端集成的稳定性")
        
        for requirement in completed_requirements:
            print(f"  {requirement}")
        
        # 计算完成度
        completed_count = sum(1 for req in completed_requirements if req.startswith("✅"))
        completion_rate = completed_count / len(completed_requirements)
        
        print(f"\n任务7.4完成度: {completed_count}/{len(completed_requirements)} ({completion_rate:.1%})")
        
        if completion_rate == 1.0:
            print("🏆 任务7.4已完全完成！")
        elif completion_rate >= 0.67:
            print("👍 任务7.4基本完成，部分测试需要优化")
        else:
            print("⚠️ 任务7.4需要进一步完善")
        
        # 保存报告
        self._save_comprehensive_report()
    
    def _save_comprehensive_report(self):
        """保存综合报告"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"comprehensive_performance_report_{timestamp}.json"
            
            report_data = {
                "test_metadata": {
                    "start_time": self.start_time.isoformat() if self.start_time else None,
                    "end_time": self.end_time.isoformat() if self.end_time else None,
                    "total_duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0,
                    "test_config": self.test_config
                },
                "test_results": self.test_results,
                "task_7_4_requirements": {
                    "concurrent_task_processing": self.test_results.get("concurrent_task_tests", {}).get("success", False),
                    "large_scale_workflow_stress": self.test_results.get("large_scale_workflow_tests", {}).get("success", False) and self.test_results.get("stress_tests", {}).get("success", False),
                    "mvp2_frontend_integration": self.test_results.get("mvp2_integration_tests", {}).get("success", False)
                }
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, default=str, ensure_ascii=False)
            
            print(f"\n📄 综合测试报告已保存到: {report_file}")
            
        except Exception as e:
            logger.error(f"保存综合报告失败: {e}")
    
    async def _cleanup_test_environment(self):
        """清理测试环境"""
        print("\n🧹 清理测试环境...")
        
        try:
            # 关闭系统集成器
            if hasattr(self, 'integrator'):
                await self.integrator.shutdown_system()
            
            # API服务器会在主线程结束时自动关闭
            
            print("✅ 测试环境清理完成")
            
        except Exception as e:
            logger.error(f"测试环境清理失败: {e}")


async def main():
    """主函数"""
    try:
        runner = ComprehensivePerformanceTestRunner()
        results = await runner.run_all_tests()
        
        # 返回结果用于验证
        return results
        
    except KeyboardInterrupt:
        print("\n用户中断测试")
        return {"interrupted": True}
    except Exception as e:
        print(f"综合性能测试执行失败: {e}")
        logger.error(f"主程序错误: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    asyncio.run(main())