#!/usr/bin/env python3
"""
性能基准测试

这个脚本对LangGraph多智能体系统进行性能基准测试。
包括：
- 单任务处理基准
- 批量任务处理基准
- 不同工作流模板性能对比
- 缓存性能测试
- 资源使用效率测试
"""

import asyncio
import logging
import time
import psutil
import statistics
from datetime import datetime
from typing import Dict, Any, List
import json
import matplotlib.pyplot as plt
import numpy as np

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


class BenchmarkRunner:
    """基准测试运行器"""
    
    def __init__(self, integrator: SystemIntegrator):
        self.integrator = integrator
        self.results = {}
        
    async def run_single_task_benchmark(self, iterations: int = 50) -> Dict[str, Any]:
        """单任务处理基准测试"""
        print(f"\n📊 单任务处理基准测试 - {iterations} 次迭代")
        
        response_times = []
        cpu_usage = []
        memory_usage = []
        
        for i in range(iterations):
            # 监控系统资源
            cpu_before = psutil.cpu_percent()
            memory_before = psutil.virtual_memory().percent
            
            # 执行单个任务
            start_time = time.time()
            
            try:
                task_data = {
                    "task_id": f"benchmark_single_{i}",
                    "title": f"基准测试任务 {i}",
                    "description": "单任务性能基准测试",
                    "requirements": ["处理输入", "生成输出"]
                }
                
                workflow_id = f"benchmark_workflow_{i}"
                await self.integrator.create_workflow(workflow_id, "simple")
                result = await self.integrator.execute_workflow(workflow_id, task_data)
                
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                # 监控资源使用
                cpu_after = psutil.cpu_percent()
                memory_after = psutil.virtual_memory().percent
                
                cpu_usage.append(max(cpu_after - cpu_before, 0))
                memory_usage.append(max(memory_after - memory_before, 0))
                
            except Exception as e:
                logger.error(f"基准测试任务 {i} 失败: {e}")
                response_times.append(float('inf'))
            
            # 显示进度
            if (i + 1) % 10 == 0:
                print(f"   进度: {i + 1}/{iterations}")
        
        # 过滤无效结果
        valid_times = [t for t in response_times if t != float('inf')]
        
        if not valid_times:
            return {"error": "所有测试都失败了"}
        
        result = {
            "iterations": iterations,
            "successful": len(valid_times),
            "failed": iterations - len(valid_times),
            "response_time": {
                "min": min(valid_times),
                "max": max(valid_times),
                "avg": statistics.mean(valid_times),
                "median": statistics.median(valid_times),
                "std": statistics.stdev(valid_times) if len(valid_times) > 1 else 0,
                "p95": statistics.quantiles(valid_times, n=20)[18] if len(valid_times) >= 20 else max(valid_times),
                "p99": statistics.quantiles(valid_times, n=100)[98] if len(valid_times) >= 100 else max(valid_times)
            },
            "resource_usage": {
                "avg_cpu_delta": statistics.mean(cpu_usage) if cpu_usage else 0,
                "avg_memory_delta": statistics.mean(memory_usage) if memory_usage else 0
            }
        }
        
        print(f"✅ 单任务基准测试完成")
        print(f"   平均响应时间: {result['response_time']['avg']:.3f} 秒")
        print(f"   P95响应时间: {result['response_time']['p95']:.3f} 秒")
        print(f"   成功率: {result['successful']/iterations:.2%}")
        
        return result
    
    async def run_batch_processing_benchmark(self, batch_sizes: List[int] = [1, 5, 10, 20, 50]) -> Dict[str, Any]:
        """批量处理基准测试"""
        print(f"\n📦 批量处理基准测试 - 批次大小: {batch_sizes}")
        
        batch_results = {}
        
        for batch_size in batch_sizes:
            print(f"   测试批次大小: {batch_size}")
            
            start_time = time.time()
            
            # 创建批量任务
            tasks = []
            for i in range(batch_size):
                task_data = {
                    "task_id": f"batch_{batch_size}_{i}",
                    "title": f"批量任务 {i}",
                    "description": f"批次大小 {batch_size} 的任务 {i}",
                    "requirements": ["批量处理", "并发执行"]
                }
                tasks.append(task_data)
            
            # 并发执行批量任务
            successful = 0
            failed = 0
            
            async def execute_task(task_data):
                try:
                    workflow_id = f"batch_workflow_{task_data['task_id']}"
                    await self.integrator.create_workflow(workflow_id, "simple")
                    result = await self.integrator.execute_workflow(workflow_id, task_data)
                    return True
                except Exception as e:
                    logger.error(f"批量任务失败: {e}")
                    return False
            
            results = await asyncio.gather(*[execute_task(task) for task in tasks], return_exceptions=True)
            
            successful = sum(1 for r in results if r is True)
            failed = len(results) - successful
            
            total_time = time.time() - start_time
            throughput = batch_size / total_time if total_time > 0 else 0
            
            batch_results[batch_size] = {
                "batch_size": batch_size,
                "total_time": total_time,
                "successful": successful,
                "failed": failed,
                "throughput": throughput,
                "avg_time_per_task": total_time / batch_size if batch_size > 0 else 0
            }
            
            print(f"     完成时间: {total_time:.2f} 秒")
            print(f"     吞吐量: {throughput:.2f} 任务/秒")
            print(f"     成功率: {successful/batch_size:.2%}")
        
        print(f"✅ 批量处理基准测试完成")
        
        return batch_results
    
    async def run_workflow_template_comparison(self) -> Dict[str, Any]:
        """工作流模板性能对比"""
        print(f"\n🔄 工作流模板性能对比")
        
        templates = ["simple", "analysis", "complex", "parallel"]
        template_results = {}
        
        for template in templates:
            print(f"   测试模板: {template}")
            
            response_times = []
            
            # 每个模板测试10次
            for i in range(10):
                try:
                    task_data = {
                        "task_id": f"template_test_{template}_{i}",
                        "title": f"模板测试 {template} {i}",
                        "description": f"测试 {template} 模板性能",
                        "requirements": ["模板处理", "性能测试"]
                    }
                    
                    start_time = time.time()
                    
                    workflow_id = f"template_workflow_{template}_{i}"
                    await self.integrator.create_workflow(workflow_id, template)
                    result = await self.integrator.execute_workflow(workflow_id, task_data)
                    
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                    
                except Exception as e:
                    logger.error(f"模板 {template} 测试 {i} 失败: {e}")
                    response_times.append(float('inf'))
            
            # 过滤无效结果
            valid_times = [t for t in response_times if t != float('inf')]
            
            if valid_times:
                template_results[template] = {
                    "template": template,
                    "iterations": 10,
                    "successful": len(valid_times),
                    "avg_response_time": statistics.mean(valid_times),
                    "min_response_time": min(valid_times),
                    "max_response_time": max(valid_times),
                    "success_rate": len(valid_times) / 10
                }
                
                print(f"     平均响应时间: {template_results[template]['avg_response_time']:.3f} 秒")
                print(f"     成功率: {template_results[template]['success_rate']:.2%}")
            else:
                template_results[template] = {
                    "template": template,
                    "error": "所有测试都失败了"
                }
        
        print(f"✅ 工作流模板对比完成")
        
        return template_results
    
    async def run_cache_performance_test(self, cache_sizes: List[int] = [100, 500, 1000, 5000]) -> Dict[str, Any]:
        """缓存性能测试"""
        print(f"\n💾 缓存性能测试 - 缓存大小: {cache_sizes}")
        
        cache_results = {}
        
        # 获取缓存管理器
        cache_manager = self.integrator.get_cache_manager()
        if not cache_manager:
            return {"error": "缓存管理器不可用"}
        
        for cache_size in cache_sizes:
            print(f"   测试缓存大小: {cache_size}")
            
            # 清空缓存
            cache_manager.clear_cache()
            
            # 预热缓存
            cache_data = {}
            for i in range(cache_size):
                key = f"cache_key_{i}"
                value = f"cache_value_{i}" * 10  # 增加数据大小
                cache_data[key] = value
            
            # 测试缓存写入性能
            write_start = time.time()
            for key, value in cache_data.items():
                cache_manager.set(key, value)
            write_time = time.time() - write_start
            
            # 测试缓存读取性能
            read_start = time.time()
            hit_count = 0
            for key in cache_data.keys():
                if cache_manager.get(key) is not None:
                    hit_count += 1
            read_time = time.time() - read_start
            
            hit_rate = hit_count / cache_size if cache_size > 0 else 0
            
            cache_results[cache_size] = {
                "cache_size": cache_size,
                "write_time": write_time,
                "read_time": read_time,
                "write_ops_per_sec": cache_size / write_time if write_time > 0 else 0,
                "read_ops_per_sec": cache_size / read_time if read_time > 0 else 0,
                "hit_rate": hit_rate
            }
            
            print(f"     写入速度: {cache_results[cache_size]['write_ops_per_sec']:.0f} ops/sec")
            print(f"     读取速度: {cache_results[cache_size]['read_ops_per_sec']:.0f} ops/sec")
            print(f"     命中率: {hit_rate:.2%}")
        
        print(f"✅ 缓存性能测试完成")
        
        return cache_results
    
    async def run_resource_efficiency_test(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """资源使用效率测试"""
        print(f"\n⚡ 资源使用效率测试 - 持续 {duration_seconds} 秒")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        task_count = 0
        cpu_samples = []
        memory_samples = []
        
        while time.time() < end_time:
            # 执行任务
            try:
                task_data = {
                    "task_id": f"efficiency_test_{task_count}",
                    "title": f"效率测试任务 {task_count}",
                    "description": "资源效率测试任务",
                    "requirements": ["资源监控", "效率测试"]
                }
                
                workflow_id = f"efficiency_workflow_{task_count}"
                await self.integrator.create_workflow(workflow_id, "simple")
                result = await self.integrator.execute_workflow(workflow_id, task_data)
                
                task_count += 1
                
            except Exception as e:
                logger.error(f"效率测试任务失败: {e}")
            
            # 采样系统资源
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            
            cpu_samples.append(cpu_percent)
            memory_samples.append(memory_percent)
            
            # 短暂休息
            await asyncio.sleep(0.1)
        
        total_time = time.time() - start_time
        
        result = {
            "test_duration": total_time,
            "tasks_completed": task_count,
            "tasks_per_second": task_count / total_time if total_time > 0 else 0,
            "resource_usage": {
                "avg_cpu": statistics.mean(cpu_samples) if cpu_samples else 0,
                "max_cpu": max(cpu_samples) if cpu_samples else 0,
                "avg_memory": statistics.mean(memory_samples) if memory_samples else 0,
                "max_memory": max(memory_samples) if memory_samples else 0
            },
            "efficiency_score": task_count / (statistics.mean(cpu_samples) + statistics.mean(memory_samples)) if cpu_samples and memory_samples else 0
        }
        
        print(f"✅ 资源效率测试完成")
        print(f"   完成任务: {task_count} 个")
        print(f"   任务速率: {result['tasks_per_second']:.2f} 任务/秒")
        print(f"   平均CPU使用: {result['resource_usage']['avg_cpu']:.1f}%")
        print(f"   平均内存使用: {result['resource_usage']['avg_memory']:.1f}%")
        print(f"   效率分数: {result['efficiency_score']:.2f}")
        
        return result


async def run_comprehensive_benchmark():
    """运行综合基准测试"""
    
    print("=" * 80)
    print("LangGraph多智能体系统 - 性能基准测试")
    print("=" * 80)
    
    # 初始化系统
    print("\n🚀 初始化基准测试系统...")
    
    config = {
        "checkpoint_storage": "memory",
        "enable_metrics": True,
        "enable_tracing": False,
        "optimization_level": "moderate",
        "performance": {
            "max_cache_size": 10000,
            "enable_auto_optimization": False,  # 关闭自动优化以获得一致的基准
            "max_workers": 4,
            "execution_mode": "adaptive"
        }
    }
    
    integrator = SystemIntegrator(config)
    
    try:
        success = await integrator.initialize_system()
        if not success:
            print("❌ 系统初始化失败")
            return
        
        print("✅ 基准测试系统初始化成功")
        
        # 创建基准测试运行器
        benchmark_runner = BenchmarkRunner(integrator)
        
        # 收集所有基准测试结果
        all_results = {}
        
        # 1. 单任务处理基准
        print("\n" + "="*60)
        print("基准测试 1/5: 单任务处理性能")
        print("="*60)
        
        single_task_result = await benchmark_runner.run_single_task_benchmark(iterations=100)
        all_results["single_task"] = single_task_result
        
        # 2. 批量处理基准
        print("\n" + "="*60)
        print("基准测试 2/5: 批量处理性能")
        print("="*60)
        
        batch_result = await benchmark_runner.run_batch_processing_benchmark()
        all_results["batch_processing"] = batch_result
        
        # 3. 工作流模板对比
        print("\n" + "="*60)
        print("基准测试 3/5: 工作流模板性能对比")
        print("="*60)
        
        template_result = await benchmark_runner.run_workflow_template_comparison()
        all_results["workflow_templates"] = template_result
        
        # 4. 缓存性能测试
        print("\n" + "="*60)
        print("基准测试 4/5: 缓存性能")
        print("="*60)
        
        cache_result = await benchmark_runner.run_cache_performance_test()
        all_results["cache_performance"] = cache_result
        
        # 5. 资源效率测试
        print("\n" + "="*60)
        print("基准测试 5/5: 资源使用效率")
        print("="*60)
        
        efficiency_result = await benchmark_runner.run_resource_efficiency_test(duration_seconds=30)
        all_results["resource_efficiency"] = efficiency_result
        
        # 生成基准报告
        print("\n" + "="*80)
        print("基准测试报告")
        print("="*80)
        
        generate_benchmark_report(all_results)
        
        # 生成性能图表
        try:
            generate_performance_charts(all_results)
        except Exception as e:
            print(f"⚠️  生成图表失败: {e}")
        
    except Exception as e:
        print(f"❌ 基准测试失败: {e}")
        logger.error(f"基准测试错误: {e}")
    
    finally:
        # 清理资源
        print("\n🧹 清理测试资源...")
        try:
            await integrator.shutdown_system()
            print("✅ 系统关闭完成")
        except Exception as e:
            print(f"⚠️  系统关闭时出现警告: {e}")
    
    print("\n" + "="*80)
    print("性能基准测试完成")
    print("="*80)


def generate_benchmark_report(results: Dict[str, Any]):
    """生成基准测试报告"""
    
    print("\n📊 基准测试结果摘要:")
    print("-" * 70)
    
    # 单任务性能
    if "single_task" in results and "error" not in results["single_task"]:
        single = results["single_task"]
        print(f"单任务处理性能:")
        print(f"  • 平均响应时间: {single['response_time']['avg']:.3f} 秒")
        print(f"  • P95响应时间: {single['response_time']['p95']:.3f} 秒")
        print(f"  • P99响应时间: {single['response_time']['p99']:.3f} 秒")
        print(f"  • 成功率: {single['successful']/single['iterations']:.2%}")
    
    # 批量处理性能
    if "batch_processing" in results:
        batch = results["batch_processing"]
        print(f"\n批量处理性能:")
        for batch_size, result in batch.items():
            if isinstance(result, dict):
                print(f"  • 批次大小 {batch_size}: {result['throughput']:.2f} 任务/秒")
    
    # 工作流模板对比
    if "workflow_templates" in results:
        templates = results["workflow_templates"]
        print(f"\n工作流模板性能对比:")
        for template, result in templates.items():
            if isinstance(result, dict) and "error" not in result:
                print(f"  • {template}: {result['avg_response_time']:.3f} 秒 (成功率: {result['success_rate']:.2%})")
    
    # 缓存性能
    if "cache_performance" in results and "error" not in results["cache_performance"]:
        cache = results["cache_performance"]
        print(f"\n缓存性能:")
        for cache_size, result in cache.items():
            if isinstance(result, dict):
                print(f"  • 大小 {cache_size}: 读取 {result['read_ops_per_sec']:.0f} ops/sec, "
                      f"写入 {result['write_ops_per_sec']:.0f} ops/sec")
    
    # 资源效率
    if "resource_efficiency" in results and "error" not in results["resource_efficiency"]:
        efficiency = results["resource_efficiency"]
        print(f"\n资源使用效率:")
        print(f"  • 任务处理速率: {efficiency['tasks_per_second']:.2f} 任务/秒")
        print(f"  • 平均CPU使用: {efficiency['resource_usage']['avg_cpu']:.1f}%")
        print(f"  • 平均内存使用: {efficiency['resource_usage']['avg_memory']:.1f}%")
        print(f"  • 效率分数: {efficiency['efficiency_score']:.2f}")
    
    # 保存详细报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"benchmark_report_{timestamp}.json"
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)
        print(f"\n📄 详细基准报告已保存到: {report_file}")
    except Exception as e:
        print(f"⚠️  保存报告失败: {e}")


def generate_performance_charts(results: Dict[str, Any]):
    """生成性能图表"""
    
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('LangGraph多智能体系统性能基准测试', fontsize=16)
        
        # 1. 批量处理吞吐量图表
        if "batch_processing" in results:
            batch = results["batch_processing"]
            batch_sizes = []
            throughputs = []
            
            for batch_size, result in batch.items():
                if isinstance(result, dict):
                    batch_sizes.append(batch_size)
                    throughputs.append(result['throughput'])
            
            if batch_sizes:
                axes[0, 0].plot(batch_sizes, throughputs, 'b-o')
                axes[0, 0].set_title('批量处理吞吐量')
                axes[0, 0].set_xlabel('批次大小')
                axes[0, 0].set_ylabel('吞吐量 (任务/秒)')
                axes[0, 0].grid(True)
        
        # 2. 工作流模板响应时间对比
        if "workflow_templates" in results:
            templates = results["workflow_templates"]
            template_names = []
            response_times = []
            
            for template, result in templates.items():
                if isinstance(result, dict) and "error" not in result:
                    template_names.append(template)
                    response_times.append(result['avg_response_time'])
            
            if template_names:
                axes[0, 1].bar(template_names, response_times)
                axes[0, 1].set_title('工作流模板响应时间对比')
                axes[0, 1].set_xlabel('模板类型')
                axes[0, 1].set_ylabel('平均响应时间 (秒)')
                axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 3. 缓存性能图表
        if "cache_performance" in results and "error" not in results["cache_performance"]:
            cache = results["cache_performance"]
            cache_sizes = []
            read_speeds = []
            write_speeds = []
            
            for cache_size, result in cache.items():
                if isinstance(result, dict):
                    cache_sizes.append(cache_size)
                    read_speeds.append(result['read_ops_per_sec'])
                    write_speeds.append(result['write_ops_per_sec'])
            
            if cache_sizes:
                axes[1, 0].plot(cache_sizes, read_speeds, 'g-o', label='读取')
                axes[1, 0].plot(cache_sizes, write_speeds, 'r-o', label='写入')
                axes[1, 0].set_title('缓存性能')
                axes[1, 0].set_xlabel('缓存大小')
                axes[1, 0].set_ylabel('操作速度 (ops/sec)')
                axes[1, 0].legend()
                axes[1, 0].grid(True)
        
        # 4. 单任务响应时间分布
        if "single_task" in results and "error" not in results["single_task"]:
            single = results["single_task"]
            response_time_data = [
                single['response_time']['min'],
                single['response_time']['median'],
                single['response_time']['avg'],
                single['response_time']['p95'],
                single['response_time']['p99'],
                single['response_time']['max']
            ]
            labels = ['最小值', '中位数', '平均值', 'P95', 'P99', '最大值']
            
            axes[1, 1].bar(labels, response_time_data)
            axes[1, 1].set_title('单任务响应时间分布')
            axes[1, 1].set_xlabel('统计指标')
            axes[1, 1].set_ylabel('响应时间 (秒)')
            axes[1, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # 保存图表
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_file = f"benchmark_charts_{timestamp}.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        
        print(f"📈 性能图表已保存到: {chart_file}")
        
        # 显示图表（如果在交互环境中）
        # plt.show()
        
    except ImportError:
        print("⚠️  matplotlib 未安装，跳过图表生成")
    except Exception as e:
        print(f"⚠️  生成图表失败: {e}")


def main():
    """主函数"""
    try:
        asyncio.run(run_comprehensive_benchmark())
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"基准测试程序执行失败: {e}")
        logger.error(f"主程序错误: {e}")


if __name__ == "__main__":
    main()