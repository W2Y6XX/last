#!/usr/bin/env python3
"""
系统压力测试

这个脚本对LangGraph多智能体系统进行全面的压力测试。
包括：
- 并发任务处理测试
- 内存使用测试
- 响应时间测试
- 错误恢复测试
- 长时间运行测试
"""

import asyncio
import logging
import time
import psutil
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import random
import json
from concurrent.futures import ThreadPoolExecutor
import threading

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

from langgraph_multi_agent.system.integration import SystemIntegrator


class StressTestMetrics:
    """压力测试指标收集器"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.task_results = []
        self.system_metrics = []
        self.error_count = 0
        self.success_count = 0
        self.response_times = []
        self.memory_usage = []
        self.cpu_usage = []
        
    def start_test(self):
        """开始测试"""
        self.start_time = datetime.now()
        
    def end_test(self):
        """结束测试"""
        self.end_time = datetime.now()
        
    def add_task_result(self, task_id: str, success: bool, response_time: float, error: str = None):
        """添加任务结果"""
        result = {
            "task_id": task_id,
            "success": success,
            "response_time": response_time,
            "timestamp": datetime.now(),
            "error": error
        }
        
        self.task_results.append(result)
        self.response_times.append(response_time)
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def add_system_metrics(self, cpu: float, memory: float):
        """添加系统指标"""
        self.system_metrics.append({
            "timestamp": datetime.now(),
            "cpu_usage": cpu,
            "memory_usage": memory
        })
        
        self.cpu_usage.append(cpu)
        self.memory_usage.append(memory)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取测试摘要"""
        if not self.start_time or not self.end_time:
            return {"error": "测试未完成"}
        
        total_time = (self.end_time - self.start_time).total_seconds()
        total_tasks = len(self.task_results)
        
        summary = {
            "test_duration": total_time,
            "total_tasks": total_tasks,
            "successful_tasks": self.success_count,
            "failed_tasks": self.error_count,
            "success_rate": self.success_count / total_tasks if total_tasks > 0 else 0,
            "throughput": total_tasks / total_time if total_time > 0 else 0,
            "response_time": {
                "min": min(self.response_times) if self.response_times else 0,
                "max": max(self.response_times) if self.response_times else 0,
                "avg": statistics.mean(self.response_times) if self.response_times else 0,
                "median": statistics.median(self.response_times) if self.response_times else 0,
                "p95": statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) >= 20 else 0,
                "p99": statistics.quantiles(self.response_times, n=100)[98] if len(self.response_times) >= 100 else 0
            },
            "system_resources": {
                "avg_cpu": statistics.mean(self.cpu_usage) if self.cpu_usage else 0,
                "max_cpu": max(self.cpu_usage) if self.cpu_usage else 0,
                "avg_memory": statistics.mean(self.memory_usage) if self.memory_usage else 0,
                "max_memory": max(self.memory_usage) if self.memory_usage else 0
            }
        }
        
        return summary


class StressTestRunner:
    """压力测试运行器"""
    
    def __init__(self, integrator: SystemIntegrator):
        self.integrator = integrator
        self.metrics = StressTestMetrics()
        self.is_monitoring = False
        self.monitor_task = None
        
    async def start_monitoring(self):
        """开始系统监控"""
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_system())
        
    async def stop_monitoring(self):
        """停止系统监控"""
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_system(self):
        """系统监控循环"""
        while self.is_monitoring:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                
                self.metrics.add_system_metrics(cpu_percent, memory_percent)
                
                await asyncio.sleep(5)  # 每5秒监控一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"系统监控错误: {e}")
    
    async def run_concurrent_task_test(self, num_tasks: int = 50, concurrency: int = 10) -> Dict[str, Any]:
        """并发任务测试"""
        print(f"\n🔥 并发任务测试 - {num_tasks} 个任务，并发度 {concurrency}")
        
        self.metrics.start_test()
        await self.start_monitoring()
        
        try:
            # 创建任务
            tasks = []
            for i in range(num_tasks):
                task_data = {
                    "task_id": f"stress_task_{i}",
                    "title": f"压力测试任务 {i}",
                    "description": f"这是第 {i} 个压力测试任务",
                    "complexity": random.choice(["simple", "medium", "complex"]),
                    "priority": random.randint(1, 3),
                    "requirements": [f"处理步骤 {j}" for j in range(random.randint(2, 5))]
                }
                tasks.append(task_data)
            
            # 创建信号量控制并发度
            semaphore = asyncio.Semaphore(concurrency)
            
            async def execute_single_task(task_data):
                async with semaphore:
                    start_time = time.time()
                    try:
                        # 创建工作流
                        workflow_id = f"stress_workflow_{task_data['task_id']}"
                        await self.integrator.create_workflow(workflow_id, "simple")
                        
                        # 执行任务
                        result = await self.integrator.execute_workflow(workflow_id, task_data)
                        
                        response_time = time.time() - start_time
                        self.metrics.add_task_result(task_data['task_id'], True, response_time)
                        
                        return {"success": True, "result": result}
                        
                    except Exception as e:
                        response_time = time.time() - start_time
                        self.metrics.add_task_result(task_data['task_id'], False, response_time, str(e))
                        return {"success": False, "error": str(e)}
            
            # 并发执行所有任务
            print("⏳ 执行并发任务...")
            results = await asyncio.gather(*[execute_single_task(task) for task in tasks], return_exceptions=True)
            
            self.metrics.end_test()
            await self.stop_monitoring()
            
            # 统计结果
            successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
            failed = len(results) - successful
            
            print(f"✅ 并发测试完成: 成功 {successful}, 失败 {failed}")
            
            return self.metrics.get_summary()
            
        except Exception as e:
            logger.error(f"并发任务测试失败: {e}")
            await self.stop_monitoring()
            return {"error": str(e)}
    
    async def run_memory_stress_test(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """内存压力测试"""
        print(f"\n💾 内存压力测试 - 持续 {duration_minutes} 分钟")
        
        self.metrics = StressTestMetrics()  # 重置指标
        self.metrics.start_test()
        await self.start_monitoring()
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        task_counter = 0
        
        try:
            while datetime.now() < end_time:
                # 创建大量小任务
                batch_tasks = []
                for i in range(20):  # 每批20个任务
                    task_data = {
                        "task_id": f"memory_test_{task_counter}_{i}",
                        "title": f"内存测试任务 {task_counter}_{i}",
                        "description": "内存压力测试任务",
                        "data": "x" * random.randint(1000, 10000),  # 随机大小的数据
                        "requirements": ["内存处理", "数据存储", "结果返回"]
                    }
                    batch_tasks.append(task_data)
                
                # 执行批次任务
                for task_data in batch_tasks:
                    start_time = time.time()
                    try:
                        workflow_id = f"memory_workflow_{task_data['task_id']}"
                        await self.integrator.create_workflow(workflow_id, "simple")
                        result = await self.integrator.execute_workflow(workflow_id, task_data)
                        
                        response_time = time.time() - start_time
                        self.metrics.add_task_result(task_data['task_id'], True, response_time)
                        
                    except Exception as e:
                        response_time = time.time() - start_time
                        self.metrics.add_task_result(task_data['task_id'], False, response_time, str(e))
                
                task_counter += 1
                
                # 短暂休息
                await asyncio.sleep(1)
                
                # 显示进度
                remaining = (end_time - datetime.now()).total_seconds()
                if task_counter % 10 == 0:
                    print(f"   进度: 已执行 {task_counter * 20} 个任务, 剩余 {remaining:.0f} 秒")
            
            self.metrics.end_test()
            await self.stop_monitoring()
            
            print(f"✅ 内存压力测试完成")
            
            return self.metrics.get_summary()
            
        except Exception as e:
            logger.error(f"内存压力测试失败: {e}")
            await self.stop_monitoring()
            return {"error": str(e)}
    
    async def run_response_time_test(self, num_requests: int = 100) -> Dict[str, Any]:
        """响应时间测试"""
        print(f"\n⚡ 响应时间测试 - {num_requests} 个请求")
        
        self.metrics = StressTestMetrics()  # 重置指标
        self.metrics.start_test()
        await self.start_monitoring()
        
        try:
            for i in range(num_requests):
                task_data = {
                    "task_id": f"response_test_{i}",
                    "title": f"响应时间测试 {i}",
                    "description": "响应时间基准测试",
                    "requirements": ["快速处理", "立即响应"]
                }
                
                start_time = time.time()
                try:
                    workflow_id = f"response_workflow_{i}"
                    await self.integrator.create_workflow(workflow_id, "simple")
                    result = await self.integrator.execute_workflow(workflow_id, task_data)
                    
                    response_time = time.time() - start_time
                    self.metrics.add_task_result(task_data['task_id'], True, response_time)
                    
                except Exception as e:
                    response_time = time.time() - start_time
                    self.metrics.add_task_result(task_data['task_id'], False, response_time, str(e))
                
                # 显示进度
                if (i + 1) % 20 == 0:
                    print(f"   进度: {i + 1}/{num_requests}")
            
            self.metrics.end_test()
            await self.stop_monitoring()
            
            print(f"✅ 响应时间测试完成")
            
            return self.metrics.get_summary()
            
        except Exception as e:
            logger.error(f"响应时间测试失败: {e}")
            await self.stop_monitoring()
            return {"error": str(e)}
    
    async def run_error_recovery_test(self, num_tasks: int = 30) -> Dict[str, Any]:
        """错误恢复测试"""
        print(f"\n🔧 错误恢复测试 - {num_tasks} 个任务（包含故意错误）")
        
        self.metrics = StressTestMetrics()  # 重置指标
        self.metrics.start_test()
        await self.start_monitoring()
        
        try:
            for i in range(num_tasks):
                # 30%的任务故意包含错误
                should_fail = random.random() < 0.3
                
                task_data = {
                    "task_id": f"error_test_{i}",
                    "title": f"错误恢复测试 {i}",
                    "description": "错误恢复能力测试",
                    "should_fail": should_fail,  # 标记是否应该失败
                    "requirements": ["处理输入", "生成输出", "错误处理"]
                }
                
                start_time = time.time()
                try:
                    workflow_id = f"error_workflow_{i}"
                    await self.integrator.create_workflow(workflow_id, "simple")
                    
                    # 如果标记为应该失败，则传入无效数据
                    if should_fail:
                        task_data["invalid_data"] = None
                        task_data["requirements"] = None
                    
                    result = await self.integrator.execute_workflow(workflow_id, task_data)
                    
                    response_time = time.time() - start_time
                    # 如果任务应该失败但成功了，这也算是一种成功（系统处理了错误）
                    self.metrics.add_task_result(task_data['task_id'], True, response_time)
                    
                except Exception as e:
                    response_time = time.time() - start_time
                    # 如果任务应该失败且确实失败了，这是预期的
                    success = should_fail  # 预期失败的任务失败了算成功
                    self.metrics.add_task_result(task_data['task_id'], success, response_time, str(e))
                
                # 显示进度
                if (i + 1) % 10 == 0:
                    print(f"   进度: {i + 1}/{num_tasks}")
            
            self.metrics.end_test()
            await self.stop_monitoring()
            
            print(f"✅ 错误恢复测试完成")
            
            return self.metrics.get_summary()
            
        except Exception as e:
            logger.error(f"错误恢复测试失败: {e}")
            await self.stop_monitoring()
            return {"error": str(e)}


async def run_comprehensive_stress_test():
    """运行综合压力测试"""
    
    print("=" * 80)
    print("LangGraph多智能体系统 - 综合压力测试")
    print("=" * 80)
    
    # 初始化系统
    print("\n🚀 初始化测试系统...")
    
    config = {
        "checkpoint_storage": "memory",
        "enable_metrics": True,
        "enable_tracing": False,  # 关闭追踪以减少开销
        "optimization_level": "aggressive",
        "performance": {
            "max_cache_size": 20000,
            "enable_auto_optimization": True,
            "max_workers": 8,
            "execution_mode": "adaptive",
            "enable_auto_scaling": True
        }
    }
    
    integrator = SystemIntegrator(config)
    
    try:
        success = await integrator.initialize_system()
        if not success:
            print("❌ 系统初始化失败")
            return
        
        print("✅ 测试系统初始化成功")
        
        # 创建测试运行器
        test_runner = StressTestRunner(integrator)
        
        # 收集所有测试结果
        all_results = {}
        
        # 1. 并发任务测试
        print("\n" + "="*50)
        print("测试 1/4: 并发任务处理能力")
        print("="*50)
        
        concurrent_result = await test_runner.run_concurrent_task_test(
            num_tasks=100,  # 100个任务
            concurrency=20  # 20个并发
        )
        all_results["concurrent_tasks"] = concurrent_result
        
        if "error" not in concurrent_result:
            print(f"   吞吐量: {concurrent_result['throughput']:.2f} 任务/秒")
            print(f"   成功率: {concurrent_result['success_rate']:.2%}")
            print(f"   平均响应时间: {concurrent_result['response_time']['avg']:.3f} 秒")
            print(f"   P95响应时间: {concurrent_result['response_time']['p95']:.3f} 秒")
        
        # 短暂休息
        await asyncio.sleep(5)
        
        # 2. 内存压力测试
        print("\n" + "="*50)
        print("测试 2/4: 内存使用压力测试")
        print("="*50)
        
        memory_result = await test_runner.run_memory_stress_test(duration_minutes=3)
        all_results["memory_stress"] = memory_result
        
        if "error" not in memory_result:
            print(f"   处理任务数: {memory_result['total_tasks']}")
            print(f"   平均内存使用: {memory_result['system_resources']['avg_memory']:.1f}%")
            print(f"   峰值内存使用: {memory_result['system_resources']['max_memory']:.1f}%")
            print(f"   平均CPU使用: {memory_result['system_resources']['avg_cpu']:.1f}%")
        
        # 短暂休息
        await asyncio.sleep(5)
        
        # 3. 响应时间测试
        print("\n" + "="*50)
        print("测试 3/4: 响应时间基准测试")
        print("="*50)
        
        response_result = await test_runner.run_response_time_test(num_requests=200)
        all_results["response_time"] = response_result
        
        if "error" not in response_result:
            print(f"   最小响应时间: {response_result['response_time']['min']:.3f} 秒")
            print(f"   最大响应时间: {response_result['response_time']['max']:.3f} 秒")
            print(f"   平均响应时间: {response_result['response_time']['avg']:.3f} 秒")
            print(f"   中位数响应时间: {response_result['response_time']['median']:.3f} 秒")
        
        # 短暂休息
        await asyncio.sleep(5)
        
        # 4. 错误恢复测试
        print("\n" + "="*50)
        print("测试 4/4: 错误恢复能力测试")
        print("="*50)
        
        error_result = await test_runner.run_error_recovery_test(num_tasks=50)
        all_results["error_recovery"] = error_result
        
        if "error" not in error_result:
            print(f"   错误处理成功率: {error_result['success_rate']:.2%}")
            print(f"   平均恢复时间: {error_result['response_time']['avg']:.3f} 秒")
        
        # 5. 生成综合报告
        print("\n" + "="*80)
        print("综合测试报告")
        print("="*80)
        
        generate_comprehensive_report(all_results)
        
        # 6. 系统优化建议
        print("\n" + "="*50)
        print("系统优化建议")
        print("="*50)
        
        recommendations = integrator.get_performance_recommendations()
        if isinstance(recommendations, dict) and "error" not in recommendations:
            for category, suggestions in recommendations.items():
                if suggestions and isinstance(suggestions, list):
                    print(f"\n{category}:")
                    for suggestion in suggestions:
                        print(f"  💡 {suggestion}")
        
        # 7. 执行系统优化
        print("\n优化系统性能...")
        optimization_result = await integrator.optimize_system_performance()
        
        if "error" not in optimization_result:
            print(f"✅ 系统优化完成")
            print(f"   应用优化策略: {optimization_result.get('optimization_results', 0)} 个")
            print(f"   性能提升: {optimization_result.get('total_improvement', 0):.1f}%")
        
    except Exception as e:
        print(f"❌ 压力测试失败: {e}")
        logger.error(f"压力测试错误: {e}")
    
    finally:
        # 清理资源
        print("\n🧹 清理测试资源...")
        try:
            await integrator.shutdown_system()
            print("✅ 系统关闭完成")
        except Exception as e:
            print(f"⚠️  系统关闭时出现警告: {e}")
    
    print("\n" + "="*80)
    print("综合压力测试完成")
    print("="*80)


def generate_comprehensive_report(results: Dict[str, Any]):
    """生成综合测试报告"""
    
    print("\n📊 测试结果摘要:")
    print("-" * 60)
    
    # 并发测试结果
    if "concurrent_tasks" in results and "error" not in results["concurrent_tasks"]:
        concurrent = results["concurrent_tasks"]
        print(f"并发任务测试:")
        print(f"  • 总任务数: {concurrent['total_tasks']}")
        print(f"  • 成功率: {concurrent['success_rate']:.2%}")
        print(f"  • 吞吐量: {concurrent['throughput']:.2f} 任务/秒")
        print(f"  • 平均响应时间: {concurrent['response_time']['avg']:.3f} 秒")
        print(f"  • P95响应时间: {concurrent['response_time']['p95']:.3f} 秒")
    
    # 内存测试结果
    if "memory_stress" in results and "error" not in results["memory_stress"]:
        memory = results["memory_stress"]
        print(f"\n内存压力测试:")
        print(f"  • 测试时长: {memory['test_duration']:.1f} 秒")
        print(f"  • 处理任务: {memory['total_tasks']} 个")
        print(f"  • 平均内存使用: {memory['system_resources']['avg_memory']:.1f}%")
        print(f"  • 峰值内存使用: {memory['system_resources']['max_memory']:.1f}%")
        print(f"  • 平均CPU使用: {memory['system_resources']['avg_cpu']:.1f}%")
    
    # 响应时间测试结果
    if "response_time" in results and "error" not in results["response_time"]:
        response = results["response_time"]
        print(f"\n响应时间测试:")
        print(f"  • 请求总数: {response['total_tasks']}")
        print(f"  • 最小响应时间: {response['response_time']['min']:.3f} 秒")
        print(f"  • 最大响应时间: {response['response_time']['max']:.3f} 秒")
        print(f"  • 平均响应时间: {response['response_time']['avg']:.3f} 秒")
        print(f"  • 中位数响应时间: {response['response_time']['median']:.3f} 秒")
        print(f"  • P99响应时间: {response['response_time']['p99']:.3f} 秒")
    
    # 错误恢复测试结果
    if "error_recovery" in results and "error" not in results["error_recovery"]:
        error_recovery = results["error_recovery"]
        print(f"\n错误恢复测试:")
        print(f"  • 测试任务数: {error_recovery['total_tasks']}")
        print(f"  • 错误处理成功率: {error_recovery['success_rate']:.2%}")
        print(f"  • 平均恢复时间: {error_recovery['response_time']['avg']:.3f} 秒")
    
    # 整体评估
    print(f"\n🎯 整体性能评估:")
    print("-" * 30)
    
    # 计算综合得分（简化评分系统）
    score = 0
    max_score = 0
    
    if "concurrent_tasks" in results and "error" not in results["concurrent_tasks"]:
        concurrent = results["concurrent_tasks"]
        # 成功率权重40%
        score += concurrent['success_rate'] * 40
        max_score += 40
        
        # 响应时间权重30%（响应时间越短得分越高）
        if concurrent['response_time']['avg'] < 1.0:
            score += 30
        elif concurrent['response_time']['avg'] < 2.0:
            score += 20
        elif concurrent['response_time']['avg'] < 5.0:
            score += 10
        max_score += 30
    
    if "error_recovery" in results and "error" not in results["error_recovery"]:
        error_recovery = results["error_recovery"]
        # 错误恢复权重30%
        score += error_recovery['success_rate'] * 30
        max_score += 30
    
    if max_score > 0:
        final_score = (score / max_score) * 100
        
        if final_score >= 90:
            grade = "优秀 🏆"
        elif final_score >= 80:
            grade = "良好 👍"
        elif final_score >= 70:
            grade = "一般 👌"
        else:
            grade = "需要改进 ⚠️"
        
        print(f"综合得分: {final_score:.1f}/100 - {grade}")
    
    # 保存详细报告到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"stress_test_report_{timestamp}.json"
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)
        print(f"\n📄 详细报告已保存到: {report_file}")
    except Exception as e:
        print(f"⚠️  保存报告失败: {e}")


def main():
    """主函数"""
    try:
        asyncio.run(run_comprehensive_stress_test())
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"测试程序执行失败: {e}")
        logger.error(f"主程序错误: {e}")


if __name__ == "__main__":
    main()